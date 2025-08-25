# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from typing import List
import frappe
from frappe.utils import now_datetime

def mark_read(user: str, ref_dt: str, ref_dn: str):
	try:
		frappe.get_doc({
			"doctype": "Portal Read Receipt",
			"user": user,
			"reference_doctype": ref_dt,
			"reference_name": ref_dn,
			"read_at": now_datetime()
		}).insert(ignore_permissions=True)
	except frappe.UniqueValidationError:
		pass

def unread_names_for(user: str, ref_dt: str, names: List[str]) -> List[str]:
	if not names:
		return []
	seen = frappe.db.get_values(
		"Portal Read Receipt",
		{"user": user, "reference_doctype": ref_dt, "reference_name": ["in", names]},
		["reference_name"], as_dict=True
	)
	seen_set = {r["reference_name"] for r in seen}
	return [n for n in names if n not in seen_set]
