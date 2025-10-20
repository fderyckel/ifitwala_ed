# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe

def redirect_student_to_portal():
    user = frappe.session.user
    roles = frappe.get_roles(user)

    # Only proceed if the user has the Student role
    if "Student" in roles:
        # Check that the user has a linked Student record
        if frappe.db.exists("Student", {"student_user_id": user}):
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/sp"
        else:
            # Optional: log for debugging, but don't interrupt login flow
            frappe.logger().warning(f"Student role but no Student profile found for user: {user}")


@frappe.whitelist()
def get_users_with_role(doctype, txt, searchfield, start, page_len, filters):
	role = filters.get("role")
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

	return frappe.db.sql(query, {
		"role": role,
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len
	})
