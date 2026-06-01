from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.accounting.receivables import is_zero, money


class ChargeBatch(Document):
    def validate(self):
        self._validate_source_reference()
        self._validate_dates_and_amounts()
        self._validate_billable_offering()
        self._validate_payment_terms_template()
        self._resolve_student_rows()
        self._set_runtime_fields()

    def _validate_source_reference(self):
        if self.source_name and not self.source_doctype:
            frappe.throw(_("Source DocType is required when Source Record is set."))
        if self.source_doctype and self.source_name and not frappe.db.exists(self.source_doctype, self.source_name):
            frappe.throw(
                _("Source Record {source_name} was not found in {source_doctype}.").format(
                    source_name=self.source_name,
                    source_doctype=self.source_doctype,
                )
            )

    def _validate_dates_and_amounts(self):
        if flt(self.default_qty or 0) <= 0:
            frappe.throw(_("Default Qty must be greater than zero."))
        if flt(self.default_rate or 0) < 0:
            frappe.throw(_("Default Rate cannot be negative."))
        if is_zero(flt(self.default_rate or 0)) and not (self.description or "").strip():
            frappe.throw(_("Description is required for zero-rate batches."))
        if self.coverage_start and self.coverage_end and self.coverage_start > self.coverage_end:
            frappe.throw(_("Coverage Start cannot be later than Coverage End."))
        if not self.payment_terms_template and not self.due_date:
            frappe.throw(_("Due Date is required when no Payment Terms Template is selected."))

    def _validate_billable_offering(self):
        offering = frappe.db.get_value(
            "Billable Offering",
            self.billable_offering,
            ["organization", "disabled"],
            as_dict=True,
        )
        if not offering:
            frappe.throw(_("Billable Offering {offering} was not found.").format(offering=self.billable_offering))
        if offering.organization != self.organization:
            frappe.throw(_("Billable Offering must belong to the same Organization as the Charge Batch."))
        if offering.disabled:
            frappe.throw(_("Billable Offering is disabled."))

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
            frappe.throw(
                _("Payment Terms Template {template} was not found.").format(template=self.payment_terms_template)
            )
        if template.organization != self.organization:
            frappe.throw(_("Payment Terms Template must belong to the same Organization as the Charge Batch."))
        if template.disabled:
            frappe.throw(_("Payment Terms Template is disabled."))

    def _resolve_student_rows(self):
        if not self.students:
            frappe.throw(_("At least one student is required."))

        seen_students: set[str] = set()
        charge_names = sorted({row.billable_charge for row in self.students if row.billable_charge})
        charge_map = {}
        if charge_names:
            charge_map = {
                row.get("name"): row
                for row in frappe.get_all(
                    "Billable Charge",
                    filters={"name": ["in", charge_names]},
                    fields=["name", "charge_batch", "student", "status", "sales_invoice", "account_holder"],
                    limit=len(charge_names),
                )
            }

        for row in self.students:
            student_name = (row.student or "").strip()
            row.issue = ""

            if not student_name:
                row.status = "Blocked"
                row.issue = _("Student is required.")
                continue

            if student_name in seen_students:
                row.status = "Blocked"
                row.issue = _("Student is duplicated in this Charge Batch.")
                row.account_holder = None
                continue
            seen_students.add(student_name)

            charge = charge_map.get(row.billable_charge)
            if row.billable_charge and not charge:
                row.status = "Blocked"
                row.issue = _("Linked Billable Charge was not found.")
                row.account_holder = None
                row.sales_invoice = None
                continue
            if charge and charge.get("charge_batch") != self.name:
                row.status = "Blocked"
                row.issue = _("Linked Billable Charge belongs to another Charge Batch.")
                row.account_holder = None
                row.sales_invoice = None
                continue
            if charge and charge.get("student") != student_name:
                row.status = "Blocked"
                row.issue = _("Linked Billable Charge belongs to another Student.")
                row.account_holder = None
                row.sales_invoice = None
                continue
            if charge:
                row.account_holder = charge.get("account_holder")
                row.sales_invoice = charge.get("sales_invoice")
                if charge.get("status") == "Invoiced":
                    row.status = "Invoiced"
                elif charge.get("status") == "Cancelled":
                    row.status = "Cancelled"
                else:
                    row.status = "Charge Created"
                continue

            student = frappe.db.get_value(
                "Student",
                student_name,
                ["student_full_name", "anchor_school", "account_holder"],
                as_dict=True,
            )
            if not student:
                row.status = "Blocked"
                row.issue = _("Student was not found.")
                row.account_holder = None
                continue

            row.student_name = student.student_full_name or student_name
            if not student.anchor_school:
                row.status = "Blocked"
                row.issue = _("Student is missing Anchor School.")
                row.account_holder = None
                continue

            try:
                student_organization = get_school_organization(student.anchor_school)
            except Exception as exc:
                row.status = "Blocked"
                row.issue = str(exc)
                row.account_holder = None
                continue

            if student_organization != self.organization:
                row.status = "Blocked"
                row.issue = _("Student belongs to a different Organization.")
                row.account_holder = None
                continue

            if not student.account_holder:
                row.status = "Blocked"
                row.issue = _("Student needs an Account Holder before charging.")
                row.account_holder = None
                continue

            account_holder_organization = frappe.db.get_value("Account Holder", student.account_holder, "organization")
            if account_holder_organization != self.organization:
                row.status = "Blocked"
                row.issue = _("Student Account Holder belongs to a different Organization.")
                row.account_holder = student.account_holder
                continue

            row.account_holder = student.account_holder
            row.status = "Ready"

    def _set_runtime_fields(self):
        self.total_charges = len([row for row in self.students or [] if row.billable_charge])
        self.total_invoices = len(self.invoices or [])
        self.total_amount = money(sum(money(row.grand_total or 0) for row in (self.invoices or [])))
        if self.status == "Cancelled":
            return
        if self.invoices:
            self.status = "Invoiced"
        elif any(row.billable_charge for row in (self.students or [])):
            self.status = "Charges Created"
        else:
            self.status = "Draft"


