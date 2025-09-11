import frappe
from frappe import _
from frappe.utils import now_datetime


def get_context(context):
	# Guests → main website
	if frappe.session.user == "Guest":
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/"
		return

	context.no_cache = 1
	context.portal_root = "/sp"
	context.page_title = "Dashboard"
	context.breadcrumbs = []
	context.current_year = now_datetime().year

