# Copyright (c) 2025, fdR and contributors
# For license information, please see license.txt

# ifitwala_ed/stock/doctype/location/location.py

import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document

class Location(Document):
	def before_insert(self):
		# Auto-inherit organization from parent (insert-time)
		self._inherit_org_from_parent()

	def validate(self):
		self.validate_capacity_against_groups()
		self._validate_org_against_parent()

	def _inherit_org_from_parent(self):
		"""If a parent is set, adopt its organization when missing or different."""
		if not getattr(self, "parent_location", None):
			return
		parent_org = frappe.db.get_value("Location", self.parent_location, "organization")
		if not parent_org:
			# allow save but nudge: better to fix parent first
			frappe.msgprint(
				_("Parent Location {0} has no Organization set; please fix the parent.")
				.format(frappe.utils.get_link_to_form("Location", self.parent_location)),
				title=_("Parent Missing Organization"),
				indicator="orange",
			)
			return
		if not self.organization or self.organization != parent_org:
			self.organization = parent_org

	def _validate_org_against_parent(self):
		"""A child cannot have an Organization different from its parent."""
		if not getattr(self, "parent_location", None):
			return
		parent_org = frappe.db.get_value("Location", self.parent_location, "organization")
		if not parent_org:
			frappe.throw(
				_("Parent Location {0} has no Organization set. Set it on the parent first.")
				.format(frappe.utils.get_link_to_form("Location", self.parent_location)),
				title=_("Parent Missing Organization"),
			)
		if self.organization and self.organization != parent_org:
			frappe.throw(
				_("Child Location Organization must match its parent. "
				  "Parent: <b>{0}</b>, Child: <b>{1}</b>.").format(parent_org, self.organization),
				title=_("Organization Mismatch"),
			)
		# normalize to parent just in case
		self.organization = parent_org


	def validate_capacity_against_groups(self):
		"""
		Highly efficient capacity check:
		- Skip if cap <= 0 (no limit).
		- SQL join to find distinct active Student Groups that schedule this location.
		- Single GROUP BY to count active students per group.
		- Hard block if any group has active_students > cap.
		"""
		cap = cint(self.maximum_capacity or 0)
		if cap <= 0:
			return

		# 1) Get distinct active Student Groups that reference this Location in their schedule
		sg_rows = frappe.db.sql(
			"""
			SELECT DISTINCT sg.name AS name
			FROM `tabStudent Group Schedule` AS sgs
			INNER JOIN `tabStudent Group` AS sg ON sg.name = sgs.parent
			WHERE sgs.location = %s
			  AND sg.status = 'Active'
			""",
			(self.name,),
			as_dict=True,
		)
		if not sg_rows:
			return

		sg_names = [r["name"] for r in sg_rows]

		# 2) Count active students per Student Group in one grouped query
		# (Only count rows with active = 1)
		count_rows = frappe.db.sql(
			"""
			SELECT parent AS name, COUNT(*) AS active_count
			FROM `tabStudent Group Student`
			WHERE parent IN %(groups)s
			  AND COALESCE(active, 0) = 1
			GROUP BY parent
			""",
			{"groups": tuple(sg_names)},
			as_dict=True,
		)
		if not count_rows:
			return

		# 3) Any group over capacity?
		over = [(r["name"], cint(r["active_count"])) for r in count_rows if cint(r["active_count"]) > cap]
		if over:
			lines = "\n".join(f"- {sg}: active students {n} > capacity {cap}" for sg, n in over)
			frappe.throw(
				_("Cannot set maximum capacity below active enrollment for groups using this location:\n{0}").format(lines),
				title=_("Capacity Too Low"),
			)
