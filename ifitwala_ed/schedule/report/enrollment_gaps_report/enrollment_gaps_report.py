# Copyright (c) 2025, François de Ryckel and contributors
# License: MIT. See license.txt

# ifitwala_ed/schedule/report/enrollment_gaps_report/enrollment_gaps_report.py

import frappe
from frappe import _
from ifitwala_ed.utilities.school_tree import get_descendant_schools, get_ancestor_schools


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	List AYs whose `school` is either:
	- the selected school,
	- any of its descendants, OR
	- any of its ancestors.

	This covers cases where a child campus uses a parent school's AY (shared calendar),
	and cases where a parent admin scopes to child-campus AYs.
	"""
	school = (filters or {}).get("school")
	params = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

	if not school:
		return frappe.db.sql(
			"""
			SELECT name
			FROM `tabAcademic Year`
			WHERE name LIKE %(txt)s
			ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
			LIMIT %(start)s, %(page_len)s
			""",
			params,
		)

	# Union of ancestors + descendants + self
	descendants = set(get_descendant_schools(school) or [])
	ancestors   = set(get_ancestor_schools(school) or [])
	scope_schools = tuple(sorted(descendants.union(ancestors) or {school}))

	return frappe.db.sql(
		"""
		SELECT name
		FROM `tabAcademic Year`
		WHERE school IN %(schools)s
		  AND name LIKE %(txt)s
		ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
		LIMIT %(start)s, %(page_len)s
		""",
		{**params, "schools": scope_schools},
	)


def execute(filters=None):
	filters = filters or {}
	ay = (filters.get("academic_year") or "").strip()
	school = (filters.get("school") or "").strip()

	if not school:
		frappe.throw(_("Please select a School."))
	if not ay:
		frappe.throw(_("Please select an Academic Year."))

	# compute school subtree once
	schools = get_descendant_schools(school) or [school]

	columns = [
		{"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 190},
		{"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 140},
		{"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 220},
		{"label": _("Program"), "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 140},
		{"label": _("Course"), "fieldname": "course", "fieldtype": "Link", "options": "Course", "width": 200},
		{"label": _("Term"), "fieldname": "term", "fieldtype": "Data", "width": 110},
		{"label": _("Missing"), "fieldname": "missing", "fieldtype": "Data", "width": 260},
	]

	# Single SQL, scoped by (AY, school subtree)
	# Assumptions:
	# - Student has a `school` link (your app does use school on Student).
	# - Student Group has a `school` link (you added this recently).
	data = frappe.db.sql(
		"""
		-- 1) Missing Program: active students belonging to the selected school subtree
		--    who have NO Program Enrollment for the selected AY.
		SELECT
			'Missing Program' AS type,
			s.name AS student,
			s.student_name AS student_name,
			NULL AS program,
			NULL AS course,
			NULL AS term,
			'No Program Enrollment in selected AY' AS missing
		FROM `tabStudent` s
		WHERE s.status = 'Active'
		  AND s.school IN %(schools)s
		  AND NOT EXISTS (
				SELECT 1
				FROM `tabProgram Enrollment` pe
				WHERE pe.student = s.name
				  AND pe.academic_year = %(ay)s
		  )

		UNION ALL

		-- 2) Missing Student Group: students with PEC rows in the selected AY,
		--    but without any SG (same AY) within the school subtree matching:
		--    (a) course-matched SG, or (b) program-matched SG where sg.course IS NULL.
		SELECT
			'Missing Student Group' AS type,
			pe.student AS student,
			st.student_name AS student_name,
			pe.program AS program,
			pec.course AS course,
			NULL AS term,
			'No Student Group in selected AY for this Course/Program' AS missing
		FROM `tabProgram Enrollment` pe
		INNER JOIN `tabProgram Enrollment Course` pec
			ON pec.parent = pe.name AND pec.parenttype = 'Program Enrollment'
		INNER JOIN `tabStudent` st
			ON st.name = pe.student
		WHERE pe.academic_year = %(ay)s
		  AND st.school IN %(schools)s
		  AND NOT EXISTS (
				SELECT 1
				FROM `tabStudent Group Student` sgs
				INNER JOIN `tabStudent Group` sg
					ON sg.name = sgs.parent AND sgs.parenttype = 'Student Group'
				WHERE sgs.student = pe.student
				  AND sg.academic_year = %(ay)s
				  AND sg.school IN %(schools)s
				  AND (
						(sg.course IS NOT NULL AND sg.course = pec.course)
						OR (sg.course IS NULL AND sg.program = pe.program)
				  )
		  )
		ORDER BY type, student
		""",
		{"ay": ay, "schools": tuple(schools)},
		as_dict=True,
	)

	return columns, data
