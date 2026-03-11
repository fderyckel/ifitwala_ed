import frappe
from frappe.utils import flt

from ifitwala_ed.accounting.fiscal_year_utils import fill_date_range_from_fiscal_year


def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": "School", "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 160},
        {"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 160},
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
    if filters.get("school"):
        data_filters["school"] = filters.get("school")
    if filters.get("program"):
        data_filters["program"] = filters.get("program")

    from_date, to_date = fill_date_range_from_fiscal_year(filters)
    if from_date and to_date:
        data_filters["posting_date"] = ["between", [from_date, to_date]]
    elif from_date:
        data_filters["posting_date"] = [">=", from_date]
    elif to_date:
        data_filters["posting_date"] = ["<=", to_date]

    entries = frappe.get_all(
        "GL Entry",
        filters=data_filters,
        fields=["posting_date", "school", "program", "voucher_type", "voucher_no", "debit", "credit", "remarks"],
        order_by="posting_date asc, name asc",
    )

    balance = 0
    rows = []
    for entry in entries:
        balance += flt(entry.debit) - flt(entry.credit)
        rows.append(
            {
                "posting_date": entry.posting_date,
                "school": entry.school,
                "program": entry.program,
                "voucher_type": entry.voucher_type,
                "voucher_no": entry.voucher_no,
                "debit": entry.debit,
                "credit": entry.credit,
                "balance": balance,
                "remarks": entry.remarks,
            }
        )

    return columns, rows
