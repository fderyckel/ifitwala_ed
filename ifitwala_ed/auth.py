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

# Routes that trigger the one-time post-login redirect guard
DESK_ROUTES = frozenset([
	"/app",
	"/desk",
])

# Roles that should be blocked from desk/app access (non-staff portal users)
RESTRICTED_ROLES = frozenset([
	"Student",
	"Guardian",
	"Admissions Applicant",
])

# Session key for one-time post-login redirect guard
FIRST_LOGIN_FLAG = "ifitwala_first_login_redirect"

def on_login():
	"""
	Hook called on user login.
	Sets a session flag to enable one-time post-login redirect guard.
	The guard ensures users land on their appropriate portal even if
	redirect-to=/app is present in the login URL.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return

	# Ensure role-based login landing is always populated on the login response.
	# This keeps behavior stable even when Frappe login flow bypasses
	# on_session_creation in edge paths.
	from ifitwala_ed.api.users import redirect_user_to_entry_portal
	redirect_user_to_entry_portal()

	# Set flag for one-time redirect guard
	# This will be checked in before_request to force portal landing
	frappe.session.data[FIRST_LOGIN_FLAG] = True
	frappe.logger().debug(f"Login guard activated for user: {user}")


def _has_active_employee_profile(*, user: str, user_roles: set) -> bool:
	"""Return True when user has Employee role and an active Employee record."""
	if "Employee" not in user_roles:
		return False
	return bool(
		frappe.db.exists(
			"Employee",
			{"user_id": user, "employment_status": "Active"},
		)
	)


def _has_staff_portal_access(*, user: str, user_roles: set) -> bool:
	"""Return True when user should land on staff portal routes."""
	if user_roles & STAFF_ROLES:
		return True
	return _has_active_employee_profile(user=user, user_roles=user_roles)


def _resolve_portal_path(*, user: str, user_roles: set) -> str:
	"""
	Resolve the appropriate portal path based on user roles.

	Priority order (locked):
	1. Admissions Applicant -> /admissions
	2. Active Employee -> /portal/staff
	3. Student -> /portal/student
	4. Guardian -> /portal/guardian
	5. Fallback -> /portal
	"""
	if "Admissions Applicant" in user_roles:
		return "/admissions"
	if _has_staff_portal_access(user=user, user_roles=user_roles):
		return "/portal/staff"
	if "Student" in user_roles:
		return "/portal/student"
	if "Guardian" in user_roles:
		return "/portal/guardian"
	return "/portal"


def before_request():
	"""
	Hook called before every request.
	
	Two responsibilities:
	1. One-time post-login redirect guard: Forces first request after login to portal
	   (prevents redirect-to=/app from overriding portal policy)
	2. Defensive blocking: Redirects non-staff users away from desk/app to their portal
	
	The one-time guard is cleared after first request, allowing staff to manually
	navigate to /app afterward (e.g., via "Switch to Desk").
	"""
	user = frappe.session.user

	# Skip for unauthenticated users
	if not user or user == "Guest":
		return

	# Get current request path
	path = getattr(frappe.request, "path", "") or ""
	
	# Get user roles
	user_roles = set(frappe.get_roles(user))

	# -------------------------------------------------------------------------
	# 1) One-time post-login redirect guard (first hop after login)
	# -------------------------------------------------------------------------
	# Check if this is the first request after login
	if frappe.session.data.get(FIRST_LOGIN_FLAG):
		# Clear the flag immediately (one-time guard)
		frappe.session.data.pop(FIRST_LOGIN_FLAG, None)
		
		# Check if user is trying to access /app or /desk on first hop
		is_desk_route = any(
			path == route or path.startswith(f"{route}/")
			for route in DESK_ROUTES
		)
		
		if is_desk_route:
			# Force redirect to appropriate portal based on role
			portal_path = _resolve_portal_path(user=user, user_roles=user_roles)
			frappe.logger().debug(
				f"Login guard redirect for {user}: {path} -> {portal_path}, roles={user_roles}"
			)
			frappe.local.flags.redirect_location = portal_path
			raise frappe.Redirect
		# If not a desk route, allow the request to proceed normally
		return
	
	# -------------------------------------------------------------------------
	# 2) Defensive blocking (ongoing: non-staff cannot access desk/app)
	# -------------------------------------------------------------------------
	# Check if this is a restricted route
	is_restricted = any(
		path == route or path.startswith(f"{route}/")
		for route in RESTRICTED_ROUTES
	)
	
	if not is_restricted:
		return
	
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
	portal_path = _resolve_portal_path(user=user, user_roles=user_roles)
	frappe.local.flags.redirect_location = portal_path
	raise frappe.Redirect
