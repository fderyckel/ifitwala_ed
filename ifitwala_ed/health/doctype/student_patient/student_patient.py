# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class StudentPatient(Document):
	pass

@frappe.whitelist()
def get_student_detail(student_patient):
	details = frappe.get_value("Student Patient", student_patient, 
														["student_name", "date_of_birth", "blood_group", "gender"], 
														as_dict=1)
	if not details:
		frappe.throw(_(f'Student patient "{student_patient}" not found. Please verify the name is correct and the record exists.'))
	return details

@frappe.whitelist()
def get_guardian_details(student_name):
    student_doc = frappe.get_doc("Student", student_name)
    guardians = []
    for guardian in student_doc.guardians:  
        guardians.append({
            "guardian_name": guardian.guardian_name,
            "relation": guardian.relation,
            "email_address": guardian.email,
            "mobile_number": guardian.phone
        })

    return guardians


