# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/www/portal/index.py

import os
import json
import frappe

APP = "ifitwala_ed"
VITE_DIR = os.path.join(frappe.get_app_path(APP), "public", "vite")
from ifitwala_ed.website.vite_utils import get_vite_assets

APP = "ifitwala_ed"
VITE_DIR = os.path.join(frappe.get_app_path(APP), "public", "vite")
MANIFEST_PATHS = [
	os.path.join(VITE_DIR, "manifest.json"),
	os.path.join(VITE_DIR, ".vite", "manifest.json"),
]
PUBLIC_BASE = f"/assets/{APP}/vite/"

def _load_assets():
	return get_vite_assets(
		app_name=APP,
		manifest_paths=MANIFEST_PATHS,
		public_base=PUBLIC_BASE,
		entry_keys=["index.html", "src/main.ts", "src/main.js"]
	)

def _redirect(to: str):
	frappe.local.flags.redirect_location = to
	raise frappe.Redirect

STAFF_PORTAL_ROLES = frozenset([
	"Academic User",
	"System Manager",
	"Teacher",
	"Administrator",
	"Finance User",
	"HR User",
	"HR Manager",
])

ALLOWED_ROLES = {
	"Student",
	"Guardian",
	"Employee",
	"Instructor",
	"Academic Staff",
	"Academic Assistant",
	"Academic Admin",
	"System Manager",
	"Administrator",
}


def get_context(context):
	user = frappe.session.user
	path = frappe.request.path if hasattr(frappe, "request") else "/portal"

	if not user or user == "Guest":
		_redirect(f"/login?redirect-to={path}")

	user_roles = set(frappe.get_roles(user))

	# ---------------------------------------------------------------
	# Portal section eligibility (portal sections != frappe roles)
	# Staff access rule:
	#   Active Employee profile OR dedicated staff role.
	# ---------------------------------------------------------------
	is_active_employee = (
		("Employee" in user_roles)
		and bool(frappe.db.exists("Employee", {"user_id": user, "employment_status": "Active"}))
	)
	has_staff_role = bool(user_roles & STAFF_PORTAL_ROLES)
	is_staff_portal_user = is_active_employee or has_staff_role

	is_student = "Student" in user_roles
	is_guardian = "Guardian" in user_roles

	portal_sections = []
	if is_staff_portal_user:
		portal_sections.append("Staff")
	if is_student:
		portal_sections.append("Student")
	if is_guardian:
		portal_sections.append("Guardian")

	# If user has no portal access at all, block hard.
	if not portal_sections:
		_redirect(f"/login?redirect-to={path}")

	# Default portal priority: Staff > Student > Guardian
	if "Staff" in portal_sections:
		default_portal = "staff"
	elif "Student" in portal_sections:
		default_portal = "student"
	else:
		default_portal = "guardian"

	context.default_portal = default_portal
	context.portal_roles = portal_sections
	context.portal_roles_json = frappe.as_json(portal_sections)

	js_entry, css_files, preload_files = _load_assets()

	context.csrf_token = frappe.sessions.get_csrf_token()
	context.vite_js = js_entry
	context.vite_css = css_files
	context.vite_preload = preload_files
	return context
