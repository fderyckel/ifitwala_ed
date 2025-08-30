# Copyright (c) 2025, Francois de Ryckel and contributors
# For license information, please see license.txt

"""Uses consistent alias `sl` for tabStudent Log in every query to
   avoid ambiguous column references when filters include `program`.
"""

import frappe


@frappe.whitelist()
def get_dashboard_data(filters=None):
	try:
		filters = frappe.parse_json(filters) or {}

		authorized_schools = get_authorized_schools(frappe.session.user)
		if not authorized_schools:
			return {"error": "No authorized schools found."}

		conditions, params = [], {}
		# ▶ enforce access by school (uses your new index on sl.school)
		conditions.append("sl.school IN %(authorized_schools)s")
		params["authorized_schools"] = tuple(authorized_schools)

		# ── School filter (now direct on Student Log) ─────────────
		if filters.get("school"):
			conditions.append("sl.school = %(field_school)s")
			params["field_school"] = filters["school"]

		# ── Direct columns in Student Log (alias sl) ──────────────
		direct_map = {
			"academic_year": "sl.academic_year",
			"program":       "sl.program",
			"author":        "sl.author_name",
		}
		for key, col in direct_map.items():
			if filters.get(key):
				ph = f"field_{key}"
				conditions.append(f"{col} = %({ph})s")
				params[ph] = filters[key]

		where_clause = " AND ".join(conditions) if conditions else "1=1"

		def q(sql):
			return frappe.db.sql(sql.format(w=where_clause), params, as_dict=True)

		# (no query bodies change below — they already read from sl.*)
		log_type_count = q(
			"SELECT sl.log_type AS label, COUNT(*) AS value "
			"FROM `tabStudent Log` sl WHERE {w} "
			"GROUP BY sl.log_type ORDER BY value DESC"
		)

		logs_by_cohort = q(
			"SELECT pe.cohort AS label, COUNT(sl.name) AS value "
			"FROM `tabStudent Log` sl "
			"LEFT JOIN `tabProgram Enrollment` pe ON sl.student = pe.student "
			"WHERE {w} GROUP BY pe.cohort ORDER BY value DESC"
		)

		logs_by_program = q(
			"SELECT sl.program AS label, COUNT(sl.name) AS value "
			"FROM `tabStudent Log` sl WHERE {w} GROUP BY sl.program ORDER BY value DESC"
		)

		logs_by_author = q(
			"SELECT sl.author_name AS label, COUNT(*) AS value "
			"FROM `tabStudent Log` sl WHERE {w} GROUP BY sl.author_name ORDER BY value DESC"
		)

		next_step_types = q(
			"SELECT sl.next_step AS label, COUNT(*) AS value "
			"FROM `tabStudent Log` sl WHERE {w} GROUP BY sl.next_step ORDER BY value DESC"
		)

		incidents_over_time = q(
			"SELECT DATE_FORMAT(sl.date,'%%Y-%%m-%%d') AS label, COUNT(*) AS value "
			"FROM `tabStudent Log` sl WHERE {w} GROUP BY label ORDER BY label ASC"
		)

		open_follow_ups = frappe.db.sql(
			f"SELECT COUNT(*) FROM `tabStudent Log` sl WHERE {where_clause} "
			"AND sl.follow_up_status = 'Open'",
			params,
		)[0][0]

		# ── Student Logs (if student filter is set) ─────────────────
		student_logs = []
		if filters.get("student"):
				# reuse the same params + conditions used above
				conds = ["sl.school IN %(authorized_schools)s", "sl.student = %(field_student)s"]
				p = {**params, "field_student": filters["student"]}

				# if the page has a School filter set, honor it too (cheap on sl.school)
				if filters.get("school"):
						conds.append("sl.school = %(field_school)s")
						p["field_school"] = filters["school"]

				where_detail = " AND ".join(conds)

				student_logs = frappe.db.sql(
						f"""
						SELECT
								sl.date,
								sl.log_type,
								sl.log AS content,
								sl.author_name AS author
						FROM `tabStudent Log` sl
						WHERE {where_detail}
						ORDER BY sl.date DESC
						""",
						p,
						as_dict=True
				)

		return {
			"logTypeCount": log_type_count,
			"logsByCohort": logs_by_cohort,
			"logsByProgram": logs_by_program,
			"logsByAuthor": logs_by_author,
			"nextStepTypes": next_step_types,
			"incidentsOverTime": incidents_over_time,
			"openFollowUps": open_follow_ups,
			"studentLogs": student_logs,
		}

	except Exception as e:
		frappe.log_error(str(e), "Student Log Dashboard Data Error")
		return {"error": str(e)}


