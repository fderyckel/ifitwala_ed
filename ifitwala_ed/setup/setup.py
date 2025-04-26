# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import os
import frappe
from frappe import _
from ifitwala_ed.setup.utils import insert_record
from frappe.utils import get_files_path

def setup_education():
  create_roles_with_homepage()
  create_designations()
  create_log_type()
  create_location_type()
  add_other_records() 
  create_student_file_folder()
  setup_website_top_bar()

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
      
def create_student_file_folder():
	records = [{
		"doctype": "File",
		"file_name": "student",
		"is_folder": 1,
		"folder": "Home"
	}]
	insert_record(records)
  
	# 🔐 Ensure the physical folder also exists
	os.makedirs(os.path.join(get_files_path(), "student"), exist_ok=True)
     
def setup_website_top_bar():
    top_bar_items = [
        # Primary items
        {"label": "Home", "url": "/"},
        {"label": "About Us", "url": "/about"},
        {"label": "Academics", "url": "/academics"},
        {"label": "Admission", "url": "/admission"},
        {"label": "News & Events", "url": "/news-events"},
        {"label": "Community", "url": "/community"},
        {"label": "Contact Us", "url": "/contact"},

        # About Us Submenu
        {"label": "Mission & Values", "url": "/mission-values", "parent_label": "About Us"},
        {"label": "Leadership & Administration", "url": "/leadership", "parent_label": "About Us"},
        {"label": "Our History", "url": "/our-history", "parent_label": "About Us"},

        # Academics Submenu
        {"label": "Programs", "url": "/programs", "parent_label": "Academics"},
        {"label": "Curriculum & Learning", "url": "/curriculum", "parent_label": "Academics"},
        {"label": "Resources & Support", "url": "/resources", "parent_label": "Academics"},

        # Community Submenu
        {"label": "Community Engagement", "url": "/engagement", "parent_label": "Community"},
        {"label": "Parents & Families", "url": "/parents", "parent_label": "Community"},
        {"label": "Alumni", "url": "/alumni", "parent_label": "Community"},
        {"label": "Recruitment", "url": "/recruitment", "parent_label": "Community"},
    ]

    ws = frappe.get_single("Website Settings")
    ws.top_bar_items = []

    for item in top_bar_items:
        ws.append("top_bar_items", item)

    ws.save(ignore_permissions=True)
	