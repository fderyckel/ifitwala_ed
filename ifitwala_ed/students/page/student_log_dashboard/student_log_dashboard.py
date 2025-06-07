# ifitwala_ed/students/page/student_log_dashboard/student_log_dashboard.py
"""Server‑side aggregation for the Student Log Dashboard (Frappe v15).
   Uses consistent alias `sl` for tabStudent Log in every query to
   avoid ambiguous column references when filters include `program`.
"""

import frappe


@frappe.whitelist()
def get_dashboard_data(filters=None):
	"""Aggregate stats with optional filters.

	Filters arrive JSON‑encoded; keys: school, academic_year, program,
	student, author.
	"""
	try:
		filters = frappe.parse_json(filters) or {}
		
		# Use the authorized school list for this user
		authorized_schools = get_authorized_schools(frappe.session.user)
		if not authorized_schools:
			return {"error": "No authorized schools found."}

		# Enforce the authorized schools filter
		conditions, params = [], {}
		conditions.append("sl.program IN (SELECT name FROM `tabProgram` WHERE school IN %(authorized_schools)s)")
		params["authorized_schools"] = tuple(authorized_schools)

		# ── School filter (via Program) ────────────────────────────
		if filters.get("school"):
			conditions.append(
				"sl.program IN (SELECT name FROM `tabProgram` WHERE school = %(field_school)s)"
			)
			params["field_school"] = filters["school"]

		# ── Direct columns in Student Log (alias sl) ──────────────
		direct_map = {
			"academic_year": "sl.academic_year",
			"program": "sl.program",
			#"student": "sl.student",
			"author": "sl.author_name",
		}
		for key, col in direct_map.items():
			if filters.get(key):
				ph = f"field_{key}"
				conditions.append(f"{col} = %({ph})s")
				params[ph] = filters[key]

		where_clause = " AND ".join(conditions) if conditions else "1=1"

		def q(sql):
			return frappe.db.sql(sql.format(w=where_clause), params, as_dict=True)

		# ── Aggregates ────────────────────────────────────────────
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
			student_logs = frappe.db.sql(
				"""
				SELECT
					sl.date,
					sl.log_type,
					sl.log AS content,
					sl.author_name AS author
				FROM `tabStudent Log` sl
				WHERE sl.student = %(field_student)s
				ORDER BY sl.date DESC
				""",
				{"field_student": filters["student"]},
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
def get_distinct_students(filters=None, search_text: str = ""):   # ★ CHANGED
    """Return up to 100 unique students matching the current filters
       *and* the user's partial search string (ID or name)."""
    try:
        filters = frappe.parse_json(filters) or {}
        txt = (search_text or "").strip()
        
				# Use the authorized school list for this user
        authorized_schools = get_authorized_schools(frappe.session.user)

        if not authorized_schools:
            return {"error": "No authorized schools found."}

        conditions, params = [], {}

        # context filters --------------------------------------------------
        if filters.get("school"):
            conditions.append("pe.school = %(school)s")
            params["school"] = filters["school"]

        if filters.get("program"):
            conditions.append("pe.program = %(program)s")
            params["program"] = filters["program"]

        if filters.get("academic_year"):
            conditions.append("pe.academic_year = %(academic_year)s")
            params["academic_year"] = filters["academic_year"]

        # partial text filter ---------------------------------------------  ★ CHANGED
        if txt:
            conditions.append("(pe.student LIKE %(txt)s OR s.student_full_name LIKE %(txt)s)")
            params["txt"] = f"%{txt}%"

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # query ------------------------------------------------------------
        students = frappe.db.sql(f"""
            SELECT DISTINCT pe.student, s.student_full_name AS student_full_name
            FROM `tabProgram Enrollment` pe
            INNER JOIN `tabStudent` s ON pe.student = s.name
            WHERE {where_clause}
            ORDER BY s.student_full_name
            LIMIT 100
        """, params, as_dict=True)

        return students

    except Exception as e:
        frappe.log_error(message=str(e), title="Student Lookup Error")
        return {"error": str(e)}

@frappe.whitelist()
def get_recent_logs(filters=None, start: int = 0, page_length: int = 25):
	"""Return the most recent Student Log rows that match the page filters
		 (school, program, academic_year, author). Excludes the student filter."""
	filters = frappe.parse_json(filters) or {}

	authorized_schools = get_authorized_schools(frappe.session.user)
	if not authorized_schools:
		return []

	conditions, params = [], {}

	conditions.append(
		"sl.program IN (SELECT name FROM `tabProgram` WHERE school IN %(authorized_schools)s)"
	)
	params["authorized_schools"] = tuple(authorized_schools)

	# reuse global filters except 'student'
	if filters.get("school"):
		conditions.append(
			"sl.program IN (SELECT name FROM `tabProgram` WHERE school = %(school)s)"
		)
		params["school"] = filters["school"]

	direct_map = {
		"academic_year": "sl.academic_year",
		"program":       "sl.program",
		"author":        "sl.author_name",
	}
	for key, col in direct_map.items():
		if filters.get(key):
			ph = key
			conditions.append(f"{col} = %({ph})s")
			params[ph] = filters[key]

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
    """Return the list of schools the user is authorized to view."""
    # Get the user's default school
    default_school = frappe.defaults.get_user_default("school")
    
    if not default_school:
        return []

    # Fetch all child schools if this is a parent school
    all_schools = frappe.db.sql("""
        WITH RECURSIVE school_tree AS (
            SELECT name
            FROM `tabSchool`
            WHERE name = %s

            UNION ALL

            SELECT s.name
            FROM `tabSchool` s
            INNER JOIN school_tree st ON s.parent_school = st.name
        )
        SELECT name FROM school_tree
    """, (default_school,), as_list=True)

    # Flatten the list and remove duplicates
    return [s[0] for s in all_schools] if all_schools else [default_school]
