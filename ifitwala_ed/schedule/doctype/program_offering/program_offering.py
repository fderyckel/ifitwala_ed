from __future__ import annotations

# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt
# ifitwala_ed/schedule/doctype/program_offering/program_offering.py
from typing import Optional, Sequence, Union

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime, get_link_to_form, getdate, now_datetime

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.schedule.basket_group_utils import get_program_course_basket_group_map
from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots
from ifitwala_ed.schedule.student_group_employee_booking import rebuild_employee_bookings_for_student_group
from ifitwala_ed.utilities.employee_booking import find_employee_conflicts
from ifitwala_ed.utilities.employee_utils import get_user_visible_schools
from ifitwala_ed.utilities.location_utils import find_room_conflicts, is_bookable_room
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, is_leaf_school

# -------------------------
# small DB helpers (used by validate)
# -------------------------


def _ay_fields(ay: str):
    """Return (school, year_start_date, year_end_date) for Academic Year."""
    if not ay:
        return (None, None, None)
    return frappe.db.get_value("Academic Year", ay, ["school", "year_start_date", "year_end_date"], as_dict=False) or (
        None,
        None,
        None,
    )


def _term_fields(term: str):
    """Return (school, academic_year, term_start_date, term_end_date) for Term."""
    if not term:
        return (None, None, None, None)
    return frappe.db.get_value(
        "Term", term, ["school", "academic_year", "term_start_date", "term_end_date"], as_dict=False
    ) or (None, None, None, None)


def _assert(cond: bool, msg: str):
    if not cond:
        frappe.throw(msg)


def _format_error_date(value) -> str:
    resolved = getdate(value) if value else None
    return resolved.isoformat() if resolved else ""


# -------------------------
# main document
# -------------------------


