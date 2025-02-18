# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from ifitwala_ed.setup.utils import insert_record
from frappe.desk.doctype.global_search_settings.global_search_settings import update_global_search_doctypes

def setup_education():
	disable_desk_access_for_guardian_role()
	create_designations()
	create_log_type()
	create_attendance_code()
	create_location_type()
	add_other_records()
	update_global_search_doctypes()


def disable_desk_access_for_guardian_role():
	try:
		guardian_role = frappe.get_doc("Role", "Guardian")
	except frappe.DoesNotExistError:
		create_guardian_role()
		return

	guardian_role.desk_access = 0
	guardian_role.save()

def create_guardian_role():
	guardian_role = frappe.get_doc({
		"doctype": "Role",
		"role_name": "Guardian",
		"desk_access": 0
	})
	guardian_role.insert()

def create_designations():
	data = [
		{"doctype": "Designation", "designation_name": "Director"},
		{"doctype": "Designation", "designation_name": "Principal"},
		{"doctype": "Designation", "designation_name": "Assistant Principal"},
		{"doctype": "Designation", "designation_name": "Nurse"},
		{"doctype": "Designation", "designation_name": "Teacher"},
		{"doctype": "Designation", "designation_name": "Teacher Assistant"}
	]
	insert_record(data)

def create_log_type():
	data = [
			{"doctype": "Student Log Type", "log_type": "Behaviour"},
			{"doctype": "Student Log Type", "log_type": "Academic"},
			{"doctype": "Student Log Type", "log_type": "Medical"}
	]
	insert_record(data)

def create_attendance_code():
	data = [
			{"doctype": "Student Attendance Code", "attendance_code": "Present"},
			{"doctype": "Student Attendance Code", "attendance_code": "Absent"},
			{"doctype": "Student Attendance Code", "attendance_code": "Tardy"},
			{"doctype": "Student Attendance Code", "attendance_code": "Excused Absence"},
			{"doctype": "Student Attendance Code", "attendance_code": "Field Trip"},
			{"doctype": "Student Attendance Code", "attendance_code": "Excused Tardy"}
	]
	insert_record(data)

def create_location_type():
	data = [
		{"doctype": "Location Type", "location_type_name": "Classroom"},
		{"doctype": "Location Type", "location_type_name": "Office"},
		{"doctype": "Location Type", "location_type_name": "Library"},
		{"doctype": "Location Type", "location_type_name": "Building"},
		{"doctype": "Location Type", "location_type_name": "Storage"},
		{"doctype": "Location Type", "location_type_name": "Sport Court"},
		{"doctype": "Location Type", "location_type_name": "Theatre"},
		{"doctype": "Location Type", "location_type_name": "Auditorium"}, 
		{"doctype": "Location Type", "location_type_name": "Gym"},
		{"doctype": "Location Type", "location_type_name": "Transit"},
	]
	insert_record(data)

def add_other_records(country=None):
	records = [
		# item group
		#{'doctype': 'Item Group', 'item_group_name': _('All Item Groups'), 'is_group': 1, 'parent_item_group': ''},

		# Employment Type
		{'doctype': 'Employment Type', 'employment_type_name': _('Full-time')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Part-time')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Probation')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Contract')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Intern')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Apprentice')},
	]
	insert_record(records)	