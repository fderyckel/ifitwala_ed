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


def redirect_user_to_entry_portal():
	"""
	Unified login redirect: Most users go to /portal, Admissions Applicants go to /admissions.
	
	The Vue SPA at /portal handles role-based routing internally via
	window.defaultPortal (set by www/portal/index.py based on user roles).
	
	The /admissions portal is a separate Vue SPA for the admissions workflow.
	
	Policy:
	- Admissions Applicants -> /admissions (separate admissions portal)
	- All other authenticated users -> /portal
	- The portal entry point determines which sub-portal to show
	  (Staff > Student > Guardian priority)
	
	This follows the single entry point pattern: server sets context,
	client-side router handles navigation.
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

	# -------------------------------------------------------------
	# 1) Admissions Applicants: always /admissions (separate portal)
	# -------------------------------------------------------------
	if "Admissions Applicant" in roles:
		_force_redirect("/admissions", also_set_home_page=True)
		return

	# ---------------------------------------------------------------
	# 2) All other users: /portal (unified portal with role-based routing)
	# ---------------------------------------------------------------
	_force_redirect("/portal", also_set_home_page=True)


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
