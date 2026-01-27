# ifitwala_ed/school_site/doctype/school_website_page/school_website_page.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.website.utils import normalize_route


class SchoolWebsitePage(Document):
	def validate(self):
		school_slug = frappe.db.get_value("School", self.school, "website_slug")
		if not school_slug:
			frappe.throw(
				_("School website slug is required to build routes."),
				frappe.ValidationError,
			)

		raw_route = (self.route or "").strip()
		if not raw_route or raw_route == "/":
			self.route = normalize_route(f"/{school_slug}")
			frappe.msgprint(
				_("Route is empty or '/'. This sets the root school page: {0}").format(self.route),
				alert=True,
			)
		else:
			relative = raw_route.lstrip("/").rstrip("/")
			if not relative:
				self.route = normalize_route(f"/{school_slug}")
				frappe.msgprint(
					_("Route is empty after cleanup. This sets the root school page: {0}").format(self.route),
					alert=True,
				)
			else:
				self.route = normalize_route(f"/{school_slug}/{relative}")

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
