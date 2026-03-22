# ifitwala_ed/accounting/doctype/payment_reconciliation/payment_reconciliation.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.accounting.ledger_utils import cancel_gl_entries, make_gl_entries, validate_posting_date
from ifitwala_ed.accounting.receivables import clamp_money, is_zero, money, persist_submitted_invoice_runtime_state


class PaymentReconciliation(Document):
    def validate(self):
        self.validate_party()
        self.validate_allocations()
        self.set_reference_dimensions()
        validate_posting_date(self.organization, self.posting_date)

    def validate_party(self):
        party_org = frappe.db.get_value("Account Holder", self.account_holder, "organization")
        if party_org and party_org != self.organization:
            frappe.throw(_("Account Holder must belong to the same Organization"))

    def validate_allocations(self):
        if not self.allocations:
            frappe.throw(_("At least one allocation is required"))

        totals_by_payment = {}
        total_allocated = 0.0
        for row in self.allocations:
            allocated_amount = money(row.allocated_amount or 0)
            if allocated_amount <= 0:
                frappe.throw(_("Allocated amount must be greater than zero"))
            if not row.payment_entry:
                frappe.throw(_("Payment Entry is required on each reconciliation row"))

            payment_entry = frappe.db.get_value(
                "Payment Entry",
                row.payment_entry,
                ["organization", "party", "unallocated_amount", "docstatus", "school", "program"],
                as_dict=True,
            )
            if not payment_entry:
                frappe.throw(_("Payment Entry {0} not found").format(row.payment_entry))
            if payment_entry.docstatus != 1:
                frappe.throw(_("Payment Entry {0} must be submitted").format(row.payment_entry))
            if payment_entry.organization != self.organization:
                frappe.throw(_("Payment Entry must belong to the same Organization"))
            if payment_entry.party != self.account_holder:
                frappe.throw(_("Payment Entry must belong to the same Account Holder"))

            invoice = frappe.db.get_value(
                "Sales Invoice",
                row.sales_invoice,
                ["organization", "account_holder", "outstanding_amount", "docstatus"],
                as_dict=True,
            )
            if not invoice:
                frappe.throw(_("Sales Invoice {0} not found").format(row.sales_invoice))
            if invoice.docstatus != 1:
                frappe.throw(_("Sales Invoice {0} must be submitted").format(row.sales_invoice))
            if invoice.organization != self.organization:
                frappe.throw(_("Sales Invoice must belong to the same Organization"))
            if invoice.account_holder != self.account_holder:
                frappe.throw(_("Sales Invoice must belong to the same Account Holder"))

            row.outstanding_amount = money(invoice.outstanding_amount or 0)
            row.payment_entry_unallocated_amount = money(payment_entry.unallocated_amount or 0)
            if allocated_amount > row.outstanding_amount and not is_zero(allocated_amount - row.outstanding_amount):
                frappe.throw(_("Allocated amount cannot exceed outstanding amount"))

            totals_by_payment[row.payment_entry] = money(totals_by_payment.get(row.payment_entry, 0) + allocated_amount)
            if totals_by_payment[row.payment_entry] > row.payment_entry_unallocated_amount and not is_zero(
                totals_by_payment[row.payment_entry] - row.payment_entry_unallocated_amount
            ):
                frappe.throw(_("Allocated amount exceeds the selected Payment Entry's unallocated amount"))

            total_allocated = money(total_allocated + allocated_amount)

        available = get_unallocated_advance(self.organization, self.account_holder)
        if total_allocated > available and not is_zero(total_allocated - available):
            frappe.throw(_("Allocated amount exceeds available advance balance"))

    def set_reference_dimensions(self):
        rows = frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", [row.sales_invoice for row in self.allocations if row.sales_invoice]]},
            fields=["school", "program"],
            limit=max(50, len(self.allocations) + 10),
        )
        schools = {row.get("school") for row in rows if row.get("school")}
        programs = {row.get("program") for row in rows if row.get("program")}
        self.school = next(iter(schools)) if len(schools) == 1 else None
        self.program = next(iter(programs)) if len(programs) == 1 else None

    def on_submit(self):
        settings = frappe.get_doc("Accounts Settings", self.organization)
        ar_account = settings.default_receivable_account
        advance_account = settings.default_advance_account
        if not ar_account or not advance_account:
            frappe.throw(_("Default receivable and advance accounts are required"))

        total_allocated = money(sum(money(row.allocated_amount) for row in self.allocations))

        entries = [
            {
                "organization": self.organization,
                "posting_date": self.posting_date,
                "account": advance_account,
                "party_type": "Account Holder",
                "party": self.account_holder,
                "against": ar_account,
                "remarks": "Advance allocation",
                "debit": total_allocated,
                "credit": 0,
                "school": self.school,
                "program": self.program,
            },
            {
                "organization": self.organization,
                "posting_date": self.posting_date,
                "account": ar_account,
                "party_type": "Account Holder",
                "party": self.account_holder,
                "against": advance_account,
                "remarks": "Advance allocation",
                "debit": 0,
                "credit": total_allocated,
                "school": self.school,
                "program": self.program,
            },
        ]

        make_gl_entries(entries, "Payment Reconciliation", self.name)

        for row in self.allocations:
            allocated_amount = money(row.allocated_amount or 0)
            frappe.db.set_value(
                "Sales Invoice",
                row.sales_invoice,
                "outstanding_amount",
                clamp_money(money(row.outstanding_amount or 0) - allocated_amount),
            )
            payment_unallocated = money(
                frappe.db.get_value("Payment Entry", row.payment_entry, "unallocated_amount") or 0
            )
            frappe.db.set_value(
                "Payment Entry",
                row.payment_entry,
                "unallocated_amount",
                clamp_money(payment_unallocated - allocated_amount),
            )
            persist_submitted_invoice_runtime_state(row.sales_invoice)

    def on_cancel(self):
        cancel_gl_entries("Payment Reconciliation", self.name)
        for row in self.allocations:
            allocated_amount = money(row.allocated_amount or 0)
            inv_outstanding = money(frappe.db.get_value("Sales Invoice", row.sales_invoice, "outstanding_amount") or 0)
            frappe.db.set_value(
                "Sales Invoice",
                row.sales_invoice,
                "outstanding_amount",
                clamp_money(inv_outstanding + allocated_amount),
            )
            payment_unallocated = money(
                frappe.db.get_value("Payment Entry", row.payment_entry, "unallocated_amount") or 0
            )
            frappe.db.set_value(
                "Payment Entry",
                row.payment_entry,
                "unallocated_amount",
                clamp_money(payment_unallocated + allocated_amount),
            )
            persist_submitted_invoice_runtime_state(row.sales_invoice)


def get_unallocated_advance(organization, account_holder):
    amounts = frappe.get_all(
        "Payment Entry",
        filters={
            "organization": organization,
            "party": account_holder,
            "docstatus": 1,
            "unallocated_amount": [">", 0],
        },
        pluck="unallocated_amount",
    )
    return money(sum(money(a) for a in amounts))


@frappe.whitelist()
def load_open_invoices(name: str) -> str:
    doc = frappe.get_doc("Payment Reconciliation", name)
    if not doc.account_holder:
        frappe.throw(_("Account Holder is required before loading open invoices."))

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "organization": doc.organization,
            "account_holder": doc.account_holder,
            "docstatus": 1,
            "outstanding_amount": [">", 0],
        },
        fields=["name", "outstanding_amount"],
        order_by="due_date asc, posting_date asc",
        limit=2000,
    )

    doc.set(
        "allocations",
        [
            {
                "sales_invoice": row.get("name"),
                "outstanding_amount": money(row.get("outstanding_amount") or 0),
                "allocated_amount": 0,
            }
            for row in invoices
        ],
    )
    doc.save()
    return doc.name
