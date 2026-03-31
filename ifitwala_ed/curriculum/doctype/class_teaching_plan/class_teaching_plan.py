# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.curriculum import planning


class ClassTeachingPlan(Document):
    def before_validate(self):
        self.course_plan = planning.normalize_text(self.course_plan)
        self.student_group = planning.normalize_text(self.student_group)
        self.team_note = planning.normalize_long_text(self.team_note)

    def validate(self):
        course_plan = planning.get_course_plan_row(self.course_plan)
        group = planning.get_student_group_row(self.student_group)

        if planning.normalize_text(group.get("course")) != planning.normalize_text(course_plan.get("course")):
            frappe.throw(_("The selected class does not belong to the selected course plan."))

        duplicate = frappe.db.exists(
            "Class Teaching Plan",
            {
                "course_plan": self.course_plan,
                "student_group": self.student_group,
                "name": ["!=", self.name],
            },
        )
        if duplicate:
            frappe.throw(_("This class already has a teaching plan for the selected course plan."))

        self.course = course_plan.get("course")
        self.academic_year = group.get("academic_year")
        self.title = planning.build_class_teaching_plan_title(group, course_plan)

        planning.sync_class_teaching_plan_units(self)
