# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from collections import defaultdict
import frappe

def execute(filters=None):
    if not filters:
        filters = {}
    
    report_type = filters.get("report_type", "Program")
    
    if report_type == "Course":
        columns = get_course_columns(filters)
        data = get_course_data(filters)
        chart = get_course_chart_data(data)
    else:
        columns = get_program_columns(filters)
        data = get_program_data(filters)
        chart = get_program_chart_data(data)
    
    return columns, data, None, chart

def get_program_columns(filters):
    return [
        {"label": "Academic Year", "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 200},
        {"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 200},
        {"label": "Enrollment Count", "fieldname": "enrollment_count", "fieldtype": "Int", "width": 150},
    ]

def get_program_data(filters):
    # Build dynamic conditions; none of the filters are compulsory.
    conditions = []
    
    
    if filters.get("school"):
        conditions.append("pe.school = %(school)s")
    if filters.get("program"):
        conditions.append("pe.program = %(program)s")
    if filters.get("academic_year"):
        conditions.append("pe.academic_year = %(academic_year)s")
    
    # Build the WHERE clause only if conditions exist
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    sql = f"""
    SELECT
        pe.academic_year as academic_year,
        pe.program as program,
        COUNT(pe.name) as enrollment_count,
        ay.year_start_date as year_start_date
    FROM `tabProgram Enrollment` pe
    LEFT JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
    {where_clause}
    GROUP BY pe.academic_year, pe.program, ay.year_start_date
    ORDER BY ay.year_start_date DESC
    """
    
    return frappe.db.sql(sql, filters, as_dict=True)


def get_program_chart_data(data): 
    # Reverse data for chart to show oldest to newest
    data_sorted = sorted(data, key=lambda x: x.get("year_start_date") or "")

    # For chart labels, we concatenate Academic Year and Program.
    labels = [f"{row.academic_year} - {row.program}" for row in data]
    values = [row.enrollment_count for row in data]
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Enrollments", "values": values}
            ]
        },
        "type": "bar",
        "fieldtype": "Data",
        "colors": ["#7cd6fd"]
    }

def get_course_columns(filters):
    return [
        {"label": "Course", "fieldname": "course", "fieldtype": "Data", "width": 200},
        {"label": "Enrollment Count", "fieldname": "enrollment_count", "fieldtype": "Int", "width": 150},
    ]

def get_course_data(filters):
    conditions = []

    if filters.get("academic_year"):
        conditions.append("pe.academic_year = %(academic_year)s")
    if filters.get("school"):
        conditions.append("pe.school = %(school)s")
    if filters.get("program"):
        conditions.append("pe.program = %(program)s")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
    SELECT
        pec.course AS course,
        pec.status AS status,
        COUNT(*) AS enrollment_count
    FROM `tabProgram Enrollment Course` pec
    JOIN `tabProgram Enrollment` pe ON pec.parent = pe.name
    {where_clause}
    GROUP BY pec.course, pec.status
    ORDER BY pec.course, pec.status
    """

    return frappe.db.sql(sql, filters, as_dict=True)

def get_course_chart_data(data):
    # Build {status: {course: count}} mapping
    dataset_map = defaultdict(lambda: defaultdict(int))
    courses = set()

    for row in data:
        course = row.course
        status = row.status
        count = row.enrollment_count

        dataset_map[status][course] = count
        courses.add(course)

    courses = sorted(courses)

    # Predefined colors per status
    status_colors = {
        "Enrolled": "#7cd6fd",
        "Completed": "#5e64ff",
        "Dropped": "#ff5858"
    }

    datasets = []
    for status, course_map in dataset_map.items():
        values = [course_map.get(course, 0) for course in courses]
        datasets.append({
            "name": status,
            "values": values,
            "chartType": "bar"  # bar is still used, even for stacked
        })

    return {
        "data": {
            "labels": courses,
            "datasets": datasets
        },
        "type": "bar",
        "colors": [status_colors.get(ds["name"], "#999999") for ds in datasets],
        "barOptions": {
            "stacked": True  # <<< enables stacked bars
        },
        "truncateLegends": False  # ensures legend labels don't get cut off
    }

@frappe.whitelist()
def get_academic_years_for_school(school):
    return frappe.db.get_list("Academic Year", 
        filters={"school": school},
        fields=["name"],
        order_by="year_start_date desc"
    )