from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class BillingSchedule(Document):
    def validate(self):
        self._validate_scope()
        _refresh_schedule_runtime_state(self)

    def _validate_scope(self):
        enrollment = frappe.db.get_value(
            "Program Enrollment",
            self.program_enrollment,
            ["student", "program_offering", "academic_year"],
            as_dict=True,
        )
        if not enrollment:
            frappe.throw(_("Program Enrollment is required."))
        if enrollment.student != self.student:
            frappe.throw(_("Billing Schedule student must match Program Enrollment student."))
        if enrollment.program_offering != self.program_offering:
            frappe.throw(_("Billing Schedule Program Offering must match Program Enrollment Program Offering."))
        if enrollment.academic_year != self.academic_year:
            frappe.throw(_("Billing Schedule Academic Year must match Program Enrollment Academic Year."))

        billing_plan = frappe.db.get_value(
            "Program Billing Plan",
            self.billing_plan,
            ["organization", "program_offering", "academic_year"],
            as_dict=True,
        )
        if not billing_plan:
            frappe.throw(_("Program Billing Plan is required."))
        if billing_plan.organization != self.organization:
            frappe.throw(_("Billing Schedule Organization must match the Program Billing Plan Organization."))
        if billing_plan.program_offering != self.program_offering:
            frappe.throw(_("Billing Schedule Program Offering must match the Program Billing Plan Program Offering."))
        if billing_plan.academic_year != self.academic_year:
            frappe.throw(_("Billing Schedule Academic Year must match the Program Billing Plan Academic Year."))

        account_holder = frappe.db.get_value("Student", self.student, "account_holder")
        if not account_holder:
            frappe.throw(_("Student must have an Account Holder before a Billing Schedule can be saved."))
        if account_holder != self.account_holder:
            frappe.throw(_("Billing Schedule Account Holder must match the linked Student Account Holder."))


def refresh_billing_schedule(name: str) -> None:
    doc = frappe.get_doc("Billing Schedule", name)
    doc.save(ignore_permissions=True)


def _refresh_schedule_runtime_state(doc) -> None:
    rows = list(doc.rows or [])
    doc.total_rows = len(rows)
    doc.pending_rows = len([row for row in rows if row.status == "Pending"])
    doc.invoiced_rows = len([row for row in rows if row.status == "Invoiced"])

    if not rows:
        doc.status = "Pending"
        return
    if all(row.status == "Cancelled" for row in rows):
        doc.status = "Cancelled"
        return
    if all(row.status == "Invoiced" for row in rows):
        doc.status = "Invoiced"
        return
    if doc.pending_rows:
        doc.status = "Pending"
        return
    doc.status = "Adjusted"


@frappe.whitelist()
def generate_draft_invoice(billing_schedule: str, row_ids: list[str] | None = None) -> dict:
    doc = frappe.get_doc("Billing Schedule", billing_schedule)
    doc.check_permission("read")

    from ifitwala_ed.accounting.billing.invoice_generation import generate_draft_invoice_for_schedule

    parsed_row_ids = frappe.parse_json(row_ids) if row_ids else None
    return generate_draft_invoice_for_schedule(billing_schedule, row_ids=parsed_row_ids)
