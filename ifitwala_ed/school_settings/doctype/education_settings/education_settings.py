# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import frappe.defaults
from frappe.model.document import Document

# education_keydict = {
# 	# "key in defaults": "key in Global Defaults"
# 	"academic_year": "current_academic_year",
# 	"term": "current_term",
# 	"validate_course": "validate_course",
# 	"school": "default_school",
# 	"meeting_color": "meeting_color",
# 	"weekend_color": "weekend_color",
# 	"break_color": "break_color",
# 	"todo_color": "todo_color"
# }

class EducationSettings(Document):
	pass

	# def on_update(self):
	# 	"""Update defaults when the document is updated."""
	# 	for key in education_keydict:
	# 		# Set the default value in the database for each key
	# 		frappe.db.set_default(key, self.get(education_keydict[key], ''))

	# 	# Clear the cache to ensure the changes take effect
	# 	frappe.clear_cache()

	# def get_defaults(self):
	# 	"""Retrieve the current default values."""
	# 	return frappe.defaults.get_defaults()

def update_website_context(context):
	context["cms_enabled"] = frappe.get_doc("Education Settings").enable_cms