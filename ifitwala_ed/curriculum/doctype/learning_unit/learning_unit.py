# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

_STEP = 10


def _next_unit_order(course: str) -> int:
    max_order = frappe.db.sql(
        "select coalesce(max(unit_order), 0) from `tabLearning Unit` where course=%s",
        (course,),
        as_list=True,
    )[0][0]
    return int(max_order) + _STEP


class LearningUnit(Document):
    def before_insert(self):
        # If no unit_order provided, append at the end (spaced by 10)
        if not int(self.unit_order or 0):
            self.unit_order = _next_unit_order(self.course)

    def before_save(self):
        # Normalize empty/zero to next slot
        if not int(self.unit_order or 0):
            self.unit_order = _next_unit_order(self.course)
            return

        # Guard against collisions within the same course
        if self.course:
            exists = frappe.db.exists(
                "Learning Unit",
                {
                    "course": self.course,
                    "unit_order": self.unit_order,
                    "name": ["!=", self.name],
                },
            )
            if exists:
                self.unit_order = _next_unit_order(self.course)


@frappe.whitelist()
def reorder_learning_units(course: str, unit_names):
    """
    Bulk reorder Learning Units for a course in a single transaction.

    Args:
            course (str): Course name
            unit_names (list|str): Ordered list of Learning Unit names. If str, JSON is parsed.

    Raises:
            frappe.PermissionError: if user lacks write permission on Course.
            frappe.ValidationError: on duplicates, unknown units, or mismatched course mapping.

    Returns:
            dict: {"updated": <count>, "order_step": 10}
    """
    # Parse and validate payload
    if isinstance(unit_names, str):
        unit_names = frappe.parse_json(unit_names)  # expects a JSON array of names

    if not isinstance(unit_names, (list, tuple)) or not unit_names:
        frappe.throw("unit_names must be a non-empty list of Learning Unit names.", frappe.ValidationError)

    # Permission: require write on the Course (or equivalent role permissions)
    if not frappe.has_permission("Course", ptype="write", doc=course):
        frappe.throw("Not permitted to reorder units for this course.", frappe.PermissionError)

    # Duplicates check
    if len(unit_names) != len(set(unit_names)):
        frappe.throw("Duplicate Learning Unit names in payload.", frappe.ValidationError)

    # Fetch existing units for this course
    existing = frappe.db.get_all(
        "Learning Unit",
        filters={"course": course},
        fields=["name"],
        pluck="name",
    )
    existing_set = set(existing)

    # Ensure payload units match existing (strict mode)
    payload_set = set(unit_names)
    if existing_set != payload_set:
        # Help the caller with specifics
        missing = ", ".join(sorted(existing_set - payload_set)) or "-"
        extra = ", ".join(sorted(payload_set - existing_set)) or "-"
        frappe.throw(
            f"Unit list mismatch.\nMissing in payload: {missing}\nNot in course: {extra}",
            frappe.ValidationError,
        )

    # Prepare spaced order values (10,20,30…)
    values = [(name, (idx + 1) * _STEP) for idx, name in enumerate(unit_names)]

    # Bulk update in one transaction
    frappe.db.bulk_update(
        "Learning Unit",
        fields=["unit_order"],
        values=values,
    )

    return {"updated": len(values), "order_step": _STEP}
