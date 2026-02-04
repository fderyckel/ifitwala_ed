# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from frappe.utils.nestedset import NestedSet


class PGPGoal(NestedSet):
	def autoname(self):
		# Generate the title based on the hierarchical structure
		self.title = self.generate_title()

		# Set the name based on the title
		self.name = self.title.lower().replace(" ", "-").replace("/", "-")

	def generate_title(self):
		# Top-Level Goal (No Parent)
		if not self.parent_pgp_goal:
			# Count top-level goals for this PGP Template context
			goal_count = frappe.db.count("PGP Goal", filters={"parent_pgp_goal": ""})
			return f"Goal-{goal_count + 1} - {self.goal_name}"

		# Sub-Goal or Milestone (Has a Parent)
		parent_goal = frappe.get_doc("PGP Goal", self.parent_pgp_goal)

		# Determine the label based on the parent's title
		if "/" in parent_goal.title:
			# This is a milestone (grandchild)
			child_count = frappe.db.count("PGP Goal", filters={"parent_goal": self.parent_pgp_goal})
			return f"{parent_goal.title}/Milestone-{child_count + 1} - {self.goal_name}"
		else:
			# This is a sub-goal (child)
			child_count = frappe.db.count("PGP Goal", filters={"parent_goal": self.parent_pgp_goal})
			return f"{parent_goal.title}/Sub-Goal-{child_count + 1} - {self.goal_name}"

	def validate(self):
		# Ensure the goal is assigned to the correct designations and departments
		self.validate_applicable_roles()

	def validate_applicable_roles(self):
		# Ensure at least one designation or department is linked, if specified
		if not self.applicable_designations and not self.applicable_departments:
			frappe.throw(_("At least one designation or department must be linked to this goal."))

		# Check for conflicting roles
		if self.applicable_designations and self.applicable_departments:
			frappe.msgprint(_("This goal is linked to both designations and departments, which may cause conflicts. Please review."))

