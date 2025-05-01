# -*- coding: utf-8 -*-
# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.website.website_generator import WebsiteGenerator

class Program(WebsiteGenerator, NestedSet):

	website_generator = "program_slug"

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