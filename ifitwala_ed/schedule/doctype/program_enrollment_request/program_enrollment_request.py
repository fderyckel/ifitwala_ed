# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.schedule.enrollment_request_utils import validate_program_enrollment_request


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
            frappe.throw(_("Invalid Request Kind: {0}").format(request_kind))
        self.request_kind = request_kind
        if request_kind == "Activity" and not self.activity_booking:
            frappe.throw(_("Activity Request Kind requires Activity Booking reference."))

        needs_snapshot = target_status in {"Submitted", "Under Review", "Approved"}

        if not needs_snapshot:
            return

        # New docs must be saved first (validator requires a name)
        if self.is_new():
            frappe.throw(_("Please save this request before submitting for validation."))

        # Stable basket fingerprint (unique, deterministic)
        current_courses = []
        seen = set()
        for r in self.courses or []:
            c = (r.course or "").strip()
            if not c or c in seen:
                continue
            seen.add(c)
            current_courses.append(c)
        current_courses.sort()

        # Read prior snapshot courses (if any) to avoid redundant revalidation
        prior_courses = None
        if self.validation_payload:
            try:
                payload = frappe.parse_json(self.validation_payload)
                prior_courses = payload.get("requested_courses")
                if isinstance(prior_courses, list):
                    prior_courses = sorted({(x or "").strip() for x in prior_courses if (x or "").strip()})
                else:
                    prior_courses = None
            except Exception:
                prior_courses = None

        status_changed = self.has_value_changed("status") if not self.is_new() else True
        basket_changed = (prior_courses is None) or (prior_courses != current_courses)

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

        # Force validation refresh (single truth)
        validate_program_enrollment_request(self.name, force=1)

        # Enforce gates after refresh
        if target_status == "Approved":
            if (self.validation_status or "").strip() != "Valid":
                frappe.throw(_("Request must be Valid before it can be Approved."))
            if int(self.requires_override or 0) == 1 and int(self.override_approved or 0) != 1:
                frappe.throw(
                    _("This request requires an override and must be override-approved before it can be Approved.")
                )


@frappe.whitelist()
def get_offering_catalog(program_offering):
    if not program_offering:
        frappe.throw(_("Program Offering is required."))

    rows = frappe.get_all(
        "Program Offering Course",
        filters={
            "parent": program_offering,
            "parenttype": "Program Offering",
        },
        fields=[
            "course",
            "course_name",
            "required",
            "elective_group",
            "capacity",
            "waitlist_enabled",
            "reserved_seats",
            "grade_scale",
        ],
        order_by="idx asc",
    )

    return rows


@frappe.whitelist()
def validate_enrollment_request(request_name):
    return validate_program_enrollment_request(request_name, force=1)