class ProgramOffering(Document):
    def validate(self):
        self._validate_required()
        _assert(
            is_leaf_school(self.school),
            _("Program Offering must be anchored on a child (leaf) school with no descendants."),
        )
        allowed = self._allowed_ancestor_schools()

        # 1) Validate AY spine (child table)
        ay_rows = self._validate_offering_ays(allowed)

        # 2) Validate head Start/End against AY span (and basic ordering)
        self._validate_head_window_against_ays(ay_rows)

        # 3) Validate course rows
        self._validate_offering_courses(ay_rows, allowed)
        self._validate_offering_course_basket_groups()
        self._validate_enrollment_rules()

        # 4) Status sanity
        if self.status not in ("Planned", "Active", "Archived"):
            frappe.throw(_("Invalid Status: {status}.").format(status=self.status))

        self._validate_catalog_membership()
        self._apply_default_span_to_rows()
        self._validate_activity_booking_configuration()

    # -------------------------
    # helpers
    # -------------------------

    def _validate_required(self):
        _assert(self.program, _("Program is required."))
        _assert(self.school, _("School is required."))

    def _allowed_ancestor_schools(self) -> set[str]:
        if not self.school:
            return set()
        return set(get_ancestor_schools(self.school))

    def _validate_offering_ays(self, allowed_schools: set[str]) -> list[dict]:
        rows = list(self.offering_academic_years or [])
        _assert(rows, _("At least one Academic Year is required."))

        seen = set()
        cols = []
        for idx, r in enumerate(rows, start=1):
            _assert(r.academic_year, _("Row {row_number}: Academic Year is required.").format(row_number=idx))
            ay = r.academic_year
            ay_school, ay_start, ay_end = _ay_fields(ay)
            _assert(
                ay_school,
                _("Row {row_number}: Academic Year {academic_year} has no School set.").format(
                    row_number=idx,
                    academic_year=get_link_to_form("Academic Year", ay),
                ),
            )
            _assert(
                ay_school in allowed_schools,
                _(
                    "Row {row_number}: Academic Year {academic_year} belongs to {school}, which is outside the offering school's ancestry."
                ).format(
                    row_number=idx,
                    academic_year=get_link_to_form("Academic Year", ay),
                    school=get_link_to_form("School", ay_school),
                ),
            )
            _assert(
                ay_start and ay_end,
                _("Row {row_number}: Academic Year {academic_year} must have start and end dates.").format(
                    row_number=idx,
                    academic_year=get_link_to_form("Academic Year", ay),
                ),
            )

            _assert(ay not in seen, _("Duplicate Academic Year: {academic_year}.").format(academic_year=ay))
            seen.add(ay)
            cols.append({"name": ay, "start": getdate(ay_start), "end": getdate(ay_end), "school": ay_school})

        cols.sort(key=lambda x: x["start"])

        for i in range(1, len(cols)):
            prev, curr = cols[i - 1], cols[i]
            _assert(
                prev["end"] < curr["start"],
                _(
                    "Academic Years overlap: {first_academic_year} ({first_start}->{first_end}) and {second_academic_year} ({second_start}->{second_end})."
                ).format(
                    first_academic_year=prev["name"],
                    first_start=_format_error_date(prev["start"]),
                    first_end=_format_error_date(prev["end"]),
                    second_academic_year=curr["name"],
                    second_start=_format_error_date(curr["start"]),
                    second_end=_format_error_date(curr["end"]),
                ),
            )
        return cols

    def _validate_head_window_against_ays(self, ay_rows: list[dict]):
        if not (self.start_date or self.end_date):
            return

        _assert(ay_rows, _("Offering dates require at least one Academic Year."))

        head_start = getdate(self.start_date) if self.start_date else None
        head_end = getdate(self.end_date) if self.end_date else None
        if head_start and head_end:
            _assert(head_start <= head_end, _("Start Date cannot be after End Date."))

        min_ay = min(r["start"] for r in ay_rows)
        max_ay = max(r["end"] for r in ay_rows)

        if head_start:
            _assert(
                min_ay <= head_start <= max_ay,
                _(
                    "Start Date {start_date} must lie within the spanning Academic Years ({academic_year_start} -> {academic_year_end})."
                ).format(
                    start_date=_format_error_date(head_start),
                    academic_year_start=_format_error_date(min_ay),
                    academic_year_end=_format_error_date(max_ay),
                ),
            )
        if head_end:
            _assert(
                min_ay <= head_end <= max_ay,
                _(
                    "End Date {end_date} must lie within the spanning Academic Years ({academic_year_start} -> {academic_year_end})."
                ).format(
                    end_date=_format_error_date(head_end),
                    academic_year_start=_format_error_date(min_ay),
                    academic_year_end=_format_error_date(max_ay),
                ),
            )

    def _validate_offering_courses(self, ay_rows: list[dict], allowed_schools: set[str]):
        """
        For each Program Offering Course row, validate:
                - start/end AY exist in the AY spine and are ordered (start ≤ end by time)
                - if terms are given: term.school ∈ allowed, term.ay matches the row AY, and dates ordered
                - compute an effective [row_start,row_end] using (from/to) or terms or AY bounds
                - ensure effective window sits within the AY envelope
                - if head dates exist:
                        • EXPLICIT dates outside head → throw
                        • IMPLICIT (blank) dates → clamp inside head
        """
        if not getattr(self, "offering_courses", None):
            return

        # quick lookups
        ay_index = {r["name"]: r for r in ay_rows}
        min_ay = min(r["start"] for r in ay_rows)
        max_ay = max(r["end"] for r in ay_rows)

        head_start = getdate(self.start_date) if self.start_date else None
        head_end = getdate(self.end_date) if self.end_date else None

        for idx, row in enumerate(self.offering_courses, start=1):
            _assert(row.course, _("Row {row_number}: Course is required.").format(row_number=idx))
            _assert(
                row.start_academic_year, _("Row {row_number}: Start Academic Year is required.").format(row_number=idx)
            )
            _assert(row.end_academic_year, _("Row {row_number}: End Academic Year is required.").format(row_number=idx))

            start_ay = ay_index.get(row.start_academic_year)
            end_ay = ay_index.get(row.end_academic_year)
            _assert(
                start_ay,
                _("Row {row_number}: Start AY {academic_year} must be listed in Offering Academic Years.").format(
                    row_number=idx,
                    academic_year=get_link_to_form("Academic Year", row.start_academic_year),
                ),
            )
            _assert(
                end_ay,
                _("Row {row_number}: End AY {academic_year} must be listed in Offering Academic Years.").format(
                    row_number=idx,
                    academic_year=get_link_to_form("Academic Year", row.end_academic_year),
                ),
            )

            # AY ordering by dates
            _assert(
                start_ay["start"] <= end_ay["end"],
                _("Row {row_number}: Start AY must not be after End AY.").format(row_number=idx),
            )

            # Terms (optional)
            start_term_name = getattr(row, "start_academic_term", None)
            end_term_name = getattr(row, "end_academic_term", None)

            start_term_dt = start_ay["start"]
            end_term_dt = end_ay["end"]

            if start_term_name:
                ts_school, ts_ay, ts_start, ts_end = _term_fields(start_term_name)
                _assert(
                    ts_ay == row.start_academic_year,
                    _("Row {row_number}: Start Term {term} must belong to Start AY {academic_year}.").format(
                        row_number=idx,
                        term=get_link_to_form("Term", start_term_name),
                        academic_year=get_link_to_form("Academic Year", row.start_academic_year),
                    ),
                )
                _assert(
                    ts_school in allowed_schools,
                    _(
                        "Row {row_number}: Start Term {term} belongs to {school}, outside the offering school's tree."
                    ).format(
                        row_number=idx,
                        term=get_link_to_form("Term", start_term_name),
                        school=get_link_to_form("School", ts_school),
                    ),
                )
                _assert(
                    ts_start,
                    _("Row {row_number}: Start Term {term} is missing term_start_date.").format(
                        row_number=idx,
                        term=get_link_to_form("Term", start_term_name),
                    ),
                )
                start_term_dt = getdate(ts_start)

            if end_term_name:
                te_school, te_ay, te_start, te_end = _term_fields(end_term_name)
                _assert(
                    te_ay == row.end_academic_year,
                    _("Row {row_number}: End Term {term} must belong to End AY {academic_year}.").format(
                        row_number=idx,
                        term=get_link_to_form("Term", end_term_name),
                        academic_year=get_link_to_form("Academic Year", row.end_academic_year),
                    ),
                )
                _assert(
                    te_school in allowed_schools,
                    _(
                        "Row {row_number}: End Term {term} belongs to {school}, outside the offering school's tree."
                    ).format(
                        row_number=idx,
                        term=get_link_to_form("Term", end_term_name),
                        school=get_link_to_form("School", te_school),
                    ),
                )
                _assert(
                    te_start or te_end,
                    _("Row {row_number}: End Term {term} is missing dates.").format(
                        row_number=idx,
                        term=get_link_to_form("Term", end_term_name),
                    ),
                )
                # prefer term end when available
                end_term_dt = getdate(te_end) if te_end else getdate(te_start)

            if start_term_name and end_term_name:
                _assert(
                    start_term_dt <= end_term_dt,
                    _("Row {row_number}: Start Term must not be after End Term.").format(row_number=idx),
                )

            # Determine explicit/implicit user input
            from_explicit = bool(getattr(row, "from_date", None))
            to_explicit = bool(getattr(row, "to_date", None))

            # Raw effective dates from either explicit fields or AY/term bounds
            row_start = getdate(row.from_date) if from_explicit else start_term_dt
            row_end = getdate(row.to_date) if to_explicit else end_term_dt

            # Head window handling:
            # - explicit out-of-bounds → throw
            # - implicit (blank) → clamp to head window
            if head_start:
                if from_explicit:
                    _assert(
                        head_start <= row_start,
                        _("Row {row_number}: From Date is before Offering Start Date.").format(row_number=idx),
                    )
                else:
                    if row_start < head_start:
                        row_start = head_start
                        # optional: persist the default so users see what will be used
                        row.from_date = row_start

            if head_end:
                if to_explicit:
                    _assert(
                        row_end <= head_end,
                        _("Row {row_number}: To Date is after Offering End Date.").format(row_number=idx),
                    )
                else:
                    if row_end > head_end:
                        row_end = head_end
                        row.to_date = row_end

            # Basic ordering (after any clamping)
            _assert(
                row_start <= row_end,
                _("Row {row_number}: From Date cannot be after To Date.").format(row_number=idx),
            )

            # Inside AY envelope (after clamping)
            _assert(
                min_ay <= row_start <= max_ay,
                _("Row {row_number}: From Date out of Academic Year span.").format(row_number=idx),
            )
            _assert(
                min_ay <= row_end <= max_ay,
                _("Row {row_number}: To Date out of Academic Year span.").format(row_number=idx),
            )

            # If terms + explicit dates both exist, ensure explicit dates lie within term windows
            if start_term_name and from_explicit:
                _assert(
                    start_term_dt <= getdate(row.from_date),
                    _("Row {row_number}: From Date is earlier than Start Term window.").format(row_number=idx),
                )
            if end_term_name and to_explicit:
                _assert(
                    getdate(row.to_date) <= end_term_dt,
                    _("Row {row_number}: To Date is later than End Term window.").format(row_number=idx),
                )

    def _validate_catalog_membership(self):
        """If a course isn't in the Program's catalog, require non_catalog + reason."""
        if not getattr(self, "offering_courses", None):
            return

        # Gather catalog set quickly
        catalog_courses = set()
        if frappe.db.table_exists("Program Course"):
            for r in frappe.get_all(
                "Program Course",
                filters={"parent": self.program},
                fields=["course"],
                limit=2000,
            ):
                if r.get("course"):
                    catalog_courses.add(r["course"])

        for idx, row in enumerate(self.offering_courses, start=1):
            course = row.course
            if not course:
                continue

            is_in_catalog = course in catalog_courses
            is_exception = int(row.get("non_catalog") or 0) == 1

            if not is_in_catalog and not is_exception:
                frappe.throw(
                    _(
                        "Row {row_number}: Course {course} is not in the Program catalog. "
                        "Either add it to Program Course, or mark this row as Non-catalog and provide a justification."
                    ).format(row_number=idx, course=frappe.utils.get_link_to_form("Course", course))
                )

            if is_exception:
                # Optional: require a reason if field exists
                if "exception_reason" in row.as_dict() and not (row.get("exception_reason") or "").strip():
                    frappe.throw(
                        _(
                            "Row {row_number}: Please provide an Exception Justification for the non-catalog course {course}."
                        ).format(
                            row_number=idx,
                            course=frappe.utils.get_link_to_form("Course", course),
                        )
                    )

    def _validate_offering_course_basket_groups(self):
        if not getattr(self, "offering_course_basket_groups", None):
            return

        valid_courses = {
            (row.course or "").strip() for row in (self.offering_courses or []) if (row.course or "").strip()
        }
        seen = set()

        for idx, row in enumerate(self.offering_course_basket_groups or [], start=1):
            course = (row.course or "").strip()
            basket_group = (row.basket_group or "").strip()
            _assert(
                course, _("Enrollment basket membership row {row_number}: Course is required.").format(row_number=idx)
            )
            _assert(
                course in valid_courses,
                _(
                    "Enrollment basket membership row {row_number}: Course {course} is not present in Offering Courses."
                ).format(
                    row_number=idx,
                    course=course,
                ),
            )
            _assert(
                basket_group,
                _("Enrollment basket membership row {row_number}: Basket Group (Enrollment) is required.").format(
                    row_number=idx
                ),
            )

            key = (course, basket_group)
            _assert(
                key not in seen,
                _(
                    "Enrollment basket membership row {row_number}: duplicate mapping for {course} -> {basket_group}."
                ).format(
                    row_number=idx,
                    course=course,
                    basket_group=basket_group,
                ),
            )
            seen.add(key)

    def _validate_enrollment_rules(self):
        if not getattr(self, "enrollment_rules", None):
            return

        for idx, row in enumerate(self.enrollment_rules or [], start=1):
            rule_type = (row.rule_type or "").strip()
            if rule_type == "REQUIRE_GROUP_COVERAGE" and not (row.basket_group or "").strip():
                frappe.throw(
                    _(
                        "Enrollment Rule row {row_number}: Basket Group (Enrollment) is required for REQUIRE_GROUP_COVERAGE."
                    ).format(row_number=idx)
                )

    def _get_ay_envelope(self) -> tuple[str | None, str | None]:
        """Return (start_ay, end_ay) from the ordered Table MultiSelect rows."""
        ay_names = [r.academic_year for r in (self.offering_academic_years or []) if r.academic_year]
        if not ay_names:
            return (None, None)
        return (ay_names[0], ay_names[-1])

    def _apply_default_span_to_rows(self) -> None:
        """Copy the parent AY envelope into child rows if missing."""
        start_ay, end_ay = self._get_ay_envelope()
        if not start_ay or not end_ay:
            return

        changed = False
        for row in self.offering_courses or []:
            # Set defaults only if empty—admins can still override per row later
            if not getattr(row, "start_academic_year", None):
                row.start_academic_year = start_ay
                changed = True  # noqa: F841
            if not getattr(row, "end_academic_year", None):
                row.end_academic_year = end_ay
                changed = True  # noqa: F841

    def _validate_activity_booking_configuration(self) -> None:
        """
        Validate activity-booking specific controls stored on Program Offering.

        This method intentionally does not depend on client-side behavior.
        All booking-window gates are enforced server-side.
        """
        if cint(self.activity_booking_enabled or 0) != 1:
            return

        status = (self.activity_booking_status or "Draft").strip() or "Draft"
        allowed_status = {"Draft", "Ready", "Open", "Closed"}
        if status not in allowed_status:
            frappe.throw(_("Invalid Activity Booking Status: {status}.").format(status=status))
        self.activity_booking_status = status

        min_age = self.activity_min_age_years
        max_age = self.activity_max_age_years
        if min_age is not None and cint(min_age) < 0:
            frappe.throw(_("Minimum activity age cannot be negative."))
        if max_age is not None and cint(max_age) < 0:
            frappe.throw(_("Maximum activity age cannot be negative."))
        if min_age is not None and max_age is not None and cint(min_age) > cint(max_age):
            frappe.throw(_("Minimum activity age cannot be greater than maximum activity age."))

        waitlist_hours = cint(self.activity_waitlist_offer_hours or 0)
        if waitlist_hours < 0:
            frappe.throw(_("Waitlist offer hours cannot be negative."))
        if waitlist_hours == 0:
            self.activity_waitlist_offer_hours = 24

        if cint(self.activity_payment_required or 0) == 1 and flt(self.activity_fee_amount or 0) < 0:
            frappe.throw(_("Activity fee amount cannot be negative."))

        open_from = get_datetime(self.activity_booking_open_from) if self.activity_booking_open_from else None
        open_to = get_datetime(self.activity_booking_open_to) if self.activity_booking_open_to else None
        if open_from and open_to and open_to <= open_from:
            frappe.throw(_("Activity booking close time must be after open time."))

        if status == "Open" and not open_from:
            self.activity_booking_open_from = now_datetime()

        self._validate_activity_sections()

        if status in {"Ready", "Open"}:
            report = self.run_activity_preopen_readiness(raise_on_failure=False)
            if not report.get("ok"):
                frappe.throw(
                    self._build_activity_gate_error(report),
                    title=_("Activity Booking Readiness Failed"),
                )

    def _validate_activity_sections(self) -> None:
        rows = [r for r in (self.activity_sections or []) if cint(getattr(r, "is_active", 1)) == 1]
        if not rows:
            frappe.throw(_("At least one active Activity Section is required when activity booking is enabled."))

        seen = set()
        group_names = []
        for idx, row in enumerate(rows, start=1):
            sg = (row.student_group or "").strip()
            if not sg:
                frappe.throw(_("Activity Section row {row_number}: Student Group is required.").format(row_number=idx))
            if sg in seen:
                frappe.throw(_("Duplicate Activity Section Student Group: {student_group}.").format(student_group=sg))
            seen.add(sg)
            group_names.append(sg)

            if row.capacity_override is not None and cint(row.capacity_override) < 0:
                frappe.throw(
                    _("Activity Section row {row_number}: Capacity Override cannot be negative.").format(row_number=idx)
                )
            if row.priority_tier is not None and cint(row.priority_tier) < 0:
                frappe.throw(
                    _("Activity Section row {row_number}: Priority Tier cannot be negative.").format(row_number=idx)
                )

        group_rows = frappe.get_all(
            "Student Group",
            filters={"name": ["in", group_names]},
            fields=[
                "name",
                "group_based_on",
                "program_offering",
                "student_group_name",
                "student_group_abbreviation",
            ],
            limit=max(200, len(group_names) + 20),
        )
        group_map = {g.get("name"): g for g in group_rows}

        for idx, row in enumerate(rows, start=1):
            sg = row.student_group
            meta = group_map.get(sg)
            if not meta:
                frappe.throw(
                    _("Activity Section row {row_number}: Student Group {student_group} was not found.").format(
                        row_number=idx,
                        student_group=sg,
                    )
                )

            if (meta.get("group_based_on") or "").strip() != "Activity":
                frappe.throw(
                    _(
                        "Activity Section row {row_number}: Student Group {student_group} must be group type Activity."
                    ).format(
                        row_number=idx,
                        student_group=get_link_to_form("Student Group", sg),
                    )
                )

            sg_offering = (meta.get("program_offering") or "").strip()
            if sg_offering and sg_offering != self.name:
                frappe.throw(
                    _(
                        "Activity Section row {row_number}: Student Group {student_group} belongs to Program Offering {actual_offering}, not {expected_offering}."
                    ).format(
                        row_number=idx,
                        student_group=get_link_to_form("Student Group", sg),
                        actual_offering=get_link_to_form("Program Offering", sg_offering),
                        expected_offering=get_link_to_form("Program Offering", self.name),
                    )
                )

            if not (row.section_label or "").strip():
                row.section_label = (
                    (meta.get("student_group_abbreviation") or "").strip()
                    or (meta.get("student_group_name") or "").strip()
                    or sg
                )

    def _get_activity_date_window(self):
        start_date = getdate(self.start_date) if self.start_date else None
        end_date = getdate(self.end_date) if self.end_date else None

        if start_date and end_date and start_date <= end_date:
            return start_date, end_date

        ay_names = [
            (row.academic_year or "").strip()
            for row in (self.offering_academic_years or [])
            if (row.academic_year or "").strip()
        ]
        if not ay_names:
            return None, None

        ay_rows = frappe.get_all(
            "Academic Year",
            filters={"name": ["in", ay_names]},
            fields=["name", "year_start_date", "year_end_date"],
            limit=max(200, len(ay_names) + 20),
        )
        dates = []
        for row in ay_rows:
            if row.get("year_start_date"):
                dates.append(getdate(row.get("year_start_date")))
            if row.get("year_end_date"):
                dates.append(getdate(row.get("year_end_date")))
        if not dates:
            return None, None
        return min(dates), max(dates)

    def _build_activity_gate_error(self, report: dict) -> str:
        sections = report.get("sections") or []
        lines = [_("Activity booking window cannot open until section readiness issues are resolved.")]
        for section in sections:
            label = section.get("section_label") or section.get("student_group") or _("Unknown Section")
            errors = section.get("errors") or []
            room_conflicts = section.get("room_conflicts") or []
            employee_conflicts = section.get("employee_conflicts") or []

            if not errors and not room_conflicts and not employee_conflicts:
                continue

            lines.append(f"<br><b>{frappe.utils.escape_html(str(label))}</b>")
            for err in errors:
                lines.append(f"<br>- {frappe.utils.escape_html(str(err))}")
            for c in room_conflicts[:8]:
                lines.append(
                    "<br>- "
                    + _("Room conflict: {location} overlaps with {doctype} {name} ({from_dt} → {to_dt})").format(
                        location=c.get("location"),
                        doctype=c.get("source_doctype"),
                        name=c.get("source_name"),
                        from_dt=c.get("from"),
                        to_dt=c.get("to"),
                    )
                )
            for c in employee_conflicts[:8]:
                lines.append(
                    "<br>- "
                    + _("Instructor conflict: {employee} overlaps with {doctype} {name} ({from_dt} → {to_dt})").format(
                        employee=c.get("employee"),
                        doctype=c.get("source_doctype"),
                        name=c.get("source_name"),
                        from_dt=c.get("from"),
                        to_dt=c.get("to"),
                    )
                )
        return "".join(lines)

    def run_activity_preopen_readiness(self, raise_on_failure: bool = True) -> dict:
        """
        Run section readiness checks before moving an activity booking window to Open.

        Checks:
        - linked Student Groups are schedule-valid and use bookable locations
        - section slots have no Location Booking collisions
        - section instructor slots have no Employee Booking collisions
        """
        report = {
            "ok": True,
            "program_offering": self.name,
            "window": {},
            "sections": [],
        }

        start_date, end_date = self._get_activity_date_window()
        report["window"] = {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
        }
        if not start_date or not end_date:
            report["ok"] = False
            report["sections"].append(
                {
                    "student_group": None,
                    "section_label": None,
                    "errors": [
                        _("Program Offering requires Start/End or valid Academic Year span for readiness checks.")
                    ],
                    "room_conflicts": [],
                    "employee_conflicts": [],
                }
            )
            if raise_on_failure:
                frappe.throw(self._build_activity_gate_error(report), title=_("Activity Booking Readiness Failed"))
            return report

        rows = [r for r in (self.activity_sections or []) if cint(getattr(r, "is_active", 1)) == 1]
        if not rows:
            report["ok"] = False
            report["sections"].append(
                {
                    "student_group": None,
                    "section_label": None,
                    "errors": [_("No active activity sections found.")],
                    "room_conflicts": [],
                    "employee_conflicts": [],
                }
            )
            if raise_on_failure:
                frappe.throw(self._build_activity_gate_error(report), title=_("Activity Booking Readiness Failed"))
            return report

        instructor_cache = {}

        for row in rows:
            sg_name = (row.student_group or "").strip()
            section_payload = {
                "student_group": sg_name,
                "section_label": (row.section_label or "").strip() or sg_name,
                "errors": [],
                "room_conflicts": [],
                "employee_conflicts": [],
            }

            if not sg_name:
                section_payload["errors"].append(_("Missing Student Group on activity section row."))
                report["sections"].append(section_payload)
                report["ok"] = False
                continue

            schedule_rows = frappe.get_all(
                "Student Group Schedule",
                filters={"parent": sg_name},
                fields=[
                    "name",
                    "rotation_day",
                    "block_number",
                    "location",
                    "instructor",
                    "employee",
                ],
                limit=5000,
            )
            if not schedule_rows:
                section_payload["errors"].append(_("Student Group has no schedule rows."))
                report["sections"].append(section_payload)
                report["ok"] = False
                continue

            schedule_index = {}
            instructor_names = set()
            for srow in schedule_rows:
                rd = srow.get("rotation_day")
                blk = srow.get("block_number")
                location = (srow.get("location") or "").strip()
                if rd is None or blk is None:
                    section_payload["errors"].append(
                        _("Schedule row {schedule_row} is missing rotation day or block number.").format(
                            schedule_row=srow.get("name")
                        )
                    )
                    continue
                key = (cint(rd), cint(blk))
                schedule_index[key] = srow

                if not location:
                    section_payload["errors"].append(
                        _("Schedule row {schedule_row} is missing location.").format(schedule_row=srow.get("name"))
                    )
                elif not is_bookable_room(location):
                    section_payload["errors"].append(
                        _("Schedule row {schedule_row} uses non-bookable location {location}.").format(
                            schedule_row=srow.get("name"),
                            location=location,
                        )
                    )

                if (srow.get("instructor") or "").strip() and not (srow.get("employee") or "").strip():
                    instructor_names.add((srow.get("instructor") or "").strip())

            if instructor_names:
                rows_i = frappe.get_all(
                    "Instructor",
                    filters={"name": ["in", sorted(instructor_names)]},
                    fields=["name", "employee"],
                    limit=max(200, len(instructor_names) + 20),
                )
                for irow in rows_i:
                    instructor_cache[irow.get("name")] = (irow.get("employee") or "").strip()

            try:
                rebuild_employee_bookings_for_student_group(
                    sg_name,
                    start_date=start_date,
                    end_date=end_date,
                    strict_location=True,
                )
            except Exception:
                section_payload["errors"].append(frappe.get_traceback())

            slots = iter_student_group_room_slots(sg_name, start_date, end_date)
            seen_room_conflicts = set()
            seen_employee_conflicts = set()

            for slot in slots:
                start_dt = slot.get("start")
                end_dt = slot.get("end")
                location = slot.get("location")
                rd = cint(slot.get("rotation_day"))
                blk = cint(slot.get("block_number"))

                if not start_dt or not end_dt or not location:
                    continue

                room_conflicts = find_room_conflicts(
                    location,
                    start_dt,
                    end_dt,
                    exclude={"doctype": "Student Group", "name": sg_name},
                )
                for conflict in room_conflicts:
                    key = (
                        conflict.get("source_doctype"),
                        conflict.get("source_name"),
                        conflict.get("location"),
                        str(conflict.get("from")),
                        str(conflict.get("to")),
                    )
                    if key in seen_room_conflicts:
                        continue
                    seen_room_conflicts.add(key)
                    section_payload["room_conflicts"].append(conflict)

                srow = schedule_index.get((rd, blk))
                if not srow:
                    continue
                employee = (srow.get("employee") or "").strip()
                if not employee:
                    instructor = (srow.get("instructor") or "").strip()
                    employee = instructor_cache.get(instructor) or ""
                if not employee:
                    continue

                conflicts = find_employee_conflicts(
                    employee,
                    start_dt,
                    end_dt,
                    exclude={"doctype": "Student Group", "name": sg_name},
                )
                for c in conflicts:
                    key = (
                        c.source_doctype,
                        c.source_name,
                        c.employee,
                        str(c.start),
                        str(c.end),
                    )
                    if key in seen_employee_conflicts:
                        continue
                    seen_employee_conflicts.add(key)
                    section_payload["employee_conflicts"].append(
                        {
                            "source_doctype": c.source_doctype,
                            "source_name": c.source_name,
                            "employee": c.employee,
                            "from": c.start,
                            "to": c.end,
                        }
                    )

            if section_payload["errors"] or section_payload["room_conflicts"] or section_payload["employee_conflicts"]:
                report["ok"] = False

            report["sections"].append(section_payload)

        if raise_on_failure and not report.get("ok"):
            frappe.throw(self._build_activity_gate_error(report), title=_("Activity Booking Readiness Failed"))
        return report


