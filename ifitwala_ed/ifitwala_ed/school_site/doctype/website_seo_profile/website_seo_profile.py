# ifitwala_ed/school_site/doctype/website_seo_profile/website_seo_profile.py

import frappe
from frappe import _
from frappe.model.document import Document


class WebsiteSEOProfile(Document):
	def validate(self):
		if self.meta_title and len(self.meta_title) > 60:
			frappe.throw(
				_("Meta title exceeds 60 characters."),
				frappe.ValidationError,
			)
		if self.meta_description and len(self.meta_description) > 160:
			frappe.throw(
				_("Meta description exceeds 160 characters."),
				frappe.ValidationError,
			)
