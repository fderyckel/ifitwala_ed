# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.nestedset import get_descendants_of, get_ancestors_of
from frappe.utils import get_link_to_form

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
		
		# Prevent self-reporting
		if self.reports_to == self.name:
			frappe.throw(
				_(f"A designation cannot report to itself: {get_link_to_form('Designation', self.name)}.")
			)
		
		# Batch fetch organization, reports_to, and archived status in one call
		reports_to_data = frappe.db.get_value(
			"Designation",
			self.reports_to,
			["organization", "reports_to", "archived"],
			as_dict=True
		)
		
		# Prevent direct loops (A reports to B, B reports to A)
		if reports_to_data.get("reports_to") == self.name:
			frappe.throw(
				_(f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} cannot report back to {get_link_to_form('Designation', self.name)}, creating a direct loop.")
			)
		
		# Check if the 'reports_to' is in the same organization or a parent organization
		current_org = self.organization
		reports_to_org = reports_to_data.get("organization")
		
		# Fetch all parent organizations once
		parent_orgs = get_ancestors_of("Organization", current_org) or []
		parent_orgs.append(current_org)  # Include the current organization itself
		
		if reports_to_org not in parent_orgs:
			frappe.throw(
				_(f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} belongs to a different organization '{reports_to_org}' that is not a parent or sibling of the current designation's organization '{current_org}' ({get_link_to_form('Organization', current_org)}).")
			)
		
		# Prevent reporting to an archived designation
		if reports_to_data.get("archived"):
			frappe.throw(
				_(f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} is archived and cannot be assigned as a supervisor.")
			)