# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.nestedset import get_descendants_of

from ifitwala_ed.curriculum import planning


class UnitPlan(Document):
    def before_validate(self):
        self.title = planning.normalize_text(self.title)
        self.course_plan = planning.normalize_text(self.course_plan)
        self.program = planning.normalize_text(getattr(self, "program", None)) or None
        self.unit_code = planning.normalize_text(getattr(self, "unit_code", None)) or None
        self.version = planning.normalize_text(getattr(self, "version", None)) or None
        self.duration = planning.normalize_text(getattr(self, "duration", None)) or None
        self.estimated_duration = planning.normalize_text(getattr(self, "estimated_duration", None)) or None
        self.overview = planning.normalize_long_text(self.overview)
        self.essential_understanding = planning.normalize_long_text(self.essential_understanding)
        self.misconceptions = planning.normalize_long_text(getattr(self, "misconceptions", None))
        self.content = planning.normalize_long_text(getattr(self, "content", None))
        self.skills = planning.normalize_long_text(getattr(self, "skills", None))
        self.concepts = planning.normalize_long_text(getattr(self, "concepts", None))

    def before_insert(self):
        if not int(self.unit_order or 0):
            self.unit_order = planning.next_unit_order(self.course_plan)

    def validate(self):
        course_plan = planning.get_course_plan_row(self.course_plan)
        self.course = course_plan.get("course")
        self.school = course_plan.get("school")

        if not int(self.unit_order or 0):
            self.unit_order = planning.next_unit_order(self.course_plan)
        elif frappe.db.exists(
            "Unit Plan",
            {
                "course_plan": self.course_plan,
                "unit_order": self.unit_order,
                "name": ["!=", self.name],
            },
        ):
            self.unit_order = planning.next_unit_order(self.course_plan)

        duplicate = frappe.db.exists(
            "Unit Plan",
            {
                "course_plan": self.course_plan,
                "title": self.title,
                "name": ["!=", self.name],
            },
        )
        if duplicate:
            frappe.throw(_("This course plan already has a unit with the same title."))

    def after_insert(self):
        planning.sync_all_class_teaching_plans(self.course_plan)

    def on_update(self):
        planning.sync_all_class_teaching_plans(self.course_plan)


@frappe.whitelist()
def get_program_subtree_scope(program: str):
    program = planning.normalize_text(program)
    if not program:
        frappe.throw(_("Program is required."), frappe.ValidationError)

    descendants = get_descendants_of("Program", program) or []
    return [program, *descendants]
