# ifitwala_ed/school_site/doctype/website_snippet/website_snippet.py

import frappe
from frappe import _
from frappe.model.document import Document


class WebsiteSnippet(Document):
	def validate(self):
		scope = (self.scope_type or "").strip() or "Global"
		if scope not in {"Global", "Organization", "School"}:
			frappe.throw(
				_("Invalid scope type: {0}").format(scope),
				frappe.ValidationError,
			)
		self.scope_type = scope

		if scope == "Global":
			self.organization = None
			self.school = None
			return

		if scope == "Organization":
			if not self.organization:
				frappe.throw(
					_("Organization is required for Organization-scoped snippets."),
					frappe.ValidationError,
				)
			self.school = None
			return

		if not self.school:
			frappe.throw(
				_("School is required for School-scoped snippets."),
				frappe.ValidationError,
			)
