# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_fullname, get_link_to_form, getdate, nowdate
from frappe.utils.nestedset import get_ancestors_of

from ifitwala_ed.schedule.schedule_utils import get_school_term_bounds
from ifitwala_ed.utilities.school_tree import ParentRuleViolation, get_descendant_schools, get_effective_record

ADMIN_ENROLLMENT_ROLES = {"Academic Admin", "Curriculum Coordinator", "Admission Manager"}
MIGRATION_ROLES = {"System Manager"}
ALLOWED_SOURCES = {"Request", "Admin", "Migration"}


def _user_has_any_role(roles: set[str]) -> bool:
    return bool(set(frappe.get_roles(frappe.session.user)) & roles)


class ProgramEnrollment(Document):
    def before_insert(self):
        # Canonical spine sync + optional seeding of required courses
        self._apply_offering_spine(allow_seed_courses=True)

    def validate(self):
        """
        Validate invariants only.
        Spine resolution is handled in before_insert() / _apply_offering_spine().
        """

        # 0) Hard requirements
        if not self.program_offering:
            frappe.throw(_("Program Offering is required."))
        if not self.student:
            frappe.throw(_("Student is required."))

        # 1) Load offering spine ONCE
        off = _offering_core(self.program_offering)
        if not off:
            frappe.throw(
                _("Invalid Program Offering {0}.").format(get_link_to_form("Program Offering", self.program_offering))
            )

        # 2) Program / school / cohort must already match offering (never reassign here)
        if self.program != off.program:
            frappe.throw(
                _("Enrollment Program {0} does not match Program Offering's Program {1}.").format(
                    get_link_to_form("Program", self.program),
                    get_link_to_form("Program", off.program),
                )
            )

        if self.school != off.school:
            frappe.throw(_("Enrollment School does not match Program Offering School."))

        if off.student_cohort and self.cohort != off.student_cohort:
            frappe.throw(_("Enrollment Cohort does not match Program Offering Cohort."))

        # 3) Academic Year must be valid for offering
        ay_names = _offering_ay_names(self.program_offering)
        if not self.academic_year:
            frappe.throw(_("Academic Year is required."))
        if self.academic_year not in ay_names:
            frappe.throw(
                _("Academic Year {0} is not part of Program Offering {1}.").format(
                    get_link_to_form("Academic Year", self.academic_year),
                    get_link_to_form("Program Offering", self.program_offering),
                )
            )

        # 4) Structural invariants (no mutation)
        self._validate_school_and_cohort_lock()
        self._validate_terms_membership_and_order()
        self._validate_dropped_requires_date()
        self._validate_enrollment_source()
        self._validate_course_terms()

        # 5) Duplication guards
        self.validate_duplicate_course()
        self.validate_duplication()

        # 6) Enrollment date must fall inside academic year
        if self.enrollment_date:
            ay = frappe.get_doc("Academic Year", self.academic_year)
            if getdate(self.enrollment_date) < getdate(ay.year_start_date):
                frappe.throw(
                    _("Enrollment date is before the start of Academic Year {0}.").format(
                        get_link_to_form("Academic Year", self.academic_year)
                    )
                )
            if getdate(self.enrollment_date) > getdate(ay.year_end_date):
                frappe.throw(
                    _("Enrollment date is after the end of Academic Year {0}.").format(
                        get_link_to_form("Academic Year", self.academic_year)
                    )
                )

        # 7) Cosmetic only (safe autofill)
        if not self.student_name:
            self.student_name = frappe.db.get_value("Student", self.student, "student_full_name")

    def _apply_offering_spine(self, *, allow_seed_courses: bool):
        """
        Canonical spine sync (single truth):
        - Require + load Program Offering once
        - Mirror authoritative values: program, school, cohort
        - Validate/assign academic_year from offering AY spine
        - Resolve academic_year via school-tree guard
        - Optionally seed required courses when empty
        - Fill student_name when missing
        """
        # 0) Require + load offering
        if not getattr(self, "program_offering", None):
            frappe.throw(_("Program Offering is required."))

        off = _offering_core(self.program_offering)
        if not off:
            frappe.throw(
                _("Invalid Program Offering {0}.").format(get_link_to_form("Program Offering", self.program_offering))
            )

        # 1) Mirror authoritative values
        # Program must match offering program
        if not self.program:
            self.program = off.get("program")
        elif self.program != off.get("program"):
            frappe.throw(
                _("Enrollment Program {0} does not match Program Offering's Program {1}.").format(
                    get_link_to_form("Program", self.program), get_link_to_form("Program", off.get("program"))
                )
            )

        # School/cohort always mirror offering
        self.school = off.get("school")
        if off.get("student_cohort"):
            self.cohort = off.get("student_cohort")

        # 2) Academic Year must come from offering AY spine (autofill when unique)
        ay_names = _offering_ay_names(self.program_offering)
        if self.academic_year:
            if self.academic_year not in ay_names:
                frappe.throw(
                    _("Academic Year {0} is not part of Program Offering {1}.").format(
                        get_link_to_form("Academic Year", self.academic_year),
                        get_link_to_form("Program Offering", self.program_offering),
                    )
                )
        else:
            if len(ay_names) == 1:
                self.academic_year = ay_names[0]
            else:
                frappe.throw(
                    _("Please choose an Academic Year from this Program Offering: {0}.").format(", ".join(ay_names))
                )

        # 3) Resolve AY via school tree guard
        self._resolve_academic_year()

        # 4) Seed required courses if empty (same behavior you had)
        if allow_seed_courses and not self.courses:
            self.extend("courses", self.get_courses())

        # 5) Student name (only if missing)
        if not self.student_name and self.student:
            self.student_name = frappe.db.get_value("Student", self.student, "student_full_name")

    def _validate_enrollment_source(self):
        source = (self.enrollment_source or "Admin").strip()
        if source not in ALLOWED_SOURCES:
            frappe.throw(_("Enrollment Source must be one of: {0}.").format(", ".join(sorted(ALLOWED_SOURCES))))
        self.enrollment_source = source

        previous_source = None
        if self.name and not self.is_new():
            previous = (
                frappe.db.get_value(
                    "Program Enrollment",
                    self.name,
                    ["enrollment_source", "program_enrollment_request"],
                    as_dict=True,
                )
                or {}
            )
            previous_source = (previous.get("enrollment_source") or "").strip() or None

            if previous_source and previous_source != source:
                frappe.throw(_("Enrollment Source cannot be changed once set."))
            if previous_source == "Request" and not self.program_enrollment_request:
                frappe.throw(_("Program Enrollment Request cannot be cleared for Request-source enrollments."))

        if source == "Request":
            self._validate_request_source(previous_source)
            return

        self._validate_non_request_source(source)

    def _validate_request_source(self, previous_source):
        if not self.program_enrollment_request:
            frappe.throw(_("Program Enrollment Request is required when source is Request."))

        if self.is_new() or (previous_source and previous_source != "Request"):
            if not getattr(frappe.flags, "enrollment_from_request", False):
                frappe.throw(_("Create enrollments from an approved request via the conversion action."))

        req = frappe.get_doc("Program Enrollment Request", self.program_enrollment_request)
        if req.status != "Approved":
            frappe.throw(_("Program Enrollment Request must be Approved to materialize enrollment."))
        if req.student != self.student:
            frappe.throw(_("Program Enrollment Request student does not match enrollment student."))
        if req.program_offering != self.program_offering:
            frappe.throw(_("Program Enrollment Request offering does not match enrollment offering."))
        if req.academic_year != self.academic_year:
            frappe.throw(_("Program Enrollment Request academic year does not match enrollment academic year."))
        if self.program and req.program and req.program != self.program:
            frappe.throw(_("Program Enrollment Request program does not match enrollment program."))
        if self.school and req.school and req.school != self.school:
            frappe.throw(_("Program Enrollment Request school does not match enrollment school."))

    def _validate_non_request_source(self, source):
        if not (self.enrollment_override_reason or "").strip():
            frappe.throw(_("Override Reason is required when enrollment source is not Request."))

        if source == "Admin":
            if not _user_has_any_role(ADMIN_ENROLLMENT_ROLES):
                frappe.throw(
                    _("Only Academic Admin, Curriculum Coordinator, or Admission Manager can create Admin enrollments.")
                )
        elif source == "Migration":
            if not _user_has_any_role(MIGRATION_ROLES):
                frappe.throw(_("Only System Manager can create Migration enrollments."))

    def before_save(self):
        # A) Only one active enrollment per student (if not archived)
        self.validate_only_one_active_enrollment()

        # B) Traceability: convert deletions to Dropped (Option B)
        if not self.is_new():
            prior = self._db_course_rows()
            now_set = self._current_course_set()
            removed = [prior[c] for c in (set(prior.keys()) - now_set)]
            self._soft_convert_deletions_to_dropped(removed)

    def on_update(self):
        self.update_student_joining_date()

    def on_trash(self):
        # when deleting an enrollment, recompute from remaining rows
        self.update_student_joining_date()

    def _resolve_academic_year(self):
        allowed_schools = [self.school] + get_ancestors_of("School", self.school)

        # 1 ▸ autofill if left blank
        if not self.academic_year:
            self.academic_year = get_effective_record(
                "Academic Year",
                self.school,
                extra_filters={"archived": 0},
            )
            if not self.academic_year:
                raise ParentRuleViolation(
                    _("No active Academic Year found for {0} or its ancestors.").format(self.school)
                )
            return

        # 2 ▸ validate manual pick
        ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school")
        if ay_school not in allowed_schools:
            raise ParentRuleViolation(
                _("Academic Year {0} belongs to {1}, which is outside the allowed hierarchy.").format(
                    self.academic_year, ay_school
                )
            )

    def validate_only_one_active_enrollment(self):
        """
        Checks if there's another active (archived=0) Program Enrollment for the same student.
        Raises an error if another active enrollment is found.
        """
        if self.archived:
            return  # if archived is checked.

        existing_enrollment = frappe.db.get_value(
            "Program Enrollment",
            {
                "student": self.student,
                "archived": 0,  # Check for active enrollments
                "name": ("!=", self.name),  # Exclude the current document
            },
            ["name", "program", "academic_year"],  # Retrieve name, program and year for the error message
            as_dict=True,
        )

        if existing_enrollment:
            frappe.throw(
                _(
                    "Student {0} already has an active Program Enrollment for program {1} in academic year {2}.  See {3}."
                ).format(
                    self.student_name,
                    get_link_to_form("Program", existing_enrollment.program),
                    existing_enrollment.academic_year,
                    get_link_to_form("Program Enrollment", existing_enrollment.name),
                ),
                title=_("Active Enrollment Exists"),  # added for better UI message.
            )

    def validate_duplicate_course(self):
        """ensure courses belong to Program Offering Course spans; prevent duplicates."""
        seen_courses = set()
        off_idx = _offering_courses_index(self.program_offering)

        for row in self.courses:
            # duplicate
            if row.course in seen_courses:
                frappe.throw(_("Course {0} entered twice.").format(get_link_to_form("Course", row.course)))
            seen_courses.add(row.course)

            # existence in offering
            if row.course not in off_idx:
                frappe.throw(
                    _("Course {0} is not part of Program Offering {1}.").format(
                        get_link_to_form("Course", row.course),
                        get_link_to_form("Program Offering", self.program_offering),
                    )
                )

            # compute enrollment window within chosen AY (narrow by terms if provided)
            enr_ay_start, enr_ay_end = _ay_bounds_for(self.program_offering, self.academic_year)
            enr_start, enr_end = enr_ay_start, enr_ay_end
            if row.term_start:
                _school_1, _ay_1, ts_start, _term_end_ignored = _term_meta(row.term_start)
                if ts_start:
                    enr_start = max(enr_start, getdate(ts_start))
            if row.term_end:
                _school_2, _ay_2, te_start, te_end = _term_meta(row.term_end)
                if te_end or te_start:
                    enr_end = min(enr_end, getdate(te_end) if te_end else getdate(te_start))

            if enr_start and enr_end and enr_start > enr_end:
                frappe.throw(
                    _("For course <b>{0}</b>: The start term window is after the end term window.").format(
                        row.course or ""
                    )
                )

            # require overlap with at least one offering span
            ok = any((enr_start <= span["end"]) and (span["start"] <= enr_end) for span in off_idx[row.course])
            if not ok:
                frappe.throw(
                    _(
                        "Course {0} is not delivered during the selected Academic Year/Term window for this Program Offering."
                    ).format(get_link_to_form("Course", row.course))
                )

    # you cannot enroll twice for the same offering and year
    def validate_duplication(self):
        existing_enrollment_name = frappe.db.exists(
            "Program Enrollment",
            {
                "student": self.student,
                "program_offering": self.program_offering,
                "academic_year": self.academic_year,
                "name": ("!=", self.name),
            },
        )
        if existing_enrollment_name:
            student_name = self.student_name or frappe.db.get_value("student", self.student, "student_name")
            link_to_existing_enrollment = get_link_to_form("Program Enrollment", existing_enrollment_name)
            frappe.throw(
                _("Student {0} is already enrolled in this Program Offering for this academic year. See {1}").format(
                    student_name, link_to_existing_enrollment
                )
            )

    def _validate_offering_ay_membership(self):
        """Enrollment AY must belong to the Program Offering spine."""
        if not (self.program_offering and self.academic_year):
            return
        ay_names = _offering_ay_names(self.program_offering)
        if self.academic_year not in ay_names:
            frappe.throw(
                _("Academic Year {0} is not part of Program Offering {1}.").format(
                    get_link_to_form("Academic Year", self.academic_year),
                    get_link_to_form("Program Offering", self.program_offering),
                )
            )

    def _validate_terms_membership_and_order(self):
        """Hard guards on each row's term selection:
        - Term order: end >= start (when both are set and have dates)
        - Term membership: each term's AY must be allowed (enrollment AY and/or offering spine)
        """
        if not getattr(self, "courses", None):
            return

        # Build the allowed AY set
        allowed_ays = set()
        if self.academic_year:
            allowed_ays.add(self.academic_year)
        # Include all AYs from the offering spine
        allowed_ays.update(_offering_ay_names(self.program_offering) or [])

        # Batch-fetch term metadata
        term_names = {r.term_start for r in self.courses if r.term_start} | {
            r.term_end for r in self.courses if r.term_end
        }
        meta = _term_meta_many(term_names)

        # Collect violations for a single, crisp error
        membership_violations = []  # [(course, fld_name, term_name, term_ay)]
        order_violations = []  # [(course, term_start, start_date, term_end, end_date)]

        for r in self.courses:
            ts = r.term_start and meta.get(r.term_start) or None
            te = r.term_end and meta.get(r.term_end) or None

            # Membership checks
            if ts and ts.academic_year and allowed_ays and ts.academic_year not in allowed_ays:
                membership_violations.append((r.course, "term_start", r.term_start, ts.academic_year))
            if te and te.academic_year and allowed_ays and te.academic_year not in allowed_ays:
                membership_violations.append((r.course, "term_end", r.term_end, te.academic_year))

            # Order check (only if both dates exist)
            if ts and te and ts.term_start_date and te.term_end_date:
                if te.term_end_date < ts.term_start_date:
                    order_violations.append((r.course, r.term_start, ts.term_start_date, r.term_end, te.term_end_date))

        # Throw with consolidated messages (if any)
        err_lines = []
        if membership_violations:
            err_lines.append("<b>Terms must belong to the selected Academic Year or the Program Offering span:</b>")
            for course, fld, term, term_ay in membership_violations:
                err_lines.append(f"• {frappe.bold(course or '')} — {frappe.bold(fld)} = {term} (AY {term_ay})")

        if order_violations:
            if err_lines:
                err_lines.append("")  # blank line between sections
            err_lines.append("<b>Term order invalid (End before Start):</b>")
            for course, tstart, dstart, tend, dend in order_violations:
                err_lines.append(f"• {frappe.bold(course or '')} — {tstart} ({dstart}) → {tend} ({dend})")

        if err_lines:
            frappe.throw("<br>".join(err_lines))

    def _validate_school_and_cohort_lock(self):
        if not self.program_offering:
            return
        off = _offering_core(self.program_offering)
        if not off:
            # earlier validate() already checks, but keep this idempotent
            return
        if off.get("school") and self.school and self.school != off["school"]:
            frappe.throw(_("School must match Program Offering ({0}).").format(off["school"]))
        target_cohort = off.get("student_cohort")
        if target_cohort and self.cohort and self.cohort != target_cohort:
            frappe.throw(_("Cohort must match Program Offering ({0}).").format(target_cohort))

    def _validate_dropped_requires_date(self):
        missing = [r.course for r in (self.courses or []) if r.status == "Dropped" and not r.dropped_date]
        if missing:
            lines = "<br>".join(f"• {frappe.bold(c or '')}" for c in missing)
            frappe.throw(_("Dropped courses require a Dropped Date:<br>{0}").format(lines))

        # require reason
        missing_reason = [
            r.course for r in (self.courses or []) if r.status == "Dropped" and not (r.dropped_reason or "").strip()
        ]
        if missing_reason:
            lines = "<br>".join(f"• {frappe.bold(c or '')}" for c in missing_reason)
            frappe.msgprint(_("Think about adding a Dropped Reason:<br>{0}").format(lines))

    # If a student is in a program offering and that offering has required courses,
    # load those that overlap the chosen Academic Year (AY).
    @frappe.whitelist()
    def get_courses(self):
        # Defensive: require offering + AY
        if not (self.program_offering and self.academic_year):
            return []

        # Bounds for the selected AY slice within the offering
        enr_ay_start, enr_ay_end = _ay_bounds_for(self.program_offering, self.academic_year)
        if not (enr_ay_start and enr_ay_end):
            return []

        # Build an index of offering courses with effective spans
        off_idx = _offering_courses_index(self.program_offering)

        rows = []
        # Include only REQUIRED courses that overlap the enrollment AY
        for course, spans in off_idx.items():
            if not any(span.get("required") for span in spans):
                continue
            # Does any span overlap the AY window?
            has_overlap = any((enr_ay_start <= s["end"]) and (s["start"] <= enr_ay_end) for s in spans)
            if not has_overlap:
                continue

            item = {"course": course, "status": "Enrolled"}

            # Optional, same behavior you had: if course doesn’t declare long-term bounds,
            # default term_start/term_end to the school’s AY term bounds for convenience.
            bounds = None
            if self.school:
                bounds = get_school_term_bounds(self.school, self.academic_year)

            term_long = frappe.db.get_value("Course", course, "term_long")
            if not term_long and bounds:
                item["term_start"] = bounds.get("term_start")
                item["term_end"] = bounds.get("term_end")

            rows.append(item)

        return rows

    # This will update the joining date on the student doctype in function of the joining date of the program.
    def update_student_joining_date(self):
        date = frappe.db.sql(
            """select min(enrollment_date) from `tabProgram Enrollment` where student= %s""", self.student
        )
        if date and date[0] and date[0][0]:
            frappe.db.set_value("Student", self.student, "student_joining_date", date[0][0])

    # Ensure all courses use terms from one valid source: either the school or the fallback ancestor, and term_start <= term_end.
    def _validate_course_terms(self):
        valid_terms, source_school = get_terms_for_ay_with_fallback(self.school, self.academic_year)
        if not valid_terms:
            return  # No terms anywhere—let other validations handle this situation

        for row in self.courses:
            # Check valid terms
            if row.term_start and row.term_start not in valid_terms:
                frappe.throw(
                    _("Term Start '{0}' must be from {1} for Academic Year '{2}'.").format(
                        row.term_start, source_school, self.academic_year
                    ),
                    title=_("Invalid Term Start"),
                )
            if row.term_end and row.term_end not in valid_terms:
                frappe.throw(
                    _("Term End '{0}' must be from {1} for Academic Year '{2}'.").format(
                        row.term_end, source_school, self.academic_year
                    ),
                    title=_("Invalid Term End"),
                )

            # Check order: term_start <= term_end
            if row.term_start and row.term_end:
                if row.term_start == row.term_end:
                    continue  # ok if same
                term_start_doc = frappe.get_doc("Term", row.term_start)
                term_end_doc = frappe.get_doc("Term", row.term_end)
                if getdate(term_start_doc.term_start_date) > getdate(term_end_doc.term_start_date):
                    frappe.throw(
                        _(
                            "For course <b>{0}</b>: The start term <b>{1}</b> ({2}) must not be after the end term <b>{3}</b> ({4})."
                        ).format(
                            row.course or "",
                            row.term_start,
                            term_start_doc.term_start_date,
                            row.term_end,
                            term_end_doc.term_start_date,
                        ),
                        title=_("Invalid Term Sequence"),
                    )

    # --- Traceability helpers (soft-convert deletions to Dropped) ----------------

    def _db_course_rows(self) -> dict[str, dict]:
        """Snapshot of existing child rows in DB keyed by course (fast, cached)."""
        # Request-scope memoization to avoid repeated DB calls in the same save cycle
        cache_attr = "_cached_db_course_rows"
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)

        if not self.name:
            setattr(self, cache_attr, {})
            return {}

        # Single, tight SQL — faster than get_all for this hot path
        rows = frappe.db.sql(
            """
            SELECT
                course,
                status,
                term_start,
                term_end,
                dropped_date,
                dropped_reason,
                idx
            FROM `tabProgram Enrollment Course`
            WHERE parent = %s
                AND parenttype = 'Program Enrollment'
                AND IFNULL(course, '') != ''
            """,
            (self.name,),
            as_dict=True,
        )

        # Key by course; if duplicates exist, keep the one with the highest idx (latest)
        result: dict[str, dict] = {}
        for r in rows:
            c = r.get("course")
            if not c:
                continue
            if (c not in result) or (int(r.get("idx") or 0) > int(result[c].get("idx") or 0)):
                result[c] = r

        # We don’t need idx outside; drop to keep payload small/clean
        for v in result.values():
            v.pop("idx", None)

        setattr(self, cache_attr, result)
        return result

    def _current_course_set(self) -> set[str]:
        return {r.course for r in (self.courses or []) if getattr(r, "course", None)}

    def _soft_convert_deletions_to_dropped(self, removed: list[dict]):
        if not removed:
            return

        existing_now = self._current_course_set()
        added = 0
        user_full = get_fullname(frappe.session.user)
        user_id = frappe.session.user
        today = nowdate()

        for r in removed:
            course = r.get("course")
            if not course or course in existing_now:
                continue

            row = self.append("courses", {})
            row.course = course
            row.status = "Dropped"
            row.dropped_date = r.get("dropped_date") or today
            row.term_start = r.get("term_start")
            row.term_end = r.get("term_end")

            # NEW: preserve existing reason if any; else write an auto-reason
            prev_reason = (r.get("dropped_reason") or "").strip() if isinstance(r, dict) else ""
            row.dropped_reason = prev_reason or (
                f"Auto-dropped on {today} by {user_full} ({user_id}) — row deleted from grid"
            )
            added += 1

        if added:
            frappe.msgprint(
                _("Direct deletions were converted to 'Dropped' with a Dropped Date and Reason to preserve history."),
                indicator="blue",
                title=_("Enrollment Traceability"),
            )


