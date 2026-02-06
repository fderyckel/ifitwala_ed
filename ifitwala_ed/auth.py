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
	Redirects non-staff users (students, guardians, admissions applicants) away from desk/app to their portal.
	
	This prevents portal users from accessing staff interfaces even if they
	directly navigate to /desk or /app URLs.
	"""
	user = frappe.session.user
	
	# Skip for unauthenticated users
	if not user or user == "Guest":
		return
	
	# Get current request path
	path = getattr(frappe.request, "path", "") or ""
	
	# Check if this is a restricted route
	is_restricted = any(
		path == route or path.startswith(f"{route}/")
		for route in RESTRICTED_ROUTES
	)
	
	if not is_restricted:
		return
	
	# Get user roles
	user_roles = set(frappe.get_roles(user))
	
	# Check if user has any staff role (staff can access desk/app)
	has_staff_role = bool(user_roles & STAFF_ROLES)
	if has_staff_role:
		return
	
	# Check if user has any restricted role (Student, Guardian, or Admissions Applicant)
	has_restricted_role = bool(user_roles & RESTRICTED_ROLES)
	if not has_restricted_role:
		# User without restricted roles can access desk/app
		return
	
	# Non-staff user with restricted role trying to access desk/app - redirect to appropriate portal
	# Admissions Applicants go to /admissions, others go to /portal
	if "Admissions Applicant" in user_roles:
		frappe.local.flags.redirect_location = "/admissions"
	else:
		frappe.local.flags.redirect_location = "/portal"
	raise frappe.Redirect
