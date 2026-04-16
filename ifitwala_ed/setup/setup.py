# ifitwala_ed/setup/setup.py
# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import os

import frappe
from frappe import _
from frappe.utils import cstr, get_files_path

from ifitwala_ed.admission.access import ADMISSIONS_FAMILY_ROLE
from ifitwala_ed.governance.policy_utils import ensure_policy_audience_records
from ifitwala_ed.printing.letter_head.sync import (
    ensure_print_settings_with_letterhead,
    sync_default_school_letter_head,
)
from ifitwala_ed.routing.policy import canonical_path_for_section
from ifitwala_ed.school_site.doctype.website_theme_profile.website_theme_profile import (
    ensure_theme_profile_presets,
)
from ifitwala_ed.setup.utils import insert_record
from ifitwala_ed.website.block_registry import (
    get_website_block_definition_records as get_canonical_website_block_definition_records,
)
from ifitwala_ed.website.block_registry import (
    sync_website_block_definitions,
)
from ifitwala_ed.website.public_brand import sync_public_brand_website_settings

DEFAULT_ADDRESS_TEMPLATE = (
    "{{ address_line1 }}<br>\n"
    "{% if address_line2 %}{{ address_line2 }}<br>{% endif -%}\n"
    "{{ city }}<br>\n"
    "{% if state %}{{ state }}<br>{% endif -%}\n"
    "{% if pincode %} PIN:  {{ pincode }}<br>{% endif -%}\n"
    "{{ country }}<br>\n"
    "{% if phone %}Phone: {{ phone }}<br>{% endif -%}\n"
    "{% if fax %}Fax: {{ fax }}<br>{% endif -%}\n"
    "{% if email_id %}Email: {{ email_id }}<br>{% endif -%}\n"
)


def setup_education():
    ensure_initial_setup_flag()
    ensure_root_organization()
    create_roles_with_homepage()
    ensure_canonical_role_records()
    ensure_leave_roles()
    grant_role_read_select_to_hr()
    create_designations()
    create_log_type()
    create_default_leave_types()
    create_default_attendance_codes()
    create_location_type()
    add_other_records()
    ensure_default_address_template()
    ensure_hr_settings()
    create_student_file_folder()
    setup_website_top_bar()
    setup_website_block_definitions()
    setup_website_theme_profiles()
    setup_default_website_pages()
    sync_public_brand_website_settings()
    sync_default_school_letter_head()
    ensure_print_settings_with_letterhead()
    grant_core_crm_permissions()
    ensure_policy_audience_records()


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
    roots = frappe.get_all("Organization", fields=["name"], filters={"parent_organization": ""})

    if len(roots) > 1:
        frappe.throw(
            _("Multiple root Organization records found: {0}").format(", ".join(d.name for d in roots)),
            title=_("Initial Setup Aborted"),
        )

    if not roots:
        try:
            frappe.get_doc(
                {
                    "doctype": "Organization",
                    "organization_name": "All Organizations",
                    "abbr": "ALL",
                    "is_group": 1,
                    "parent_organization": "",
                }
            ).insert(ignore_permissions=True)
        except Exception as e:
            # Bubble up any DB/validation issue
            frappe.throw(_("Unable to create root Organization: {0}").format(str(e)), title=_("Initial Setup Aborted"))


