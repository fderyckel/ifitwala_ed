# -*- coding: utf-8 -*-
# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.website.website_generator import WebsiteGenerator
from frappe.utils.nestedset import NestedSet
from frappe import _dict

class Program(NestedSet):

	def validate(self):
		self.validate_duplicate_course()

	def validate_duplicate_course(self):
		found = []
		for course in self.courses:
			doc = frappe.get_doc("Course", course.course)
			if doc.status != "Active":
				frappe.throw(_("Course {0} has been discontinued. It cannot be part of this program or set up this course as active.").format(course.course))

			if course.course in found:
				frappe.throw(_("Course {0} is entered twice. Please remove one of them.").format(course.course))
			else:
				found.append(course.course)
	

	class Program(WebsiteGenerator):
		website_generator = "program_slug" 
	
		website = _dict(
			template = "templates/generators/program.html",
			condition_field = "is_published",
			page_title_field = "program_name",
  	)	
		def get_context(self, context):
			# disable caching so editors see changes immediately
			context.no_cache = True

			# basics
			context.title = self.program_name
			context.program = self  # so your template can do {{ program.program_overview }}

			# breadcrumbs
			crumbs = []
			# top‐level “Programs” landing page
			crumbs.append({"name": "/programs", "title": "Programs"})

			# any parent programs
			parent = self.parent_program
			while parent:
				p = frappe.get_doc("Program", parent)
				crumbs.append({"name": f"/program/{p.program_slug}", "title": p.program_name})
				parent = p.parent_program

			context.parents = crumbs

			# if this is a group, list its children
			context.children = []
			if self.is_group:
				for child in self.get_children():
					doc = frappe.get_doc("Program", child.name)
					context.children.append(doc)

			return context