# ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.py

import frappe
from frappe import _
from frappe.model.document import Document


class ProgramWebsiteProfile(Document):
	def validate(self):
		self._sync_status_from_program()
		self._validate_unique_profile()
		self._validate_program_slug()

	def _sync_status_from_program(self):
		if not self.program:
			return
		is_published = frappe.db.get_value("Program", self.program, "is_published")
		self.status = "Published" if int(is_published or 0) == 1 else "Draft"

	def _validate_unique_profile(self):
		exists = frappe.db.exists(
			"Program Website Profile",
			{
				"program": self.program,
				"school": self.school,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(
				_("A Program Website Profile already exists for this Program and School."),
				frappe.ValidationError,
			)

	def _validate_program_slug(self):
		if self.status != "Published":
			return
		program_slug = frappe.db.get_value("Program", self.program, "program_slug")
		if not program_slug:
			frappe.throw(
				_("Program slug is required before publishing a Program Website Profile."),
				frappe.ValidationError,
			)