def create_roles_with_homepage():
    """Create or update roles with home_page and desk_access."""
    roles = [
        {"role_name": "Student", "desk_access": 0, "home_page": canonical_path_for_section("student")},
        {"role_name": "Guardian", "desk_access": 0, "home_page": canonical_path_for_section("guardian")},
        {"role_name": "Admissions Applicant", "desk_access": 0, "home_page": "/admissions"},
        {"role_name": ADMISSIONS_FAMILY_ROLE, "desk_access": 0, "home_page": "/admissions"},
        {"role_name": "Academic Staff", "desk_access": 1, "home_page": canonical_path_for_section("staff")},
        {"role_name": "Nurse", "desk_access": 1, "home_page": "/desk/health"},
        {"role_name": "Academic Admin", "desk_access": 1, "home_page": "/desk/admin"},
        {"role_name": "Admission Officer", "desk_access": 1, "home_page": "/desk/admission"},
        {"role_name": "Admission Manager", "desk_access": 1, "home_page": "/desk/admission"},
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
            frappe.get_doc({"doctype": "Role", **role}).insert(ignore_permissions=True)


def ensure_canonical_role_records():
    """Ensure role records exist for canonical role names used in seed data."""
    roles = [
        {"role_name": "Academic Assistant", "desk_access": 1},
        {"role_name": "Counselor", "desk_access": 1},
    ]

    for role in roles:
        existing = frappe.db.exists("Role", role["role_name"])
        if existing:
            doc = frappe.get_doc("Role", role["role_name"])
            if int(doc.desk_access or 0) != int(role["desk_access"]):
                doc.desk_access = role["desk_access"]
                doc.save(ignore_permissions=True)
            continue

        frappe.get_doc({"doctype": "Role", **role}).insert(ignore_permissions=True)


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
    organization = _resolve_designation_seed_organization()
    if not organization:
        return

    data = [
        {
            "doctype": "Designation",
            "designation_name": "Director",
            "organization": organization,
            "default_role_profile": "Academic Admin",
            "default_workspace": "Admin",
        },
        {
            "doctype": "Designation",
            "designation_name": "Principal",
            "organization": organization,
            "default_role_profile": "Academic Admin",
            "default_workspace": "Admin",
        },
        {
            "doctype": "Designation",
            "designation_name": "Academic Assistant",
            "organization": organization,
            "default_role_profile": "Academic Assistant",
            "default_workspace": "Admin",
        },
        {"doctype": "Designation", "designation_name": "Assistant Principal", "organization": organization},
        {
            "doctype": "Designation",
            "designation_name": "Nurse",
            "organization": organization,
            "default_role_profile": "Nurse",
            "default_workspace": "Health",
        },
        {
            "doctype": "Designation",
            "designation_name": "Teacher",
            "organization": organization,
            "default_role_profile": "Academic Staff",
            "default_workspace": "Academics",
        },
        {"doctype": "Designation", "designation_name": "Teacher Assistant", "organization": organization},
        {
            "doctype": "Designation",
            "designation_name": "Counselor",
            "organization": organization,
            "default_role_profile": "Counselor",
            "default_workspace": "Counseling",
        },
        {
            "doctype": "Designation",
            "designation_name": "Curriculum Coordinator",
            "organization": organization,
            "default_role_profile": "Curriculum Coordinator",
            "default_workspace": "Curriculum",
        },
        {
            "doctype": "Designation",
            "designation_name": "HR Director",
            "organization": organization,
            "default_role_profile": "HR Manager",
            "default_workspace": "HR",
        },
    ]
    insert_record(data)


def _resolve_designation_seed_organization():
    organization = frappe.db.get_value(
        "Organization",
        {"name": ["!=", "All Organizations"]},
        "name",
        order_by="lft asc",
    )
    return cstr(organization).strip() or None


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
        {"doctype": "Student Log Type", "log_type": "Positive Attitude Towards Learning"},
    ]
    insert_record(data)


def create_default_leave_types():
    data = [
        {"doctype": "Leave Type", "leave_type_name": "Annual Leave"},
        {"doctype": "Leave Type", "leave_type_name": "Sick Leave"},
        {"doctype": "Leave Type", "leave_type_name": "Personal Leave"},
        {"doctype": "Leave Type", "leave_type_name": "School Related Activities"},
        {"doctype": "Leave Type", "leave_type_name": "Bereavement Leave"},
        {"doctype": "Leave Type", "leave_type_name": "Maternity Leave"},
        {"doctype": "Leave Type", "leave_type_name": "Paternity Leave"},
        {"doctype": "Leave Type", "leave_type_name": "Family Care Leave"},
        {"doctype": "Leave Type", "leave_type_name": "Professional Development Leave"},
        {"doctype": "Leave Type", "leave_type_name": "Unpaid Leave", "is_lwp": 1},
    ]
    insert_record(data)


