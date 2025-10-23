# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet

class Program(NestedSet):
	nsm_parent_field = "parent_program"

	def validate(self):
		self._validate_duplicate_course()
		self._validate_active_courses()

	def _validate_duplicate_course(self):
		seen = set()
		for row in self.courses:
			if row.course in seen:
				frappe.throw(_("Course {0} entered twice").format(row.course))
			seen.add(row.course)

	def _validate_active_courses(self):
		# Batch fetch statuses to minimize DB calls
		names = [r.course for r in (self.courses or []) if r.course]
		if not names:
			return

		rows = frappe.get_all("Course", filters={"name": ["in", names]}, fields=["name", "status"])
		status_by_name = {r.name: (r.status or "") for r in rows}

		inactive = []
		for row in self.courses or []:
			if not row.course:
				continue
			st = status_by_name.get(row.course, "")
			if st != "Active":
				inactive.append((row.idx, row.course, st or "Unknown"))

		if inactive:
			lines = "\n".join([f"Row {idx}: {name} (status: {st})" for idx, name, st in inactive])
			frappe.throw(_("Only Active Courses can be added:\n{0}").format(lines))


@frappe.whitelist()
def inherit_assessment_categories(program: str, overwrite: int = 1):
	"""Copy parent's Assessment Categories into this Program (overwrites by default)."""
	if not program:
		frappe.throw(_("Program is required."))

	doc = frappe.get_doc("Program", program)

	if not doc.parent_program:
		frappe.throw(_("This Program has no Parent Program set."))

	parent = frappe.get_doc("Program", doc.parent_program)
	parent_rows = parent.get("assessment_categories") or []
	if not parent_rows:
		frappe.throw(_("Parent Program <b>{0}</b> has no Assessment Categories to inherit.").format(parent.name))

	# Build a normalized set to avoid duplicates within the parent list itself
	seen = set()
	clean_rows = []
	for r in parent_rows:
		key = (r.assessment_category or "").strip().lower()
		if not key:
			# skip empty names quietly
			continue
		if key in seen:
			# skip duplicate names coming from parent (child table has unique on field anyway)
			continue
		seen.add(key)
		clean_rows.append({
			"assessment_category": r.assessment_category,
			# keep the exact fieldname as in your child doctype (note the spelling)
			"asessment_category_color": r.asessment_category_color,
			"default_weight": r.default_weight
		})

	if not clean_rows:
		frappe.throw(_("Nothing to import after cleaning duplicates / empty rows."))

	# Overwrite current child table
	if cint(overwrite):
		doc.set("assessment_categories", [])

	for row in clean_rows:
		doc.append("assessment_categories", row)

	# Save once to minimize DB round-trips
	doc.save(ignore_permissions=False)

	return {
		"parent": parent.name,
		"added": len(clean_rows),
		"total": len(doc.get("assessment_categories") or [])
	}
