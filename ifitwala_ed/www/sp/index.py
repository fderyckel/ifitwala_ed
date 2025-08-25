import frappe
from frappe import _
from frappe.utils import now_datetime

def get_context(context):
	# Guests should not access the portal: redirect to site's main page
	if frappe.session.user == "Guest":
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/"
		return

	# Ensure only Students access this dashboard
	user_roles = frappe.get_roles(frappe.session.user)
	if "Student" not in user_roles:
		frappe.throw(_("You are not authorized to access this page."), frappe.PermissionError)

	# Fetch preferred name + image from Student linked via email
	student = frappe.db.get_value(
		"Student",
		{"student_email": frappe.session.user},
		["student_preferred_name", "student_image"],
		as_dict=True
	)

	if not student:
		frappe.throw(_("Student profile not found. Please contact the administrator."))

	# Page context
	context.no_cache = 1
	context.portal_root = "/sp"
	context.page_title = _("Dashboard")

	# Personalization
	preferred = student.get("student_preferred_name") or _("Student")
	context.student_preferred_name = preferred
	context.student_image = student.get("student_image")
	context.welcome_message = _("Welcome back, {0}!").format(preferred)
	context.current_year = now_datetime().year
