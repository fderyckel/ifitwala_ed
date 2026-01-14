import frappe
from frappe.utils import flt


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

	if filters.get("from_date") and filters.get("to_date"):
		conditions.append("gl.posting_date between %(from_date)s and %(to_date)s")
		params.update({"from_date": filters.get("from_date"), "to_date": filters.get("to_date")})
	elif filters.get("from_date"):
		conditions.append("gl.posting_date >= %(from_date)s")
		params.update({"from_date": filters.get("from_date")})
	elif filters.get("to_date"):
		conditions.append("gl.posting_date <= %(to_date)s")
		params.update({"to_date": filters.get("to_date")})

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
