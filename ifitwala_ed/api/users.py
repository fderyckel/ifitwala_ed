import frappe


def redirect_student_to_portal():
	"""Redirect students with portal access immediately after login."""
	user = frappe.session.user
	roles = frappe.get_roles(user)

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
