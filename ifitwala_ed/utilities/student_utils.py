# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_basic_student_info(student_id: str) -> dict:
    if not student_id:
        frappe.throw(_("Student ID is required"))

    student = frappe.db.get_value(
        "Student",
        student_id,
        ["student_full_name", "student_preferred_name", "student_gender", "student_date_of_birth", "student_image"],
        as_dict=True,
    )

    if not student:
        frappe.throw(_("Student not found"))

    return student
