import frappe

def get_context(context):
	# do your magic here
	pass

import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_valid_academic_years():
    today = frappe.utils.today()
    return frappe.get_all(
        "Academic Year",
        filters={"year_end_date": [">=", today]},
        fields=["name"],
        order_by="start_date asc"
    )
