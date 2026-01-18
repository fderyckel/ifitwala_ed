import frappe


def execute(filters=None):
	filters = filters or {}

	columns = [
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 160},
		{"label": "Account Holder", "fieldname": "account_holder", "fieldtype": "Link", "options": "Account Holder", "width": 180},
		{"label": "Sales Invoice", "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
		{"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": "Billable Offering", "fieldname": "billable_offering", "fieldtype": "Link", "options": "Billable Offering", "width": 180},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
	]

	conditions = ["si.organization = %(organization)s", "si.docstatus = 1"]
	params = {"organization": filters.get("organization")}

	if filters.get("from_date") and filters.get("to_date"):
		conditions.append("si.posting_date between %(from_date)s and %(to_date)s")
		params.update({"from_date": filters.get("from_date"), "to_date": filters.get("to_date")})
	elif filters.get("from_date"):
		conditions.append("si.posting_date >= %(from_date)s")
		params.update({"from_date": filters.get("from_date")})
	elif filters.get("to_date"):
		conditions.append("si.posting_date <= %(to_date)s")
		params.update({"to_date": filters.get("to_date")})

	if filters.get("student"):
		conditions.append("sii.student = %(student)s")
		params.update({"student": filters.get("student")})

	if filters.get("account_holder"):
		conditions.append("si.account_holder = %(account_holder)s")
		params.update({"account_holder": filters.get("account_holder")})

	where_clause = " and ".join(conditions)

	rows = frappe.db.sql(
		f"""
		select
			sii.student as student,
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
