# ifitwala_ed/hooks.py
from ifitwala_ed.routing.policy import WEBSITE_REDIRECTS, WEBSITE_ROUTE_RULES

app_name = "ifitwala_ed"
app_title = "Ifitwala"
app_publisher = "François de Ryckel"
app_description = "School management System"
app_email = "f.deryckel@gmail.com"
app_license = "MIT"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ifitwala",
# 		"logo": "/assets/ifitwala/logo.png",
# 		"title": "Ifitwala",
# 		"route": "/ifitwala",
# 		"has_permission": "ifitwala.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html

app_include_js = ["/assets/ifitwala_ed/js/ifitwala_ed.bundle.js", "/assets/ifitwala_ed/js/initial_setup.js"]

# app_include_css = "/assets/ifitwala_ed/css/desk_overrides.bundle.css"

# include js, css files in header of web template
# web_include_css = "/assets/ifitwala/css/ifitwala.css"
# web_include_js = "/assets/ifitwala/js/ifitwala.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ifitwala/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}
webform_include_css = {
    "Inquiry": "public/css/admissions_webform_shell.css",
    "Registration of Interest": "public/css/admissions_webform_shell.css",
}
webform_include_js = {
    "Inquiry": "public/js/admissions_webform_shell.js",
    "Registration of Interest": "public/js/admissions_webform_shell.js",
}

# include js in page

# include js in doctype views
doctype_js = {
    "Contact": "public/js/contact.js",
    "School Website Page Block": "school_site/doctype/school_website_page_block/school_website_page_block.js",
}

standard_queries = {
    "Academic Year": "ifitwala_ed.utilities.link_queries.academic_year_global_desc_query",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# ifitwala_ed/hooks.py

website_route_rules = WEBSITE_ROUTE_RULES
website_redirects = WEBSITE_REDIRECTS


# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ifitwala/public/icons.svg"

# Home Pages
# ----------
# Force role-based entry path immediately after successful login.
on_login = "ifitwala_ed.api.users.redirect_user_to_entry_portal"
# Re-apply redirect target after session creation so Desk default path cannot override it.
on_session_creation = "ifitwala_ed.api.users.redirect_user_to_entry_portal"
# application home page (will override Website Settings)
# home_page = "/portal"

# website user home page (by Role)
role_home_page = {
    "Desk User": "/portal/staff",
    "Employee": "/portal/staff",
    "Student": "/portal/student",
    "Guardian": "/portal/guardian",
}

# Generators
# ----------

# automatically create page for each record of this doctype

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ifitwala.utils.jinja_methods",
# 	"filters": "ifitwala.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ifitwala.install.before_install"
after_install = "ifitwala_ed.setup.setup.setup_education"

# Uninstallation
# ------------

# before_uninstall = "ifitwala.uninstall.before_uninstall"
# after_uninstall = "ifitwala.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ifitwala.utils.before_app_install"
# after_app_install = "ifitwala.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ifitwala.utils.before_app_uninstall"
# after_app_uninstall = "ifitwala.utils.after_app_uninstall"

calendars = ["School Event", "School Calendar", "Leave Application"]

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ifitwala.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Contact": "ifitwala_ed.utilities.contact_utils.contact_permission_query_conditions",
    "Program Enrollment": "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_permission_query_conditions",
    "Instructor": "ifitwala_ed.schedule.doctype.instructor.instructor.get_permission_query_conditions",
    "Term": "ifitwala_ed.school_settings.doctype.term.term.get_permission_query_conditions",
    "Academic Year": "ifitwala_ed.school_settings.doctype.academic_year.academic_year.get_permission_query_conditions",
    "Student Referral": "ifitwala_ed.students.doctype.student_referral.student_referral.get_permission_query_conditions",
    "Employee": "ifitwala_ed.hr.doctype.employee.employee.get_permission_query_conditions",
    "Program Offering": "ifitwala_ed.schedule.doctype.program_offering.program_offering.get_permission_query_conditions",
    "Activity Booking": "ifitwala_ed.eca.doctype.activity_booking.activity_booking.get_permission_query_conditions",
    "Org Communication": "ifitwala_ed.setup.doctype.org_communication.org_communication.get_permission_query_conditions",
    "Leave Application": "ifitwala_ed.hr.leave_permissions.leave_application_pqc",
    "Leave Allocation": "ifitwala_ed.hr.leave_permissions.leave_allocation_pqc",
    "Leave Policy": "ifitwala_ed.hr.leave_permissions.leave_policy_pqc",
    "Leave Policy Assignment": "ifitwala_ed.hr.leave_permissions.leave_policy_assignment_pqc",
    "Leave Ledger Entry": "ifitwala_ed.hr.leave_permissions.leave_ledger_entry_pqc",
    "Leave Period": "ifitwala_ed.hr.leave_permissions.leave_period_pqc",
    "Leave Block List": "ifitwala_ed.hr.leave_permissions.leave_block_list_pqc",
    "Compensatory Leave Request": "ifitwala_ed.hr.leave_permissions.compensatory_leave_request_pqc",
    "Leave Adjustment": "ifitwala_ed.hr.leave_permissions.leave_adjustment_pqc",
    "Leave Encashment": "ifitwala_ed.hr.leave_permissions.leave_encashment_pqc",
}

