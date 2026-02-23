import frappe


def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": "Account", "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 180},
        {"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data", "width": 120},
        {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Data", "width": 140},
        {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "width": 120},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "width": 120},
        {"label": "Party Type", "fieldname": "party_type", "fieldtype": "Data", "width": 120},
        {"label": "Party", "fieldname": "party", "fieldtype": "Data", "width": 160},
        {"label": "Remarks", "fieldname": "remarks", "fieldtype": "Data", "width": 200},
    ]

    data_filters = {
        "organization": filters.get("organization"),
        "is_cancelled": 0,
    }

    if filters.get("account"):
        data_filters["account"] = filters.get("account")

    if filters.get("from_date") and filters.get("to_date"):
        data_filters["posting_date"] = ["between", [filters.get("from_date"), filters.get("to_date")]]
    elif filters.get("from_date"):
        data_filters["posting_date"] = [">=", filters.get("from_date")]
    elif filters.get("to_date"):
        data_filters["posting_date"] = ["<=", filters.get("to_date")]

    rows = frappe.get_all(
        "GL Entry",
        filters=data_filters,
        fields=[
            "posting_date",
            "account",
            "voucher_type",
            "voucher_no",
            "debit",
            "credit",
            "party_type",
            "party",
            "remarks",
        ],
        order_by="posting_date asc, name asc",
    )

    return columns, rows
