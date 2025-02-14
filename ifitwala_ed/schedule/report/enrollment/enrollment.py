# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

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
    conditions.append("status = 1")           # Only active enrollments
    conditions.append("docstatus < 2")          # Not cancelled (draft or submitted)
    
    if filters.get("school"):
        conditions.append("school = %(school)s")
    if filters.get("program"):
        conditions.append("program = %(program)s")
    if filters.get("academic_year"):
        conditions.append("academic_year = %(academic_year)s")
    
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
    # Build dynamic conditions; school, program, and academic_year are optional.
    conditions = ["ce.current = 1", "ce.docstatus < 2"]
    
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
    labels = [row.course for row in data]
    values = [row.enrollment_count for row in data]
    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Enrollments", "values": values}]
        },
        "type": "bar",
        "fieldtype": "Data",
        "colors": ["#7cd6fd"]
    }

