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
    from collections import defaultdict

    filters = filters or {}
    school_filter = filters.get("school")
    program_filter = filters.get("program")

    data_sorted = sorted(data, key=lambda x: x.get("year_start_date") or "")

    # 🎯 CASE 3: School + Program selected
    if school_filter and program_filter:
        labels = [row.academic_year for row in data_sorted]
        values = [row.enrollment_count for row in data_sorted]
        return {
            "data": {
                "labels": labels,
                "datasets": [
                    {"name": program_filter, "values": values}
                ]
            },
            "type": "bar",
            "colors": ["#7cd6fd"],
            "barOptions": {"stacked": False},
            "truncateLegends": False
        }

    # 🎯 CASE 2: School selected (program breakdown)
    if school_filter and not program_filter:
        year_totals = defaultdict(int)
        breakdown = defaultdict(list)

        for row in data_sorted:
            year = row.academic_year
            year_totals[year] += row.enrollment_count
            breakdown[year].append(f"{row.program}: {row.enrollment_count}")

        sorted_years = sorted(year_totals)
        values = [year_totals[year] for year in sorted_years]

        return {
            "data": {
                "labels": sorted_years,
                "datasets": [
                    {"name": school_filter, "values": values}
                ]
            },
            "type": "bar",
            "colors": ["#7cd6fd"],
            "barOptions": {"stacked": False},
            "truncateLegends": False,
            "custom_options": {
                "tooltip_breakdown": dict(breakdown)
            }
        }

    # 🎯 CASE 1: No filters - one bar per academic year, colored by its school
    school_color_map = {}
    color_index = 0
    color_palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]

    # Group by academic year (since 1 year = 1 school)
    year_groups = {}
    for row in data_sorted:
        year = row.academic_year
        if year not in year_groups:
            year_groups[year] = {
                "school": row.school,
                "school_abbr": row.school_abbr,
                "total": 0,
                "programs": [],
                "year_start_date": row.year_start_date
            }
        year_groups[year]["total"] += row.enrollment_count
        year_groups[year]["programs"].append(f"{row.program}: {row.enrollment_count}")

    # Sort years by start date (descending)
    sorted_years = sorted(
        year_groups.values(),
        key=lambda x: x["year_start_date"],
        reverse=True
    )

    # Prepare chart components
    labels = []
    values = []
    colors = []
    tooltip_breakdown = {}
    legend_labels = []
    legend_colors = []

    for year_data in sorted_years:
        labels.append(year_data["school_abbr"] + " - " + year_data["academic_year"])
        values.append(year_data["total"])
        tooltip_breakdown[year_data["academic_year"]] = year_data["programs"]
        
        # Manage school colors
        school = year_data["school"]
        if school not in school_color_map:
            school_color_map[school] = color_palette[color_index % len(color_palette)]
            legend_labels.append(year_data["school_abbr"])
            legend_colors.append(school_color_map[school])
            color_index += 1
        
        colors.append(school_color_map[school])

    return {
        "data": {
            "labels": [yd["academic_year"] for yd in sorted_years],  # Just year as label
            "datasets": [{"name": "Enrollments", "values": values}]
        },
        "type": "bar",
        "colors": colors,
        "barOptions": {"stacked": False},
        "truncateLegends": False,
        "custom_options": {
            "tooltip_breakdown": tooltip_breakdown,
            "legend_labels": legend_labels,
            "legend_colors": legend_colors
        }
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
