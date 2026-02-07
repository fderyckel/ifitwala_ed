# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/users.py

import frappe

def _is_active_employee(user: str) -> bool:
	return bool(
		frappe.db.exists(
			"Employee",
			{"user_id": user, "employment_status": "Active"},
		)
	)


def _resolve_login_redirect_path(user: str, roles: set[str]) -> str:
	"""
	Server-owned role routing after login.
	Priority is locked: Staff > Student > Guardian.
	"""
	if "Admissions Applicant" in roles:
		return "/admissions"
	if _is_active_employee(user):
		return "/portal/staff"
	if "Student" in roles:
		return "/portal/student"
	if "Guardian" in roles:
		return "/portal/guardian"
	return "/portal"


def redirect_user_to_entry_portal():
	"""
	Role-based login redirect with explicit server routing.
	Priority is locked: Staff > Student > Guardian.
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

	roles = set(frappe.get_roles(user))
	path = _resolve_login_redirect_path(user, roles)
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
