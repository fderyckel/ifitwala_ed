from frappe import _


def get_data():
    return {
        "fieldname": "sales_invoice",
        "non_standard_fieldnames": {
            "Sales Invoice": "against_sales_invoice",
        },
        "transactions": [
            {"label": _("Payment"), "items": ["Payment Request"]},
            {
                "label": _("Adjustments"),
                "items": ["Sales Invoice"],
            },
        ],
    }
