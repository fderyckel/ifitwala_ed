from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.accounting.receivables import is_zero, money


class BillableCharge(Document):
    def validate(self):
        self._validate_source_reference()
        self._validate_dates_and_amounts()
        self._validate_batch_scope()
        self._validate_student_and_account_holder()
        self._validate_billable_offering()
        self._validate_invoice_link()
        self.amount = money(flt(self.qty or 0) * flt(self.rate or 0))

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
        if flt(self.qty or 0) <= 0:
            frappe.throw(_("Qty must be greater than zero."))
        if flt(self.rate or 0) < 0:
            frappe.throw(_("Rate cannot be negative."))
        if is_zero(flt(self.rate or 0)) and not (self.description or "").strip():
            frappe.throw(_("Description is required for zero-rate charges."))
        if self.coverage_start and self.coverage_end and self.coverage_start > self.coverage_end:
            frappe.throw(_("Coverage Start cannot be later than Coverage End."))
        if not self.payment_terms_template and not self.due_date:
            frappe.throw(_("Due Date is required when no Payment Terms Template is selected."))

    def _validate_batch_scope(self):
        if not self.charge_batch:
            return
        batch = frappe.db.get_value(
            "Charge Batch",
            self.charge_batch,
            [
                "organization",
                "billable_offering",
                "source_type",
                "source_doctype",
                "source_name",
                "payment_terms_template",
            ],
            as_dict=True,
        )
        if not batch:
            frappe.throw(_("Charge Batch {charge_batch} was not found.").format(charge_batch=self.charge_batch))
        if batch.organization != self.organization:
            frappe.throw(_("Billable Charge Organization must match Charge Batch Organization."))
        if batch.billable_offering != self.billable_offering:
            frappe.throw(_("Billable Charge Offering must match Charge Batch Offering."))
        if (batch.payment_terms_template or "") != (self.payment_terms_template or ""):
            frappe.throw(_("Billable Charge Payment Terms must match Charge Batch Payment Terms."))
        self.source_type = self.source_type or batch.source_type
        self.source_doctype = self.source_doctype or batch.source_doctype
        self.source_name = self.source_name or batch.source_name

    def _validate_student_and_account_holder(self):
        student = frappe.db.get_value(
            "Student",
            self.student,
            ["student_full_name", "anchor_school", "account_holder"],
            as_dict=True,
        )
        if not student:
            frappe.throw(_("Student {student} was not found.").format(student=self.student))
        if not student.anchor_school:
            frappe.throw(_("Student {student} is missing Anchor School.").format(student=self.student))

        student_organization = get_school_organization(student.anchor_school)
        if student_organization != self.organization:
            frappe.throw(_("Student must belong to the same Organization as the Billable Charge."))
        if not student.account_holder:
            frappe.throw(
                _("Student {student} needs an Account Holder before this charge can be invoiced.").format(
                    student=self.student
                )
            )
        if student.account_holder != self.account_holder:
            frappe.throw(_("Billable Charge Account Holder must match the Student Account Holder."))

        account_holder_organization = frappe.db.get_value("Account Holder", self.account_holder, "organization")
        if not account_holder_organization:
            frappe.throw(_("Account Holder {account_holder} was not found.").format(account_holder=self.account_holder))
        if account_holder_organization != self.organization:
            frappe.throw(_("Account Holder must belong to the same Organization as the Billable Charge."))

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
            frappe.throw(_("Billable Offering must belong to the same Organization as the Billable Charge."))
        if offering.disabled:
            frappe.throw(_("Billable Offering is disabled."))

    def _validate_invoice_link(self):
        if self.status == "Invoiced" and not self.sales_invoice:
            frappe.throw(_("Sales Invoice is required for invoiced charges."))
        if self.status != "Invoiced" and self.sales_invoice:
            frappe.throw(_("Only invoiced charges may keep a Sales Invoice link."))
        if not self.sales_invoice:
            return

        invoice = frappe.db.get_value(
            "Sales Invoice",
            self.sales_invoice,
            ["organization", "account_holder", "docstatus"],
            as_dict=True,
        )
        if not invoice:
            frappe.throw(_("Sales Invoice {sales_invoice} was not found.").format(sales_invoice=self.sales_invoice))
        if invoice.organization != self.organization:
            frappe.throw(_("Sales Invoice must belong to the same Organization as the Billable Charge."))
        if invoice.account_holder != self.account_holder:
            frappe.throw(_("Sales Invoice Account Holder must match the Billable Charge Account Holder."))