# -------------------------
# Program Offering helpers
# -------------------------


def _offering_ay_names(offering: str) -> list[str]:
    """Ordered AY names from the offering child table (grid order)."""
    if not offering:
        return []
    return (
        frappe.get_all(
            "Program Offering Academic Year",
            filters={"parent": offering, "parenttype": "Program Offering"},
            pluck="academic_year",
            order_by="idx asc",
        )
        or []
    )


def _offering_core(offering_name: str) -> dict | None:
    """Return head fields of Program Offering (strict field names)."""
    if not offering_name:
        return None
    return frappe.db.get_value(
        "Program Offering",
        offering_name,
        ["program", "school", "student_cohort", "start_date", "end_date"],
        as_dict=True,
    )


def _offering_ay_spine(offering_name: str) -> list[dict]:
    """
    Return [{'academic_year', 'start', 'end'}...] using *real* bounds
    from the Academic Year doctype. Child rows only provide ordering (idx).
    """
    rows = frappe.get_all(
        "Program Offering Academic Year",
        filters={"parent": offering_name, "parenttype": "Program Offering"},
        fields=["academic_year", "idx"],
        order_by="idx asc",
    )
    if not rows:
        return []

    ay_names = [r["academic_year"] for r in rows if r.get("academic_year")]
    if not ay_names:
        return []

    # Batch fetch true AY bounds
    ay_meta = {
        r.name: r
        for r in frappe.get_all(
            "Academic Year",
            filters={"name": ("in", ay_names)},
            fields=["name", "year_start_date", "year_end_date"],
        )
    }

    out = []
    for r in rows:
        name = r.get("academic_year")
        if not name:
            continue
        meta = ay_meta.get(name)
        # Skip malformed AYs (don’t fabricate "today")
        if not meta or not (meta.year_start_date and meta.year_end_date):
            continue
        out.append(
            {
                "academic_year": name,
                "start": getdate(meta.year_start_date),
                "end": getdate(meta.year_end_date),
            }
        )
    return out


