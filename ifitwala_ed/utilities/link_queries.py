# Copyright (c) 2025, François de Ryckel and contributors
# License: MIT. See license.txt

# ifitwala_ed/utilities/link_queries.py

import frappe
from frappe.utils.nestedset import get_descendants_of
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools

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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_group_link_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	Limit the Student Group picker to active groups within the selected school/program branches.
	"""
	filters = filters or {}
	conditions = ["status = 'Active'"]
	params = []

	# scope by school tree
	school = filters.get("school")
	if school:
		schools = get_descendant_schools(school) or [school]
		if schools:
			placeholders = ", ".join(["%s"] * len(schools))
			conditions.append(f"school in ({placeholders})")
			params.extend(schools)

	# scope by program tree
	program = filters.get("program")
	if program:
		programs = _expand_program_scope(program)
		if programs:
			placeholders = ", ".join(["%s"] * len(programs))
			conditions.append(f"program in ({placeholders})")
			params.extend(programs)

	search_txt = (txt or "").strip()
	if search_txt:
		search_txt = f"%{search_txt}%"
		conditions.append("(name like %s or student_group_name like %s)")
		params.extend([search_txt, search_txt])

	sql = f"""
		select name, student_group_name
		from `tabStudent Group`
		where {' and '.join(conditions)}
		order by student_group_name asc, name asc
		limit %s, %s
	"""
	params.extend([start, page_len])
	return frappe.db.sql(sql, params)


def _expand_program_scope(program: str | None) -> list[str]:
	if not program:
		return []
	descendants = get_descendants_of("Program", program) or []
	return [program, *descendants]
