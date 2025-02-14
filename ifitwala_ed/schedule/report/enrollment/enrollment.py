# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe

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
        {"label": "Academic Year", "fieldname": "academic_year", "fieldtype": "Data", "width": 200},
        {"label": "Enrollment Count", "fieldname": "enrollment_count", "fieldtype": "Int", "width": 150},
    ]

def get_program_data(filters):
    # Build dynamic conditions; none of the filters (school, program, academic_year) are compulsory.
    conditions = []
    
    if filters.get("school"):
        conditions.append("school = %(school)s")
    if filters.get("program"):
        conditions.append("program = %(program)s")
    if filters.get("academic_year"):
        conditions.append("academic_year = %(academic_year)s")
    
    # Build the WHERE clause only if there are conditions
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    sql = f"""
    SELECT
        IFNULL(academic_year, 'Not Specified') as academic_year,
        COUNT(name) as enrollment_count
    FROM `tabProgram Enrollment`
    {where_clause}
    GROUP BY academic_year
    ORDER BY enrollment_count DESC
    """
    
    return frappe.db.sql(sql, filters, as_dict=True)

def get_program_chart_data(data):
    return {
        "data": {
            "labels": [row.academic_year for row in data],
            "datasets": [
                {"name": "Enrollments", "values": [row.enrollment_count for row in data]}
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
    # Build dynamic conditions; school, program, and academic_year filters are optional.
    conditions = ["ce.current = 1"]
    
    if filters.get("academic_year"):
        conditions.append("ce.academic_year = %(academic_year)s")
    if filters.get("school"):
        conditions.append("pe.school = %(school)s")
    if filters.get("program"):
        conditions.append("pe.program = %(program)s")
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    sql = f"""
    SELECT
        ce.course as course,
        COUNT(ce.name) as enrollment_count
    FROM `tabCourse Enrollment` ce
    JOIN `tabProgram Enrollment` pe ON ce.program_enrollment = pe.name
    {where_clause}
    GROUP BY ce.course
    ORDER BY enrollment_count DESC
    """
    
    return frappe.db.sql(sql, filters, as_dict=True)

def get_course_chart_data(data):
    return {
        "data": {
            "labels": [row.course for row in data],
            "datasets": [
                {"name": "Enrollments", "values": [row.enrollment_count for row in data]}
            ]
        },
        "type": "bar",
        "fieldtype": "Data",
        "colors": ["#7cd6fd"]
    }