def _ay_bounds_for(offering_name: str, ay_name: str) -> tuple[object, object]:
    """(start,end) of an AY from the offering spine; avoids fetching the AY doc."""
    for r in _offering_ay_spine(offering_name):
        if r["academic_year"] == ay_name:
            return r["start"], r["end"]
    return (None, None)


def _term_meta(term: str) -> tuple[str | None, str | None, object | None, object | None]:
    """(school, academic_year, term_start_date, term_end_date) for Term."""
    return frappe.db.get_value(
        "Term", term, ["school", "academic_year", "term_start_date", "term_end_date"], as_dict=False
    ) or (None, None, None, None)


def _term_meta_many(term_names: set[str]) -> dict[str, dict]:
    """Batch fetch term metadata to minimize DB round-trips."""
    if not term_names:
        return {}
    rows = frappe.get_all(
        "Term",
        filters={"name": ("in", list(term_names))},
        fields=["name", "school", "academic_year", "term_start_date", "term_end_date"],
    )
    return {r.name: r for r in rows}


def _compute_effective_course_span(offering_name: str, roc: dict) -> tuple[object, object]:
    """
    Compute effective (start_dt, end_dt) for a Program Offering Course row.
    Child fields: start_academic_year/end_academic_year, start_academic_term/end_academic_term.
    """
    say = roc.get("start_academic_year")
    eay = roc.get("end_academic_year")

    s_ay_start, s_ay_end_unused = _ay_bounds_for(offering_name, say)
    e_ay_start_unused, e_ay_end = _ay_bounds_for(offering_name, eay)
    if not (s_ay_start and e_ay_end):
        return (getdate("1900-01-01"), getdate("1899-12-31"))

    start_dt = s_ay_start
    end_dt = e_ay_end

    # Narrow by terms (use start date of start term; end date of end term if available)
    ts_name = roc.get("start_academic_term")
    if ts_name:
        ts_school_ignore, ts_ay_ignore, ts_start, ts_end_ignore = _term_meta(ts_name)
        if ts_start:
            start_dt = max(start_dt, getdate(ts_start))

    te_name = roc.get("end_academic_term")
    if te_name:
        te_school_ignore, te_ay_ignore, te_start, te_end = _term_meta(te_name)
        if te_end or te_start:
            end_dt = min(end_dt, getdate(te_end) if te_end else getdate(te_start))

    return (start_dt, end_dt)


