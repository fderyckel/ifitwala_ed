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
	Allow picking Academic Years whose `school` is the selected school
	or any of its **ancestors** (covers IIS parent AY when ISS is selected).
	"""
	school = (filters or {}).get("school")
	params = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

	if not school:
		# permissive before School is chosen
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

	# Ancestors list already includes self per your util
	scope_schools = tuple(get_ancestor_schools(school) or [school])

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

	schools = tuple(get_descendant_schools(school) or [school])

	columns = [
		{"label": _("Type"),         "fieldname": "type",         "fieldtype": "Data",   "width": 170},
		{"label": _("Student"),      "fieldname": "student",      "fieldtype": "Link",   "options": "Student", "width": 130},
		{"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data",   "width": 220},
		{"label": _("Program"),      "fieldname": "program",      "fieldtype": "Link",   "options": "Program", "width": 180},
		{"label": _("Course"),       "fieldname": "course",       "fieldtype": "Link",   "options": "Course",  "width": 240},
		{"label": _("Missing"),      "fieldname": "missing",      "fieldtype": "Data",   "width": 180},
	]

	data = frappe.db.sql(
		"""
		WITH enrollments AS (
			SELECT
				pe.student,
				st.student_full_name AS student_name,
				pe.program,
				pe.academic_year,
				st.school,
				pec.course
			FROM `tabProgram Enrollment` pe
			INNER JOIN `tabProgram Enrollment Course` pec
				ON pec.parent = pe.name
			   AND pec.parenttype = 'Program Enrollment'
			   AND COALESCE(pec.status, 'Enrolled') = 'Enrolled'
			INNER JOIN `tabStudent` st
				ON st.name = pe.student
			WHERE pe.academic_year = %(ay)s
			  AND st.school IN %(schools)s
		)

		-- (1) In-scope students with NO Program Enrollment in AY
		SELECT
			'Missing Program Enrollment' AS type,
			s.name                       AS student,
			s.student_full_name          AS student_name,
			NULL                         AS program,
			NULL                         AS course,
			'Program Enrollment'         AS missing
		FROM `tabStudent` s
		WHERE COALESCE(s.enabled, 1) = 1
		  AND s.school IN %(schools)s
		  AND NOT EXISTS (
				SELECT 1
				FROM `tabProgram Enrollment` pe
				WHERE pe.student = s.name
				  AND pe.academic_year = %(ay)s
		  )

		UNION ALL

		-- (2) Enrolled in a course but NOT placed in a matching Course-based SG (term ignored)
		SELECT
			'Missing Student Group' AS type,
			e.student               AS student,
			e.student_name          AS student_name,
			e.program               AS program,
			e.course                AS course,
			'Student Group (Course)' AS missing
		FROM enrollments e
		WHERE NOT EXISTS (
			SELECT 1
			FROM `tabStudent Group` sg
			JOIN `tabStudent Group Student` sgs
			  ON sgs.parent = sg.name
			 AND sgs.parenttype = 'Student Group'
			 And sgs.student = e.student
			 AND COALESCE(sgs.active, 1) = 1
			WHERE sg.status = 'Active'
			  AND sg.group_based_on = 'Course'
			  AND sg.academic_year = e.academic_year
			  AND sg.course = e.course
			  -- NOTE: term deliberately ignored for year-long vs multi-term cases
		)
		ORDER BY 1, 2
		""",
		{"ay": ay, "schools": schools},
		as_dict=True,
	)

	return columns, data
