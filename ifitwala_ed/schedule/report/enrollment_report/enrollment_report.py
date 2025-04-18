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
        {"label": "School", "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 200},
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
        pe.school AS school,
        sc.abbr AS school_abbr,
        pe.academic_year AS academic_year,
        pe.program AS program,
        COUNT(pe.name) AS enrollment_count,
        ay.year_start_date AS year_start_date
    FROM `tabProgram Enrollment` pe
    LEFT JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
    LEFT JOIN `tabSchool` sc ON pe.school = sc.name
    {where_clause}
    GROUP BY pe.school, sc.abbr, pe.academic_year, pe.program, ay.year_start_date
    ORDER BY ay.year_start_date DESC
    """
    
    return frappe.db.sql(sql, filters, as_dict=True)

def get_program_chart_data(data, filters=None):
    filters = filters or {}
    school_filter = filters.get("school")

    if not school_filter:
        # Aggregate by school + academic year
        school_year_totals = defaultdict(lambda: defaultdict(int))  # [school][year] = total_enrollment
        academic_years = set()

        for row in data:
            school = row.school_abbr or row.school or "Unknown"
            year = row.academic_year
            count = row.enrollment_count
            school_year_totals[school][year] += count
            academic_years.add(year)

        labels = sorted(academic_years)
        datasets = []

        color_palette = [
            "#7cd6fd", "#5e64ff", "#743ee2", "#ff5858", "#ffa00a", "#00b0f0", "#00a65a",
            "#ffa3ef", "#99cc00", "#6b5b95", "#00b894", "#fab1a0"
        ]

        for i, (school, year_data) in enumerate(school_year_totals.items()):
            values = [year_data.get(year, 0) for year in labels]  # ✅ Just integers
            datasets.append({
                "name": school,
                "values": values
            })

        return {
            "data": {
                "labels": labels,
                "datasets": datasets
            },
            "type": "bar",
            "colors": color_palette[:len(datasets)],
            "barOptions": {
                "stacked": False
            },
            "truncateLegends": False
        }

    else:
        # Single school selected → one dataset only
        data_sorted = sorted(data, key=lambda x: x.get("year_start_date") or "")
        labels = [f"{row.academic_year} - {row.program}" for row in data_sorted]
        values = [row.enrollment_count for row in data_sorted]

        return {
            "data": {
                "labels": labels,
                "datasets": [
                    {"name": "Enrollments", "values": values}
                ]
            },
            "type": "bar",
            "colors": ["#7cd6fd"],
            "barOptions": {
                "stacked": False
            },
            "truncateLegends": False
        }


def get_course_columns(filters):
    return [
        {"label": "School", "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 200},
        {"label": "Academic Year", "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 150},
        {"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 200},
        {"label": "Course", "fieldname": "course", "fieldtype": "Data", "width": 200},
        {"label": "Status", "fieldname": "status", "fieldtype": "Select", "width": 120},
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
        pe.program AS program,
        pe.school AS school,
        pe.academic_year AS academic_year,
        pec.status AS status,
        COUNT(*) AS enrollment_count
    FROM `tabProgram Enrollment Course` pec
    JOIN `tabProgram Enrollment` pe ON pec.parent = pe.name
    {where_clause}
    GROUP BY pec.course, pe.program, pe.school, pe.academic_year, pec.status
    ORDER BY pe.academic_year DESC, pec.course, pe.program, pe.school
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
def get_academic_years_for_school(doctype, txt, searchfield, start, page_len, filters):
    import json

    # Safely handle filters passed as str or dict
    if isinstance(filters, str):
        filters = json.loads(filters)
    elif filters is None:
        filters = {}

    school = filters.get("school")

    conditions = ""
    if school:
        conditions = "WHERE school = %(school)s"

    return frappe.db.sql(f"""
        SELECT name FROM `tabAcademic Year`
        {conditions}
        ORDER BY year_start_date DESC
        LIMIT %(page_len)s OFFSET %(start)s
    """, {
        "school": school,
        "start": start,
        "page_len": page_len
    })
