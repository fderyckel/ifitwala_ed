# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class StudentPatient(Document):
	pass

@frappe.whitelist()
def get_student_detail(student_patient):
	patient_dict = frappe.db.sql("""
			SELECT
				student_name, date_of_birth, blood_group, gender
			FROM
				`tabStudent Patient`
			WHERE
				name = %s""", (student_patient), as_dict=1)
	if not patient_dict:
		frappe.throw(_('Student as patient not found'))
	details = patient_dict[0]
	return details
