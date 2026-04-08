# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.curriculum import planning


class ClassSession(Document):
    def before_validate(self):
        self.class_teaching_plan = planning.normalize_text(self.class_teaching_plan)
        self.unit_plan = planning.normalize_text(self.unit_plan)
        self.title = planning.normalize_text(self.title)
        self.learning_goal = planning.normalize_long_text(self.learning_goal)
        self.teacher_note = planning.normalize_long_text(self.teacher_note)

    def validate(self):
        teaching_plan = frappe.db.get_value(
            "Class Teaching Plan",
            self.class_teaching_plan,
            ["name", "course_plan", "student_group", "course", "academic_year"],
            as_dict=True,
        )
        if not teaching_plan:
            frappe.throw(_("Class Teaching Plan not found."))

        allowed_unit = frappe.db.exists(
            "Class Teaching Plan Unit",
            {
                "parent": self.class_teaching_plan,
                "parenttype": "Class Teaching Plan",
                "parentfield": "units",
                "unit_plan": self.unit_plan,
            },
        )
        if not allowed_unit:
            frappe.throw(_("This class session must belong to the governed unit backbone for the class teaching plan."))

        self.student_group = teaching_plan.get("student_group")
        self.course_plan = teaching_plan.get("course_plan")
        self.course = teaching_plan.get("course")
        self.academic_year = teaching_plan.get("academic_year")

        if not int(self.sequence_index or 0):
            self.sequence_index = planning.next_session_sequence(self.class_teaching_plan, self.unit_plan)
