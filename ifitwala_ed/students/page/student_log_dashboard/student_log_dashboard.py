# ifitwala_ed/students/page/student_log_dashboard/student_log_dashboard.py
import frappe
from frappe import _

# ────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_filter_data():
    """Populate dropdown filters (currently used only if you bind them in JS)."""
    try:
        schools = frappe.get_all("School", fields=["name"])
        academic_years = frappe.get_all("Academic Year", fields=["name"])
        programs = frappe.get_all("Program", fields=["name"])
        authors = frappe.get_all(
            "Employee",
            filters={"role": ["in", ["Academic Staff", "Teacher"]]},
            fields=["name", "employee_full_name"],
        )
        students = frappe.get_all("Student", fields=["name", "student_full_name"])

        return {
            "schools": [{"label": s.name, "value": s.name} for s in schools],
            "academic_years": [
                {"label": ay.name, "value": ay.name} for ay in academic_years
            ],
            "programs": [{"label": p.name, "value": p.name} for p in programs],
            "authors": [
                {"label": a.employee_full_name, "value": a.name} for a in authors
            ],
            "students": [
                {"label": s.student_full_name, "value": s.name} for s in students
            ],
        }

    except Exception as e:
        frappe.log_error(str(e), "Student Log Dashboard Filter Data Error")
        return {"error": str(e)}


# ────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_dashboard_data(filters):
    """
    Return aggregated stats for the Student Log Dashboard.
    `filters` is a dict coming from JS (school, academic_year, etc.).
    """
    try:
        # Build WHERE clause
        cond = []
        for field in ("school", "academic_year", "program", "student", "author"):
            if filters.get(field):
                db_field = "author_name" if field == "author" else field
                cond.append(f"{db_field} = %(field_{field})s")

        where_clause = " AND ".join(cond) if cond else "1=1"

        # Map named parameters for safety
        params = {f"field_{k}": v for k, v in filters.items() if v}

        # Generic helper
        def q(sql):
            return frappe.db.sql(sql.format(where=where_clause), params, as_dict=True)

        # ─── Queries ────────────────────────────────────────────────
        log_type_count = q(
            """
            SELECT log_type AS label, COUNT(*) AS value
            FROM `tabStudent Log`
            WHERE {where}
            GROUP BY log_type
            ORDER BY value DESC
        """
        )

        logs_by_cohort = q(
            """
            SELECT pe.cohort AS label, COUNT(sl.name) AS value
            FROM `tabStudent Log` sl
            LEFT JOIN `tabProgram Enrollment` pe ON sl.student = pe.student
            WHERE {where}
            GROUP BY pe.cohort
            ORDER BY value DESC
        """
        )

        logs_by_program = q(
            """
            SELECT pe.program AS label, COUNT(sl.name) AS value
            FROM `tabStudent Log` sl
            LEFT JOIN `tabProgram Enrollment` pe ON sl.student = pe.student
            WHERE {where}
            GROUP BY pe.program
            ORDER BY value DESC
        """
        )

        logs_by_author = q(
            """
            SELECT author_name AS label, COUNT(*) AS value
            FROM `tabStudent Log`
            WHERE {where}
            GROUP BY author_name
            ORDER BY value DESC
        """
        )

        next_step_types = q(
            """
            SELECT next_step AS label, COUNT(*) AS value
            FROM `tabStudent Log`
            WHERE {where}
            GROUP BY next_step
            ORDER BY value DESC
        """
        )

        incidents_over_time = q(
            """
            SELECT DATE_FORMAT(date, '%Y-%m-%d') AS label, COUNT(*) AS value
            FROM `tabStudent Log`
            WHERE {where}
            GROUP BY label
            ORDER BY label ASC
        """
        )

        # CHANGED ⮕ filtered Open Follow‑Ups
        open_follow_ups = frappe.db.sql(
            f"""
            SELECT COUNT(*) FROM `tabStudent Log`
            WHERE {where_clause} AND follow_up_status = 'Open'
        """,
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
