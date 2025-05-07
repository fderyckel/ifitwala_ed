import frappe
from frappe import _


@frappe.whitelist()
def get_filter_data():
    try:
        # Fetching Schools
        schools = frappe.get_all("School", fields=["name"])

        # Fetching Academic Years
        academic_years = frappe.get_all("Academic Year", fields=["name"])

        # Fetching Programs
        programs = frappe.get_all("Program", fields=["name"])

        # Fetching Authors (Academic Staff)
        authors = frappe.get_all(
            "Employee",
            filters={"role": ["in", ["Academic Staff", "Teacher"]]},
            fields=["name", "employee_full_name"]
        )

        # Fetching Students (active enrollments)
        students = frappe.get_all(
            "Student",
            fields=["name", "student_full_name"]
        )

        return {
            "schools": [{"label": s.name, "value": s.name} for s in schools],
            "academic_years": [{"label": ay.name, "value": ay.name} for ay in academic_years],
            "programs": [{"label": p.name, "value": p.name} for p in programs],
            "authors": [{"label": a.employee_full_name, "value": a.name} for a in authors],
            "students": [{"label": s.student_full_name, "value": s.name} for s in students]
        }

    except Exception as e:
        frappe.log_error(message=str(e), title="Student Log Dashboard Filter Data Error")
        return {"error": str(e)}

import frappe
from frappe import _

@frappe.whitelist()
def get_dashboard_data(filters):
    try:
        # Building the WHERE clause based on filters
        conditions = []

        if filters.get("school"):
            conditions.append(f"school = '{filters.get('school')}'")

        if filters.get("academic_year"):
            conditions.append(f"academic_year = '{filters.get('academic_year')}'")

        if filters.get("program"):
            conditions.append(f"program = '{filters.get('program')}'")

        if filters.get("student"):
            conditions.append(f"student = '{filters.get('student')}'")

        if filters.get("author"):
            conditions.append(f"author_name = '{filters.get('author')}'")

        # Combine conditions into a single WHERE clause
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Fetching Log Type Count
        log_type_count = frappe.db.sql(f"""
            SELECT log_type AS label, COUNT(*) AS value
            FROM `tabStudent Log`
            WHERE {where_clause}
            GROUP BY log_type
            ORDER BY value DESC
        """, as_dict=True)

        # Fetching Logs by Cohort (needs join with Program Enrollment)
        logs_by_cohort = frappe.db.sql(f"""
            SELECT pe.cohort AS label, COUNT(sl.name) AS value
            FROM `tabStudent Log` sl
            LEFT JOIN `tabProgram Enrollment` pe ON sl.student = pe.student
            WHERE {where_clause}
            GROUP BY pe.cohort
            ORDER BY value DESC
        """, as_dict=True)

        # Fetching Logs by Program (needs join with Program Enrollment)
        logs_by_program = frappe.db.sql(f"""
            SELECT pe.program AS label, COUNT(sl.name) AS value
            FROM `tabStudent Log` sl
            LEFT JOIN `tabProgram Enrollment` pe ON sl.student = pe.student
            WHERE {where_clause}
            GROUP BY pe.program
            ORDER BY value DESC
        """, as_dict=True)

        # Fetching Logs by Author
        logs_by_author = frappe.db.sql(f"""
            SELECT author_name AS label, COUNT(*) AS value
            FROM `tabStudent Log`
            WHERE {where_clause}
            GROUP BY author_name
            ORDER BY value DESC
        """, as_dict=True)

        # Fetching Next Step Types
        next_step_types = frappe.db.sql(f"""
            SELECT next_step AS label, COUNT(*) AS value
            FROM `tabStudent Log`
            WHERE {where_clause}
            GROUP BY next_step
            ORDER BY value DESC
        """, as_dict=True)

        # Fetching Incidents Over Time
        incidents_over_time = frappe.db.sql(f"""
            SELECT DATE_FORMAT(date, '%Y-%m-%d') AS label, COUNT(*) AS value
            FROM `tabStudent Log`
            WHERE {where_clause}
            GROUP BY label
            ORDER BY label ASC
        """, as_dict=True)

        # Counting Open Follow‑Ups with the same filters
        open_follow_ups = frappe.db.sql(f"""
            SELECT COUNT(*) FROM `tabStudent Log` 
            WHERE {where_clause} AND follow_up_status = 'Open' 
            """)[0][0]

        # Return the combined data
        return {
            "logTypeCount": log_type_count,
            "logsByCohort": logs_by_cohort,
            "logsByProgram": logs_by_program,
            "logsByAuthor": logs_by_author,
            "nextStepTypes": next_step_types,
            "incidentsOverTime": incidents_over_time,
            "openFollowUps": open_follow_ups
        }

    except Exception as e:
        frappe.log_error(message=str(e), title="Student Log Dashboard Data Error")
        return {"error": str(e)}

