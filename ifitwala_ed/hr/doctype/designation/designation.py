# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.nestedset import get_descendants_of, get_ancestors_of

class Designation(Document):
	def validate(self):
		self.validate_school_organization_relationship()
		self.validate_reports_to_hierarchy()

	def validate_school_organization_relationship(self):
		if not self.organization or not self.school:
			return
		
		# Fetch the full organization tree
		valid_organizations = get_descendants_of("Organization", self.organization) or []
		valid_organizations.append(self.organization)  # Include the selected organization itself
		
		# Fetch the parent organization of the selected school
		school_org = frappe.get_value("School", self.school, "organization")
		
		if school_org not in valid_organizations:
			frappe.throw(
				_(f"The selected school '{self.school}' does not belong to the organization '{self.organization}'.")
			)

	def validate_reports_to_hierarchy(self):
		if not self.reports_to:
			return
		
		# Ensure the 'reports_to' designation is not a descendant of the current designation
		current_designation_ancestors = get_ancestors_of("Designation", self.name) or []
		if self.reports_to in current_designation_ancestors:
			frappe.throw(
				_(f"The selected 'Reports to' designation '{self.reports_to}' creates a hierarchy loop.")
			)

		# Check if the reports_to designation is in the same organization tree
		reports_to_org = frappe.get_value("Designation", self.reports_to, "organization")
		if reports_to_org != self.organization:
			frappe.throw(
				_(f"The selected 'Reports to' designation '{self.reports_to}' belongs to a different organization '{reports_to_org}' than the current designation '{self.organization}'.")
			)