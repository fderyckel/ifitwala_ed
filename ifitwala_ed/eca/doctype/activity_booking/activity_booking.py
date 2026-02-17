# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/eca/doctype/activity_booking/activity_booking.py

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document

ACTIVE_BOOKING_STATUSES = {"Submitted", "Waitlisted", "Offered", "Confirmed"}
ALL_STATUSES = {
    "Draft",
    "Submitted",
    "Waitlisted",
    "Offered",
    "Confirmed",
    "Cancelled",
    "Rejected",
    "Expired",
}


class ActivityBooking(Document):
    def validate(self):
        self._normalize_choices_json()
        self._validate_status()
        self._validate_confirmation_requirements()
        self._enforce_unique_active_booking()

    def _normalize_choices_json(self):
        choices = []
        raw = (self.choices_json or "").strip()
        if raw:
            try:
                parsed = frappe.parse_json(raw)
            except Exception:
                frappe.throw(_("Choices JSON must be valid JSON."))

            if not isinstance(parsed, list):
                frappe.throw(_("Choices JSON must be an array of Student Group names."))

            seen = set()
            for row in parsed:
                if isinstance(row, dict):
                    name = (row.get("student_group") or row.get("name") or "").strip()
                else:
                    name = (row or "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                choices.append(name)

        self.choices_json = json.dumps(choices, sort_keys=False)

    def _validate_status(self):
        status = (self.status or "Draft").strip() or "Draft"
        if status not in ALL_STATUSES:
            frappe.throw(_("Invalid Activity Booking status: {0}").format(status))
        self.status = status

    def _validate_confirmation_requirements(self):
        if self.status == "Confirmed" and not self.allocated_student_group:
            frappe.throw(_("Confirmed Activity Booking requires Allocated Student Group."))

        if self.status == "Confirmed" and int(self.payment_required or 0) == 1:
            if (self.amount or 0) > 0 and not self.account_holder:
                frappe.throw(_("Confirmed paid Activity Booking requires Account Holder."))

    def _enforce_unique_active_booking(self):
        if not self.program_offering or not self.student:
            return

        if self.status not in ACTIVE_BOOKING_STATUSES:
            return

        existing = frappe.get_all(
            "Activity Booking",
            filters={
                "name": ["!=", self.name or ""],
                "program_offering": self.program_offering,
                "student": self.student,
                "status": ["in", sorted(ACTIVE_BOOKING_STATUSES)],
            },
            fields=["name", "status"],
            limit=1,
        )
        if existing:
            row = existing[0]
            frappe.throw(
                _("Student already has an active booking ({0}) with status {1} for this offering.").format(
                    row.get("name"), row.get("status")
                ),
                title=_("Duplicate Active Booking"),
            )


def on_doctype_update():
    frappe.db.add_index(
        "Activity Booking",
        ["program_offering", "student", "status"],
        index_name="idx_activity_booking_offer_student_status",
    )
    frappe.db.add_index(
        "Activity Booking",
        ["allocated_student_group", "status"],
        index_name="idx_activity_booking_section_status",
    )


def get_permission_query_conditions(user: str):
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    roles = set(frappe.get_roles(user))
    staff_roles = {"Academic Admin", "Activity Coordinator", "Academic Staff"}
    if roles & staff_roles:
        return None

    student = frappe.db.get_value("Student", {"student_email": user}, "name")
    if student:
        return f"`tabActivity Booking`.`student` = {frappe.db.escape(student)}"

    guardian = frappe.db.get_value("Guardian", {"user": user}, "name")
    if guardian:
        students = frappe.get_all(
            "Guardian Student",
            filters={"parent": guardian, "parenttype": "Guardian"},
            pluck="student",
        )
        if not students:
            return "1=0"
        escaped = ", ".join(frappe.db.escape(s) for s in sorted(set(students)))
        return f"`tabActivity Booking`.`student` in ({escaped})"

    return "1=0"


def has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    ptype = (ptype or "read").lower()
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    roles = set(frappe.get_roles(user))
    staff_roles = {"Academic Admin", "Activity Coordinator", "Academic Staff"}
    if roles & staff_roles:
        return True

    student = frappe.db.get_value("Student", {"student_email": user}, "name")
    if student and doc and doc.student == student:
        return ptype in {"read", "write", "create"}

    guardian = frappe.db.get_value("Guardian", {"user": user}, "name")
    if guardian and doc:
        if frappe.db.exists(
            "Guardian Student",
            {"parent": guardian, "parenttype": "Guardian", "student": doc.student},
        ):
            return ptype in {"read", "write", "create"}

    return False
