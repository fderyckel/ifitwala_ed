# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/users.py

import frappe

def redirect_user_to_entry_portal():
	"""
	Authoritative login routing (Option C).

	Policy:
	- Real students -> /sp (always)
	- Active employees -> default /portal/staff, but allow opt-in to Desk:
	  If User.home_page is already set (e.g. /app), we DO NOT override it.
	- Guardians -> /portal/guardian (will route to guardian-home via SPA router)

	Why:
	- Desk /app logins can override weak response redirects.
	- Setting User.home_page is the durable source of truth.
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

	# ---------------------------------------------------------------
	# 1) Students: always /sp (durable)
	# ---------------------------------------------------------------
	if frappe.db.exists("Student", {"student_user_id": user}):
		_force_redirect("/sp", also_set_home_page=True)
		return

	# ---------------------------------------------------------------
	# 2) Guardians: /portal/guardian (SPA will route to guardian-home based on defaultPortal)
	# ---------------------------------------------------------------
	roles = set(frappe.get_roles(user))
	if "Guardian" in roles:
		current_home = (frappe.db.get_value("User", user, "home_page") or "").strip()
		if not current_home:
			_force_redirect("/portal/guardian", also_set_home_page=True)
		else:
			# If already set to portal or guardian-specific path, redirect without overwriting
			if current_home in ("/portal", "/portal/guardian"):
				_force_redirect(current_home, also_set_home_page=False)
			# Otherwise respect their explicit home_page choice
		return

	# ---------------------------------------------------------------
	# 3) Employees: default /portal/staff (but respect explicit opt-in)
	# ---------------------------------------------------------------
	if frappe.db.exists("Employee", {"user_id": user, "employment_status": "Active"}):
		current_home = (frappe.db.get_value("User", user, "home_page") or "").strip()

		# If home_page already explicitly set (e.g. /app), respect it.
		# If empty/unset, apply portal default.
		if not current_home:
			_force_redirect("/portal/staff", also_set_home_page=True)
		else:
			# Optional: still redirect immediately if already set to portal
			# (keeps login snappy + consistent)
			if current_home == "/portal/staff":
				_force_redirect("/portal/staff", also_set_home_page=False)

		return

	# ---------------------------------------------------------------
	# 4) Admissions Applicant: always /admissions
	# ---------------------------------------------------------------
	if "Admissions Applicant" in roles:
		current_home = (frappe.db.get_value("User", user, "home_page") or "").strip()
		if not current_home:
			_force_redirect("/admissions", also_set_home_page=True)
		else:
			if current_home == "/admissions":
				_force_redirect("/admissions", also_set_home_page=False)

	# Others: do nothing (Desk defaults remain)
	return


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
