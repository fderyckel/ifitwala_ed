# ifitwala_ed/setup/setup.py
# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from ifitwala_ed.setup.utils import insert_record
from ifitwala_ed.school_site.doctype.website_theme_profile.website_theme_profile import (
	ensure_theme_profile_presets,
)
from ifitwala_ed.routing.policy import canonical_path_for_section
from ifitwala_ed.website.block_registry import (
	get_website_block_definition_records as get_canonical_website_block_definition_records,
	sync_website_block_definitions,
)
from frappe.utils import get_files_path
import os

def setup_education():
	ensure_initial_setup_flag()
	ensure_root_organization()
	create_roles_with_homepage()
	ensure_leave_roles()
	grant_role_read_select_to_hr()
	create_designations()
	create_log_type()
	create_location_type()
	add_other_records()
	ensure_hr_settings()
	create_student_file_folder()
	setup_website_top_bar()
	setup_website_block_definitions()
	setup_website_theme_profiles()
	setup_default_website_pages()
	grant_core_crm_permissions()


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
		{"role_name": "Student", "desk_access": 0, "home_page": canonical_path_for_section("student")},
		{"role_name": "Guardian", "desk_access": 0, "home_page": canonical_path_for_section("guardian")},
		{"role_name": "Admissions Applicant", "desk_access": 0, "home_page": "/admissions"},
		{"role_name": "Nurse", "desk_access": 1, "home_page": "/app/health"},
		{"role_name": "Academic Admin", "desk_access": 1, "home_page": "/app/admin"},
		{"role_name": "Admission Officer", "desk_access": 1, "home_page": "/app/admission"},
		{"role_name": "Admission Manager", "desk_access": 1, "home_page": "/app/admission"},
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


def ensure_leave_roles():
	for role_name in ["Leave Approver"]:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)


def ensure_hr_settings():
	if not frappe.db.exists("DocType", "HR Settings"):
		return

	settings = frappe.get_single("HR Settings")
	defaults = {
		"leave_approver_mandatory_in_leave_application": 1,
		"prevent_self_leave_approval": 1,
		"restrict_backdated_leave_application": 0,
		"send_leave_notification": 0,
		"show_leaves_of_all_department_members_in_calendar": 0,
		"enable_earned_leave_scheduler": 1,
		"enable_leave_expiry_scheduler": 1,
		"enable_leave_encashment": 0,
		"auto_leave_encashment": 0,
	}

	changed = False
	for fieldname, value in defaults.items():
		if settings.get(fieldname) is None:
			settings.set(fieldname, value)
			changed = True

	if changed:
		settings.save(ignore_permissions=True)


def create_designations():
	data = [
		{"doctype": "Designation", "designation_name": "Director", 								"default_role_profile": "Academic Admin", 				"default_workspace": "Admin"},
		{"doctype": "Designation", "designation_name": "Principal", 							"default_role_profile": "Academic Admin", 				"default_workspace": "Admin"},
		{"doctype": "Designation", "designation_name": "Academic Assistant", 			"default_role_profile": "Academic Assistant", 		"default_workspace": "Admin"},
		{"doctype": "Designation", "designation_name": "Assistant Principal"},
		{"doctype": "Designation", "designation_name": "Nurse", 									"default_role_profile": "Nurse", 									"default_workspace": "Health"},
		{"doctype": "Designation", "designation_name": "Teacher", 								"default_role_profile": "Academic Staff", 				"default_workspace": "Academics"},
		{"doctype": "Designation", "designation_name": "Teacher Assistant"},
		{"doctype": "Designation", "designation_name": "Counsellor", 							"default_role_profile": "Counsellor", 						"default_workspace": "Counseling"},
		{"doctype": "Designation", "designation_name": "Curriculum Coordinator", 	"default_role_profile": "Curriculum Coordinator", "default_workspace": "Curriculum"},
		{"doctype": "Designation", "designation_name": "HR Director", 						"default_role_profile": "HR Manager", 						"default_workspace": "HR"},
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
    {'doctype': 'Student Log Next Step', 'next_step': 'Refer to Curriculum Coordinator', 'associated_role': 'Curriculum Coordinator'},
		{'doctype': 'Student Log Next Step', 'next_step': 'Refer to Patoral Lead'},
		{'doctype': 'Student Log Next Step', 'next_step': 'Refer to counseling', 'associated_role': 'Counsellor'},
		{'doctype': 'Student Log Next Step', 'next_step': 'Refer to academic admin', 'associated_role': 'Academic Admin'},
		{"doctype": "Student Log Next Step", "next_step": "Parents meeting needed", "associated_role": "Academic Assistant"},
		{"doctype": "Student Log Next Step", "next_step": "Refer to Learning Support", "associated_role": "Learning Support"},
		{"doctype": "Student Log Next Step", "next_step": "Behaviour follow-up", "associated_role": "Pastoral Lead"},
		{"doctype": "Student Log Next Step", "next_step": "IT / Device support", "associated_role": "Organization IT"},
		{"doctype": "Student Log Next Step", "next_step": "Refer to Nurse / Health", "associated_role": "Nurse"},

		# Program tree root (global)
		{'doctype': 'Program', 'name': 'All Programs', 'program_name': 'All Programs', 'is_group': 1, 'parent_program': ''},
	]
	for record in records:
		block_type = record.get("block_type")
		if not block_type:
			continue
		if frappe.db.exists("Website Block Definition", {"block_type": block_type}):
			continue
		doc = frappe.get_doc(record)
		doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
		frappe.db.commit()


