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
		self.ensure_unique_members()
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

	def ensure_unique_members(self):
		seen = set()
		duplicates = []
		for d in self.members or []:
			member = d.member
			if not member:
				continue
			if member in seen:
				duplicates.append(d.member_name or d.member)
			else:
				seen.add(member)

		if duplicates:
			names = ", ".join(frappe.bold(name) for name in duplicates)
			frappe.throw(
				_("The following members are already part of this team: {0}. Remove duplicates before saving.").format(names)
			)


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
