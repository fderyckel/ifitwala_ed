# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/portal.py

import frappe
from frappe import _

CACHE_TTL_SECONDS = 600


@frappe.whitelist()
def get_staff_home_header():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	cache = frappe.cache()
	cache_key = f"staff_home:header:{user}"
	cached = cache.get_value(cache_key)
	if cached:
		try:
			return frappe.parse_json(cached)
		except Exception:
			pass

	row = frappe.db.get_value("User", user, ["name", "first_name", "full_name"], as_dict=True)
	if not row:
		frappe.throw(_("User not found."), frappe.DoesNotExistError)

	payload = {
		"user": row.name,
		"first_name": row.first_name,
		"full_name": row.full_name,
	}

	cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=CACHE_TTL_SECONDS)
	return payload
