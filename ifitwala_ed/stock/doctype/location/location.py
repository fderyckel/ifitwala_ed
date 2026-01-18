# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/stock/doctype/location/location.py

import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document
from ifitwala_ed.utilities.school_tree import get_ancestor_schools

class Location(Document):
	def before_insert(self):
		# Auto-inherit organization from parent (insert-time)
		self._inherit_org_from_parent()

	def validate(self):
		self.validate_capacity_against_groups()
		self._validate_org_against_parent()
		self._validate_school_organization_membership()

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

	def _validate_school_organization_membership(self):
			"""
			If a school is set:
			- Find the first ancestor school (including self) that has an Organization.
			- Auto-fill Location.organization from that if blank.
			- Else require that Location.organization is the same Org OR an ancestor
				of that Org in the Organization NestedSet.
			"""
			if not self.school:
				return

			# 1) find effective school organization up the school tree
			school_chain = get_ancestor_schools(self.school) or [self.school]
			school_org = None
			org_source_school = None

			for sch in school_chain:
				org = frappe.db.get_value("School", sch, "organization")
				if org:
					school_org = org
					org_source_school = sch
					break

			if not school_org:
				# This is a configuration error; we cannot safely validate membership.
				link = frappe.utils.get_link_to_form("School", self.school)
				frappe.throw(
					_("School {0} and its ancestor schools have no Organization set. "
						"Set an Organization on the School tree before assigning it to a Location.")
					.format(link),
					title=_("Missing School Organization"),
				)

			# 2) if Location.organization is empty → auto-fill from school_org
			if not self.organization:
				self.organization = school_org
				return

			# 3) if exact match, we are good
			if self.organization == school_org:
				return

			# 4) otherwise, require Location.organization to be an ancestor of school_org
			loc_org_row = frappe.db.get_value(
				"Organization",
				self.organization,
				["lft", "rgt"],
				as_dict=True,
			)
			school_org_row = frappe.db.get_value(
				"Organization",
				school_org,
				["lft", "rgt"],
				as_dict=True,
			)

			# If either org is misconfigured, fail loudly
			if not loc_org_row or not school_org_row:
				frappe.throw(
					_("Cannot validate Organization membership because one of the Organizations "
						"({0} or {1}) is missing or corrupted.").format(self.organization, school_org),
					title=_("Organization Tree Error"),
				)

			is_ancestor = (
				loc_org_row.lft <= school_org_row.lft
				and loc_org_row.rgt >= school_org_row.rgt
			)

			if not is_ancestor:
				school_link = frappe.utils.get_link_to_form("School", org_source_school or self.school)
				org_link = frappe.utils.get_link_to_form("Organization", self.organization)
				school_org_link = frappe.utils.get_link_to_form("Organization", school_org)

				frappe.throw(
					_(
						"Invalid School / Organization combination for this Location.<br>"
						"Selected School {school} belongs to Organization {school_org}, "
						"which is not under Organization {loc_org}."
					).format(
						school=school_link,
						school_org=school_org_link,
						loc_org=org_link,
					),
					title=_("School Does Not Belong to Organization"),
				)
