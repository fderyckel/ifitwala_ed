# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime

from ifitwala_ed.schedule.basket_group_utils import get_offering_course_semantics
from ifitwala_ed.schedule.program_enrollment_request_seed import (
    build_request_rows_for_student,
    create_draft_request,
    get_source_enrollment_map,
    get_target_enrollments,
    get_target_request_map,
    target_courses_by_group,
)

WINDOW_STATUS_OPTIONS = {"Draft", "Open", "Closed", "Archived"}
WINDOW_AUDIENCE_OPTIONS = {"Student", "Guardian"}
SOURCE_MODE_OPTIONS = {"Program Enrollment", "Cohort", "Manual"}


class ProgramOfferingSelectionWindow(Document):
    def validate(self):
        self._validate_status()
        self._validate_program_offering_context()
        self._validate_source_mode()
        self._normalize_student_rows()

    def _validate_status(self):
        status = (self.status or "Draft").strip() or "Draft"
        if status not in WINDOW_STATUS_OPTIONS:
            frappe.throw(_("Invalid Program Offering Selection Window status: {0}.").format(status))
        self.status = status

        audience = (self.audience or "").strip()
        if audience not in WINDOW_AUDIENCE_OPTIONS:
            frappe.throw(_("Audience must be Student or Guardian."))
        self.audience = audience

        if self.open_from and self.due_on:
            if get_datetime(self.open_from) > get_datetime(self.due_on):
                frappe.throw(_("Opening time cannot be after the submission deadline."))

    def _validate_program_offering_context(self):
        if not self.program_offering:
            frappe.throw(_("Program Offering is required."))
        if not self.academic_year:
            frappe.throw(_("Academic Year is required."))

        offering = frappe.db.get_value(
            "Program Offering",
            self.program_offering,
            ["program", "school", "allow_self_enroll"],
            as_dict=True,
        )
        if not offering:
            frappe.throw(_("Program Offering {0} does not exist.").format(self.program_offering))
        if cint(offering.get("allow_self_enroll") or 0) != 1:
            frappe.throw(
                _(
                    "Program Offering {0} must have Allow Self Enroll enabled before a selection window can open."
                ).format(self.program_offering)
            )

        ay_names = frappe.get_all(
            "Program Offering Academic Year",
            filters={"parent": self.program_offering, "parenttype": "Program Offering"},
            pluck="academic_year",
            order_by="idx asc",
        )
        if self.academic_year not in set(ay_names or []):
            frappe.throw(
                _("Academic Year {0} is not part of Program Offering {1}.").format(
                    self.academic_year,
                    self.program_offering,
                )
            )

        self.program = offering.get("program")
        self.school = offering.get("school")

    def _validate_source_mode(self):
        source_mode = (self.source_mode or "Manual").strip() or "Manual"
        if source_mode not in SOURCE_MODE_OPTIONS:
            frappe.throw(_("Invalid source mode: {0}.").format(source_mode))
        self.source_mode = source_mode

        if source_mode == "Program Enrollment":
            if not self.source_program_offering or not self.source_academic_year:
                frappe.throw(_("Source Program Offering and Source Academic Year are required for this source mode."))
        elif source_mode == "Cohort":
            if not self.source_student_cohort:
                frappe.throw(_("Source Student Cohort is required for this source mode."))

    def _normalize_student_rows(self):
        rows = []
        seen = set()
        for row in self.get("students") or []:
            student = (row.student or "").strip()
            if not student or student in seen:
                continue
            seen.add(student)
            rows.append(
                {
                    "student": student,
                    "student_name": (row.student_name or "").strip(),
                    "student_cohort": (row.student_cohort or "").strip(),
                    "source_program_enrollment": (row.source_program_enrollment or "").strip(),
                    "program_enrollment_request": (row.program_enrollment_request or "").strip(),
                }
            )
        if rows != [
            {
                "student": (row.student or "").strip(),
                "student_name": (row.student_name or "").strip(),
                "student_cohort": (row.student_cohort or "").strip(),
                "source_program_enrollment": (row.source_program_enrollment or "").strip(),
                "program_enrollment_request": (row.program_enrollment_request or "").strip(),
            }
            for row in self.get("students") or []
            if (row.student or "").strip()
        ]:
            self.set("students", rows)

    def _fetch_source_students(self) -> list[dict]:
        if self.source_mode == "Manual":
            output = []
            for row in self.students or []:
                student = (row.student or "").strip()
                if not student:
                    continue
                output.append(
                    {
                        "student": student,
                        "student_name": (row.student_name or "").strip(),
                        "student_cohort": (row.student_cohort or "").strip(),
                        "source_program_enrollment": (row.source_program_enrollment or "").strip(),
                    }
                )
            return output

        if self.source_mode == "Cohort":
            return frappe.get_all(
                "Student",
                filters={"cohort": self.source_student_cohort, "enabled": 1},
                fields=[
                    "name as student",
                    "student_full_name as student_name",
                    "cohort as student_cohort",
                ],
                order_by="student_full_name asc, name asc",
            )

        rows = frappe.get_all(
            "Program Enrollment",
            filters={
                "program_offering": self.source_program_offering,
                "academic_year": self.source_academic_year,
            },
            fields=["name", "student", "student_name", "cohort as student_cohort"],
            order_by="student_name asc, student asc",
        )
        if self.source_student_cohort:
            rows = [row for row in rows if (row.get("student_cohort") or "").strip() == self.source_student_cohort]
        return [
            {
                "student": row.get("student"),
                "student_name": row.get("student_name"),
                "student_cohort": row.get("student_cohort"),
                "source_program_enrollment": row.get("name"),
            }
            for row in rows
            if row.get("student")
        ]

    @frappe.whitelist()
    def load_students(self):
        students = self._fetch_source_students()
        if not students:
            frappe.throw(_("No students found with the current source filters."))
        self.set("students", students)
        self.save(ignore_permissions=True)
        return students

    @frappe.whitelist()
    def prepare_requests(self):
        if not self.students:
            self.load_students()

        student_ids = [(row.student or "").strip() for row in self.students or [] if (row.student or "").strip()]
        if not student_ids:
            frappe.throw(_("Add at least one student before preparing requests."))

        target_enrollments = get_target_enrollments(
            student_ids=student_ids,
            program_offering=self.program_offering,
            academic_year=self.academic_year,
        )
        target_requests = get_target_request_map(
            student_ids=student_ids,
            program_offering=self.program_offering,
            academic_year=self.academic_year,
        )
        source_enrollments = (
            get_source_enrollment_map(
                student_ids=student_ids,
                program_offering=self.source_program_offering,
                academic_year=self.source_academic_year,
            )
            if self.source_mode == "Program Enrollment"
            else {}
        )
        target_semantics = get_offering_course_semantics((self.program_offering or "").strip())
        target_courses_by_group_map = target_courses_by_group(target_semantics)

        counts = {
            "created_requests": 0,
            "already_requested": 0,
            "already_enrolled": 0,
            "needs_review": 0,
            "failed": 0,
        }
        issues = []
        kept_rows = []

        for row in self.students or []:
            student = (row.student or "").strip()
            if not student:
                counts["failed"] += 1
                issues.append("(missing student),Missing student row in selection window.")
                continue

            if student in target_enrollments:
                counts["already_enrolled"] += 1
                issues.append(f"{student},Skipped because the student already has a target Program Enrollment.")
                continue

            existing_request = target_requests.get(student)
            if existing_request:
                row.program_enrollment_request = existing_request.get("name")
                if not (existing_request.get("selection_window") or "").strip():
                    frappe.db.set_value(
                        "Program Enrollment Request",
                        existing_request.get("name"),
                        "selection_window",
                        self.name,
                        update_modified=False,
                    )
                elif (existing_request.get("selection_window") or "").strip() != self.name:
                    issues.append(
                        _("{0},Active request {1} is already linked to another selection window.").format(
                            student, existing_request.get("name")
                        )
                    )
                counts["already_requested"] += 1
                kept_rows.append(
                    {
                        "student": student,
                        "student_name": (row.student_name or "").strip(),
                        "student_cohort": (row.student_cohort or "").strip(),
                        "source_program_enrollment": (row.source_program_enrollment or "").strip(),
                        "program_enrollment_request": (row.program_enrollment_request or "").strip(),
                    }
                )
                continue

            request_rows, review_notes = build_request_rows_for_student(
                source_enrollment=source_enrollments.get(student),
                target_semantics=target_semantics,
                target_courses_by_group_map=target_courses_by_group_map,
            )

            if not request_rows:
                counts["failed"] += 1
                issues.append(f"{student},No destination courses could be prepared for this student.")
                continue

            try:
                request = create_draft_request(
                    student=student,
                    program_offering=self.program_offering,
                    academic_year=self.academic_year,
                    request_rows=request_rows,
                    selection_window=self.name if not self.is_new() else None,
                )
                row.program_enrollment_request = request.name
                counts["created_requests"] += 1
                if review_notes:
                    counts["needs_review"] += 1
                    for note in review_notes:
                        issues.append(f"{student},{note}")
                kept_rows.append(
                    {
                        "student": student,
                        "student_name": (row.student_name or "").strip(),
                        "student_cohort": (row.student_cohort or "").strip(),
                        "source_program_enrollment": (row.source_program_enrollment or "").strip(),
                        "program_enrollment_request": request.name,
                    }
                )
            except Exception as exc:
                counts["failed"] += 1
                issues.append(f"{student},{exc}")

        self.set("students", kept_rows)
        self.save(ignore_permissions=True)
        return {"counts": counts, "issues": issues}

    @frappe.whitelist()
    def open_window(self):
        if not self.students:
            frappe.throw(_("Load students and prepare requests before opening the portal window."))
        missing_requests = [
            row.student for row in self.students or [] if not (row.program_enrollment_request or "").strip()
        ]
        if missing_requests:
            frappe.throw(_("Every student in the window must have a linked Program Enrollment Request before opening."))

        self.status = "Open"
        if not self.open_from:
            self.open_from = now_datetime()
        self.save(ignore_permissions=True)
        return {"ok": True, "status": self.status}

    @frappe.whitelist()
    def close_window(self):
        self.status = "Closed"
        self.save(ignore_permissions=True)
        return {"ok": True, "status": self.status}
