# ifitwala_ed/accounting/doctype/payment_request/payment_request.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.accounting.receivables import clamp_money, is_zero, money


class PaymentRequest(Document):
    def validate(self):
        self._sync_from_invoice()
        self._sync_contacts()
        self._set_status()

    def _sync_from_invoice(self):
        if not self.sales_invoice:
            self.invoice_outstanding_amount = 0
            self.outstanding_amount = money(self.requested_amount or 0)
            return

        invoice = frappe.db.get_value(
            "Sales Invoice",
            self.sales_invoice,
            ["organization", "account_holder", "outstanding_amount", "due_date", "school", "program", "docstatus"],
            as_dict=True,
        )
        if not invoice:
            frappe.throw(_("Sales Invoice {0} not found.").format(self.sales_invoice))
        if invoice.docstatus != 1:
            frappe.throw(_("Payment Requests can only be created for submitted invoices."))
        if self.organization and invoice.organization != self.organization:
            frappe.throw(_("Sales Invoice must belong to the same Organization."))
        if self.account_holder and invoice.account_holder != self.account_holder:
            frappe.throw(_("Sales Invoice must belong to the same Account Holder."))

        self.organization = invoice.organization
        self.account_holder = invoice.account_holder
        self.invoice_outstanding_amount = money(invoice.outstanding_amount or 0)
        self.outstanding_amount = min(money(self.requested_amount or 0), self.invoice_outstanding_amount)
        if not self.requested_amount:
            self.requested_amount = self.invoice_outstanding_amount
            self.outstanding_amount = self.invoice_outstanding_amount
        if not self.due_date:
            self.due_date = invoice.due_date
        self.school = invoice.school
        self.program = invoice.program

    def _sync_contacts(self):
        if not self.account_holder:
            return
        holder = frappe.db.get_value(
            "Account Holder",
            self.account_holder,
            ["primary_email", "primary_phone"],
            as_dict=True,
        )
        if holder:
            if not self.contact_email:
                self.contact_email = holder.primary_email
            if not self.contact_phone:
                self.contact_phone = holder.primary_phone

    def _set_status(self):
        if self.status == "Cancelled":
            return
        requested = money(self.requested_amount or 0)
        outstanding = clamp_money(
            min(requested, money(self.invoice_outstanding_amount or self.outstanding_amount or 0))
        )
        self.outstanding_amount = outstanding

        if is_zero(outstanding):
            self.status = "Paid"
            return
        if self.sent_on:
            if outstanding < requested:
                self.status = "Partly Paid"
            else:
                self.status = "Sent"
            return
        self.status = "Draft"


@frappe.whitelist()
def create_from_sales_invoice(sales_invoice: str) -> str:
    invoice = frappe.db.get_value(
        "Sales Invoice",
        sales_invoice,
        ["organization", "account_holder", "outstanding_amount", "due_date"],
        as_dict=True,
    )
    if not invoice:
        frappe.throw(_("Sales Invoice {0} not found.").format(sales_invoice))

    doc = frappe.get_doc(
        {
            "doctype": "Payment Request",
            "organization": invoice.organization,
            "account_holder": invoice.account_holder,
            "sales_invoice": sales_invoice,
            "request_date": frappe.utils.today(),
            "due_date": invoice.due_date,
            "requested_amount": money(invoice.outstanding_amount or 0),
        }
    )
    doc.insert()
    return doc.name


@frappe.whitelist()
def mark_sent(name: str) -> str:
    doc = frappe.get_doc("Payment Request", name)
    doc.sent_on = now_datetime()
    doc.save()
    return doc.name
