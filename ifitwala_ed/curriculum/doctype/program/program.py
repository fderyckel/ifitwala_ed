# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.website.website_generator import WebsiteGenerator
#from frappe.utils.nestedset import NestedSet
from frappe import _dict

class Program(WebsiteGenerator):
	# we’ll hard-code the route ourselves,
	# so WebsiteGenerator won’t try to be clever.
	condition_field = "is_published"       # honour the publish flag

	# ------------------------------------------------------------------
	def before_save(self):
		"""Always set route = 'program/<slug>' (or name fallback)."""
		self.route = f"program/{self.program_slug or self.name}"

	def after_save(self):
		"""Ensure a Website Route row exists for this document."""
		if not self.is_published:
			return  # don’t publish if flag is off

		route_name = frappe.db.get_value(
			"Website Route",
			{"ref_doctype": self.doctype, "docname": self.name},
			"name",
		)

		if route_name:
			# update existing row if route changed
			frappe.db.set_value("Website Route", route_name, "route", self.route)
		else:
			# insert a fresh Website Route
			frappe.get_doc({
				"doctype":      "Website Route Meta",
				"route":        self.route,
				"ref_doctype":  self.doctype,
				"docname":      self.name,
				"page_title":   self.program_name,
			}).insert(ignore_permissions=True)

	def get_context(self, context):
		# nothing fancy—just prove it renders
		context.no_cache = True
		context.greeting = "Hello World! Routing works 🎉"

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
