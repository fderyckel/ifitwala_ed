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


def _has_active_employee_profile(*, user: str, roles: set) -> bool:
	"""Return True when user has Employee role and an active Employee record."""
	if "Employee" not in roles:
		return False
	return bool(
		frappe.db.exists(
			"Employee",
			{"user_id": user, "employment_status": "Active"},
		)
	)


def _resolve_login_redirect_path(*, user: str, roles: set) -> str:
	"""
	Resolve the appropriate portal path based on user roles.

	Priority order (locked):
	1. Admissions Applicant -> /admissions
	2. Active Employee -> /portal/staff
	3. Student -> /portal/student
	4. Guardian -> /portal/guardian
	5. Fallback -> /portal
	"""
	if "Admissions Applicant" in roles:
		return "/admissions"
	if _has_active_employee_profile(user=user, roles=roles):
		return "/portal/staff"
	if "Student" in roles:
		return "/portal/student"
	if "Guardian" in roles:
		return "/portal/guardian"
	return "/portal"


def redirect_user_to_entry_portal():
	"""
	Login redirect handler: Routes users to role-appropriate portal entry point.

	Policy:
	- Admissions Applicants -> /admissions
	- Active Employees -> /portal/staff
	- Students -> /portal/student
	- Guardians -> /portal/guardian
	- Fallback -> /portal
	
	Home-page persistence note:
	We always overwrite User.home_page with the resolved role-specific path.
	This is acceptable for fresh installations; custom home-page preferences
	(e.g., staff setting /app) will be lost on next login.
	Maintainer decision: "fine for fresh install" (2026-02-07).
	TODO: User preference persistence planned for v2.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return

	def _force_redirect(path: str, also_set_home_page: bool = True):
		if also_set_home_page:
			try:
				frappe.db.set_value("User", user, "home_page", path, update_modified=False)
			except Exception:
				pass

		# Immediate redirect for this request
		frappe.local.response["home_page"] = path
		frappe.local.response["redirect_to"] = path
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = path

	# Check user roles
	roles = set(frappe.get_roles(user))

	# Resolve the appropriate portal path
	path = _resolve_login_redirect_path(user=user, roles=roles)

	# Debug logging to confirm redirect path during login
	frappe.logger().debug(
		f"Login redirect for {user}: roles={roles}, path={path}"
	)

	_force_redirect(path, also_set_home_page=True)


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
