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
		self.validate_default_role()

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
				_(f"This designation {get_link_to_form('Designation', self.reports_to)} is reporting to a designation that belongs to a different organizational lineage than the current designation's organization '{current_org}' ({get_link_to_form('Organization', current_org)}).")
			)

		# Step 4: Prevent reporting to an archived designation
		if reports_to_data.get("archived"):
			frappe.throw(
				_(f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} is archived and cannot be assigned as a supervisor.")
			)

		# Step 5: Indirect Loop Prevention (Multi-Level)
		if self._check_indirect_loop(self.name, self.reports_to):
			frappe.throw(
				_(f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} would create a circular reporting loop with {get_link_to_form('Designation', self.name)}.")
			)

	def validate_default_role(self):
		if not self.default_role_profile:
			return

		disallowed = {"System Manager", "Administrator", "Guest", "All"}
		if self.default_role_profile in disallowed:
			frappe.throw(
				_("This role cannot be assigned via Designation.")
			)

	def _check_indirect_loop(self, start_designation, target_designation):
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


@frappe.whitelist()
def get_valid_parent_organizations(organization):
    """
    Return the full parent hierarchy for a given organization,
    including the organization itself.
    """
    if not organization:
        frappe.throw(_("Organization is required"))

    # Fetch all parent organizations
    valid_orgs = get_ancestors_of("Organization", organization) or []
    valid_orgs.append(organization)  # Include the current organization itself

    return valid_orgs


@frappe.whitelist()
def get_assignable_roles(doctype, txt, searchfield, start, page_len, filters):
	# Curated Role list for Link field dropdown (search + pagination)

	excluded_roles = ("System Manager", "Administrator", "Guest", "All")

	# Frappe passes these as strings sometimes
	start = int(start or 0)
	page_len = int(page_len or 20)
	txt = (txt or "").strip()

	role_filters = [["name", "not in", excluded_roles]]
	if txt:
		role_filters.append(["name", "like", f"%{txt}%"])

	return frappe.db.get_all(
		"Role",
		filters=role_filters,
		fields=["name"],
		order_by="name asc",
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,  # return list-of-lists for link queries
	)