def _offering_courses_index(offering_name: str) -> dict[str, list[dict]]:
    """
    Build index from Program Offering Course. Normalize term keys to term_start/term_end
    so the rest of the enrollment logic can keep using those names.
    """
    rows = frappe.get_all(
        "Program Offering Course",
        filters={"parent": offering_name, "parenttype": "Program Offering"},
        fields=[
            "course",
            "start_academic_year",
            "end_academic_year",
            "start_academic_term",
            "end_academic_term",
            "from_date",
            "to_date",
            "required",
            "idx",
        ],
        order_by="idx asc",
    )

    idx: dict[str, list[dict]] = {}
    for r in rows:
        s, e = _compute_effective_course_span(offering_name, r)
        item = {
            "start": s,
            "end": e,
            "start_ay": r.get("start_academic_year"),
            "end_ay": r.get("end_academic_year"),
            # normalized keys expected elsewhere
            "term_start": r.get("start_academic_term"),
            "term_end": r.get("end_academic_term"),
            "required": r.get("required") or 0,
        }
        idx.setdefault(r["course"], []).append(item)

    return idx


# from JS to filter out students that have already been enrolled for a given year and/or term
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_students(doctype, txt, searchfield, start, page_len, filters):
    page_len = 50

    if not filters.get("academic_year"):
        return []

    enrolled_students = (
        frappe.db.get_values(
            "Program Enrollment", filters={"academic_year": filters.get("academic_year")}, fieldname="student"
        )
        or []
    )

    # Efficient and clean conversion to list of dicts (if you want it)
    excluded_students = [d[0] for d in enrolled_students] or [""]

    # Build SQL
    sql = f"""
        SELECT name, student_full_name
        FROM tabStudent
        WHERE
            enabled = 1
            AND name NOT IN ({", ".join(["%s"] * len(excluded_students))})
            AND (
              name LIKE %s
        OR student_full_name LIKE %s
            )
        ORDER BY idx DESC, name
        LIMIT %s, %s
    """

    # Params: excluded list + search text + pagination
    # params = excluded_students + [f"%{txt}%", start, page_len]
    params = excluded_students + [f"%{txt}%", f"%{txt}%", start, page_len]

    return frappe.db.sql(sql, params)


