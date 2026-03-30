# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form

from ifitwala_ed.schedule.basket_group_utils import get_offering_course_semantics
from ifitwala_ed.schedule.enrollment_request_utils import (
    build_program_enrollment_request_validation,
    validate_program_enrollment_request,
)


class ProgramEnrollmentRequest(Document):
    def validate(self):
        """
        Single enforcement point for PER workflow integrity.

        Rules:
        - If status is in gate states ("Submitted", "Under Review", "Approved"), we must have a validation snapshot.
        - Refresh snapshot only when needed (status moved into gate state OR basket changed).
        - If requires_override=1, status cannot be "Approved" unless override_approved=1.
        """
        target_status = (self.status or "").strip()
        request_kind = (self.request_kind or "Academic").strip() or "Academic"
        if request_kind not in {"Academic", "Activity"}:
            frappe.throw(_("Invalid Request Kind: {request_kind}.").format(request_kind=request_kind))
        self.request_kind = request_kind
        if request_kind == "Activity" and not self.activity_booking:
            frappe.throw(_("Activity Request Kind requires Activity Booking reference."))

        self._apply_offering_spine()
        self._sync_course_semantics_from_offering()
        self._validate_course_rows()

        needs_snapshot = target_status in {"Submitted", "Under Review", "Approved"}

        if not needs_snapshot:
            return

        # New docs must be saved first (validator requires a name)
        if self.is_new():
            frappe.throw(_("Please save this request before submitting for validation."))

        # Stable basket fingerprint (unique, deterministic, includes resolved basket semantics)
        current_rows = _normalize_request_rows(self.courses or [])

        # Read prior snapshot rows (if any) to avoid redundant revalidation
        prior_rows = None
        if self.validation_payload:
            try:
                payload = frappe.parse_json(self.validation_payload)
                prior_rows = payload.get("requested_rows")
                if isinstance(prior_rows, list):
                    prior_rows = _normalize_request_rows(prior_rows)
                else:
                    prior_courses = payload.get("requested_courses")
                    if isinstance(prior_courses, list):
                        prior_rows = [
                            {
                                "course": course_name,
                                "applied_basket_group": "",
                                "choice_rank": None,
                            }
                            for course_name in sorted({(x or "").strip() for x in prior_courses if (x or "").strip()})
                        ]
                    else:
                        prior_rows = None
            except Exception:
                prior_rows = None

        status_changed = self.has_value_changed("status") if not self.is_new() else True
        basket_changed = (prior_rows is None) or (prior_rows != current_rows)

        # If nothing relevant changed and we already have a snapshot, keep it (still enforce override gate)
        if (
            not status_changed
            and not basket_changed
            and (self.validation_status or "").strip() in {"Valid", "Invalid"}
            and self.validation_payload
        ):
            if (
                target_status == "Approved"
                and int(self.requires_override or 0) == 1
                and int(self.override_approved or 0) != 1
            ):
                frappe.throw(
                    _("This request requires an override and must be override-approved before it can be Approved.")
                )
            if target_status == "Approved" and (self.validation_status or "").strip() != "Valid":
                frappe.throw(_("Request must be Valid before it can be Approved."))
            return

        # Validate the current in-memory request snapshot before save persists it.
        _engine_payload, validation_updates = build_program_enrollment_request_validation(self, force=1)
        for fieldname, value in (validation_updates or {}).items():
            self.set(fieldname, value)

        # Enforce gates after refresh
        if target_status == "Approved":
            if (self.validation_status or "").strip() != "Valid":
                frappe.throw(_("Request must be Valid before it can be Approved."))
            if int(self.requires_override or 0) == 1 and int(self.override_approved or 0) != 1:
                frappe.throw(
                    _("This request requires an override and must be override-approved before it can be Approved.")
                )

    def _sync_course_semantics_from_offering(self):
        if not self.program_offering or not getattr(self, "courses", None):
            return

        offering_semantics = get_offering_course_semantics(self.program_offering)
        for row in self.courses or []:
            course = (row.course or "").strip()
            if not course:
                continue
            row.required = 1 if (offering_semantics.get(course) or {}).get("required") else 0

    def _validate_course_rows(self):
        if not getattr(self, "courses", None):
            return

        offering_semantics = get_offering_course_semantics(self.program_offering) if self.program_offering else {}
        gate_statuses = {"Submitted", "Under Review", "Approved"}
        seen = set()

        for idx, row in enumerate(self.courses or [], start=1):
            course = (row.course or "").strip()
            if not course:
                frappe.throw(_("Course row {row_number}: Course is required.").format(row_number=idx))
            if course in seen:
                frappe.throw(
                    _("Course row {row_number}: duplicate course {course}.").format(
                        row_number=idx,
                        course=course,
                    )
                )
            seen.add(course)

            semantics = offering_semantics.get(course) or {}
            allowed_groups = list(semantics.get("basket_groups") or [])
            applied_group = (row.applied_basket_group or "").strip()

            if applied_group and applied_group not in allowed_groups:
                frappe.throw(
                    _(
                        "Course row {row_number}: Applied Basket Group (Enrollment) {basket_group} is not allowed for course {course}."
                    ).format(
                        row_number=idx,
                        basket_group=applied_group,
                        course=course,
                    )
                )

            if not applied_group and len(allowed_groups) == 1 and not int(row.required or 0):
                row.applied_basket_group = allowed_groups[0]
                applied_group = allowed_groups[0]

            if row.choice_rank and not applied_group:
                frappe.throw(
                    _("Course row {row_number}: Choice Rank requires an Applied Basket Group (Enrollment).").format(
                        row_number=idx
                    )
                )

            if (self.status or "").strip() in gate_statuses and len(allowed_groups) > 1 and not applied_group:
                frappe.throw(
                    _(
                        "Course row {row_number}: select an Applied Basket Group (Enrollment) for course {course} before the request can advance."
                    ).format(
                        row_number=idx,
                        course=course,
                    )
                )

    def _apply_offering_spine(self):
        if not self.program_offering:
            return

        offering = frappe.db.get_value(
            "Program Offering",
            self.program_offering,
            ["program", "school"],
            as_dict=True,
        )
        if not offering:
            frappe.throw(
                _("Invalid Program Offering {program_offering}.").format(
                    program_offering=get_link_to_form("Program Offering", self.program_offering)
                )
            )

        self.program = offering.get("program")
        self.school = offering.get("school")

        ay_names = _offering_ay_names(self.program_offering)
        if not ay_names:
            frappe.throw(
                _(
                    "Program Offering {program_offering} must define at least one Academic Year before requests can be saved."
                ).format(program_offering=get_link_to_form("Program Offering", self.program_offering))
            )

        if self.academic_year:
            if self.academic_year not in ay_names:
                frappe.throw(
                    _("Academic Year {academic_year} is not part of Program Offering {program_offering}.").format(
                        academic_year=get_link_to_form("Academic Year", self.academic_year),
                        program_offering=get_link_to_form("Program Offering", self.program_offering),
                    )
                )
            return

        if len(ay_names) == 1:
            self.academic_year = ay_names[0]
            return

        frappe.throw(
            _("Please choose an Academic Year from this Program Offering: {academic_years}.").format(
                academic_years=", ".join(ay_names)
            )
        )


def _normalize_request_rows(rows):
    normalized = []
    seen = set()

    for row in rows or []:
        course = ((row or {}).get("course") or "").strip()
        if not course or course in seen:
            continue
        seen.add(course)
        normalized.append(
            {
                "course": course,
                "applied_basket_group": ((row or {}).get("applied_basket_group") or "").strip(),
                "choice_rank": (row or {}).get("choice_rank"),
            }
        )

    normalized.sort(
        key=lambda row: (
            row.get("course") or "",
            row.get("applied_basket_group") or "",
            "" if row.get("choice_rank") is None else str(row.get("choice_rank")),
        )
    )
    return normalized


def _offering_ay_names(offering: str) -> list[str]:
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


@frappe.whitelist()
def get_offering_catalog(program_offering):
    if not program_offering:
        frappe.throw(_("Program Offering is required."))

    return list(get_offering_course_semantics(program_offering).values())


@frappe.whitelist()
def validate_enrollment_request(request_name):
    return validate_program_enrollment_request(request_name, force=1)