# -------------------------
# one whitelisted helper used by the client
# -------------------------


@frappe.whitelist()
def preview_activity_booking_readiness(program_offering: str):
    if not program_offering:
        frappe.throw(_("Program Offering is required."))

    doc = frappe.get_doc("Program Offering", program_offering)
    return doc.run_activity_preopen_readiness(raise_on_failure=False)


@frappe.whitelist()
def compute_program_offering_defaults(program: str, school: str, ay_names=None):
    """
    Return {"start_date": date|None, "end_date": date|None, "offering_title": str|None}
    - start_date = earliest AY start
    - end_date   = latest AY end
    - offering_title = "<ORG_ABBR> <PROG_ABBR> Cohort of YYYY"
      (YYYY from latest AY end; if no ends, from latest start)
    """

    def _list(x):
        if isinstance(x, str):
            try:
                return frappe.parse_json(x) or []
            except Exception:
                return []
        return list(x or [])

    ays = _list(ay_names)

    # Abbreviations (server-side; bypass UI perms)
    prog_abbr = frappe.db.get_value("Program", program, "program_abbreviation")

    org_name = frappe.db.get_value("School", school, "organization")
    org_abbr = None
    if org_name:
        row = frappe.db.sql(
            "select abbr from `tabOrganization` where name = %s",
            (org_name,),
            as_dict=False,
        )
        if row and row[0] and row[0][0]:
            org_abbr = row[0][0]

    # AY envelope
    min_start, max_end = None, None
    if ays:
        for r in frappe.get_all(
            "Academic Year",
            filters={"name": ["in", ays]},
            fields=["year_start_date", "year_end_date"],
        ):
            if r.get("year_start_date"):
                sd = getdate(r["year_start_date"])
                min_start = sd if not min_start or sd < min_start else min_start
            if r.get("year_end_date"):
                ed = getdate(r["year_end_date"])
                max_end = ed if not max_end or ed > max_end else max_end

    cohort_year = max_end.year if max_end else (min_start.year if min_start else None)
    title = f"{org_abbr} {prog_abbr} Cohort of {cohort_year}" if (org_abbr and prog_abbr and cohort_year) else None

    return {"start_date": min_start, "end_date": max_end, "offering_title": title}


