# Copyright (c) 2025, François de Ryckel and contributors
# License: MIT. See license.txt

# ifitwala_ed/utilities/link_queries.py

import frappe
from frappe import _
from ifitwala_ed.utilities.school_tree import get_ancestor_schools

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	Return Academic Years ordered by most recent first (year_start_date DESC, name DESC).
	If `filters.school` is provided, restrict to that school's ancestor chain (incl. self).
	Otherwise, fall back to user's default school when available.
	"""
	filters = filters or {}
	txt = f"%{txt or ''}%"

	# scope by school → allow AY at self or any ancestor
	school = filters.get("school") or frappe.defaults.get_user_default("school")
	params = [txt]

	where = "name LIKE %s"
	if school:
		chain = [school] + (get_ancestor_schools(school) or [])
		placeholders = ", ".join(["%s"] * len(chain))
		where += f" AND school IN ({placeholders})"
		params.extend(chain)

	sql = f"""
		SELECT name
		FROM `tabAcademic Year`
		WHERE {where}
		ORDER BY year_start_date DESC, name DESC
		LIMIT %s, %s
	"""
	params.extend([start, page_len])
	return frappe.db.sql(sql, params)