# from JS to display AY in descending order
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_academic_years(doctype, txt, searchfield, start, page_len, filters):
    filters = frappe.parse_json(filters) if isinstance(filters, str) else filters or {}

    school = filters.get("school")
    if not school:
        return []

    def find_school_with_ay(school):
        # Search for AYs for this school, else walk up to parent
        while school:
            ay_exists = frappe.db.exists("Academic Year", {"school": school})
            if ay_exists:
                return school
            # Standard NestedSet parent
            parent = frappe.db.get_value("School", school, "parent_school")
            if not parent or parent == school:
                break
            school = parent
        return None

    target_school = find_school_with_ay(school)
    if not target_school:
        return []

    conditions = ["school = %(school)s"]
    values = {"school": target_school}

    if txt:
        conditions.append("name LIKE %(txt)s")
        values["txt"] = f"%{txt}%"

    where_clause = "WHERE " + " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT name
        FROM `tabAcademic Year`
        {where_clause}
        ORDER BY year_start_date DESC
        LIMIT %(start)s, %(page_len)s
    """,
        {**values, "start": start, "page_len": page_len},
    )


@frappe.whitelist()
def get_program_courses_for_enrollment(program_offering):
    if not program_offering:
        return []
    courses = frappe.get_all(
        "Program Offering Course",
        filters={"parent": program_offering, "parenttype": "Program Offering"},
        pluck="course",
        order_by="idx asc",
    )
    return [c for c in courses if c]


@frappe.whitelist()
def get_offering_ay_spine(offering: str):
    if not offering:
        return []
    spine = _offering_ay_spine(offering)
    # shape it like the client expects
    return [
        {
            "academic_year": r["academic_year"],
            "year_start_date": r["start"],
            "year_end_date": r["end"],
        }
        for r in spine
    ]


def get_terms_for_ay_with_fallback(school, academic_year):
    """Returns (terms, source_school) for the best available school: leaf, else nearest ancestor with terms for AY."""
    if not (school and academic_year):
        return [], None
    # 1. Try direct school first
    terms = frappe.db.get_values("Term", {"school": school, "academic_year": academic_year}, "name")
    if terms:
        return [t[0] for t in terms], school
    # 2. Fallback to ancestors in order
    current_school = frappe.get_doc("School", school)
    ancestors = frappe.get_all(
        "School",
        filters={"lft": ["<", current_school.lft], "rgt": [">", current_school.rgt]},
        fields=["name"],
        order_by="lft desc",
    )
    for ancestor in ancestors:
        ancestor_terms = frappe.db.get_values("Term", {"school": ancestor.name, "academic_year": academic_year}, "name")
        if ancestor_terms:
            return [t[0] for t in ancestor_terms], ancestor.name
    return [], None


@frappe.whitelist()
def get_valid_terms_with_fallback(school, academic_year):
    terms, source_school = get_terms_for_ay_with_fallback(school, academic_year)
    return {"valid_terms": terms, "source_school": source_school}


@frappe.whitelist()
def candidate_courses_for_add_multiple(program_offering: str, academic_year: str, existing=None):
    """Return candidate courses… (docstring unchanged)"""
    if isinstance(existing, str):
        try:
            existing = frappe.parse_json(existing) or []
        except Exception:
            existing = []
    elif not isinstance(existing, (list, tuple, set)):
        existing = []
    existing_set = set(existing)

    enr_ay_start, enr_ay_end = _ay_bounds_for(program_offering, academic_year)
    if not (enr_ay_start and enr_ay_end):
        return []

    off_idx = _offering_courses_index(program_offering)
    off = _offering_core(program_offering)
    school = off.get("school") if off else None

    out = []
    for course, spans in off_idx.items():
        if course in existing_set:
            continue
        # Overlap with selected AY slice?
        if not any((enr_ay_start <= s["end"]) and (s["start"] <= enr_ay_end) for s in spans):
            continue

        row = {
            "course": course,
            "course_name": frappe.db.get_value("Course", course, "course_name"),
            "required": 1 if any(s.get("required") for s in spans) else 0,
        }

        # Suggest term bounds for non-term-long courses
        if school:
            term_long = frappe.db.get_value("Course", course, "term_long")
            if not term_long:
                bounds = get_school_term_bounds(school, academic_year)
                if bounds:
                    row["suggested_term_start"] = bounds.get("term_start")
                    row["suggested_term_end"] = bounds.get("term_end")

        out.append(row)

    # Sort: required first, then by earliest span start, then by name
    def _first_start(cname: str):
        try:
            return min(s["start"] for s in off_idx.get(cname, []))
        except ValueError:
            return enr_ay_start

    out.sort(key=lambda r: (-(r["required"]), _first_start(r["course"]), (r["course_name"] or r["course"])))
    return out


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(
        """
        SELECT name
        FROM `tabAcademic Year`
        WHERE name LIKE %(txt)s
        ORDER BY year_start_date DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {"txt": f"%{txt}%", "start": start, "page_len": page_len},
    )


def get_permission_query_conditions(user):
    # Allow full access to Administrator or System Manager
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return "1=0"  # No access if no default school

    descendant_schools = get_descendant_schools(user_school)
    if not descendant_schools:
        return "1=0"
    schools_list = "', '".join(descendant_schools)
    return f"`tabProgram Enrollment`.`school` IN ('{schools_list}')"


def has_permission(doc, user=None):
    if not user:
        user = frappe.session.user

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return False

    descendant_schools = get_descendant_schools(user_school)
    return doc.school in descendant_schools


def on_doctype_update():
    # useful for AY-scoped lookups
    frappe.db.add_index("Program Enrollment", ["student", "academic_year"])
    frappe.db.add_index("Program Enrollment", ["program_offering", "academic_year"])
    # not duplicaiton of enrollmnent for same offering+year
    frappe.db.add_unique("Program Enrollment", ["student", "program_offering", "academic_year"])
