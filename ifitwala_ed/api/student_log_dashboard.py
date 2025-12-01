# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_log_dashboard.py

from __future__ import annotations

import frappe
from frappe.utils import getdate


def _normalize_date_filter(value):
	"""Accepts None, string, date, datetime and returns a YYYY-MM-DD string or None."""
	if not value:
		return None
	if isinstance(value, str):
		v = value.strip()
		return v or None
	# Fallback for date/datetime objects etc.
	try:
		return getdate(value).isoformat()
	except Exception:
		# Last resort: string representation (still safe for SQL parameter)
		return str(value)


def _resolve_date_window(filters):
	"""
	Return (date_from, date_to) as strings 'YYYY-MM-DD' applying these rules:

	- If no Academic Year: use from_date/to_date as provided (open-ended ok).
	- If Academic Year set:
		• If no from/to provided -> AY range.
		• If provided range(s) fully within AY -> keep provided (narrower).
		• If provided range(s) fall outside AY or are missing -> AY takes precedence.
	"""
	fd = _normalize_date_filter(filters.get("from_date"))
	td = _normalize_date_filter(filters.get("to_date"))

	ay = (filters.get("academic_year") or "").strip()
	ay_start, ay_end = (None, None)
	if ay:
		ay_start, ay_end = frappe.db.get_value(
			"Academic Year", ay, ["year_start_date", "year_end_date"]
		) or (None, None)

	# No AY → pass through (already normalized)
	if not (ay_start and ay_end):
		return fd, td

	# Normalize AY dates to strings as well
	ay_start_s = getdate(ay_start).isoformat()
	ay_end_s = getdate(ay_end).isoformat()

	# AY present; precedence logic
	if not fd and not td:
		return ay_start_s, ay_end_s

	if fd and td and (fd >= ay_start_s and td <= ay_end_s):
		return fd, td

	if fd and not td and (ay_start_s <= fd <= ay_end_s):
		return fd, ay_end_s

	if td and not fd and (ay_start_s <= td <= ay_end_s):
		return ay_start_s, td

	# Not matching → AY wins
	return ay_start_s, ay_end_s


def _apply_common_filters(filters, authorized_schools):
	"""
	Build WHERE conditions/params shared by queries, including date window.
	"""
	conditions, params = [], {}

	# enforce access by school (uses your index on sl.school)
	conditions.append("sl.school IN %(authorized_schools)s")
	params["authorized_schools"] = tuple(authorized_schools)

	# School filter (include descendants)
	if filters.get("school"):
		conditions.append("""
			sl.school IN (
				SELECT s2.name
				FROM `tabSchool` s1
				JOIN `tabSchool` s2
					ON s2.lft >= s1.lft AND s2.rgt <= s1.rgt
				WHERE s1.name = %(field_school)s
			)
		""")
		params["field_school"] = filters["school"]

	# Direct columns in Student Log (alias sl)
	direct_map = {
		"academic_year": "sl.academic_year",
		"program": "sl.program",
		"author": "sl.author_name",
	}
	for key, col in direct_map.items():
		if filters.get(key):
			ph = f"field_{key}"
			conditions.append(f"{col} = %({ph})s")
			params[ph] = filters[key]

	# Date window (From/To with AY precedence)
	date_from, date_to = _resolve_date_window(filters)
	if date_from:
		conditions.append("sl.date >= %(date_from)s")
		params["date_from"] = date_from
	if date_to:
		conditions.append("sl.date <= %(date_to)s")
		params["to_date"] = date_to
		params["date_to"] = date_to  # keep original param name used in SQL

	where_clause = " AND ".join(conditions) if conditions else "1=1"
	return where_clause, params


