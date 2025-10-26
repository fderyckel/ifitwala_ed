# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

# ifitwala_ed/curriculum/doctype/program/program.py

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.utils import cint


FLOAT_EPS = 1e-6

class Program(NestedSet):
	nsm_parent_field = "parent_program"

	def validate(self):
		self._validate_duplicate_course()
		self._validate_active_courses()
		self._validate_assessment_scheme_flags()
		self._validate_program_assessment_categories()

	def _validate_duplicate_course(self):
		seen = set()
		for row in self.courses or []:
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

	def _validate_assessment_scheme_flags(self):
		"""Only one scheme may be selected among points / criteria / binary."""
		flags = [cint(self.points), cint(self.criteria), cint(self.binary)]
		if sum(flags) > 1:
			frappe.throw(_("Select only one assessment scheme: either Points, or Criteria, or Binary."))
		# If you want to require exactly one scheme, keep the check below; otherwise remove it.
		if sum(flags) == 0:
			frappe.throw(_("Select one assessment scheme for this Program (Points, Criteria, or Binary)."))

	def _validate_program_assessment_categories(self):
		"""
		Child table: Program Assessment Category
		Rules:
		  - No duplicate 'assessment_category'
		  - Each 'default_weight' must be between 0 and 100 (inclusive)
		  - Sum of weights across ACTIVE rows ≤ 100
		  - If 'points' is checked: require ≥1 active row and total == 100 (±epsilon)
		  - If 'binary' is checked: disallow any rows with weight > 0 (suggest zero rows)
		"""
		rows = self.get("assessment_categories") or []

		# Early exits by scheme:
		use_points = cint(self.points) == 1
		use_criteria = cint(self.criteria) == 1
		use_binary = cint(self.binary) == 1

		# Deduplicate and per-row checks
		seen = set()
		active_total = 0.0
		bad_rows = []
		neg_rows = []
		over_rows = []
		nonzero_when_binary = []

		for r in rows:
			cat = (r.assessment_category or "").strip()
			weight = float(r.default_weight or 0)
			active = cint(r.active) == 1

			# Duplicate category guard
			if cat:
				if cat in seen:
					bad_rows.append((r.idx, cat))
				else:
					seen.add(cat)

			# Range checks
			if weight < 0 - FLOAT_EPS:
				neg_rows.append(r.idx)
			if weight > 100 + FLOAT_EPS:
				over_rows.append(r.idx)

			# Scheme-specific aggregation
			if active:
				active_total += weight

			if use_binary and weight > 0 + FLOAT_EPS:
				nonzero_when_binary.append(r.idx)

		if bad_rows:
			lines = "\n".join([f"Row {idx}: {cat}" for idx, cat in bad_rows])
			frappe.throw(_("Duplicate Assessment Categories are not allowed:\n{0}").format(lines))

		if neg_rows:
			frappe.throw(_("Default Weight cannot be negative (rows: {0}).").format(", ".join(map(str, neg_rows))))
		if over_rows:
			frappe.throw(_("Default Weight cannot exceed 100 (rows: {0}).").format(", ".join(map(str, over_rows))))

		# Totals by scheme
		if use_points:
			# Must have at least one active row
			if not any(cint(r.active) == 1 for r in rows):
				frappe.throw(_("With Points selected, add at least one active Program Assessment Category."))
			# Total must be 100 (±epsilon)
			if abs(active_total - 100.0) > 0.0001:
				frappe.throw(_("With Points selected, the total of active category weights must equal 100 (current total: {0:.2f}).").format(active_total))
		else:
			# Non-points schemes: just ensure we don't exceed 100
			if active_total > 100.0 + 0.0001:
				frappe.throw(_("Total of active category weights must not exceed 100 (current total: {0:.2f}).").format(active_total))

		if use_binary:
			# Binary scheme shouldn't carry weighted categories
			if nonzero_when_binary:
				frappe.throw(_("With Binary selected, category weights must all be 0 (rows: {0}).").format(", ".join(map(str, nonzero_when_binary))))



@frappe.whitelist()
def inherit_assessment_categories(program: str, overwrite: int = 1):
	"""Copy parent's Program Assessment Category rows into this Program (overwrites by default)."""
	if not program:
		frappe.throw(_("Program is required."))

	doc = frappe.get_doc("Program", program)

	if not doc.parent_program:
		frappe.throw(_("This Program has no Parent Program set."))

	parent = frappe.get_doc("Program", doc.parent_program)
	parent_rows = parent.get("assessment_categories") or []  # this field now options: Program Assessment Category
	if not parent_rows:
		frappe.throw(_("Parent Program <b>{0}</b> has no Program Assessment Categories to inherit.").format(parent.name))

	# De-dup by Assessment Category link
	seen = set()
	clean_rows = []
	for r in parent_rows:
		cat = (r.assessment_category or "").strip()
		if not cat or cat in seen:
			continue
		seen.add(cat)
		clean_rows.append({
			"assessment_category": r.assessment_category,
			"default_weight": r.default_weight,
			"color_override": r.color_override,
			"active": int(r.active or 0),
		})

	if not clean_rows:
		frappe.throw(_("Nothing to import after cleaning duplicates / empty rows."))

	# Overwrite current child table
	if int(overwrite or 0):
		doc.set("assessment_categories", [])

	for row in clean_rows:
		doc.append("assessment_categories", row)

	doc.save(ignore_permissions=False)

	return {
		"parent": parent.name,
		"added": len(clean_rows),
		"total": len(doc.get("assessment_categories") or [])
	}
