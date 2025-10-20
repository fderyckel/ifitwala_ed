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

app_include_js = [
  "/assets/ifitwala_ed/dist/ifitwala_ed.bundle.js",
  "/assets/ifitwala_ed/js/initial_setup.js"
]

#app_include_css = "/assets/ifitwala_ed/dist/desk_overrides.bundle.css"

# include js, css files in header of web template
# web_include_css = "/assets/ifitwala/css/ifitwala.css"
# web_include_js = "/assets/ifitwala/js/ifitwala.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ifitwala/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page

# include js in doctype views
doctype_js = {"Contact": "public/js/contact.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# ifitwala_ed/hooks.py

website_route_rules = [
    {"from_route": "/portal", "to_route": "portal"},
    {"from_route": "/portal/<path:subpath>", "to_route": "portal"},
]


# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ifitwala/public/icons.svg"

# Home Pages
# ----------
after_login = "ifitwala_ed.api.redirect_student_to_portal"
# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

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

calendars = ["School Event", "School Calendar"]

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ifitwala.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
 	"School Event": "ifitwala_ed.school_settings.doctype.school_event.school_event.get_permission_query_conditions",
  "Contact": "ifitwala_ed.utilities.contact_utils.contact_permission_query_conditions",
	"Program Enrollment": "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_permission_query_conditions",
	"Instructor": "ifitwala_ed.schedule.doctype.instructor.instructor.get_permission_query_conditions",
	"Term": "ifitwala_ed.school_settings.doctype.term.term.get_permission_query_conditions",
	"Academic Year": "ifitwala_ed.school_settings.doctype.academic_year.academic_year.get_permission_query_conditions",
	"Course": "ifitwala_ed.curriculum.doctype.course.course.get_permission_query_conditions",
	"Student Referral": "ifitwala_ed.students.doctype.student_referral.student_referral.get_permission_query_conditions",
	"Employee": "ifitwala_ed.hr.doctype.employee.employee.get_permission_query_conditions",
	"Program Offering": "ifitwala_ed.schedule.doctype.program_offering.program_offering.get_permission_query_conditions",
}

has_permission = {
	"School Event": "ifitwala_ed.school_settings.doctype.school_event.school_event.event_has_permission",
  "Contact": "ifitwala_ed.utilities.contact_utils.contact_has_permission",
	"Program Enrollment": "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.has_permission",
	"Instructor": "ifitwala_ed.schedule.doctype.instructor.instructor.has_permission",
	"Term": "ifitwala_ed.school_settings.doctype.term.term.has_permission",
	"Academic Year": "ifitwala_ed.school_settings.doctype.academic_year.academic_year.has_permission",
	"Course": "ifitwala_ed.curriculum.doctype.course.course.has_permission",
	"Student Referral": "ifitwala_ed.students.doctype.student_referral.student_referral.has_permission",
	"Employee": "ifitwala_ed.hr.doctype.employee.employee.employee_has_permission",
	"Program Offering": "ifitwala_ed.schedule.doctype.program_offering.program_offering.has_permission",
}

default_roles = [
	{'role': 'Student', 'doctype':'Student', 'email_field': 'student_email'},
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
  "Contact": {
    "on_update": "ifitwala_ed.utilities.contact_utils.update_profile_from_contact"
  },
	"ToDo": {
		"on_update": "ifitwala_ed.admission.admission_utils.on_todo_update_close_marks_contacted"
	},
  "User":{
    "after_insert": "frappe.contacts.doctype.contact.contact.update_contact",
    "validate": [
      "ifitwala_ed.hr.doctype.employee.employee.validate_employee_role",
      "ifitwala_ed.hr.workspace_utils.set_default_workspace_based_on_roles"
    ],
    "on_update": "ifitwala_ed.hr.doctype.employee.employee.update_user_permissions"
  },
  "File": {
    "after_insert": "ifitwala_ed.utilities.image_utils.handle_file_after_insert",
    "on_update": "ifitwala_ed.utilities.image_utils.handle_file_on_update"
    },
	"Student Group": {
		"on_update": "ifitwala_ed.schedule.schedule_utils.invalidate_for_student_group"
	},
	"School Calendar Holiday": {
		"after_insert": "ifitwala_ed.schedule.schedule_utils.invalidate_all_for_calendar"
	}
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
			"ifitwala_ed.schedule.attendance_jobs.prewarm_meeting_dates_hourly_guard"
		],
  "daily": [
    "ifitwala_ed.students.doctype.student_log.student_log.auto_close_completed_logs"
  ]
}



#fixtures = [{"doctype": "Web Page"}]

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
# before_request = ["ifitwala.utils.before_request"]
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

# auth_hooks = [
# 	"ifitwala.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
