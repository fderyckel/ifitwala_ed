# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py

import csv
import io
from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate
from frappe.utils.file_manager import save_file

from ifitwala_ed.schedule.basket_group_utils import get_offering_course_semantics
from ifitwala_ed.schedule.enrollment_request_utils import (
    materialize_program_enrollment_request,
    validate_program_enrollment_request,
)

QUEUE_THRESHOLD = 100
NON_TERMINAL_REQUEST_STATUSES = {"Draft", "Submitted", "Under Review", "Approved"}

ACTION_META = {
    "prepare_requests": {
        "label": _("Preparing requests"),
        "done_title": _("Request Preparation Finished"),
    },
    "validate_requests": {
        "label": _("Validating requests"),
        "done_title": _("Request Validation Finished"),
    },
    "approve_requests": {
        "label": _("Approving requests"),
        "done_title": _("Batch Approval Finished"),
    },
    "materialize_requests": {
        "label": _("Materializing enrollments"),
        "done_title": _("Batch Materialization Finished"),
    },
}


def _run_program_enrollment_tool_action(tool_doctype, tool_name, action):
    tool = frappe.get_doc(tool_doctype, tool_name)
    tool._run_action(action, batch_mode=True)


class ProgramEnrollmentTool(Document):
    @frappe.whitelist()
    def get_students(self):
        """Populate the child table based on source filters and pre-mark target collisions."""
        students = self._fetch_students()
        if not students:
            frappe.throw(_("No students found with the given criteria."))

        if self.new_program_offering and self.new_target_academic_year:
            target_enrollments = self._get_target_enrollments([s["student"] for s in students])
            for student in students:
                student["already_enrolled"] = 1 if student["student"] in target_enrollments else 0

        return students

    @frappe.whitelist()
    def prepare_requests(self):
        return self._dispatch_action("prepare_requests")

    @frappe.whitelist()
    def validate_requests(self):
        return self._dispatch_action("validate_requests")

    @frappe.whitelist()
    def approve_requests(self):
        return self._dispatch_action("approve_requests")

    @frappe.whitelist()
    def materialize_requests(self):
        return self._dispatch_action("materialize_requests")

    def _dispatch_action(self, action: str):
        if action not in ACTION_META:
            frappe.throw(_("Unsupported Program Enrollment Tool action: {0}").format(action))

        total = len(self.students or [])
        if total == 0:
            frappe.throw(_("No students in the list."))

        self._validate_destination_context()

        if total > QUEUE_THRESHOLD:
            frappe.enqueue(
                _run_program_enrollment_tool_action,
                queue="long",
                job_name=f"{action} {total} students PE Tool",
                tool_doctype=self.doctype,
                tool_name=self.name,
                action=action,
            )
            frappe.msgprint(
                _("{0} students queued for {1}. You will be notified when the job completes.").format(
                    total, ACTION_META[action]["label"].lower()
                )
            )
            return

        return self._run_action(action, batch_mode=False)

    def _run_action(self, action: str, *, batch_mode: bool):
        handlers = {
            "prepare_requests": self._run_prepare_requests,
            "validate_requests": self._run_validate_requests,
            "approve_requests": self._run_approve_requests,
            "materialize_requests": self._run_materialize_requests,
        }
        return handlers[action](batch_mode=batch_mode)

    def _run_prepare_requests(self, *, batch_mode: bool):
        student_ids = self._selected_student_ids()
        target_enrollments = self._get_target_enrollments(student_ids)
        target_requests = self._get_target_request_map(student_ids)
        source_enrollments = self._get_source_enrollment_map(student_ids)
        target_semantics = get_offering_course_semantics((self.new_program_offering or "").strip())
        target_courses_by_group = self._target_courses_by_group(target_semantics)

        counts = {
            "created_requests": 0,
            "already_requested": 0,
            "already_enrolled": 0,
            "needs_review": 0,
            "failed": 0,
        }
        issues = []
        total = len(self.students or [])

        for idx, row in enumerate(self.students or [], start=1):
            student = (getattr(row, "student", None) or "").strip()
            if not student:
                counts["failed"] += 1
                issues.append("(missing student),Missing student row in Program Enrollment Tool.")
                self._publish_progress(action="prepare_requests", position=idx, total=total, batch_mode=batch_mode)
                continue

            if student in target_enrollments:
                counts["already_enrolled"] += 1
                self._publish_progress(action="prepare_requests", position=idx, total=total, batch_mode=batch_mode)
                continue

            if student in target_requests:
                counts["already_requested"] += 1
                self._publish_progress(action="prepare_requests", position=idx, total=total, batch_mode=batch_mode)
                continue

            request_rows, review_notes = self._build_request_rows_for_student(
                source_enrollment=source_enrollments.get(student),
                target_semantics=target_semantics,
                target_courses_by_group=target_courses_by_group,
            )

            if not request_rows:
                counts["failed"] += 1
                issues.append(f"{student},No destination courses could be prepared for this student.")
                self._publish_progress(action="prepare_requests", position=idx, total=total, batch_mode=batch_mode)
                continue

            try:
                request = frappe.get_doc(
                    {
                        "doctype": "Program Enrollment Request",
                        "student": student,
                        "program_offering": self.new_program_offering,
                        "academic_year": self.new_target_academic_year,
                        "status": "Draft",
                        "courses": request_rows,
                    }
                )
                request.insert(ignore_permissions=True)
                counts["created_requests"] += 1

                if review_notes:
                    counts["needs_review"] += 1
                    for note in review_notes:
                        issues.append(f"{student},{note}")
            except Exception as exc:
                counts["failed"] += 1
                if getattr(frappe.flags, "in_test", False):
                    issues.append(f"{student},{frappe.get_traceback(with_context=False)}")
                else:
                    issues.append(f"{student},{exc}")

            self._publish_progress(action="prepare_requests", position=idx, total=total, batch_mode=batch_mode)

        return self._finalize_action(
            action="prepare_requests",
            counts=counts,
            issues=issues,
            batch_mode=batch_mode,
        )

    def _run_validate_requests(self, *, batch_mode: bool):
        request_map = self._get_target_request_map(self._selected_student_ids())
        counts = {
            "validated": 0,
            "already_valid": 0,
            "invalid": 0,
            "failed": 0,
        }
        issues = []
        total = len(self.students or [])

        for idx, row in enumerate(self.students or [], start=1):
            student = (getattr(row, "student", None) or "").strip()
            request_info = request_map.get(student)
            if not student or not request_info:
                counts["failed"] += 1
                issues.append(f"{student or '(missing student)'},No active Program Enrollment Request found.")
                self._publish_progress(action="validate_requests", position=idx, total=total, batch_mode=batch_mode)
                continue

            try:
                request = frappe.get_doc("Program Enrollment Request", request_info["name"])
                if request.status == "Draft":
                    request.status = "Submitted"
                    request.save(ignore_permissions=True)
                else:
                    validate_program_enrollment_request(request.name, force=1)
                    request.reload()

                if request.validation_status == "Valid":
                    if request_info.get("status") == "Approved":
                        counts["already_valid"] += 1
                    else:
                        counts["validated"] += 1
                else:
                    counts["invalid"] += 1
                    issues.append(f"{student},Request {request.name} is invalid and needs review.")
            except Exception as exc:
                counts["failed"] += 1
                issues.append(f"{student},{exc}")

            self._publish_progress(action="validate_requests", position=idx, total=total, batch_mode=batch_mode)

        return self._finalize_action(
            action="validate_requests",
            counts=counts,
            issues=issues,
            batch_mode=batch_mode,
        )

    def _run_approve_requests(self, *, batch_mode: bool):
        request_map = self._get_target_request_map(self._selected_student_ids())
        counts = {
            "approved": 0,
            "already_approved": 0,
            "blocked": 0,
            "failed": 0,
        }
        issues = []
        total = len(self.students or [])

        for idx, row in enumerate(self.students or [], start=1):
            student = (getattr(row, "student", None) or "").strip()
            request_info = request_map.get(student)
            if not student or not request_info:
                counts["blocked"] += 1
                issues.append(f"{student or '(missing student)'},No active Program Enrollment Request found.")
                self._publish_progress(action="approve_requests", position=idx, total=total, batch_mode=batch_mode)
                continue

            try:
                request = frappe.get_doc("Program Enrollment Request", request_info["name"])
                if request.status == "Approved" and request.validation_status == "Valid":
                    counts["already_approved"] += 1
                    self._publish_progress(action="approve_requests", position=idx, total=total, batch_mode=batch_mode)
                    continue

                if request.status == "Draft":
                    request.status = "Submitted"
                    request.save(ignore_permissions=True)
                    request.reload()
                else:
                    validate_program_enrollment_request(request.name, force=1)
                    request.reload()

                if request.validation_status != "Valid":
                    counts["blocked"] += 1
                    issues.append(f"{student},Request {request.name} is invalid and cannot be approved.")
                elif cint(request.requires_override):
                    counts["blocked"] += 1
                    issues.append(f"{student},Request {request.name} requires an override before approval.")
                else:
                    request.status = "Approved"
                    request.save(ignore_permissions=True)
                    counts["approved"] += 1
            except Exception as exc:
                counts["failed"] += 1
                issues.append(f"{student},{exc}")

            self._publish_progress(action="approve_requests", position=idx, total=total, batch_mode=batch_mode)

        return self._finalize_action(
            action="approve_requests",
            counts=counts,
            issues=issues,
            batch_mode=batch_mode,
        )

    def _run_materialize_requests(self, *, batch_mode: bool):
        request_map = self._get_target_request_map(self._selected_student_ids())
        counts = {
            "materialized": 0,
            "blocked": 0,
            "failed": 0,
        }
        issues = []
        total = len(self.students or [])
        enrollment_date = self._resolve_destination_enrollment_date()

        for idx, row in enumerate(self.students or [], start=1):
            student = (getattr(row, "student", None) or "").strip()
            request_info = request_map.get(student)
            if not student or not request_info:
                counts["blocked"] += 1
                issues.append(f"{student or '(missing student)'},No active Program Enrollment Request found.")
                self._publish_progress(action="materialize_requests", position=idx, total=total, batch_mode=batch_mode)
                continue

            try:
                request = frappe.get_doc("Program Enrollment Request", request_info["name"])
                if request.status != "Approved" or request.validation_status != "Valid":
                    counts["blocked"] += 1
                    issues.append(f"{student},Request {request.name} must be Approved and Valid before materializing.")
                else:
                    materialize_program_enrollment_request(request.name, enrollment_date=enrollment_date)
                    counts["materialized"] += 1
            except Exception as exc:
                counts["failed"] += 1
                issues.append(f"{student},{exc}")

            self._publish_progress(action="materialize_requests", position=idx, total=total, batch_mode=batch_mode)

        return self._finalize_action(
            action="materialize_requests",
            counts=counts,
            issues=issues,
            batch_mode=batch_mode,
        )

    def _fetch_students(self):
        """Return list of dicts with keys: student, student_name, student_cohort."""
        out = []
        if self.get_students_from == "Cohort":
            if not self.student_cohort:
                frappe.throw(_("Please specify the Student Cohort."))
            out = frappe.get_all(
                "Student",
                filters={"cohort": self.student_cohort, "enabled": 1},
                fields=["name as student", "student_full_name as student_name", "cohort as student_cohort"],
            )
        elif self.get_students_from == "Program Enrollment":
            if not self.target_academic_year or not self.program_offering:
                frappe.throw(_("Please specify both Source Program Offering and Source Academic Year."))
            filters = {
                "program_offering": self.program_offering,
                "academic_year": self.target_academic_year,
            }
            if self.student_cohort:
                filters["cohort"] = self.student_cohort
            out = frappe.get_all(
                "Program Enrollment",
                filters=filters,
                fields=["student", "student_name", "cohort as student_cohort"],
                order_by="student_name asc",
            )
            ids = [student["student"] for student in out]
            if ids:
                disabled = set(frappe.get_all("Student", filters={"name": ["in", ids], "enabled": 0}, pluck="name"))
                out = [student for student in out if student["student"] not in disabled]
        else:
            frappe.throw(_("Unsupported source {0}.").format(self.get_students_from))
        return out

    def _selected_student_ids(self) -> list[str]:
        output = []
        seen = set()
        for row in self.students or []:
            student = (getattr(row, "student", None) or "").strip()
            if not student or student in seen:
                continue
            seen.add(student)
            output.append(student)
        return output

    def _validate_destination_context(self):
        if not self.new_program_offering or not self.new_target_academic_year:
            frappe.throw(_("Destination Program Offering and Destination Academic Year are required."))

    def _resolve_destination_enrollment_date(self):
        year_doc = frappe.get_doc("Academic Year", self.new_target_academic_year)
        if not getattr(year_doc, "year_start_date", None) or not getattr(year_doc, "year_end_date", None):
            frappe.throw(_("Selected Academic Year must have start and end dates."))

        ay_start = getdate(year_doc.year_start_date)
        ay_end = getdate(year_doc.year_end_date)
        enrollment_date = getdate(self.new_enrollment_date) if self.new_enrollment_date else ay_start
        if not (ay_start <= enrollment_date <= ay_end):
            frappe.throw(_("Destination enrollment date must fall inside the selected Destination Academic Year."))
        return enrollment_date

    def _get_target_enrollments(self, student_ids: list[str]) -> set[str]:
        if not student_ids:
            return set()
        return set(
            frappe.get_all(
                "Program Enrollment",
                filters={
                    "program_offering": self.new_program_offering,
                    "academic_year": self.new_target_academic_year,
                    "student": ["in", student_ids],
                },
                pluck="student",
            )
        )

    def _get_target_request_map(self, student_ids: list[str]) -> dict[str, dict]:
        if not student_ids:
            return {}
        rows = frappe.get_all(
            "Program Enrollment Request",
            filters={
                "student": ["in", student_ids],
                "program_offering": self.new_program_offering,
                "academic_year": self.new_target_academic_year,
                "status": ["in", list(NON_TERMINAL_REQUEST_STATUSES)],
            },
            fields=["name", "student", "status", "validation_status", "requires_override", "modified"],
            order_by="modified desc",
            limit_page_length=5000,
        )
        output = {}
        for row in rows:
            if row.student in output:
                continue
            output[row.student] = row
        return output

    def _get_source_enrollment_map(self, student_ids: list[str]) -> dict[str, dict]:
        if self.get_students_from != "Program Enrollment" or not student_ids:
            return {}

        source_rows = frappe.get_all(
            "Program Enrollment",
            filters={
                "student": ["in", student_ids],
                "program_offering": self.program_offering,
                "academic_year": self.target_academic_year,
            },
            fields=["name", "student"],
            order_by="modified desc",
            limit_page_length=5000,
        )
        output = {}
        parent_to_student = {}
        for row in source_rows:
            if row.student in output:
                continue
            output[row.student] = {"name": row.name, "courses": []}
            parent_to_student[row.name] = row.student

        if not parent_to_student:
            return output

        course_rows = frappe.get_all(
            "Program Enrollment Course",
            filters={
                "parent": ["in", list(parent_to_student.keys())],
                "parenttype": "Program Enrollment",
            },
            fields=["parent", "course", "status", "credited_basket_group"],
            order_by="idx asc",
            limit_page_length=5000,
        )
        for row in course_rows:
            student = parent_to_student.get(row.parent)
            if not student:
                continue
            output.setdefault(student, {"name": row.parent, "courses": []})["courses"].append(row)

        return output

    def _target_courses_by_group(self, target_semantics: dict[str, dict]) -> dict[str, list[str]]:
        output: dict[str, list[str]] = defaultdict(list)
        for course, semantics in target_semantics.items():
            if cint(semantics.get("required")):
                continue
            for basket_group in semantics.get("basket_groups") or []:
                output[basket_group].append(course)
        return output

    def _build_request_rows_for_student(self, *, source_enrollment, target_semantics, target_courses_by_group):
        rows = []
        seen = set()
        review_notes = []

        for course, semantics in target_semantics.items():
            if not cint(semantics.get("required")):
                continue
            rows.append(
                {
                    "course": course,
                    "required": 1,
                    "applied_basket_group": "",
                    "choice_rank": None,
                }
            )
            seen.add(course)

        for source_row in (source_enrollment or {}).get("courses") or []:
            source_course = (source_row.course or "").strip()
            status = (source_row.status or "").strip()
            source_group = (source_row.credited_basket_group or "").strip()
            if not source_course or status == "Dropped":
                continue

            target_course = None
            applied_group = ""
            allowed_groups = []

            if source_course in target_semantics:
                target_course = source_course
                allowed_groups = list((target_semantics.get(target_course) or {}).get("basket_groups") or [])
                applied_group = self._resolve_applied_basket_group(
                    allowed_groups=allowed_groups,
                    source_group=source_group,
                    allow_blank=True,
                )
                if len(allowed_groups) > 1 and not applied_group:
                    review_notes.append(_("Request needs a basket-group choice for course {0}.").format(source_course))
            elif source_group and len(target_courses_by_group.get(source_group) or []) == 1:
                target_course = target_courses_by_group[source_group][0]
                allowed_groups = list((target_semantics.get(target_course) or {}).get("basket_groups") or [])
                applied_group = source_group if source_group in allowed_groups else ""

            if not target_course or target_course in seen:
                continue

            semantics = target_semantics.get(target_course) or {}
            if cint(semantics.get("required")):
                continue

            rows.append(
                {
                    "course": target_course,
                    "required": 0,
                    "applied_basket_group": applied_group,
                    "choice_rank": None,
                }
            )
            seen.add(target_course)

        return rows, review_notes

    def _resolve_applied_basket_group(self, *, allowed_groups: list[str], source_group: str, allow_blank: bool):
        if not allowed_groups:
            return ""
        if len(allowed_groups) == 1:
            return allowed_groups[0]
        if source_group and source_group in allowed_groups:
            return source_group
        return "" if allow_blank else None

    def _publish_progress(self, *, action: str, position: int, total: int, batch_mode: bool):
        if batch_mode:
            return
        frappe.publish_realtime(
            "program_enrollment_tool",
            {
                "action": action,
                "action_label": ACTION_META[action]["label"],
                "progress": [position, total],
            },
            user=frappe.session.user,
        )

    def _finalize_action(self, *, action: str, counts: dict, issues: list[str], batch_mode: bool):
        summary = {
            "action": action,
            "title": ACTION_META[action]["done_title"],
            "counts": counts,
        }

        if issues:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["student", "detail"])
            for line in issues:
                parts = (line or "").split(",", 1)
                writer.writerow(parts if len(parts) == 2 else [parts[0], ""])
            filedoc = save_file(
                f"program_enrollment_tool_{action}_{self.name}.csv",
                buf.getvalue(),
                self.doctype,
                self.name,
                is_private=1,
            )
            summary["details_link"] = filedoc.file_url

        if batch_mode:
            frappe.publish_realtime("program_enrollment_tool_done", summary, user=self.owner)
        else:
            message = ", ".join(
                _("{0}: {1}").format(self._humanize_count_key(key), value) for key, value in counts.items()
            )
            if summary.get("details_link"):
                message += '<br><a href="{0}" target="_blank">{1}</a>'.format(
                    summary["details_link"], _("Download details CSV")
                )
            frappe.msgprint({"title": summary["title"], "message": message, "indicator": "green"})

        return summary

    def _humanize_count_key(self, key: str) -> str:
        return key.replace("_", " ").title()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(
        """
        SELECT name
        FROM `tabAcademic Year`
        WHERE name LIKE %(txt)s
        ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {"txt": f"%{txt}%", "start": start, "page_len": page_len},
    )


def _get_offering_window(program_offering: str):
    """
    Return (start_date, end_date) as date objects for a Program Offering.

    Preferred source: Program Offering Academic Year child rows (min/max of their AY dates).
    Fallback: Program Offering.start_date / .end_date on the parent.
    """
    if not program_offering:
        return None, None

    min_max = frappe.db.sql(
        """
        SELECT MIN(year_start_date), MAX(year_end_date)
        FROM `tabProgram Offering Academic Year`
        WHERE parent = %(po)s AND parenttype = 'Program Offering'
        """,
        {"po": program_offering},
        as_dict=False,
    )
    child_start, child_end = min_max[0] if min_max else (None, None)

    if child_start or child_end:
        return (getdate(child_start) if child_start else None, getdate(child_end) if child_end else None)

    row = frappe.db.get_value("Program Offering", program_offering, ["start_date", "end_date"], as_dict=True) or {}
    start = getdate(row.get("start_date")) if row.get("start_date") else None
    end = getdate(row.get("end_date")) if row.get("end_date") else None
    return start, end


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def program_offering_target_ay_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Return Academic Years explicitly linked to the Program Offering (child rows),
    ordered by AY start date desc. If no child rows exist, fall back to AYs that
    overlap the offering's (start_date, end_date) window.
    """
    po = (filters or {}).get("program_offering")
    if not po:
        return []

    params = {
        "po": po,
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len,
    }

    rows = frappe.db.sql(
        """
        SELECT poay.academic_year
        FROM `tabProgram Offering Academic Year` poay
        WHERE poay.parent = %(po)s
          AND poay.parenttype = 'Program Offering'
          AND (poay.academic_year LIKE %(txt)s OR IFNULL(poay.ay_name, '') LIKE %(txt)s)
        ORDER BY COALESCE(poay.year_start_date, '0001-01-01') DESC, poay.academic_year DESC
        LIMIT %(start)s, %(page_len)s
        """,
        params,
    )
    if rows:
        return rows

    off_start, off_end = _get_offering_window(po)
    if not (off_start or off_end):
        return []

    clauses = ["name LIKE %(txt)s"]
    if off_start and off_end:
        clauses += [
            "COALESCE(year_start_date, '0001-01-01') <= %(off_end)s",
            "COALESCE(year_end_date,   '9999-12-31') >= %(off_start)s",
        ]
        params.update({"off_start": off_start, "off_end": off_end})
    elif off_start:
        clauses.append("COALESCE(year_end_date, '9999-12-31') >= %(off_start)s")
        params["off_start"] = off_start
    elif off_end:
        clauses.append("COALESCE(year_start_date, '0001-01-01') <= %(off_end)s")
        params["off_end"] = off_end

    where_sql = " AND ".join(clauses)
    return frappe.db.sql(
        f"""
        SELECT name
        FROM `tabAcademic Year`
        WHERE {where_sql}
        ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
        LIMIT %(start)s, %(page_len)s
        """,
        params,
    )
