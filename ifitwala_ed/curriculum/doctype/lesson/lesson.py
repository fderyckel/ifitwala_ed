# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

# ifitwala_ed/curriculum/doctype/lesson/lesson.py

import frappe
from frappe import _
from frappe.model.document import Document

ORDER_STEP = 10


class Lesson(Document):
    pass


@frappe.whitelist()
def reorder_lessons(unit_plan: str, lesson_names):
    if isinstance(lesson_names, str):
        lesson_names = frappe.parse_json(lesson_names)

    if not isinstance(lesson_names, (list, tuple)) or not lesson_names:
        frappe.throw(_("lesson_names must be a non-empty list of Lesson names."), frappe.ValidationError)

    if not frappe.has_permission("Unit Plan", ptype="write", doc=unit_plan):
        frappe.throw(_("Not permitted to reorder lessons for this unit plan."), frappe.PermissionError)

    if len(lesson_names) != len(set(lesson_names)):
        frappe.throw(_("Duplicate Lesson names in payload."), frappe.ValidationError)

    existing = frappe.db.get_all(
        "Lesson",
        filters={"unit_plan": unit_plan},
        fields=["name"],
        pluck="name",
    )
    existing_set = set(existing)
    payload_set = set(lesson_names)
    if existing_set != payload_set:
        missing = ", ".join(sorted(existing_set - payload_set)) or "-"
        extra = ", ".join(sorted(payload_set - existing_set)) or "-"
        frappe.throw(
            _("Lesson list mismatch.\nMissing in payload: {missing}\nNot in unit plan: {extra}").format(
                missing=missing,
                extra=extra,
            ),
            frappe.ValidationError,
        )

    values = [(name, (idx + 1) * ORDER_STEP) for idx, name in enumerate(lesson_names)]
    frappe.db.bulk_update(
        "Lesson",
        fields=["lesson_order"],
        values=values,
    )
    return {"updated": len(values), "order_step": ORDER_STEP}
