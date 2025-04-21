# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from ifitwala_ed.setup.utils import insert_record

def setup_education():
	create_roles_with_homepage()
	create_designations()
	create_log_type()
	create_location_type()
	add_other_records()

def create_roles_with_homepage():
    """Create or update roles with home_page and desk_access."""
    roles = [
        {"role_name": "Student", "desk_access": 0, "home_page": "/sp"},
        {"role_name": "Guardian", "desk_access": 0, "home_page": "/sp"},
        {"role_name": "Nurse", "desk_access": 1, "home_page": "/app/health"},
        {"role_name": "Academic Admin", "desk_access": 1, "home_page": "/app/settings"},
    ]

    for role in roles:
        existing = frappe.db.exists("Role", role["role_name"])
        if existing:
            doc = frappe.get_doc("Role", role["role_name"])
            updated = False

            if doc.home_page != role["home_page"]:
                doc.home_page = role["home_page"]
                updated = True
            if doc.desk_access != role["desk_access"]:
                doc.desk_access = role["desk_access"]
                updated = True

            if updated:
                doc.save(ignore_permissions=True)
        else:
            frappe.get_doc({
                "doctype": "Role",
                **role
            }).insert(ignore_permissions=True)



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
			{"doctype": "Student Log Type", "log_type": "Academic Concern"},
			{"doctype": "Student Log Type", "log_type": "Medical"}, 
			{"doctype": "Student Log Type", "log_type": "Other"}, 
			{"doctype": "Student Log Type", "log_type": "Dress Code"}, 
			{"doctype": "Student Log Type", "log_type": "Medical"}, 
			{"doctype": "Student Log Type", "log_type": "Academic Honesty"}, 
			{"doctype": "Student Log Type", "log_type": "Social-Emotional"}, 
			{"doctype": "Student Log Type", "log_type": "Positive Attitude Towards Learning"}
	]
	insert_record(data)

# def create_attendance_code():
# 	data = [
# 			{"doctype": "Student Attendance Code", "attendance_code": "Present"},
# 			{"doctype": "Student Attendance Code", "attendance_code": "Absent"},
# 			{"doctype": "Student Attendance Code", "attendance_code": "Tardy"},
# 			{"doctype": "Student Attendance Code", "attendance_code": "Excused Absence"},
# 			{"doctype": "Student Attendance Code", "attendance_code": "Field Trip"},
# 			{"doctype": "Student Attendance Code", "attendance_code": "Excused Tardy"}
# 	]
# 	insert_record(data)

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