@frappe.whitelist()
def program_course_options(
    program: str,
    search: str = "",
    exclude_courses: Optional[Union[str, Sequence[str]]] = None,
):
    """
    Return catalog rows for a Program (Program Course child table),
    excluding any already-present course names and matching an optional search term.
    Each row -> { "course", "course_name", "required", "basket_groups" }
    """

    # Coerce exclude_courses to a python list[str]
    if isinstance(exclude_courses, str):
        try:
            exclude = frappe.parse_json(exclude_courses) or []
        except Exception:
            exclude = []
    elif exclude_courses:
        exclude = list(exclude_courses)
    else:
        exclude = []

    filters = {"parent": program}
    if exclude:
        filters["course"] = ["not in", exclude]

    or_filters = []
    if search:
        like = f"%{search}%"
        or_filters = [{"course": ["like", like]}, {"course_name": ["like", like]}]

    pc_rows = frappe.get_all(
        "Program Course",
        filters=filters,
        or_filters=or_filters,
        fields=["course", "course_name", "required"],
        order_by="idx asc",
        limit=2000,
    )
    basket_group_map = get_program_course_basket_group_map(program)

    out = []
    for r in pc_rows:
        out.append(
            {
                "course": r.get("course"),
                "course_name": r.get("course_name") or r.get("course"),
                "required": 1 if r.get("required") else 0,
                "basket_groups": list(basket_group_map.get(r.get("course")) or []),
            }
        )

    return out


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def program_course_link_query(doctype, txt, searchfield, start, page_len, filters):
    filters = filters or {}
    program = filters.get("program")
    if not program:
        return []

    exclude_courses = filters.get("exclude_courses") or []
    if isinstance(exclude_courses, str):
        try:
            exclude_courses = frappe.parse_json(exclude_courses) or []
        except Exception:
            exclude_courses = []
    elif exclude_courses:
        exclude_courses = list(exclude_courses)
    else:
        exclude_courses = []

    db_filters = {
        "parent": program,
        "parenttype": "Program",
    }
    if exclude_courses:
        db_filters["course"] = ["not in", exclude_courses]

    search_txt = (txt or "").strip()
    or_filters = None
    if search_txt:
        like_txt = f"%{search_txt}%"
        or_filters = [
            ["Program Course", "course", "like", like_txt],
            ["Program Course", "course_name", "like", like_txt],
        ]

    rows = frappe.get_all(
        "Program Course",
        fields=["course", "course_name"],
        filters=db_filters,
        or_filters=or_filters,
        order_by="idx asc",
        start=int(start or 0),
        limit=int(page_len or 20),
    )
    return [[row.get("course"), (row.get("course_name") or row.get("course"))] for row in rows if row.get("course")]


