# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.website.website_generator import WebsiteGenerator
#from frappe.utils.nestedset import NestedSet
from frappe import _dict

class Program(WebsiteGenerator):
	route = "program"  # => /program/<slug>
	page_name_field = "program_slug"
	page_title_field = "program_name"
	condition_field = "is_published"  # must be checked to publish
	template = "templates/generators/program.html"

	def validate(self):
		super().validate()
		# your duplicate‐course guard
		self.validate_duplicate_course()
		# ensure route is recalculated on every save
		self.set_route()

	def validate_duplicate_course(self):
		seen = set()
		for row in self.courses:
			if row.course in seen:
				frappe.throw(_("Course {0} entered twice").format(row.course))
			seen.add(row.course)

	# plain vanilla context: just prove the route works
	def get_context(self, context):
		context.no_cache = True
		context.message  = "Hello World from Program!"			
		return context