@frappe.whitelist()
def get_dashboard_data(filters=None):
	try:
		# Make it robust whether filters arrives as JSON string or dict
		if isinstance(filters, str):
			filters = frappe.parse_json(filters) or {}
		else:
			filters = filters or {}

		authorized_schools = get_authorized_schools(frappe.session.user)
		if not authorized_schools:
			return {"error": "No authorized schools found."}

		where_clause, params = _apply_common_filters(filters, authorized_schools)

		def q(sql):
			return frappe.db.sql(sql.format(w=where_clause), params, as_dict=True)

		log_type_count = q(
			"SELECT sl.log_type AS label, COUNT(*) AS value "
			"FROM `tabStudent Log` sl WHERE {w} "
			"GROUP BY sl.log_type ORDER BY value DESC"
		)

		logs_by_cohort = q(
			"SELECT pe.cohort AS label, COUNT(sl.name) AS value "
			"FROM `tabStudent Log` sl "
			"LEFT JOIN `tabProgram Enrollment` pe "
			"  ON pe.student = sl.student "
			" AND pe.academic_year = sl.academic_year "
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

		# ── Student Logs (detail for a specific student) ─────────────
		student_logs = []
		if filters.get("student"):
			conds = ["sl.school IN %(authorized_schools)s", "sl.student = %(field_student)s"]
			p = {**params, "field_student": filters["student"]}

			if filters.get("school"):
				conds.append("""
					sl.school IN (
						SELECT s2.name
						FROM `tabSchool` s1
						JOIN `tabSchool` s2
							ON s2.lft >= s1.lft AND s2.rgt <= s1.rgt
						WHERE s1.name = %(field_school)s
					)
				""")
				p["field_school"] = filters["school"]

			where_detail = " AND ".join(conds)

			student_logs = frappe.db.sql(
				f"""
				SELECT
					sl.date,
					sl.log_type,
					sl.log         AS content,
					sl.author_name AS author
				FROM `tabStudent Log` sl
				WHERE {where_detail}
				ORDER BY sl.date DESC
				""",
				p,
				as_dict=True,
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
		if isinstance(filters, str):
			filters = frappe.parse_json(filters) or {}
		else:
			filters = filters or {}

		txt = (search_text or "").strip()

		authorized_schools = get_authorized_schools(frappe.session.user)
		if not authorized_schools:
			return {"error": "No authorized schools found."}

		conditions, params = [], {}
		params["authorized_schools"] = tuple(authorized_schools)

		if filters.get("school"):
			conditions.append("""
				pe.school IN (
					SELECT s2.name
					FROM `tabSchool` s1
					JOIN `tabSchool` s2
						ON s2.lft >= s1.lft AND s2.rgt <= s1.rgt
					WHERE s1.name = %(field_school)s
				)
			""")
			params["field_school"] = filters["school"]

		if filters.get("program"):
			conditions.append("pe.program = %(program)s")
			params["program"] = filters["program"]
		if filters.get("academic_year"):
			conditions.append("pe.academic_year = %(academic_year)s")
			params["academic_year"] = filters["academic_year"]

		if txt:
			conditions.append("(pe.student LIKE %(txt)s OR s.student_full_name LIKE %(txt)s)")
			params["txt"] = f"%{txt}%"

		conditions.append("pe.school IN %(authorized_schools)s")

		where_clause = " AND ".join(conditions) if conditions else "1=1"

		return frappe.db.sql(
			f"""
			SELECT DISTINCT pe.student, s.student_full_name AS student_full_name
			FROM `tabProgram Enrollment` pe
			INNER JOIN `tabStudent` s ON pe.student = s.name
			WHERE {where_clause}
			ORDER BY s.student_full_name
			LIMIT 100
			""",
			params,
			as_dict=True,
		)

	except Exception as e:
		frappe.log_error(message=str(e), title="Student Lookup Error")
		return {"error": str(e)}


@frappe.whitelist()
def get_recent_logs(filters=None, start: int = 0, page_length: int = 25):
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or {}
	else:
		filters = filters or {}

	authorized_schools = get_authorized_schools(frappe.session.user)
	if not authorized_schools:
		return []

	where_clause, params = _apply_common_filters(filters, authorized_schools)

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



@frappe.whitelist()
def get_filter_meta():
    """Return schools, academic years and programs the user can filter on.

    - Schools are restricted to the user's authorized school branch.
    - Academic Years are restricted to those same schools.
    - Programs are returned unfiltered for now (we do NOT assume Program has `school`).
    """
    user = frappe.session.user
    authorized_schools = get_authorized_schools(user)

    # ── Schools (branch) ────────────────────────────────────────────────
    schools = []
    default_school = None

    if authorized_schools:
        schools = frappe.get_all(
            "School",
            filters={"name": ["in", authorized_schools]},
            fields=["name", "school_name as label"],
            order_by="lft",
        )
        default_school = authorized_schools[0]

    # ── Academic Years (scoped to authorized schools) ───────────────────
    # Fieldnames from your Academic Year JSON:
    # - academic_year_name
    # - year_start_date
    # - year_end_date
    # - school
    # - archived
    ay_filters = {"archived": 0}
    if authorized_schools:
        ay_filters["school"] = ["in", authorized_schools]

    academic_years = frappe.get_all(
        "Academic Year",
        filters=ay_filters,
        fields=[
            "name",
            "academic_year_name as label",
            "year_start_date",
            "year_end_date",
            "school",
        ],
        order_by="year_start_date desc",
    )

    # ── Programs (no school filter until we see Program.json) ───────────
    programs = frappe.get_all(
        "Program",
        fields=["name", "program_name as label"],
        order_by="program_name",
    )

    return {
        "schools": schools,
        "default_school": default_school,
        "academic_years": academic_years,
        "programs": programs,
    }



