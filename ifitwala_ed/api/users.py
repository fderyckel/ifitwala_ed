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


def _has_staff_portal_access(*, user: str, roles: set) -> bool:
	"""Return True when user should land on the staff portal."""
	if roles & STAFF_ROLES:
		return True
	return _has_active_employee_profile(user=user, roles=roles)


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
	if _has_staff_portal_access(user=user, roles=roles):
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
	
	Refactored (2026-02-13):
	We no longer persist `User.home_page` to the database on login.
	The redirect is calculated in-memory and returned via `frappe.local.response`.
	This prevents database locking and performance issues during high-concurrency login events.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return

	# Check user roles
	roles = set(frappe.get_roles(user))

	# Resolve the appropriate portal path
	path = _resolve_login_redirect_path(user=user, roles=roles)

	# Login response redirect contract: let Frappe login client handle navigation.
	frappe.local.response["home_page"] = path
	frappe.local.response["redirect_to"] = path


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
