import frappe
from frappe.utils import flt, getdate, today


def execute(filters=None):
    filters = filters or {}
    as_of = getdate(filters.get("as_of_date") or today())

    columns = [
        {
            "label": "Account Holder",
            "fieldname": "account_holder",
            "fieldtype": "Link",
            "options": "Account Holder",
            "width": 180,
        },
        {
            "label": "Sales Invoice",
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 140,
        },
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": "Due Date", "fieldname": "due_date", "fieldtype": "Date", "width": 110},
        {"label": "Outstanding", "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Age (Days)", "fieldname": "age_days", "fieldtype": "Int", "width": 90},
        {"label": "Bucket", "fieldname": "bucket", "fieldtype": "Data", "width": 100},
    ]

    invoice_filters = {
        "organization": filters.get("organization"),
        "docstatus": 1,
        "outstanding_amount": [">", 0],
    }
    if filters.get("account_holder"):
        invoice_filters["account_holder"] = filters.get("account_holder")

    invoices = frappe.get_all(
        "Sales Invoice",
        filters=invoice_filters,
        fields=["name", "account_holder", "posting_date", "due_date", "outstanding_amount"],
        order_by="due_date asc, posting_date asc",
    )

    rows = []
    for inv in invoices:
        base_date = getdate(inv.due_date) if inv.due_date else getdate(inv.posting_date)
        age_days = (as_of - base_date).days
        if age_days <= 30:
            bucket = "0-30"
        elif age_days <= 60:
            bucket = "31-60"
        elif age_days <= 90:
            bucket = "61-90"
        else:
            bucket = "90+"

        rows.append(
            {
                "account_holder": inv.account_holder,
                "sales_invoice": inv.name,
                "posting_date": inv.posting_date,
                "due_date": inv.due_date,
                "outstanding_amount": flt(inv.outstanding_amount),
                "age_days": age_days,
                "bucket": bucket,
            }
        )

    return columns, rows
