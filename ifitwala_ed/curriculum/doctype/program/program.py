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
		# Keep existing validations
		self._validate_duplicate_course()
		self._validate_active_courses()

		# New/updated validations for assessment model
		self._apply_default_colors_for_assessment_categories()
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

	# ──────────────────────────────────────────────────────────────────────────────
	# Assessment Categories (Program Assessment Category child)
	# We ALLOW multiple schemes together (points/binary/criteria/feedback).
	# We ONLY enforce weight math when Points is enabled.
	# ──────────────────────────────────────────────────────────────────────────────

	def _apply_default_colors_for_assessment_categories(self):
		"""For any row missing color_override, pull the color from the master
		Assessment Category (field: assessment_category_color) in one batch.
		"""
		rows = self.get("assessment_categories") or []
		missing = [r.assessment_category.strip() for r in rows
		           if getattr(r, "assessment_category", None)
		           and not getattr(r, "color_override", None)]
		if not missing:
			return

		# Batch fetch colors from master doctype
		masters = frappe.get_all(
			"Assessment Category",
			filters={"name": ["in", list(set(missing))]},
			fields=["name", "assessment_category_color"],
		)
		color_map = {m.name: (m.assessment_category_color or "") for m in masters}

		for r in rows:
			cat = (r.assessment_category or "").strip()
			if cat and not r.color_override:
				default_color = color_map.get(cat, "")
				if default_color:
					r.color_override = default_color

	def _validate_program_assessment_categories(self):
		rows = self.get("assessment_categories") or []

		points_on = cint(self.points) == 1
		# criteria_on  = cint(self.criteria) == 1  # allowed concurrently
		# binary_on    = cint(self.binary)   == 1  # allowed concurrently
		# feedback_on  = (cint(self.observations) == 1) if your flag becomes 'feedback'

		# Per-row checks + duplicate guard
		seen = set()
		active_total = 0.0
		neg_rows, over_rows, dup_rows = [], [], []

		for r in rows:
			cat = (r.assessment_category or "").strip()
			weight = float(r.default_weight or 0)
			active = cint(r.active) == 1

			# duplicate category guard
			if cat:
				if cat in seen:
					dup_rows.append((r.idx, cat))
				else:
					seen.add(cat)

			# 0..100 guard per row (weight field itself should be sane)
			if weight < 0 - FLOAT_EPS:
				neg_rows.append(r.idx)
			if weight > 100 + FLOAT_EPS:
				over_rows.append(r.idx)

			# Only meaningful when Points is enabled, but we sum now;
			# enforcement happens below.
			if active:
				active_total += weight

		if dup_rows:
			lines = "\n".join([f"Row {idx}: {cat}" for idx, cat in dup_rows])
			frappe.throw(_("Duplicate Assessment Categories are not allowed:\n{0}").format(lines))
		if neg_rows:
			frappe.throw(_("Default Weight cannot be negative (rows: {0}).").format(", ".join(map(str, neg_rows))))
		if over_rows:
			frappe.throw(_("Default Weight cannot exceed 100 (rows: {0}).").format(", ".join(map(str, over_rows))))

		# Weight math ONLY enforced if Points is enabled
		if points_on:
			has_active = any(cint(r.active) == 1 for r in rows)
			if not has_active:
				frappe.throw(_("With Points enabled, add at least one active Assessment Category with a weight."))

			if active_total > 100.0 + 0.0001:
				frappe.throw(_("For Points, the total of active category weights must not exceed 100 (current total: {0:.2f}).")
				             .format(active_total))

			# If you want exact 100 when publishing later, enforce in on_submit or before_publish hook.
			# Example (not enabled here):
			# if cint(self.is_published) and abs(active_total - 100.0) > 0.0001:
			#     frappe.throw(_("Published Programs using Points must total exactly 100 (current total: {0:.2f}).").format(active_total))


@frappe.whitelist()
def inherit_assessment_categories(program: str, overwrite: int = 1):
	"""Copy parent's Program Assessment Category rows into this Program (overwrites by default)."""
	if not program:
		frappe.throw(_("Program is required."))

	doc = frappe.get_doc("Program", program)

	if not doc.parent_program:
		frappe.throw(_("This Program has no Parent Program set."))

	parent = frappe.get_doc("Program", doc.parent_program)
	parent_rows = parent.get("assessment_categories") or []  # Program Assessment Category
	if not parent_rows:
		frappe.throw(_("Parent Program <b>{0}</b> has no Program Assessment Categories to inherit.").format(parent.name))

	# De-dup by Assessment Category link while copying
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
