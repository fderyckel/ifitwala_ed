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

        conditions, params = [], {}

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
            "student": "sl.student",
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

        return {
            "logTypeCount": log_type_count,
            "logsByCohort": logs_by_cohort,
            "logsByProgram": logs_by_program,
            "logsByAuthor": logs_by_author,
            "nextStepTypes": next_step_types,
            "incidentsOverTime": incidents_over_time,
            "openFollowUps": open_follow_ups,
        }

    except Exception as e:
        frappe.log_error(str(e), "Student Log Dashboard Data Error")
        return {"error": str(e)}