@frappe.whitelist()
def hydrate_catalog_rows(program: str, course_names: str) -> list:
    """
    Given a JSON list of Course names, return ready Program Offering Course rows,
    mapping Program Course defaults + basket-group memberships.
    """
    try:
        names = frappe.parse_json(course_names) or []
    except Exception:
        names = []
    if not names:
        return []

    # Base info from Course
    course_info = {
        r["name"]: (r.get("course_name") or r["name"])
        for r in frappe.get_all(
            "Course", filters={"name": ["in", names]}, fields=["name", "course_name"], limit=len(names)
        )
    }

    pc_map = {}
    basket_group_map = get_program_course_basket_group_map(program)
    if frappe.db.table_exists("Program Course"):
        for r in frappe.get_all(
            "Program Course",
            filters={"parent": program, "course": ["in", names]},
            fields=["course", "required"],
            limit=len(names),
        ):
            pc_map[r["course"]] = {
                "required": 1 if (r.get("required") or 0) else 0,
                "basket_groups": list(basket_group_map.get(r.get("course")) or []),
            }

    rows = []
    for nm in names:
        base = pc_map.get(nm, {"required": 0, "basket_groups": []})
        rows.append(
            {
                "course": nm,
                "course_name": course_info.get(nm) or nm,
                "required": base["required"],
                "basket_groups": list(base["basket_groups"]),
                "non_catalog": 0,
                "catalog_ref": f"{program}::{nm}",
            }
        )
    return rows


