# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/team/team.py

import frappe
from frappe import _
from frappe.model.document import Document

class Team(Document):

	def validate(self):
		self.ensure_minimum_members()
		self.check_parent_team_loop()
		self.validate_members_status()
		# other validations as needed

	def ensure_minimum_members(self):
		members = [d for d in (self.members or []) if d.active]
		if len(members) < 2:
			frappe.throw(_("A team must have at least 2 active members."))

	def check_parent_team_loop(self):
		if self.parent_team:
			parent = self.parent_team
			seen = set()
			while parent:
				if parent == self.name:
					frappe.throw(_("Circular parent_team reference detected."))
				if parent in seen:
					frappe.throw(_("Circular parent_team chain detected."))
				seen.add(parent)
				parent = frappe.db.get_value("Team", parent, "parent_team")

	def validate_members_status(self):
		for d in self.members or []:
			if d.active not in (0, 1):
				frappe.throw(_("Invalid status for member {0}.").format(d.member_name or d.member))


@frappe.whitelist()
def get_eligible_users(school, organization):
	"""Return enabled users whose linked Employee record belongs
	to the given school and organization."""
	sql = """
		SELECT u.name as value, u.full_name as label
		FROM `tabUser` u
		JOIN `tabEmployee` e ON e.user_id = u.name
		WHERE e.school = %(school)s
		AND e.organization = %(organization)s
		AND u.enabled = 1
	"""
	return frappe.db.sql(sql, {"school": school, "organization": organization}, as_dict=1)
