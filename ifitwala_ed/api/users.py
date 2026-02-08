# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/users.py

import frappe

# Staff roles that take priority for desk access
STAFF_ROLES = frozenset([
	"Academic User",
	"System Manager",
	"Teacher",
	"Administrator",
	"Finance User",
	"HR User",
	"HR Manager",
])


def _resolve_login_redirect_path(roles: set) -> str | None:
	"""
	Resolve the appropriate portal path based on user roles.
	
	Architecture: Unified /portal entry with client-side routing (Option B).
	The Vue SPA at /portal reads window.defaultPortal to route internally.
	
	Priority order (locked):
	1. Admissions Applicant -> /admissions (separate admissions portal)
	2. Staff (Academic User, etc.) -> None (let Frappe handle to /app/{workspace})
	3. All other users -> /portal (unified entry, client-side routing handles the rest)
	
	Rationale: Admissions is a separate flow; staff go to Desk with their default
	workspace; all other users use unified /portal with client-side role detection.
	"""
	if "Admissions Applicant" in roles:
		return "/admissions"
	
	# Check if user has any staff role - let Frappe handle their redirect
	if roles & STAFF_ROLES:
		return None  # Let Frappe redirect to /app/{default_workspace}
	
	# Unified /portal entry for all non-staff, non-admissions users
	# Client-side router handles role-specific sub-portal selection
	return "/portal"


def redirect_user_to_entry_portal():
	"""
	Login redirect handler: Routes users to unified portal entry point.
	
	This is the PRIMARY redirect authority. It runs via the after_login hook
	and OVERRIDES any redirect-to parameter from the login URL.
	
	Architecture: Unified /portal entry with client-side routing (Option B).
	The Vue SPA at /portal reads window.defaultPortal (set by www/portal/index.py)
	and routes internally to the appropriate sub-portal.
	
	Policy:
	- Admissions Applicants -> /admissions (separate admissions portal)
	- Staff (Academic User, Teacher, etc.) -> Let Frappe handle to /app/{workspace}
	- All other authenticated users -> /portal (unified entry)
	
	The portal entry point determines which sub-portal to show via client-side logic
	with priority: Staff > Student > Guardian.
	
	Home-page persistence note:
	We overwrite User.home_page with the portal path for non-staff users.
	This is acceptable for fresh installations; custom home-page preferences
	(e.g., staff setting /app) will be lost on next login for portal users only.
	Maintainer decision: "fine for fresh install" (2026-02-07).
	TODO: User preference persistence planned for v2.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return

	# Check user roles
	roles = set(frappe.get_roles(user))

	# Resolve the appropriate portal path
	path = _resolve_login_redirect_path(roles)

	# If path is None, this is a staff user - let Frappe handle their redirect
	if path is None:
		frappe.logger().info(
			f"[AFTER_LOGIN] User {user} is staff with roles {roles} -> letting Frappe handle redirect to /app"
		)
		return

	# Debug logging to confirm redirect path during login
	frappe.logger().info(
		f"[AFTER_LOGIN] User {user} with roles {roles} -> redirecting to {path}"
	)

	# Update User.home_page for persistence across sessions
	try:
		frappe.db.set_value("User", user, "home_page", path, update_modified=False)
	except Exception:
		pass

	# FORCE redirect by setting all response keys
	# This OVERRIDES any redirect-to parameter from the login URL
	# Frappe uses the LAST value set for redirect_to, so we set it here
	frappe.local.response["home_page"] = path
	frappe.local.response["redirect_to"] = path
	frappe.local.response["location"] = path
	frappe.local.response["type"] = "redirect"

	frappe.logger().info(
		f"[AFTER_LOGIN] Response set: home_page={path}, redirect_to={path}"
	)


@frappe.whitelist()
def get_users_with_role(doctype, txt, searchfield, start, page_len, filters):
	"""Return enabled users matching the provided role for link-field queries."""
	role = filters.get("role") if filters else None
	if not role:
		return []

	query = """
		SELECT u.name, u.full_name
		FROM `tabUser` u
		JOIN `tabHas Role` r ON u.name = r.parent
		WHERE r.role = %(role)s
			AND u.enabled = 1
			AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.name
		LIMIT %(start)s, %(page_len)s
	"""

	return frappe.db.sql(
		query,
		{
			"role": role,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)