@frappe.whitelist()
def hydrate_non_catalog_rows(course_names: str, exception_reason: str = "") -> list:
    """
    Given a JSON list of Course names, return minimal rows flagged as non-catalog.
    """
    try:
        names = frappe.parse_json(course_names) or []
    except Exception:
        names = []
    if not names:
        return []

    course_info = {
        r["name"]: r.get("course_name")
        for r in frappe.get_all(
            "Course", filters={"name": ["in", names]}, fields=["name", "course_name"], limit=len(names)
        )
    }

    return [
        {
            "course": nm,
            "course_name": course_info.get(nm) or nm,
            "required": 0,
            "basket_groups": [],
            "non_catalog": 1,
            "exception_reason": exception_reason or "",
            "catalog_ref": "",
        }
        for nm in names
    ]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
    filters = filters or {}
    school = filters.get("school")
    search_txt = (txt or "").strip()
    like_txt = f"%{search_txt}%"

    db_filters = {}
    if school:
        db_filters["school"] = ["in", get_ancestor_schools(school) or [school]]

    or_filters = None
    if search_txt:
        or_filters = [
            ["Academic Year", "name", "like", like_txt],
            ["Academic Year", "academic_year_name", "like", like_txt],
        ]

    rows = frappe.get_list(
        "Academic Year",
        fields=["name", "academic_year_name"],
        filters=db_filters,
        or_filters=or_filters,
        order_by="year_start_date DESC, name DESC",
        start=int(start or 0),
        limit=int(page_len or 20),
    )
    return [[r.get("name"), (r.get("academic_year_name") or r.get("name"))] for r in rows]


