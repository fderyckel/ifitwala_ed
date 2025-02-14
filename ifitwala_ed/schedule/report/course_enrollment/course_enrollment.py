# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    filters = filters or {}
    report_type = filters.get("report_type", "Program")
    
    if report_type == "Course":
        return execute_course(filters)
    else:
        return execute_program(filters)

def execute_program(filters):
    # Validate required filters for Program view
    if not filters.get("school") or not filters.get("program"):
        frappe.throw("Please set School and Program filters.")
        
    # Optional academic term filter:
    term_condition = ""
    if filters.get("academic_term"):
        term_condition = "AND term = %(academic_term)s"
        
    sql = f"""
    SELECT
        IFNULL(term, 'Not Specified') as term,
        COUNT(name) as enrollment_count
    FROM `tabProgram Enrollment`
    WHERE status = 1
      AND school = %(school)s
      AND program = %(program)s
      {term_condition}
    GROUP BY term
    ORDER BY enrollment_count DESC
    """
    
    data = frappe.db.sql(sql, filters, as_dict=1)
    
    columns = [
        {"label": "Academic Term", "fieldname": "term", "fieldtype": "Data", "width": 200},
        {"label": "Enrollment Count", "fieldname": "enrollment_count", "fieldtype": "Int", "width": 150},
    ]
    
    chart = {
        "data": {
            "labels": [row.term for row in data],
            "datasets": [
                {"name": "Enrollments", "values": [row.enrollment_count for row in data]}
            ]
        },
        "type": "bar",
        "fieldtype": "Data",
        "colors": ["#7cd6fd"]
    }
    
    return columns, data, None, chart

def execute_course(filters):
    # Validate required filters for Course view
    if not filters.get("school") or not filters.get("program") or not filters.get("academic_year"):
        frappe.throw(_("Please set School, Program, and Academic Year filters."))
    
    sql = """
    SELECT
        ce.course as course,
        COUNT(ce.name) as enrollment_count
    FROM `tabCourse Enrollment` ce
    JOIN `tabProgram Enrollment` pe ON ce.program_enrollment = pe.name
    WHERE ce.current = 1
      AND ce.academic_year = %(academic_year)s
      AND pe.school = %(school)s
      AND pe.program = %(program)s
    GROUP BY ce.course
    ORDER BY enrollment_count DESC
    """
    
    data = frappe.db.sql(sql, filters, as_dict=1)
    
    columns = [
        {"label": "Course", "fieldname": "course", "fieldtype": "Data", "width": 200},
        {"label": "Enrollment Count", "fieldname": "enrollment_count", "fieldtype": "Int", "width": 150},
    ]
    
    chart = {
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
    
    return columns, data, None, chart