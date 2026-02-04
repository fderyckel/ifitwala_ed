# ifitwala_ed/school_site/doctype/website_story/website_story.py

import frappe
from frappe import _
from frappe.model.document import Document


class WebsiteStory(Document):
	def validate(self):
		self._validate_status()
		self._validate_unique_slug()

	def _validate_status(self):
		status = (self.status or "").strip() or "Draft"
		if status not in {"Draft", "Published"}:
			frappe.throw(
				_("Invalid status: {0}").format(status),
				frappe.ValidationError,
			)
		self.status = status

	def _validate_unique_slug(self):
		exists = frappe.db.exists(
			"Website Story",
			{
				"school": self.school,
				"slug": self.slug,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(
				_("A story with this slug already exists for this school."),
				frappe.ValidationError,
			)
