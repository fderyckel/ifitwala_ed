# ifitwala_ed/students/page/student_log_dashboard/student_log_dashboard.py
"""Server‑side aggregation for the Student Log Dashboard (Frappe v15)."""

import frappe


@frappe.whitelist()
def get_dashboard_data(filters=None):
    """Return aggregated data for the Student Log Dashboard.

    Args:
        filters (dict | str | None): JSON string or dict containing optional keys:
            school, academic_year, program, student, author
    Returns:
        dict: Aggregated datasets or {"error": str}
    """
    try:
        # Ensure `filters` is a dict (may arrive as JSON‑encoded str)
        filters = frappe.parse_json(filters) or {}

        conditions: list[str] = []
        params: dict[str, str] = {}

        # ── School filter (via Program) ────────────────────────────────
        if filters.get("school"):
            conditions.append(
                "program IN (SELECT name FROM `tabProgram` WHERE school = %(field_school)s)"
            )
            params["field_school"] = filters["school"]

        # ── Direct column filters ─────────────────────────────────────
        direct_map = {
            "academic_year": "academic_year",
            "program": "program",
            "student": "student",
            "author": "author_name",
        }
        for key, column in direct_map.items():
            if filters.get(key):
                ph = f"field_{key}"
                conditions.append(f"{column} = %({ph})s")
                params[ph] = filters[key]

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        def q(sql: str):
            """Execute a parameterised SQL with the shared WHERE clause."""
            return frappe.db.sql(sql.format(where=where_clause), params, as_dict=True)

        # ── Aggregations ─────────────────────────────────────────────
        log_type_count = q(
            "SELECT log_type AS label, COUNT(*) AS value "
            "FROM `tabStudent Log` WHERE {where} GROUP BY log_type ORDER BY value DESC"
        )

        logs_by_cohort = q(
            "SELECT pe.cohort AS label, COUNT(sl.name) AS value "
            "FROM `tabStudent Log` sl "
            "LEFT JOIN `tabProgram Enrollment` pe ON sl.student = pe.student "
            "WHERE {where} GROUP BY pe.cohort ORDER BY value DESC"
        )

        logs_by_program = q(
            "SELECT pe.program AS label, COUNT(sl.name) AS value "
            "FROM `tabStudent Log` sl "
            "LEFT JOIN `tabProgram Enrollment` pe ON sl.student = pe.student "
            "WHERE {where} GROUP BY pe.program ORDER BY value DESC"
        )

        logs_by_author = q(
            "SELECT author_name AS label, COUNT(*) AS value "
            "FROM `tabStudent Log` WHERE {where} GROUP BY author_name ORDER BY value DESC"
        )

        next_step_types = q(
            "SELECT next_step AS label, COUNT(*) AS value "
            "FROM `tabStudent Log` WHERE {where} GROUP BY next_step ORDER BY value DESC"
        )

        incidents_over_time = q(
            "SELECT DATE_FORMAT(date,'%%Y-%%m-%%d') AS label, COUNT(*) AS value "
            "FROM `tabStudent Log` WHERE {where} GROUP BY label ORDER BY label ASC"
        )

        open_follow_ups = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabStudent Log` "
            f"WHERE {where_clause} AND follow_up_status = 'Open'",
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
