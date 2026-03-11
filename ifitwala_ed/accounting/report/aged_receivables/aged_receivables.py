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
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "School", "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 160},
        {"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 160},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": "Due Date", "fieldname": "due_date", "fieldtype": "Date", "width": 110},
        {"label": "Outstanding", "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Age (Days)", "fieldname": "age_days", "fieldtype": "Int", "width": 90},
        {"label": "Bucket", "fieldname": "bucket", "fieldtype": "Data", "width": 100},
    ]

    conditions = ["si.organization = %(organization)s", "si.docstatus = 1", "si.outstanding_amount > 0"]
    params = {"organization": filters.get("organization")}
    if filters.get("account_holder"):
        conditions.append("si.account_holder = %(account_holder)s")
        params["account_holder"] = filters.get("account_holder")
    if filters.get("school"):
        conditions.append(
            "exists (select 1 from `tabSales Invoice Item` sii where sii.parent = si.name and sii.school = %(school)s)"
        )
        params["school"] = filters.get("school")
    if filters.get("program"):
        conditions.append(
            "exists (select 1 from `tabSales Invoice Item` sii where sii.parent = si.name and sii.program = %(program)s)"
        )
        params["program"] = filters.get("program")

    invoices = frappe.db.sql(
        f"""
        select
            si.name,
            si.account_holder,
            si.status,
            si.school,
            si.program,
            si.posting_date,
            si.due_date,
            si.outstanding_amount
        from `tabSales Invoice` si
        where {" and ".join(conditions)}
        order by si.due_date asc, si.posting_date asc
        """,
        params,
        as_dict=True,
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
                "status": inv.status,
                "school": inv.school,
                "program": inv.program,
                "posting_date": inv.posting_date,
                "due_date": inv.due_date,
                "outstanding_amount": flt(inv.outstanding_amount),
                "age_days": age_days,
                "bucket": bucket,
            }
        )

    return columns, rows
