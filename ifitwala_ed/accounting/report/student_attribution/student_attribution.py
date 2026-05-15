import frappe

from ifitwala_ed.accounting.fiscal_year_utils import fill_date_range_from_fiscal_year
from ifitwala_ed.utilities.school_tree import get_descendant_schools


def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Student", "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 160},
        {"label": "School", "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 160},
        {"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 160},
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
        {
            "label": "Billable Offering",
            "fieldname": "billable_offering",
            "fieldtype": "Link",
            "options": "Billable Offering",
            "width": 180,
        },
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
    ]

    conditions = ["si.organization = %(organization)s", "si.docstatus = 1"]
    params = {"organization": filters.get("organization")}

    from_date, to_date = fill_date_range_from_fiscal_year(filters)
    if from_date and to_date:
        conditions.append("si.posting_date between %(from_date)s and %(to_date)s")
        params.update({"from_date": from_date, "to_date": to_date})
    elif from_date:
        conditions.append("si.posting_date >= %(from_date)s")
        params.update({"from_date": from_date})
    elif to_date:
        conditions.append("si.posting_date <= %(to_date)s")
        params.update({"to_date": to_date})

    if filters.get("student"):
        conditions.append("sii.student = %(student)s")
        params.update({"student": filters.get("student")})

    if filters.get("account_holder"):
        conditions.append("si.account_holder = %(account_holder)s")
        params.update({"account_holder": filters.get("account_holder")})
    if filters.get("school"):
        school_scope = tuple(get_descendant_schools(filters.get("school")) or [filters.get("school")])
        conditions.append("sii.school IN %(school_list)s")
        params.update({"school_list": school_scope})
    if filters.get("program"):
        conditions.append("sii.program = %(program)s")
        params.update({"program": filters.get("program")})

    where_clause = " and ".join(conditions)

    rows = frappe.db.sql(
        f"""
		select
			sii.student as student,
			sii.school as school,
			sii.program as program,
			si.account_holder as account_holder,
			si.name as sales_invoice,
			si.posting_date as posting_date,
			sii.billable_offering as billable_offering,
			sii.amount as amount
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where {where_clause}
		order by si.posting_date asc, si.name asc
		""",
        params,
        as_dict=True,
    )

    return columns, rows
