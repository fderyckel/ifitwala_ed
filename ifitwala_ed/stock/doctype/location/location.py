# Copyright (c) 2025, fdR and contributors
# For license information, please see license.txt

# ifitwala_ed/stock/doctype/location/location.py

import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document

class Location(Document):
	def validate(self):
		self.validate_capacity_against_groups()

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
