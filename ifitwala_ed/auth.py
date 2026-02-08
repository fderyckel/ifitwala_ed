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


def _resolve_portal_path(user_roles: set) -> str:
	"""
	Resolve the appropriate portal path based on user roles.
	
	Architecture: Unified /portal entry with client-side routing (Option B).
	The Vue SPA at /portal reads window.defaultPortal to route internally.
	
	Priority order (locked):
	1. Admissions Applicant -> /admissions (separate admissions portal)
	2. All other users -> /portal (unified entry, client-side routing handles the rest)
	
	Rationale: Admissions is a separate flow; all other users use unified /portal
	with client-side role detection for cleaner SPA architecture.
	"""
	if "Admissions Applicant" in user_roles:
		return "/admissions"
	# Unified /portal entry for all non-admissions users
	# Client-side router handles role-specific sub-portal selection
	return "/portal"


def _force_redirect_response(path: str):
	"""
	Force a redirect by setting frappe.local.response.
	This overrides any redirect-to parameter from the login URL.
	"""
	frappe.local.response["home_page"] = path
	frappe.local.response["redirect_to"] = path
	frappe.local.response["location"] = path
	frappe.local.response["type"] = "redirect"


def on_login():
	"""
	Hook called on user login (via auth_hooks).
	
	This hook runs during validate_auth_via_hooks() which happens early
	in the request lifecycle. We don't set redirects here because
	the after_login hook runs later and has final authority.
	"""
	# Redirect logic is handled by after_login hook in api/users.py
	# which runs after successful authentication and has final say
	pass


def before_request():
	"""
	Hook called before every request.
	
	Defensive blocking only: Redirects non-staff users away from desk/app.
	This prevents portal users from accessing staff interfaces even if they
	directly navigate to /desk or /app URLs.
	
	Note: This does NOT handle login redirects - those are handled by
	the after_login hook to ensure proper override of redirect-to parameter.
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
	portal_path = _resolve_portal_path(user_roles)
	frappe.logger().debug(
		f"Desk block redirect for {user}: {path} -> {portal_path}, roles={user_roles}"
	)
	_force_redirect_response(portal_path)
