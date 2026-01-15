# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/users.py

import frappe



def redirect_user_to_entry_portal():
	"""
	Redirect portal users immediately after login.

	Priority:
	1) Active Employee users -> Staff Portal (/portal/staff)
	2) Students with a linked Student profile -> Student portal (/sp)

	Notes:
	- "Active Employee" rule matches /portal/index.py:
	  role "Employee" AND linked Employee.status == "Active"
	- We intentionally do NOT redirect everyone else (e.g. System Manager) here.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return

	roles = set(frappe.get_roles(user))

	# ---------------------------------------------------------------
	# Staff portal eligibility (portal sections != frappe roles)
	# Compromise rule:
	#   Staff: user has role "Employee" AND linked Employee.status == "Active"
	# ---------------------------------------------------------------
	is_active_employee = (
		("Employee" in roles)
		and bool(frappe.db.exists("Employee", {"user_id": user, "status": "Active"}))
	)

	if is_active_employee:
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/portal/staff"
		return

	# Student portal: only if Student role + linked Student profile exists
	if "Student" not in roles:
		return

	if frappe.db.exists("Student", {"student_user_id": user}):
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/sp"
	else:
		frappe.logger().warning(
			f"Student role but no Student profile found for user: {user}"
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
