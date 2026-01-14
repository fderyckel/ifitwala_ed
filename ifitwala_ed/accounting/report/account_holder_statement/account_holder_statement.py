import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}

	columns = [
		{"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data", "width": 120},
		{"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Data", "width": 140},
		{"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "width": 120},
		{"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "width": 120},
		{"label": "Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 120},
		{"label": "Remarks", "fieldname": "remarks", "fieldtype": "Data", "width": 200},
	]

	data_filters = {
		"organization": filters.get("organization"),
		"party_type": "Account Holder",
		"party": filters.get("account_holder"),
		"is_cancelled": 0,
	}

	if filters.get("from_date") and filters.get("to_date"):
		data_filters["posting_date"] = ["between", [filters.get("from_date"), filters.get("to_date")]]
	elif filters.get("from_date"):
		data_filters["posting_date"] = [">=", filters.get("from_date")]
	elif filters.get("to_date"):
		data_filters["posting_date"] = ["<=", filters.get("to_date")]

	entries = frappe.get_all(
		"GL Entry",
		filters=data_filters,
		fields=["posting_date", "voucher_type", "voucher_no", "debit", "credit", "remarks"],
		order_by="posting_date asc, name asc",
	)

	balance = 0
	rows = []
	for entry in entries:
		balance += flt(entry.debit) - flt(entry.credit)
		rows.append(
			{
				"posting_date": entry.posting_date,
				"voucher_type": entry.voucher_type,
				"voucher_no": entry.voucher_no,
				"debit": entry.debit,
				"credit": entry.credit,
				"balance": balance,
				"remarks": entry.remarks,
			}
		)

	return columns, rows
