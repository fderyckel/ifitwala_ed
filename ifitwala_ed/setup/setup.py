# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import os
import json
import frappe
from frappe import _
from ifitwala_ed.setup.utils import insert_record
from frappe.utils import get_files_path

def setup_education():
	ensure_initial_setup_flag()  
	ensure_root_organization()
	create_roles_with_homepage()
	create_designations()
	create_log_type()
	create_location_type()
	add_other_records()
	create_student_file_folder()
	setup_website_top_bar()
	setup_web_pages()


def ensure_initial_setup_flag():
	"""Ensure the Ifitwala Initial Setup flag exists on Org Setting."""
	doc = frappe.get_single("Org Setting")
	# safer check – explicit field lookup
	if doc.get("ifitwala_initial_setup") is None:
		doc.ifitwala_initial_setup = 0
		doc.save(ignore_permissions=True)

def ensure_root_organization():
	"""
	Create “All Organizations” as the single NestedSet root if it does not
	already exist. If more than one blank parent record exists, raise an error.
	"""

	# Sanity‑check: zero or one root only
	roots = frappe.get_all("Organization",
		fields=["name"],
		filters={"parent_organization": ""}
	)

	if len(roots) > 1:
		frappe.throw(
			_("Multiple root Organization records found: {0}")
			.format(", ".join(d.name for d in roots)),
			title=_("Initial Setup Aborted")
		)

	if not roots:
		try:
			frappe.get_doc({
				"doctype":            "Organization",
				"organization_name":  "All Organizations",
				"abbr":               "ALL",
				"is_group":           1,
				"parent_organization": ""
			}).insert(ignore_permissions=True)
		except Exception as e:
			# Bubble up any DB/validation issue
			frappe.throw(
				_("Unable to create root Organization: {0}").format(str(e)),
				title=_("Initial Setup Aborted")
			)



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

		# Employment Type
		{'doctype': 'Employment Type', 'employment_type_name': _('Full-time')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Part-time')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Probation')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Contract')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Intern')},
		{'doctype': 'Employment Type', 'employment_type_name': _('Apprentice')},
        
        # Student Log Next Steps
        {'doctype': 'Student Log Next Step', 'next_step': 'Refer to Curriculum Coordinator'},
		{'doctype': 'Student Log Next Step', 'next_step': 'Refer to Grade Level Leader'},
		{'doctype': 'Student Log Next Step', 'next_step': 'Refer to counseling'},
		{'doctype': 'Student Log Next Step', 'next_step': 'Refer to academic admin'},
		{'doctype': 'Student Log Next Step', 'next_step': 'Parents meeting needed'},
		{'doctype': 'Student Log Next Step', 'next_step': 'For information only'},
		{'doctype': 'Student Log Next Step', 'next_step': 'No Action Required at this time'},
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
  
	# Ensure the physical folder also exists
	os.makedirs(os.path.join(get_files_path(), "student"), exist_ok=True)
     
def setup_website_top_bar():
    
    top_bar_items = [
        # Primary items
        {"label": "Home"},
        {"label": "About Us"},
        {"label": "Academics"},
        {"label": "Admission"},
        {"label": "News & Events"},
        {"label": "Community"},
        {"label": "Contact Us"},

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
	
METADATA_FIELDS = { 
	"docstatus", "modified", "modified_by",
  "owner", "creation", "idx", "_user_tags"
}

def setup_web_pages():
	"""
	Insert Web Page records from fixtures/web_page.json.
	Any error aborts execution via frappe.throw().
	"""
	fixture_path = frappe.get_app_path("ifitwala_ed", "setup", "data", "web_page.json")

	#  Ensure the fixture file exists
	if not os.path.exists(fixture_path):
		frappe.throw(
			_("Web Page fixture not found at {0}").format(fixture_path),
			title=_("Initial Setup Aborted")
		)

	# Load JSON
	try:
		with open(fixture_path, encoding="utf-8") as f:
			records = json.load(f)
	except Exception as e:
		frappe.throw(
			_("Failed to load Web Page fixtures: {0}").format(str(e)),
			title=_("Initial Setup Aborted")
		)

	#  Insert each record
	for record in records:
		if record.get("doctype") != "Web Page":
			continue

		identifier = record.get("name") or record.get("route") or record.get("title")
		if not identifier:
			frappe.throw(
				_("Web Page record missing a unique identifier (name/route/title)."),
				title=_("Initial Setup Aborted")
			)

		# Skip if already present – not an error
		if frappe.db.exists("Web Page", identifier):
			continue

		filtered = {k: v for k, v in record.items() if k not in METADATA_FIELDS}
		# Ensure required keys
		filtered.setdefault("doctype", "Web Page")
		filtered.setdefault("name", identifier)
		if "name" not in filtered:
			filtered["name"] = identifier

		try:
			frappe.get_doc(filtered).insert(ignore_permissions=True)
		except Exception as e:
			frappe.throw(
				_("Failed to insert Web Page '{0}': {1}").format(identifier, str(e)),
				title=_("Initial Setup Aborted")
			)