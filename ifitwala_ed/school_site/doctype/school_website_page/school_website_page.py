# ifitwala_ed/school_site/doctype/school_website_page/school_website_page.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.website.utils import normalize_route


class SchoolWebsitePage(Document):
	def validate(self):
		if not self.route or not str(self.route).startswith("/"):
			frappe.throw(
				_("Route must start with '/'."),
				frappe.ValidationError,
			)

		normalized = normalize_route(self.route)
		if normalized != self.route:
			self.route = normalized

		exists = frappe.db.exists(
			"School Website Page",
			{
				"school": self.school,
				"route": self.route,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(
				_("A page already exists for this school and route."),
				frappe.ValidationError,
			)
