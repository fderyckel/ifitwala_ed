# ifitwala_ed/students/page/student_log_dashboard/student_log_dashboard.py
import frappe
import json
from frappe import _

# ────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_dashboard_data(filters=None):
    """
    Aggregated stats for the Student Log Dashboard.
    `filters` arrives as a JSON string → convert to dict first.
    """
    try:
        # CHANGED ⮕ make sure filters is a dict
        filters = frappe.parse_json(filters) or {}

        # Build WHERE clause & param map
        conditions = []
        params = {}
        for field in ("school", "academic_year", "program", "student", "author"):
            if filters.get(field):
                db_field = "author_name" if field == "author" else field
                placeholder = f"field_{field}"
                conditions.append(f"{db_field} = %({placeholder})s")
                params[placeholder] = filters[field]

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Helper to run parameterised queries safely
        def q(sql):
            return frappe.db.sql(sql.format(where=where_clause), params, as_dict=True)

        # ─── Aggregates ───────────────────────────────────────────
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
            "SELECT DATE_FORMAT(date,'%Y-%m-%d') AS label, COUNT(*) AS value "
            "FROM `tabStudent Log` WHERE {where} GROUP BY label ORDER BY label ASC"
        )

        # CHANGED ⮕ same filters for open follow‑ups
        open_follow_ups = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabStudent Log` "
            f"WHERE {where_clause} AND follow_up_status='Open'",
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
