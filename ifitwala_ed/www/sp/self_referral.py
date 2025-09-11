# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/www/sp/self_referral.py

import frappe
from frappe import _
from frappe.utils import now_datetime

# Optional: reflect server-side upload limits/types in the template
try:
	from ifitwala_ed.utilities.portal_utils import ALLOWED_EXTS, MAX_MB
except Exception:
	ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".pdf"}
	MAX_MB = 10

def _resolve_current_student():
	"""
	Map the logged-in portal user to a Student record.
	Preferred: match User.email → Student.student_email.
	Fallbacks: match user_id across legacy fields.
	"""
	user_id = frappe.session.user
	if not user_id or user_id in ("Guest", "Administrator"):
		frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

	user_email = frappe.db.get_value("User", user_id, "email") or user_id

	row = frappe.db.get_value(
		"Student",
		{"student_email": user_email},
		["name", "student_full_name"],
		as_dict=True,
	)
	if row:
		return row

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
	# Enforce login (friendly redirect)
	if frappe.session.user == "Guest":
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/login?redirect-to=/sp/self_referral"
		return

	# Restrict to Student role (keeps parity with API guard)
	if "Student" not in frappe.get_roles(frappe.session.user):
		frappe.throw(_("This page is for students."), frappe.PermissionError)

	student = _resolve_current_student()

	context.no_cache = 1
	context.portal_root = "/sp"
	context.page_title = _("Self-Referral")
	context.current_year = now_datetime().year

	# Optional tokens if you want to show in the UI later
	context.student_name = student.get("student_full_name")
	context.student_id = student.get("name")

	# Settings tokens (default confidentiality copy, etc.)
	try:
		settings = frappe.get_cached_doc("Referral Settings")
		context.default_confidentiality = getattr(settings, "default_confidentiality_for_self_referral", "Restricted")
	except Exception:
		context.default_confidentiality = "Restricted"

	# Attachment hints for the template (kept in sync with server limits)
	context.attach_max_mb = MAX_MB
	context.attach_allowed = ", ".join(sorted(ALLOWED_EXTS))

	# Breadcrumbs (works with your sp_breadcrumbs include)
	context.breadcrumbs = [
		{"label": _("Dashboard"), "route": "/sp"},
		{"label": _("Wellbeing"), "route": "/sp/wellbeing"},
		{"label": _("Self-Referral"), "route": "/sp/self_referral"},
	]

