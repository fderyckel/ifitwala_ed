# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.py

import frappe

_STEP = 10  # spacing (10, 20, 30…)

@frappe.whitelist()
def reorder_lesson_activities(lesson: str, activity_names):
	"""
	Bulk reorder Lesson Activity child rows for a given Lesson in one transaction.

	Args:
		lesson (str): Parent Lesson name.
		activity_names (list|str): Ordered list of Lesson Activity docnames (child rows).
		                           If str, must be a JSON array of names.

	Returns:
		dict: {"updated": <count>, "order_step": 10}

	Raises:
		frappe.PermissionError: if user lacks write on the Lesson.
		frappe.ValidationError: on invalid payload (duplicates/mismatch).
	"""
	# Parse JSON payload if needed
	if isinstance(activity_names, str):
		activity_names = frappe.parse_json(activity_names)

	if not isinstance(activity_names, (list, tuple)) or not activity_names:
		frappe.throw("activity_names must be a non-empty list of Lesson Activity names.", frappe.ValidationError)

	# Permission: require write on the parent Lesson
	if not frappe.has_permission("Lesson", ptype="write", doc=lesson):
		frappe.throw("Not permitted to reorder activities for this Lesson.", frappe.PermissionError)

	# Duplicates check
	if len(activity_names) != len(set(activity_names)):
		frappe.throw("Duplicate Lesson Activity names in payload.", frappe.ValidationError)

	# Fetch existing child rows for this parent lesson
	existing_names = frappe.db.get_all(
		"Lesson Activity",
		filters={"parent": lesson, "parenttype": "Lesson", "parentfield": "activities"},
		pluck="name",
	)

	existing_set = set(existing_names)
	payload_set  = set(activity_names)

	# Ensure payload exactly matches existing set (strict mode)
	if existing_set != payload_set:
		missing = ", ".join(sorted(existing_set - payload_set)) or "-"
		extra   = ", ".join(sorted(payload_set - existing_set)) or "-"
		frappe.throw(
			f"Activity list mismatch.\nMissing in payload: {missing}\nNot in this lesson: {extra}",
			frappe.ValidationError,
		)

	# Prepare spaced order values (10,20,30…)
	values = [(name, (idx + 1) * _STEP) for idx, name in enumerate(activity_names)]

	# Bulk update child table in one go
	frappe.db.bulk_update(
		"Lesson Activity",
		fields=["order"],  # child field is named `order`
		values=values,
	)

	return {"updated": len(values), "order_step": _STEP}
