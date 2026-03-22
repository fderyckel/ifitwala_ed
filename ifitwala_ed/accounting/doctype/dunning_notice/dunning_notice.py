# ifitwala_ed/accounting/doctype/dunning_notice/dunning_notice.py

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, now_datetime

from ifitwala_ed.accounting.receivables import money


class DunningNotice(Document):
    def validate(self):
        self.total_invoices = len(self.items or [])
        self.total_outstanding = money(sum(money(row.outstanding_amount or 0) for row in (self.items or [])))
        self._set_status()

    def _set_status(self):
        if self.status == "Cancelled":
            return
        open_rows = 0
        for row in self.items or []:
            outstanding = (
                frappe.db.get_value("Sales Invoice", row.sales_invoice, "outstanding_amount")
                if row.sales_invoice
                else 0
            )
            if money(outstanding or 0) > 0:
                open_rows += 1
        if open_rows == 0 and self.items:
            self.status = "Resolved"
        elif self.sent_on:
            self.status = "Sent"
        else:
            self.status = "Draft"


def _get_overdue_rows(doc) -> list[dict]:
    posting_date = getdate(doc.posting_date)
    invoice_filters = {
        "organization": doc.organization,
        "docstatus": 1,
        "outstanding_amount": [">", 0],
        "due_date": ["<=", posting_date],
    }
    if doc.account_holder:
        invoice_filters["account_holder"] = doc.account_holder

    rows = frappe.get_all(
        "Sales Invoice",
        filters=invoice_filters,
        fields=["name", "account_holder", "due_date", "outstanding_amount"],
        order_by="due_date asc, posting_date asc",
        limit=5000,
    )

    out = []
    for row in rows:
        due_date = getdate(row.get("due_date"))
        age_days = (posting_date - due_date).days if due_date else 0
        if age_days < int(doc.minimum_days_overdue or 0):
            continue
        out.append(
            {
                "sales_invoice": row.get("name"),
                "account_holder": row.get("account_holder"),
                "due_date": row.get("due_date"),
                "age_days": age_days,
                "outstanding_amount": money(row.get("outstanding_amount") or 0),
            }
        )
    return out


@frappe.whitelist()
def load_overdue_items(name: str) -> str:
    doc = frappe.get_doc("Dunning Notice", name)
    doc.set("items", _get_overdue_rows(doc))
    doc.save()
    return doc.name


@frappe.whitelist()
def create_payment_requests(name: str) -> list[str]:
    doc = frappe.get_doc("Dunning Notice", name)
    created = []
    for row in doc.items or []:
        if row.payment_request:
            created.append(row.payment_request)
            continue
        payment_request = frappe.get_doc(
            {
                "doctype": "Payment Request",
                "organization": doc.organization,
                "account_holder": row.account_holder,
                "sales_invoice": row.sales_invoice,
                "request_date": doc.posting_date,
                "due_date": row.due_date,
                "requested_amount": money(row.outstanding_amount or 0),
            }
        )
        payment_request.insert()
        row.payment_request = payment_request.name
        created.append(payment_request.name)
    doc.save()
    return created


@frappe.whitelist()
def mark_sent(name: str) -> str:
    doc = frappe.get_doc("Dunning Notice", name)
    doc.sent_on = get_datetime(now_datetime())
    doc.save()
    return doc.name
