import frappe
from frappe.utils import flt

from ifitwala_ed.accounting.fiscal_year_utils import fill_date_range_from_fiscal_year


def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Account", "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 200},
        {"label": "Root Type", "fieldname": "root_type", "fieldtype": "Data", "width": 120},
        {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "width": 140},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "width": 140},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 140},
    ]

    conditions = ["gl.organization = %(organization)s", "gl.is_cancelled = 0"]
    params = {"organization": filters.get("organization")}

    from_date, to_date = fill_date_range_from_fiscal_year(filters)
    if from_date and to_date:
        conditions.append("gl.posting_date between %(from_date)s and %(to_date)s")
        params.update({"from_date": from_date, "to_date": to_date})
    elif from_date:
        conditions.append("gl.posting_date >= %(from_date)s")
        params.update({"from_date": from_date})
    elif to_date:
        conditions.append("gl.posting_date <= %(to_date)s")
        params.update({"to_date": to_date})
    if filters.get("school"):
        conditions.append("gl.school = %(school)s")
        params.update({"school": filters.get("school")})
    if filters.get("program"):
        conditions.append("gl.program = %(program)s")
        params.update({"program": filters.get("program")})

    where_clause = " and ".join(conditions)

    rows = frappe.db.sql(
        f"""
		select
			gl.account as account,
			acc.root_type as root_type,
			sum(gl.debit) as debit,
			sum(gl.credit) as credit
		from `tabGL Entry` gl
		join `tabAccount` acc on acc.name = gl.account
		where {where_clause}
		group by gl.account, acc.root_type
		order by acc.root_type asc, gl.account asc
		""",
        params,
        as_dict=True,
    )

    for row in rows:
        row.balance = flt(row.debit) - flt(row.credit)

    return columns, rows
