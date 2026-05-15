from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.accounting.receivables import money


class BillingRun(Document):
    def validate(self):
        self._resolve_billing_plan()
        self._validate_scope()
        self._validate_payment_terms_template()
        self._set_runtime_fields()

    def _resolve_billing_plan(self):
        filters = {
            "organization": self.organization,
            "program_offering": self.program_offering,
            "academic_year": self.academic_year,
            "is_active": 1,
        }
        if self.billing_plan:
            if not frappe.db.exists("Program Billing Plan", {"name": self.billing_plan, **filters}):
                frappe.throw(_("Billing Run must use the active Program Billing Plan for this scope."))
            return

        matches = frappe.get_all("Program Billing Plan", filters=filters, pluck="name", limit=2)
        if not matches:
            frappe.throw(_("Create an active Program Billing Plan before generating a Billing Run."))
        if len(matches) > 1:
            frappe.throw(_("Only one active Program Billing Plan can exist for this Billing Run scope."))
        self.billing_plan = matches[0]

    def _validate_scope(self):
        school = frappe.db.get_value("Program Offering", self.program_offering, "school")
        if not school:
            frappe.throw(_("Program Offering is required."))
        if get_school_organization(school) != self.organization:
            frappe.throw(_("Billing Run Program Offering must belong to the same Organization."))

        billing_plan = frappe.db.get_value(
            "Program Billing Plan",
            self.billing_plan,
            ["organization", "program_offering", "academic_year"],
            as_dict=True,
        )
        if not billing_plan:
            frappe.throw(_("Billing Run requires a valid Program Billing Plan."))
        if billing_plan.organization != self.organization:
            frappe.throw(_("Billing Run Organization must match the Program Billing Plan Organization."))
        if billing_plan.program_offering != self.program_offering:
            frappe.throw(_("Billing Run Program Offering must match the Program Billing Plan Program Offering."))
        if billing_plan.academic_year != self.academic_year:
            frappe.throw(_("Billing Run Academic Year must match the Program Billing Plan Academic Year."))

        if self.due_date_from and self.due_date_to and self.due_date_from > self.due_date_to:
            frappe.throw(_("Due Date From cannot be later than Due Date To."))

    def _validate_payment_terms_template(self):
        if not self.payment_terms_template:
            return
        template = frappe.db.get_value(
            "Payment Terms Template",
            self.payment_terms_template,
            ["organization", "disabled"],
            as_dict=True,
        )
        if not template:
            frappe.throw(_("Payment Terms Template not found."))
        if template.organization != self.organization:
            frappe.throw(_("Payment Terms Template must belong to the same Organization."))
        if template.disabled:
            frappe.throw(_("Payment Terms Template is disabled."))

    def _set_runtime_fields(self):
        self.total_invoices = len(self.items or [])
        self.total_rows = sum(int(getattr(row, "billing_row_count", 0) or 0) for row in (self.items or []))
        self.total_amount = money(sum(money(getattr(row, "grand_total", 0) or 0) for row in (self.items or [])))
        if self.status == "Cancelled":
            return
        self.status = "Processed" if self.processed_on else "Draft"


@frappe.whitelist()
def generate_draft_invoices(billing_run: str) -> dict:
    doc = frappe.get_doc("Billing Run", billing_run)
    doc.check_permission("write")

    from ifitwala_ed.accounting.billing.invoice_generation import generate_draft_invoices_for_run

    return generate_draft_invoices_for_run(billing_run)
