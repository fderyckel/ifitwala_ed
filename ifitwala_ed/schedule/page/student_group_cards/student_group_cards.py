# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe

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
    
    medical_info_data = frappe.db.get_values( 
        "Student Patient", 
        {"student": ["in", student_ids]}, 
        ["student", "medical_info"], 
        as_dict=True)
    
    # Inject only if medical_info is non-empty
    for entry in medical_info_data:
        if entry.medical_info:
            student_dict[entry.student]["medical_info"] = entry.medical_info

    students = []
    for student_id, student_name in student_data:
        student_info = student_dict.get(student_id, {})
        students.append({
            "student": student_id,
            "student_name": student_info.get("student_full_name", student_name),
            "preferred_name": student_info.get("student_preferred_name", ""),
            "student_image": student_info.get("student_image", ""), 
            "medical_info": student_info.get("medical_info", "")
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
