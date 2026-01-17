# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/users.py

import frappe

def redirect_user_to_entry_portal():
	"""
	Redirect portal users immediately after login.

	Policy (locked):
	- Staff (incl. Academic Staff) -> /portal/staff
	- Students -> /sp
	- Others (e.g. System Manager) -> no forced redirect here

	Implementation notes:
	- Desk login flows can override a weak response redirect.
	  So we ALSO set User.home_page + response.redirect_to to make it stick.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return

	roles = set(frappe.get_roles(user))

	def _force_redirect(path: str):
		# Make redirect durable across Desk /app and Website /login flows.
		try:
			frappe.db.set_value("User", user, "home_page", path, update_modified=False)
		except Exception:
			# If anything blocks setting home_page, still attempt a response redirect.
			pass

		frappe.local.response["home_page"] = path
		frappe.local.response["redirect_to"] = path
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = path

	# ---------------------------------------------------------------
	# Staff portal eligibility
	# - Employee role AND active Employee record
	# - OR Academic Staff role (requested) even if Employee record is missing
	# ---------------------------------------------------------------
	is_active_employee = (
		("Employee" in roles)
		and bool(frappe.db.exists("Employee", {"user_id": user, "status": "Active"}))
	)

	is_academic_staff = ("Academic Staff" in roles)

	if is_active_employee or is_academic_staff:
		_force_redirect("/portal/staff")
		return

	# Student portal: only if Student role + linked Student profile exists
	if "Student" not in roles:
		return

	if frappe.db.exists("Student", {"student_user_id": user}):
		_force_redirect("/sp")
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
