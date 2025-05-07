import frappe
from frappe import _

@frappe.whitelist()
def get_filter_data():
    try:
        # Fetching schools
        schools = frappe.get_all("School", fields=["name"])

        # Fetching academic years
        academic_years = frappe.get_all("Academic Year", fields=["name"])

        # Fetching programs
        programs = frappe.get_all("Program", fields=["name"])

        # Fetching authors (academic roles)
        authors = frappe.get_all(
            "Employee",
            filters={"role": ["in", ["Academic Staff", "Teacher"]]},
            fields=["name", "employee_full_name"]
        )

        # Fetching students (linked to active enrollments)
        students = frappe.get_all("Student", fields=["name", "student_full_name"])

        return {
            "schools": schools,
            "academic_years": academic_years,
            "programs": programs,
            "authors": authors,
            "students": students,
        }
    except Exception as e:
        frappe.log_error(message=str(e), title="Error in Student Log Dashboard Filters")
        return {"error": str(e)}

@frappe.whitelist()
def get_dashboard_data(filters):
    try:
        conditions = []

        # Applying filters based on the input
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

        # Build the WHERE clause
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Aggregating data for charts
        log_type_count = frappe.db.sql(f"""
            SELECT log_type, COUNT(*) AS count
            FROM `tabStudent Log`
            WHERE {where_clause}
            GROUP BY log_type
        """, as_dict=True)

        logs_by_cohort = frappe.db.sql(f"""
            SELECT cohort, COUNT(*) AS count
            FROM `tabProgram Enrollment`
            WHERE {where_clause}
            GROUP BY cohort
        """, as_dict=True)

        logs_by_program = frappe.db.sql(f"""
            SELECT program, COUNT(*) AS count
            FROM `tabProgram Enrollment`
            WHERE {where_clause}
            GROUP BY program
        """, as_dict=True)

        logs_by_author = frappe.db.sql(f"""
            SELECT author_name, COUNT(*) AS count
            FROM `tabStudent Log`
            WHERE {where_clause}
            GROUP BY author_name
        """, as_dict=True)

        next_step_types = frappe.db.sql(f"""
            SELECT next_step, COUNT(*) AS count
            FROM `tabStudent Log`
            WHERE {where_clause}
            GROUP BY next_step
        """, as_dict=True)

        incidents_over_time = frappe.db.sql(f"""
            SELECT DATE_FORMAT(date, '%Y-%m-%d') AS day, COUNT(*) AS count
            FROM `tabStudent Log`
            WHERE {where_clause}
            GROUP BY day
            ORDER BY day ASC
        """, as_dict=True)

        # Counting open follow-ups
        open_follow_ups = frappe.db.count("Student Log", {"follow_up_status": "Open"})

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
        frappe.log_error(message=str(e), title="Error in Student Log Dashboard Data")
        return {"error": str(e)}
