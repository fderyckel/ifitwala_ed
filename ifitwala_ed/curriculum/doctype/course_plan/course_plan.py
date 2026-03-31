# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.model.document import Document

from ifitwala_ed.curriculum import planning


class CoursePlan(Document):
    def before_validate(self):
        self.title = planning.normalize_text(self.title)
        self.course = planning.normalize_text(self.course)
        self.academic_year = planning.normalize_text(self.academic_year) or None
        self.cycle_label = planning.normalize_text(self.cycle_label) or None
        self.summary = planning.normalize_long_text(self.summary)
        if not self.title and self.course:
            self.title = self.course

    def validate(self):
        if not self.title and self.course:
            self.title = self.course