@frappe.whitelist()
def resolve_students(charge_batch: str) -> dict:
    doc = frappe.get_doc("Charge Batch", charge_batch)
    doc.check_permission("write")
    doc.save()
    return _summarize_batch(doc)


@frappe.whitelist()
def create_pending_charges(charge_batch: str) -> dict:
    doc = frappe.get_doc("Charge Batch", charge_batch)
    doc.check_permission("write")

    from ifitwala_ed.accounting.charges.charge_generation import create_pending_charges_for_batch

    return create_pending_charges_for_batch(charge_batch)


@frappe.whitelist()
def generate_draft_invoices(charge_batch: str) -> dict:
    doc = frappe.get_doc("Charge Batch", charge_batch)
    doc.check_permission("write")
    doc.save()

    from ifitwala_ed.accounting.charges.charge_generation import generate_draft_invoices_for_charge_batch_or_enqueue

    return generate_draft_invoices_for_charge_batch_or_enqueue(charge_batch, target_user=frappe.session.user)


def _summarize_batch(doc) -> dict:
    rows = list(doc.students or [])
    return {
        "charge_batch": doc.name,
        "ready_count": len([row for row in rows if row.status == "Ready"]),
        "blocked_count": len([row for row in rows if row.status == "Blocked"]),
        "charge_created_count": len([row for row in rows if row.status == "Charge Created"]),
        "invoiced_count": len([row for row in rows if row.status == "Invoiced"]),
        "cancelled_count": len([row for row in rows if row.status == "Cancelled"]),
        "charge_count": len([row for row in rows if row.billable_charge]),
        "invoice_count": len(doc.invoices or []),
        "invoice_generation_status": doc.invoice_generation_status,
        "invoice_generation_progress": doc.invoice_generation_progress,
        "invoice_generation_error": doc.invoice_generation_error,
    }
