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


def _get_staff_workspace_path(user: str) -> str | None:
	"""
	Get the default workspace path for a staff user based on their Employee designation.
	
	Returns /app/{workspace} if employee has a designation with default_workspace,
	otherwise returns None to let Frappe handle it.
	"""
	try:
		employee = frappe.get_value("Employee", {"user_id": user}, ["designation"], as_dict=True)
		if not employee or not employee.designation:
			return None
		
		designation = frappe.get_doc("Designation", employee.designation)
		if designation.default_workspace:
			return f"/app/{designation.default_workspace.lower().replace(' ', '-')}" if not designation.default_workspace.startswith('/app/') else designation.default_workspace
		return None
	except Exception:
		return None


def _resolve_login_redirect_path(user: str, roles: set) -> str | None:
	"""
	Resolve the appropriate portal path based on user roles.
	
	Architecture: Mixed approach - staff go to /app/{workspace}, portal users to /portal.
	
	Priority order (locked):
	1. Admissions Applicant -> /admissions (separate admissions portal)
	2. Staff (Academic User, etc.) -> /app/{workspace} (from Employee designation)
	3. All other users -> /portal (unified entry, client-side routing handles the rest)
	"""
	if "Admissions Applicant" in roles:
		return "/admissions"
	
	# Check if user has any staff role
	if roles & STAFF_ROLES:
		# Get workspace from Employee designation
		workspace_path = _get_staff_workspace_path(user)
		if workspace_path:
			return workspace_path
		# Fallback: let Frappe handle it if no workspace found
		return None
	
	# Unified /portal entry for all non-staff, non-admissions users
	return "/portal"


def redirect_user_to_entry_portal():
	"""
	Login redirect handler: Routes users to unified portal entry point.
	"""
	user = frappe.session.user
	
	# CRITICAL DEBUG LOGGING - These will always appear in logs
	frappe.log_error(f"=== REDIRECT HOOK CALLED ===")
	frappe.log_error(f"User: {user}")
	frappe.log_error(f"Guest check: {user == 'Guest'}")
	
	if not user or user == "Guest":
		frappe.log_error(f"ABORT: User is Guest or None")
		return

	# Check user roles
	try:
		roles = set(frappe.get_roles(user))
		frappe.log_error(f"Roles found: {roles}")
	except Exception as e:
		frappe.log_error(f"ERROR getting roles: {str(e)}")
		roles = set()

	# Resolve the appropriate portal path
	try:
		path = _resolve_login_redirect_path(user, roles)
		frappe.log_error(f"Resolved path: {path}")
	except Exception as e:
		frappe.log_error(f"ERROR resolving path: {str(e)}")
		path = None

	# If path is None and user is staff, let Frappe handle their redirect
	if path is None:
		if roles & STAFF_ROLES:
			frappe.log_error(f"Staff user - letting Frappe handle to /app/{{workspace}}")
		else:
			frappe.log_error(f"ERROR: No path resolved for non-staff user!")
		return

	# We have a path - FORCE the redirect
	frappe.log_error(f"FORCING redirect to: {path}")
	frappe.log_error(f"Response BEFORE: {dict(frappe.local.response)}")

	# Update User.home_page for persistence across sessions
	try:
		frappe.db.set_value("User", user, "home_page", path, update_modified=False)
		frappe.log_error(f"Updated User.home_page to: {path}")
	except Exception as e:
		frappe.log_error(f"ERROR updating home_page: {str(e)}")

	# FORCE redirect by setting all response keys
	frappe.local.response["home_page"] = path
	frappe.local.response["redirect_to"] = path
	frappe.local.response["location"] = path
	frappe.local.response["type"] = "redirect"

	frappe.log_error(f"Response AFTER: {dict(frappe.local.response)}")
	frappe.log_error(f"=== REDIRECT HOOK COMPLETE ===")


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