@frappe.whitelist()
def create_draft_tuition_invoice(program_offering: str, account_holder: str, posting_date: str, items: str):
    if not program_offering:
        frappe.throw(_("Program Offering is required"))
    if not account_holder:
        frappe.throw(_("Account Holder is required"))
    if not posting_date:
        frappe.throw(_("Posting Date is required"))

    try:
        item_rows = frappe.parse_json(items) or []
    except Exception:
        item_rows = []

    if not item_rows:
        frappe.throw(_("At least one line item is required"))

    account_holder_org = frappe.db.get_value("Account Holder", account_holder, "organization")
    if not account_holder_org:
        frappe.throw(_("Account Holder organization is required"))

    school = frappe.db.get_value("Program Offering", program_offering, "school")
    if not school:
        frappe.throw(_("Program Offering is missing School"))
    offering_org = get_school_organization(school)
    if offering_org and offering_org != account_holder_org:
        frappe.throw(_("Program Offering must belong to the same Organization as the Account Holder"))

    invoice = frappe.new_doc("Sales Invoice")
    invoice.update(
        {
            "account_holder": account_holder,
            "organization": account_holder_org,
            "program_offering": program_offering,
            "posting_date": posting_date,
        }
    )

    for idx, row in enumerate(item_rows, start=1):
        billable_offering = (row or {}).get("billable_offering")
        if not billable_offering:
            frappe.throw(_("Row {0}: Billable Offering is required").format(idx))

        qty = flt((row or {}).get("qty") or 0)
        if qty <= 0:
            frappe.throw(_("Row {0}: Qty must be greater than zero").format(idx))

        rate = (row or {}).get("rate")
        if rate is None or rate == "":
            frappe.throw(_("Row {0}: Rate is required").format(idx))
        rate_val = flt(rate)
        if rate_val < 0:
            frappe.throw(_("Row {0}: Rate cannot be negative").format(idx))
        if rate_val == 0 and not (row or {}).get("description"):
            frappe.throw(_("Row {0}: Description is required for zero-rate lines").format(idx))

        charge_source = (row or {}).get("charge_source") or "Program Offering"
        item = invoice.append(
            "items",
            {
                "billable_offering": billable_offering,
                "qty": qty,
                "rate": rate_val,
                "student": (row or {}).get("student"),
                "description": (row or {}).get("description"),
                "charge_source": charge_source,
            },
        )
        if charge_source == "Program Offering":
            item.program_offering = program_offering

    invoice.insert()
    return {"sales_invoice": invoice.name}