def grant_role_read_select_to_hr():
	"""Allow HR Manager / HR User to link to Role from Designation (and read role names).
	This must be done at setup time because Frappe validates Link fields via validate_link,
	which requires Read or Select on the target doctype (Role).
	"""
	target_doctype = "Role"
	# Roles that can edit Designation should be able to resolve Role links.
	target_roles = ["HR Manager", "HR User", "Academic Admin"]

	# Custom permissions are stored as Custom DocPerm (safe to add; survives updates).
	# We only grant read + select at permlevel 0.
	for role in target_roles:
		existing_name = frappe.db.get_value(
			"Custom DocPerm",
			{"parent": target_doctype, "role": role, "permlevel": 0},
			"name",
		)

		if existing_name:
			doc = frappe.get_doc("Custom DocPerm", existing_name)
			changed = False

			if not int(doc.get("read") or 0):
				doc.read = 1
				changed = True

			# 'select' exists on DocPerm/Custom DocPerm in Frappe v15+
			if doc.meta.has_field("select") and not int(doc.get("select") or 0):
				doc.select = 1
				changed = True

			if changed:
				doc.save(ignore_permissions=True)
		else:
			payload = {
				"doctype": "Custom DocPerm",
				"parent": target_doctype,
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": role,
				"permlevel": 0,
				"read": 1,
			}
			# Only set 'select' if field exists in this site/schema
			meta = frappe.get_meta("Custom DocPerm")
			if meta.has_field("select"):
				payload["select"] = 1

			frappe.get_doc(payload).insert(ignore_permissions=True)

	# Make sure the permission cache is refreshed
	frappe.clear_cache(doctype=target_doctype)


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

    # Keep login surface nav minimal and deterministic.
    # Public school website navigation is rendered from School Website Page records.
    top_bar_items = [
        {"label": "Home", "url": "/"},
        {"label": "Login", "url": "/login"},
    ]

    ws = frappe.get_single("Website Settings")
    ws.top_bar_items = []
    if ws.meta.has_field("home_page"):
        ws.home_page = "/"

    for item in top_bar_items:
        ws.append("top_bar_items", item)

    ws.save(ignore_permissions=True)

def setup_website_block_definitions():
	sync_website_block_definitions()


def setup_website_theme_profiles():
	if not frappe.db.exists("DocType", "Website Theme Profile"):
		return
	ensure_theme_profile_presets()


def setup_default_website_pages():
	"""
	Seed a usable default website for fresh installs when a School already exists.
	Idempotent and safe to run multiple times.
	"""
	school_name = frappe.db.get_value(
		"School",
		{"is_group": 1},
		"name",
		order_by="lft asc",
	)
	if not school_name:
		return

	from ifitwala_ed.website.bootstrap import ensure_default_school_website

	ensure_default_school_website(
		school_name=school_name,
		set_default_organization=True,
	)

def get_website_block_definition_records():
	return get_canonical_website_block_definition_records()

def grant_core_crm_permissions():
	"""Ensure critical roles have access to Contact and Address Doctypes."""

	crm_doctypes = ["Contact", "Address"]

	# Define permissions by role
	role_permissions = {
		"Admission Officer": ["read", "email", "comment", "assign"],
		"Admission Manager": ["read", "write", "create", "delete", "email", "comment", "assign"],
		"Academic Admin": ["read", "write", "create", "delete", "email", "comment", "assign"],
		"Academic Assistant": ["read", "write", "create", "delete", "email", "comment", "assign"],
	}

	for doctype in crm_doctypes:
		for role, perms in role_permissions.items():
			existing = frappe.get_all(
				"Custom DocPerm",
				filters={"parent": doctype, "role": role, "permlevel": 0}
			)
			if existing:
				# Always overwrite — setup is idempotent
				for docname in [d.name for d in existing]:
					frappe.delete_doc("Custom DocPerm", docname, force=True)

			docperm = frappe.new_doc("Custom DocPerm")
			docperm.parent = doctype
			docperm.parenttype = "DocType"
			docperm.parentfield = "permissions"  # Required field for correct behavior
			docperm.role = role
			docperm.permlevel = 0

			for perm in ["read", "write", "create", "delete", "email", "comment", "assign"]:
				docperm.set(perm, 1 if perm in perms else 0)

			docperm.insert(ignore_permissions=True)
		frappe.clear_cache(doctype=doctype)  # Clear cache after permission update
