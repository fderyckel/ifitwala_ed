# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/auth.py
# Authentication hooks and access control guards

import frappe

# Staff roles that should NOT be redirected away from desk/app
STAFF_ROLES = frozenset([
	"Academic User",
	"System Manager",
	"Teacher",
	"Administrator",
	"Finance User",
	"HR User",
	"HR Manager",
])

# Routes that guardians should not access (redirect to portal)
GUARDIAN_RESTRICTED_ROUTES = frozenset([
	"/desk",
	"/app",
])


def on_login():
	"""
	Hook called on user login.
	Redirect logic is handled by after_login hook in api/users.py.
	This function exists for any additional login-time processing.
	"""
	pass


def before_request():
	"""
	Hook called before every request.
	Redirects guardians away from desk/app to their portal.
	
	This prevents guardians from accessing staff interfaces even if they
	directly navigate to /desk or /app URLs.
	"""
	user = frappe.session.user
	
	# Skip for unauthenticated users or Administrator
	if not user or user == "Guest":
		return
	
	# Get current request path
	path = getattr(frappe.request, "path", "") or ""
	
	# Check if this is a restricted route for guardians
	is_restricted = any(
		path == route or path.startswith(f"{route}/")
		for route in GUARDIAN_RESTRICTED_ROUTES
	)
	
	if not is_restricted:
		return
	
	# Check if user is a guardian
	is_guardian = frappe.db.exists("Guardian", {"user": user})
	if not is_guardian:
		return
	
	# Check if user has any staff role (staff takes priority)
	user_roles = set(frappe.get_roles(user))
	has_staff_role = bool(user_roles & STAFF_ROLES)
	
	if has_staff_role:
		# Staff members can access desk/app even if they're also guardians
		return
	
	# Guardian without staff role trying to access desk/app - redirect
	frappe.local.flags.redirect_location = "/portal/guardian"
	raise frappe.Redirect
