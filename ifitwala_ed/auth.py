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

# Cache key prefix for one-time post-login redirect guard
FIRST_LOGIN_FLAG_PREFIX = "ifitwala_first_login_redirect"


def _get_first_login_flag_key(user: str) -> str:
	"""Get cache key for user's first-login flag."""
	return f"{FIRST_LOGIN_FLAG_PREFIX}:{user}"


def on_login():
	"""
	Hook called on user login.
	Sets a cache flag to enable one-time post-login redirect guard.
	The guard ensures users land on their appropriate portal even if
	redirect-to=/app is present in the login URL.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return

	# Set flag for one-time redirect guard (expires in 5 minutes)
	# This will be checked in before_request to force portal landing
	cache_key = _get_first_login_flag_key(user)
	frappe.cache().set(cache_key, True, expires_in=300)
	frappe.logger().debug(f"Login guard activated for user: {user}")


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


def _perform_redirect(path: str):
	"""
	Perform a redirect by setting frappe.local.response.
	
	This is the proper way to redirect from before_request hooks,
	as raising frappe.Redirect before request init completes doesn't work
	with the website renderer.
	"""
	frappe.local.response = frappe.utils.response.build_response("redirect")
	frappe.local.response["location"] = path
	frappe.local.response["http_status_code"] = 302


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
	cache_key = _get_first_login_flag_key(user)
	first_login_flag = frappe.cache().get(cache_key)
	
	if first_login_flag:
		# Clear the flag immediately (one-time guard)
		frappe.cache().delete(cache_key)
		
		# Check if user is trying to access /app or /desk on first hop
		is_desk_route = any(
			path == route or path.startswith(f"{route}/")
			for route in DESK_ROUTES
		)
		
		if is_desk_route:
			# Force redirect to appropriate portal based on role
			portal_path = _resolve_portal_path(user_roles)
			frappe.logger().debug(
				f"Login guard redirect for {user}: {path} -> {portal_path}, roles={user_roles}"
			)
			_perform_redirect(portal_path)
			return
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
	portal_path = _resolve_portal_path(user_roles)
	frappe.logger().debug(
		f"Desk block redirect for {user}: {path} -> {portal_path}, roles={user_roles}"
	)
	_perform_redirect(portal_path)