def create_default_attendance_codes():
    data = [
        {
            "doctype": "Student Attendance Code",
            "attendance_code_name": "Present",
            "attendance_code": "P",
            "count_as_present": 1,
            "is_default": 1,
            "show_in_attendance_tool": 1,
            "show_in_reports": 1,
            "color": "#29CD42",
            "display_order": 10,
        },
        {
            "doctype": "Student Attendance Code",
            "attendance_code_name": "Absent",
            "attendance_code": "A",
            "count_as_present": 0,
            "is_default": 0,
            "show_in_attendance_tool": 1,
            "show_in_reports": 1,
            "color": "#CB2929",
            "display_order": 20,
        },
        {
            "doctype": "Student Attendance Code",
            "attendance_code_name": "Late",
            "attendance_code": "L",
            "count_as_present": 1,
            "is_default": 0,
            "show_in_attendance_tool": 1,
            "show_in_reports": 1,
            "color": "#FC8200",
            "display_order": 30,
        },
        {
            "doctype": "Student Attendance Code",
            "attendance_code_name": "Informed Absence",
            "attendance_code": "IA",
            "count_as_present": 0,
            "is_default": 0,
            "show_in_attendance_tool": 0,
            "show_in_reports": 1,
            "color": "#CC6045",
            "display_order": 40,
        },
        {
            "doctype": "Student Attendance Code",
            "attendance_code_name": "Field Trip",
            "attendance_code": "FT",
            "count_as_present": 1,
            "is_default": 0,
            "show_in_attendance_tool": 1,
            "show_in_reports": 1,
            "color": "#4463F0",
            "display_order": 50,
        },
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
        {"doctype": "Employment Type", "employment_type_name": _("Full-time")},
        {"doctype": "Employment Type", "employment_type_name": _("Part-time")},
        {"doctype": "Employment Type", "employment_type_name": _("Probation")},
        {"doctype": "Employment Type", "employment_type_name": _("Contract")},
        {"doctype": "Employment Type", "employment_type_name": _("Intern")},
        {"doctype": "Employment Type", "employment_type_name": _("Apprentice")},
        # Student Log Next Steps
        {
            "doctype": "Student Log Next Step",
            "next_step": "Refer to Curriculum Coordinator",
            "associated_role": "Curriculum Coordinator",
        },
        {"doctype": "Student Log Next Step", "next_step": "Refer to Patoral Lead"},
        {"doctype": "Student Log Next Step", "next_step": "Refer to counseling", "associated_role": "Counselor"},
        {
            "doctype": "Student Log Next Step",
            "next_step": "Refer to academic admin",
            "associated_role": "Academic Admin",
        },
        {
            "doctype": "Student Log Next Step",
            "next_step": "Parents meeting needed",
            "associated_role": "Academic Assistant",
        },
        {
            "doctype": "Student Log Next Step",
            "next_step": "Refer to Learning Support",
            "associated_role": "Learning Support",
        },
        {"doctype": "Student Log Next Step", "next_step": "Behaviour follow-up", "associated_role": "Pastoral Lead"},
        {"doctype": "Student Log Next Step", "next_step": "IT / Device support", "associated_role": "Organization IT"},
        {"doctype": "Student Log Next Step", "next_step": "Refer to Nurse / Health", "associated_role": "Nurse"},
        # Program tree root (global)
        {
            "doctype": "Program",
            "name": "All Programs",
            "program_name": "All Programs",
            "is_group": 1,
            "parent_program": "",
        },
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


def ensure_default_address_template():
    if not frappe.db.table_exists("Address Template"):
        return

    if frappe.db.exists("Address Template", {"is_default": 1}):
        return

    country = _get_address_template_seed_country()
    if country:
        frappe.get_doc(
            {
                "doctype": "Address Template",
                "country": country,
                "is_default": 1,
                "template": DEFAULT_ADDRESS_TEMPLATE,
            }
        ).insert(ignore_permissions=True, ignore_if_duplicate=True)
        frappe.clear_cache(doctype="Address Template")
        return

    template_name = _get_existing_address_template_to_promote()
    if not template_name:
        return

    doc = frappe.get_doc("Address Template", template_name)
    changed = False

    if not int(doc.is_default or 0):
        doc.is_default = 1
        changed = True

    if not cstr(doc.template).strip():
        doc.template = DEFAULT_ADDRESS_TEMPLATE
        changed = True

    if changed:
        doc.save(ignore_permissions=True)
        frappe.clear_cache(doctype="Address Template")


def _get_address_template_seed_country() -> str | None:
    if not frappe.db.table_exists("Country"):
        return None

    preferred_country = cstr(frappe.db.get_single_value("System Settings", "country")).strip()
    templated_countries = set(frappe.get_all("Address Template", pluck="country", limit=500))
    countries: list[str] = []

    if (
        preferred_country
        and preferred_country not in templated_countries
        and frappe.db.exists("Country", preferred_country)
    ):
        countries.append(preferred_country)

    all_countries = frappe.get_all("Country", pluck="name", order_by="name asc", limit=500)
    countries.extend(country for country in all_countries if country not in countries)

    for country in countries:
        if country not in templated_countries:
            return country

    return None


def _get_existing_address_template_to_promote() -> str | None:
    preferred_country = cstr(frappe.db.get_single_value("System Settings", "country")).strip()
    if preferred_country and frappe.db.exists("Address Template", preferred_country):
        return preferred_country

    template_name = frappe.db.get_value("Address Template", {}, "name", order_by="creation asc")
    return cstr(template_name).strip() or None


def _get_doctype_editor_roles(doctype: str) -> list[str]:
    """Return roles that can create or edit the given DocType at permlevel 0."""
    meta = frappe.get_meta(doctype)
    roles: list[str] = []

    for perm in meta.permissions or []:
        role = cstr(perm.get("role")).strip()
        if not role:
            continue
        if int(perm.get("write") or 0) or int(perm.get("create") or 0):
            roles.append(role)

    return list(dict.fromkeys(roles))


def grant_role_read_select_to_hr():
    """Allow staff who manage Role-linked setup doctypes to resolve Role links safely.

    Frappe validates Link fields via validate_link, which requires Read or Select on
    the target doctype (Role). Student Log Next Step editors need the same access as
    Designation editors so they can set the associated role for a next step.
    """
    target_doctype = "Role"
    target_roles = [
        "HR Manager",
        "HR User",
        "Academic Admin",
        *_get_doctype_editor_roles("Student Log Next Step"),
    ]
    target_roles = list(dict.fromkeys(role for role in target_roles if cstr(role).strip()))

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

            # 'select' exists on DocPerm/Custom DocPerm in Frappe v16+
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
    records = [{"doctype": "File", "file_name": "student", "is_folder": 1, "folder": "Home"}]
    insert_record(records)

    # Ensure the physical folder also exists
    os.makedirs(os.path.join(get_files_path(), "student"), exist_ok=True)


def setup_website_top_bar():

    # Keep login surface nav minimal and deterministic.
    # Public school website navigation is rendered from School Website Page records.
    top_bar_items = [
        {"label": "Home", "url": "/"},
        {"label": "Schools", "url": "/schools"},
        {"label": "Inquire", "url": "/apply/inquiry"},
        {"label": "Login", "url": "/login"},
    ]

    ws = frappe.get_single("Website Settings")
    ws.top_bar_items = []
    if ws.meta.has_field("home_page"):
        ws.home_page = "index"

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
    """Ensure Contact/Address Desk permissions stay aligned with the app contract."""

    doctype_role_permissions = {
        "Contact": {
            "Admission Officer": ["read", "write", "create", "email", "comment", "assign"],
            "Admission Manager": ["read", "write", "create", "delete", "email", "comment", "assign"],
            "Academic Admin": ["read", "write", "create", "delete", "email", "comment", "assign"],
            "Academic Assistant": ["read", "write", "create", "delete", "email", "comment", "assign"],
            "Curriculum Coordinator": ["read"],
            "HR Manager": ["read"],
            "HR User": ["read"],
            "Employee": ["read"],
            "Accounts User": ["read", "write", "create", "email", "comment", "assign"],
            "Accounts Manager": ["read", "write", "create", "delete", "email", "comment", "assign"],
        },
        "Address": {
            "Admission Officer": ["read", "email", "comment", "assign"],
            "Admission Manager": ["read", "write", "create", "delete", "email", "comment", "assign"],
            "Academic Admin": ["read", "write", "create", "delete", "email", "comment", "assign"],
            "Academic Assistant": ["read", "write", "create", "delete", "email", "comment", "assign"],
            "Curriculum Coordinator": ["read"],
        },
    }

    required_roles = sorted(
        {
            role
            for role_permissions in doctype_role_permissions.values()
            for role in role_permissions
            if (role or "").strip()
        }
    )
    for role_name in required_roles:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)

    for doctype, role_permissions in doctype_role_permissions.items():
        for role, perms in role_permissions.items():
            existing = frappe.get_all("Custom DocPerm", filters={"parent": doctype, "role": role, "permlevel": 0})
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
