# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def get_context(context):
    context.programs = frappe.db.get_values("Program", {"status": "Active"}, ["name", "program_name"], as_dict=True)
    context.courses = frappe.db.get_values("Course", {"status": "Active"}, ["name", "course_name"], as_dict=True)
    context.cohorts = frappe.db.get_values("Student Cohort", {}, ["name", "cohort_name"], as_dict=True)
    context.student_groups = []
    context.student_group_selected = None
    context.students = []
    context.start = 0
    context.page_length = 25
    context.total_students = 0

def get_student_group_students(student_group, start=0, page_length=25):
    student_data = frappe.get_all(
        "Student Group Student",
        filters={"parent": student_group},
        fields=["student", "student_name"],
        start=start,
        page_length=page_length,
        as_list=True
    )
    
    student_ids = [s[0] for s in student_data]
    student_details = frappe.db.get_values(
        "Student", 
        {"name": ("in", student_ids)}, 
        ["name", "student_full_name", "student_preferred_name", "student_image"], 
        as_dict=True
    )
    student_dict = {s["name"]: s for s in student_details}

    students = []
    for student_id, student_name in student_data:
        student_info = student_dict.get(student_id, {})
        students.append({
            "student": student_id,
            "student_name": student_info.get("student_full_name", student_name),
            "preferred_name": student_info.get("student_preferred_name", ""),
            "student_image": student_info.get("student_image", "")
        })
    
    return students

@frappe.whitelist()
def fetch_student_groups(program=None, course=None, cohort=None):
    filters = {}
    if program:
        filters["program"] = program
    if course:
        filters["course"] = course
    if cohort:
        filters["cohort"] = cohort

    student_groups = frappe.get_all("Student Group", filters=filters, fields=["name", "student_group_name"])
    return student_groups

@frappe.whitelist()
def fetch_students(student_group, start=0, page_length=25):
    students = get_student_group_students(student_group, start, page_length)
    total_students = frappe.db.count("Student Group Student", {"parent": student_group})
    return {"students": students, "start": start + page_length, "total": total_students}

@frappe.whitelist()
def reset_student_fetch(student_group):
    return {
        "students": get_student_group_students(student_group, start=0, page_length=25), 
        "start": 25, 
        "total": frappe.db.count("Student Group Student", {"parent": student_group})
    }
