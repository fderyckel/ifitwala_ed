# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/portal.py

import frappe
from frappe import _

CACHE_TTL_SECONDS = 600


def _resolve_staff_first_name(user: str, user_first_name: str | None, user_full_name: str | None) -> str:
	"""
	Resolve the preferred greeting name for StaffHome.

	Priority:
	1) Employee Preferred Name
	2) Employee First Name
	3) User.first_name
	4) First token of User.full_name
	5) "Staff"
	"""
	# Employee-based name (preferred)
	emp = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["employee_preferred_name", "employee_first_name"],
		as_dict=True,
	)

	if emp:
		preferred = (emp.employee_preferred_name or "").strip()
		if preferred:
			return preferred

		first = (emp.employee_first_name or "").strip()
		if first:
			return first

	# Fallback to User fields
	first = (user_first_name or "").strip()
	if first:
		return first

	full = (user_full_name or "").strip()
	if full:
		# Avoid clever parsing; just take the first token deterministically.
		return full.split(" ")[0].strip() or "Staff"

	return "Staff"


@frappe.whitelist()
def get_staff_home_header():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	cache = frappe.cache()
	cache_key = f"staff_home:header:v2:{user}"
	cached = cache.get_value(cache_key)
	if cached:
		try:
			return frappe.parse_json(cached)
		except Exception:
			pass

	row = frappe.db.get_value("User", user, ["name", "first_name", "full_name"], as_dict=True)
	if not row:
		frappe.throw(_("User not found."), frappe.DoesNotExistError)

	first_name = _resolve_staff_first_name(user, row.first_name, row.full_name)

	payload = {
		"user": row.name,
		"first_name": first_name,
		"full_name": row.full_name,
	}

	cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=CACHE_TTL_SECONDS)
	return payload