has_permission = {
    "Contact": "ifitwala_ed.utilities.contact_utils.contact_has_permission",
    "Program Enrollment": "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.has_permission",
    "Instructor": "ifitwala_ed.schedule.doctype.instructor.instructor.has_permission",
    "Term": "ifitwala_ed.school_settings.doctype.term.term.has_permission",
    "Academic Year": "ifitwala_ed.school_settings.doctype.academic_year.academic_year.has_permission",
    "Student Referral": "ifitwala_ed.students.doctype.student_referral.student_referral.has_permission",
    "Employee": "ifitwala_ed.hr.doctype.employee.employee.employee_has_permission",
    "Program Offering": "ifitwala_ed.schedule.doctype.program_offering.program_offering.has_permission",
    "Activity Booking": "ifitwala_ed.eca.doctype.activity_booking.activity_booking.has_permission",
    "Org Communication": "ifitwala_ed.setup.doctype.org_communication.org_communication.has_permission",
    "Leave Application": "ifitwala_ed.hr.leave_permissions.leave_application_has_permission",
    "Leave Allocation": "ifitwala_ed.hr.leave_permissions.leave_allocation_has_permission",
    "Leave Policy": "ifitwala_ed.hr.leave_permissions.leave_policy_has_permission",
    "Leave Policy Assignment": "ifitwala_ed.hr.leave_permissions.leave_policy_assignment_has_permission",
    "Leave Ledger Entry": "ifitwala_ed.hr.leave_permissions.leave_ledger_entry_has_permission",
    "Leave Period": "ifitwala_ed.hr.leave_permissions.leave_period_has_permission",
    "Leave Block List": "ifitwala_ed.hr.leave_permissions.leave_block_list_has_permission",
    "Compensatory Leave Request": "ifitwala_ed.hr.leave_permissions.compensatory_leave_request_has_permission",
    "Leave Adjustment": "ifitwala_ed.hr.leave_permissions.leave_adjustment_has_permission",
    "Leave Encashment": "ifitwala_ed.hr.leave_permissions.leave_encashment_has_permission",
    "Leave Control Panel": "ifitwala_ed.hr.leave_permissions.leave_control_panel_has_permission",
}

default_roles = [
    {"role": "Student", "doctype": "Student", "email_field": "student_email"},
]

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
    "Contact": {"on_update": "ifitwala_ed.utilities.contact_utils.update_profile_from_contact"},
    "ToDo": {"on_update": "ifitwala_ed.admission.admission_utils.on_todo_update_close_marks_contacted"},
    "User": {
        "after_insert": "frappe.contacts.doctype.contact.contact.update_contact",
        "validate": [
            "ifitwala_ed.hr.doctype.employee.employee.validate_employee_role",
            "ifitwala_ed.hr.workspace_utils.set_default_workspace_based_on_roles",
        ],
        "on_update": "ifitwala_ed.hr.doctype.employee.employee.update_user_permissions",
    },
    "Employee": {"after_save": "ifitwala_ed.hr.employee_access.sync_user_access_from_employee"},
    "File": {
        "validate": "ifitwala_ed.utilities.file_management.validate_admissions_attachment",
        "after_insert": "ifitwala_ed.utilities.file_dispatcher.handle_file_after_insert",
        "on_update": "ifitwala_ed.utilities.file_dispatcher.handle_file_on_update",
    },
    "Student Group": {"on_update": "ifitwala_ed.schedule.schedule_utils.invalidate_for_student_group"},
    "School Calendar Holiday": {"after_insert": "ifitwala_ed.schedule.schedule_utils.invalidate_all_for_calendar"},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ifitwala.tasks.all"
# 	],
# 	"daily": [
# 		"ifitwala.tasks.daily"
# 	],
# 	"hourly": [
# 		"ifitwala.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ifitwala.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ifitwala.tasks.monthly"
# 	],
# }

scheduler_events = {
    "hourly": [
        "ifitwala_ed.admission.admission_utils.check_sla_breaches",
        "ifitwala_ed.schedule.attendance_jobs.prewarm_meeting_dates_hourly_guard",
    ],
    "daily": [
        "ifitwala_ed.students.doctype.student_log.student_log.auto_close_completed_logs",
        "ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_expired_allocation",
        "ifitwala_ed.hr.utils.allocate_earned_leaves",
        "ifitwala_ed.hr.utils.generate_leave_encashment",
    ],
}


# fixtures = [{"doctype": "Web Page"}]

# Testing
# -------

# before_tests = "ifitwala.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ifitwala.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ifitwala.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# after_request = ["ifitwala.utils.after_request"]

# Job Events
# ----------
# before_job = ["ifitwala.utils.before_job"]
# after_job = ["ifitwala.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
