# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.utilities.student_utils import get_basic_student_info


class StudentPatient(Document):
    def validate(self):
        self.sync_photo_from_student()

    # ensure that the nurse role has the current picture of the student
    def sync_photo_from_student(self):
        if not self.student:
            return

        student_image = frappe.db.get_value("Student", self.student, "student_image")
        self.photo = student_image


@frappe.whitelist()
def get_student_basic_info(student):
    if not frappe.has_permission("Student Patient", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    return get_basic_student_info(student)


@frappe.whitelist()
def get_guardian_details(student_name):
    student_doc = frappe.get_doc("Student", student_name)
    guardians = []
    for guardian in student_doc.guardians:
        guardians.append(
            {
                "guardian_name": guardian.guardian_name,
                "relation": guardian.relation,
                "email_address": guardian.email,
                "mobile_number": guardian.phone,
            }
        )

    return guardians
