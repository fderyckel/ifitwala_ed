# ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.py

import frappe
from frappe import _
from frappe.model.document import Document


class ProgramWebsiteProfile(Document):
	def validate(self):
		self._validate_status()
		self._validate_unique_profile()
		self._validate_program_slug()

	def _validate_status(self):
		status = (self.status or "").strip() or "Draft"
		if status not in {"Draft", "Published"}:
			frappe.throw(
				_("Invalid status: {0}").format(status),
				frappe.ValidationError,
			)
		self.status = status

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
