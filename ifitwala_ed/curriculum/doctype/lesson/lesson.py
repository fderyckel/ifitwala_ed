# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

# ifitwala_ed/curriculum/doctype/lesson/lesson.py
import frappe
from frappe.model.document import Document

_STEP = 10

def _next_lesson_order(learning_unit: str) -> int:
	max_order = frappe.db.sql(
		"select coalesce(max(lesson_order), 0) from `tabLesson` where learning_unit=%s",
		(learning_unit,),
		as_list=True,
	)[0][0]
	return int(max_order) + _STEP

class Lesson(Document):
	def before_insert(self):
		# If no lesson_order provided, append at the end (spaced by 10)
		if not int(self.lesson_order or 0):
			self.lesson_order = _next_lesson_order(self.learning_unit)

	def before_save(self):
		# Normalize empty/zero to next slot
		if not int(self.lesson_order or 0):
			self.lesson_order = _next_lesson_order(self.learning_unit)
			return

		# Guard against collisions within the same learning unit
		if self.learning_unit:
			exists = frappe.db.exists(
				"Lesson",
				{
					"learning_unit": self.learning_unit,
					"lesson_order": self.lesson_order,
					"name": ["!=", self.name],
				},
			)
			if exists:
				self.lesson_order = _next_lesson_order(self.learning_unit)

@frappe.whitelist()
def reorder_lessons(learning_unit: str, lesson_names):
	"""
	Bulk reorder Lessons for a Learning Unit in a single transaction.

	Args:
		learning_unit (str): Learning Unit name
		lesson_names (list|str): Ordered list of Lesson names. If str, JSON is parsed.

	Raises:
		frappe.PermissionError: if user lacks write permission on the Learning Unit.
		frappe.ValidationError: on duplicates, unknown lessons, or mismatched mapping.

	Returns:
		dict: {"updated": <count>, "order_step": 10}
	"""
	# Parse and validate payload
	if isinstance(lesson_names, str):
		lesson_names = frappe.parse_json(lesson_names)  # expects a JSON array of names

	if not isinstance(lesson_names, (list, tuple)) or not lesson_names:
		frappe.throw("lesson_names must be a non-empty list of Lesson names.", frappe.ValidationError)

	# Permission: require write on the Learning Unit
	if not frappe.has_permission("Learning Unit", ptype="write", doc=learning_unit):
		frappe.throw("Not permitted to reorder lessons for this learning unit.", frappe.PermissionError)

	# Duplicates check
	if len(lesson_names) != len(set(lesson_names)):
		frappe.throw("Duplicate Lesson names in payload.", frappe.ValidationError)

	# Fetch existing lessons for this learning unit
	existing = frappe.db.get_all(
		"Lesson",
		filters={"learning_unit": learning_unit},
		fields=["name"],
		pluck="name",
	)
	existing_set = set(existing)

	# Ensure payload lessons match existing (strict mode)
	payload_set = set(lesson_names)
	if existing_set != payload_set:
		missing = ", ".join(sorted(existing_set - payload_set)) or "-"
		extra = ", ".join(sorted(payload_set - existing_set)) or "-"
		frappe.throw(
			f"Lesson list mismatch.\nMissing in payload: {missing}\nNot in unit: {extra}",
			frappe.ValidationError,
		)

	# Prepare spaced order values (10,20,30…)
	values = [(name, (idx + 1) * _STEP) for idx, name in enumerate(lesson_names)]

	# Bulk update in one transaction
	frappe.db.bulk_update(
		"Lesson",
		fields=["lesson_order"],
		values=values,
	)

	return {"updated": len(values), "order_step": _STEP}
