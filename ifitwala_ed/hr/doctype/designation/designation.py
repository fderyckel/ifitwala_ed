# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from frappe.utils.nestedset import get_ancestors_of

class Designation(Document):
	def validate(self):
		self.validate_reports_to_hierarchy()

	def validate_reports_to_hierarchy(self):
		if not self.reports_to:
			return
			
		# Step 1: Prevent self-reporting
		if self.reports_to == self.name:
			frappe.throw(
				_(f"A designation cannot report to itself: {get_link_to_form('Designation', self.name)}.")
			)
			
		# Step 2: Prevent direct loops (A → B → A)
		reports_to_data = frappe.db.get_value(
			"Designation",
			self.reports_to,
			["organization", "reports_to", "archived"],
			as_dict=True
		)
			
		# Prevent direct loop
		if reports_to_data.get("reports_to") == self.name:
			frappe.throw(
				_(f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} cannot report back to {get_link_to_form('Designation', self.name)}, creating a direct loop.")
			)
			
		# Step 3: Organizational Lineage Check (Using Organization NestedSet)
		current_org = self.organization
		reports_to_org = reports_to_data.get("organization")
			
		# Fetch all parent organizations for the current organization
		valid_orgs = get_ancestors_of("Organization", current_org) or []
		valid_orgs.append(current_org)  # Include the current organization itself
			
		if reports_to_org not in valid_orgs:
			frappe.throw(
				_(f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} belongs to a different organizational lineage than the current designation's organization '{current_org}' ({get_link_to_form('Organization', current_org)}).")
			)
			
		# Step 4: Prevent reporting to an archived designation
		if reports_to_data.get("archived"):
			frappe.throw(
				_(f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} is archived and cannot be assigned as a supervisor.")
			)
			
		# Step 5: Indirect Loop Prevention (Multi-Level)
		if check_indirect_loop(self.name, self.reports_to):
			frappe.throw(
				_(f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} would create a circular reporting loop with {get_link_to_form('Designation', self.name)}.")
			)

	def check_indirect_loop(start_designation, target_designation):
		"""
		Recursively check if assigning the target_designation as a supervisor
		would create a multi-level loop.	
		"""
		current = target_designation
			
		while current:
			# Get the next level up
			next_supervisor = frappe.db.get_value("Designation", current, "reports_to")
					
			# If we loop back to the start, we have a problem
			if next_supervisor == start_designation:
				return True
					
			# Move up the hierarchy
			current = next_supervisor
			
		return False
