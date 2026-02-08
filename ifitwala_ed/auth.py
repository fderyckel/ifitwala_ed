# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/auth.py
# Authentication hooks and access control guards

import frappe
from ifitwala_ed.api.users import _get_employee_access_state, _resolve_login_redirect_path

# Routes that non-staff users should not access (redirect to portal)
RESTRICTED_ROUTES = frozenset([
	"/desk",
	"/app",
])

# Roles that should be blocked from desk/app access (non-staff portal users)
RESTRICTED_ROLES = frozenset([
	"Student",
	"Guardian",
	"Admissions Applicant",
])

def _redirect(to: str):
	frappe.local.response["home_page"] = to
	frappe.local.response["redirect_to"] = to
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = to
	frappe.local.flags.redirect_location = to
	raise frappe.Redirect


def on_login():
	"""
	Hook called on user login.
	Role-based login redirect is handled by the after_login hook.
	"""
	return


def before_request():
	"""
	Hook called before every request.
	Normalizes reserved auth/desk routes before website catch-all handling.
	Redirects non-staff users away from desk/app to role landing portals.
	"""
	# Get current request path
	path = getattr(frappe.request, "path", "") or ""
	normalized_path = path.rstrip("/") or "/"

	# Normalize logout to canonical Frappe web logout endpoint.
	if normalized_path == "/logout":
		_redirect("/?cmd=web_logout")

	user = frappe.session.user

	# Skip for unauthenticated users
	if not user or user == "Guest":
		return

	form_dict = getattr(frappe, "form_dict", {}) or {}
	cmd = str(form_dict.get("cmd") or "").strip()

	employee_state = _get_employee_access_state(user)
	if employee_state.get("is_blocked"):
		# Hard cutoff for relieved/blocked employees.
		if normalized_path != "/logout" and cmd != "web_logout":
			_redirect("/?cmd=web_logout")
		return

	# Get user roles
	user_roles = set(frappe.get_roles(user))

	# Check if this is a restricted route
	is_restricted = any(
		path == route or path.startswith(f"{route}/")
		for route in RESTRICTED_ROUTES
	)
	
	if not is_restricted:
		return
	
	# Staff eligibility is server-owned in access state helper.
	if employee_state.get("can_access_staff_portal"):
		return
	
	# Check if user has any restricted role (Student, Guardian, or Admissions Applicant)
	has_restricted_role = bool(user_roles & RESTRICTED_ROLES)
	if not has_restricted_role:
		# User without restricted roles can access desk/app
		return
	
	# Non-staff user with restricted role trying to access desk/app.
	# Use the same server-owned login routing policy for consistency.
	_redirect(_resolve_login_redirect_path(user, user_roles))
