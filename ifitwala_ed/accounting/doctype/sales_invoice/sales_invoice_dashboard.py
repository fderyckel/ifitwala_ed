from frappe import _


def get_data():
    return {
        "fieldname": "sales_invoice",
        "transactions": [
            {
                "label": _("Payment"),
                "items": ["Payment Entry", "Journal Entry", "Payment Reconciliation"],
            },
        ],
    }
