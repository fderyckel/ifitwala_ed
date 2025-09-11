# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/www/sp/wellbeing.py

import frappe
from frappe import _
from frappe.utils import now_datetime

def _resolve_current_student():
	user_id = frappe.session.user
	if not user_id or user_id in ("Guest", "Administrator"):
		frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

	# Try by email first
	user_email = frappe.db.get_value("User", user_id, "email") or user_id
	row = frappe.db.get_value(
		"Student",
		{"student_email": user_email},
		["name", "student_full_name"],
		as_dict=True,
	)
	if row:
		return row

	# Fallbacks on legacy fields
	for cond in (
		{"student_email": user_id},
		{"email": user_id},
		{"student_email_id": user_id},
		{"user": user_id},
	):
		row = frappe.db.get_value("Student", cond, ["name", "student_full_name"], as_dict=True)
		if row:
			return row

	frappe.throw(_("No Student record found for your account."), frappe.PermissionError)

def get_context(context):
	# Friendly redirect if guest
	if frappe.session.user == "Guest":
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/login?redirect-to=/sp/wellbeing"
		return

	# Limit to Student role to match the self-referral flow
	if "Student" not in frappe.get_roles(frappe.session.user):
		frappe.throw(_("This page is for students."), frappe.PermissionError)

	student = _resolve_current_student()

	context.no_cache = 1
	context.portal_root = "/sp"
	context.page_title = _("Wellbeing")
	context.current_year = now_datetime().year

	# Student info (optional for greeting)
	context.student_name = student.get("student_full_name")
	context.student_id = student.get("name")

	# Settings toggles we care about
	try:
		settings = frappe.get_cached_doc("Referral Settings")
		context.can_self_refer = 1 if getattr(settings, "allow_student_self_referral", 0) else 0
		context.anonymous_enabled = 1 if getattr(settings, "enable_anonymous_student_referral", 0) else 0
	except Exception:
		context.can_self_refer = 1
		context.anonymous_enabled = 0

	# Breadcrumbs for sp_breadcrumbs.html
	context.breadcrumbs = [
		{"label": _("Dashboard"), "route": "/sp"},
		{"label": _("Wellbeing"), "route": "/sp/wellbeing"},
	]
