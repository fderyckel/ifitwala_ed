# ifitwala_ed/accounting/doctype/statement_of_accounts_run/statement_of_accounts_run.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

from ifitwala_ed.accounting.receivables import money


class StatementOfAccountsRun(Document):
    def validate(self):
        self.total_account_holders = len(self.items or [])
        self.total_outstanding = money(sum(money(row.statement_balance or 0) for row in (self.items or [])))
        if self.status == "Cancelled":
            return
        self.status = "Processed" if self.processed_on else "Draft"


@frappe.whitelist()
def load_account_holders(name: str) -> str:
    doc = frappe.get_doc("Statement Of Accounts Run", name)
    filters = {
        "organization": doc.organization,
        "docstatus": 1,
        "outstanding_amount": [">", 0],
    }
    if doc.account_holder:
        filters["account_holder"] = doc.account_holder
    if doc.from_date and doc.as_of_date:
        filters["posting_date"] = ["between", [doc.from_date, doc.as_of_date]]

    rows = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=["account_holder", "posting_date", "due_date", "outstanding_amount"],
        order_by="account_holder asc, posting_date asc",
        limit_page_length=5000,
    )

    grouped = {}
    for row in rows:
        key = row.get("account_holder")
        state = grouped.setdefault(
            key,
            {
                "account_holder": key,
                "statement_balance": 0.0,
                "overdue_amount": 0.0,
                "invoice_count": 0,
                "latest_invoice_date": row.get("posting_date"),
                "latest_due_date": row.get("due_date"),
                "contact_email": frappe.db.get_value("Account Holder", key, "primary_email"),
            },
        )
        state["statement_balance"] = money(state["statement_balance"] + money(row.get("outstanding_amount") or 0))
        if row.get("due_date") and row.get("due_date") <= doc.as_of_date:
            state["overdue_amount"] = money(state["overdue_amount"] + money(row.get("outstanding_amount") or 0))
        state["invoice_count"] += 1
        if row.get("posting_date") and (
            not state["latest_invoice_date"] or row.get("posting_date") > state["latest_invoice_date"]
        ):
            state["latest_invoice_date"] = row.get("posting_date")
        if row.get("due_date") and (not state["latest_due_date"] or row.get("due_date") > state["latest_due_date"]):
            state["latest_due_date"] = row.get("due_date")

    doc.set("items", list(grouped.values()))
    doc.save()
    return doc.name


@frappe.whitelist()
def mark_processed(name: str) -> str:
    doc = frappe.get_doc("Statement Of Accounts Run", name)
    if not doc.items:
        frappe.throw(_("Load account holders before marking the run as processed."))
    doc.processed_on = get_datetime(now_datetime())
    doc.save()
    return doc.name