@frappe.whitelist()
def get_distinct_students(filters=None, search_text: str = ""):
	try:
		filters = frappe.parse_json(filters) or {}
		txt = (search_text or "").strip()

		# Authorize by user's school branch (self + descendants)
		authorized_schools = get_authorized_schools(frappe.session.user)
		if not authorized_schools:
			return {"error": "No authorized schools found."}

		conditions, params = [], {}
		params["authorized_schools"] = tuple(authorized_schools)

		# Context filters
		if filters.get("school"):
			conditions.append("pe.school = %(school)s")
			params["school"] = filters["school"]
		if filters.get("program"):
			conditions.append("pe.program = %(program)s")
			params["program"] = filters["program"]
		if filters.get("academic_year"):
			conditions.append("pe.academic_year = %(academic_year)s")
			params["academic_year"] = filters["academic_year"]

		# Partial text match (id or full name)
		if txt:
			conditions.append("(pe.student LIKE %(txt)s OR s.student_full_name LIKE %(txt)s)")
			params["txt"] = f"%{txt}%"

		# 🔒 Always constrain to authorized schools (no siblings)
		conditions.append("pe.school IN %(authorized_schools)s")

		where_clause = " AND ".join(conditions) if conditions else "1=1"

		return frappe.db.sql(f"""
			SELECT DISTINCT pe.student, s.student_full_name AS student_full_name
			FROM `tabProgram Enrollment` pe
			INNER JOIN `tabStudent` s ON pe.student = s.name
			WHERE {where_clause}
			ORDER BY s.student_full_name
			LIMIT 100
		""", params, as_dict=True)

	except Exception as e:
		frappe.log_error(message=str(e), title="Student Lookup Error")
		return {"error": str(e)}


@frappe.whitelist()
def get_recent_logs(filters=None, start: int = 0, page_length: int = 25):
	filters = frappe.parse_json(filters) or {}

	authorized_schools = get_authorized_schools(frappe.session.user)
	if not authorized_schools:
		return []

	conditions, params = [], {}

	# 🔒 scope by school branch (self + descendants)
	conditions.append("sl.school IN %(authorized_schools)s")
	params["authorized_schools"] = tuple(authorized_schools)

	# page filters (same as before), but school now direct on Student Log
	if filters.get("school"):
		conditions.append("sl.school = %(school)s")
		params["school"] = filters["school"]

	direct_map = {
		"academic_year": "sl.academic_year",
		"program":       "sl.program",
		"author":        "sl.author_name",
	}
	for key, col in direct_map.items():
		if filters.get(key):
			conditions.append(f"{col} = %({key})s")
			params[key] = filters[key]

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	logs = frappe.db.sql(
		f"""
		SELECT
			sl.date,
			s.student_full_name AS student,
			sl.program,
			sl.log_type,
			sl.log              AS content,
			sl.author_name      AS author,
			sl.requires_follow_up
		FROM `tabStudent Log` sl
		LEFT JOIN `tabStudent` s ON s.name = sl.student
		WHERE {where_clause}
		ORDER BY sl.date DESC
		LIMIT %(start)s, %(page_len)s
		""",
		{**params, "start": start, "page_len": page_length},
		as_dict=True,
	)
	return logs


def get_authorized_schools(user):
	"""Return user's school + all descendants using one SQL join on lft/rgt."""
	# Resolve the anchor school: user default first, else Employee.school
	default_school = frappe.defaults.get_user_default("school", user)
	if not default_school:
		default_school = frappe.db.get_value("Employee", {"user_id": user}, "school")
	if not default_school:
		return []

	rows = frappe.db.sql(
		"""
		SELECT s2.name
		FROM `tabSchool` s1
		JOIN `tabSchool` s2
			ON s2.lft >= s1.lft AND s2.rgt <= s1.rgt
		WHERE s1.name = %s
		""",
		(default_school,),
		as_list=True,
	)
	return [r[0] for r in rows] or [default_school]