def _user_school_chain(user: str) -> list[str]:
    """
    Return the staff Desk school visibility scope.

    - If the user's active Employee has a school, use that school plus descendants.
    - If the active Employee has no school, fall back to all schools in the
      employee organization's descendant scope.
    """
    return get_user_visible_schools(user)


def get_permission_query_conditions(user: str):
    """
    Limit list views to Program Offerings in the user's Desk school visibility scope.
    Admins/System Managers see everything.
    """
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    schools = _user_school_chain(user)
    if not schools:
        return "1=0"

    in_list = ", ".join(frappe.db.escape(s) for s in schools)
    return f"`tabProgram Offering`.`school` in ({in_list})"


def has_permission(doc, ptype: str, user: str) -> bool:
    """
    Doc-level enforcement:
    - Read/Write/Delete allowed iff doc.school is in the user's Desk school visibility scope
    - Admin/System Manager bypass
    - For Create (doc is usually None), defer to Role Permission Manager; restrict via link field filters in the UI.
    """
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    # For create, Frappe calls this with doc=None; leave it to RPR + link-field filters.
    if not doc:
        return True

    schools = _user_school_chain(user)
    if not schools:
        return False

    return doc.school in schools


def on_doctype_update():
    frappe.db.add_index("Program Offering", ["program", "school"])
