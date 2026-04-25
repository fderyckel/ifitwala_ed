# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/reporting_cycle/reporting_cycle.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class ReportingCycle(Document):
    def validate(self):
        # Basic uniqueness: one cycle per (school, academic_year, term, program, name_label)
        if self.school and self.academic_year and self.term:
            filters = [
                ["Reporting Cycle", "school", "=", self.school],
                ["Reporting Cycle", "academic_year", "=", self.academic_year],
                ["Reporting Cycle", "term", "=", self.term],
            ]
            if self.program:
                filters.append(["Reporting Cycle", "program", "=", self.program])
            if self.name_label:
                filters.append(["Reporting Cycle", "name_label", "=", self.name_label])
            if self.name:
                filters.append(["Reporting Cycle", "name", "!=", self.name])

            exists = frappe.get_all("Reporting Cycle", filters=filters, limit=1)
            if exists:
                frappe.throw(
                    _(
                        "A Reporting Cycle with the same School, Academic Year, Term and Program/Name already exists ({0})."
                    ).format(exists[0].name)
                )

        if self.status in ("Locked", "Published") and not self.teacher_edit_close:
            frappe.throw(_("Instructor edit close must be set before locking or publishing."))

        if self.status in ("Open", "Calculated", "Locked", "Published") and not self.task_cutoff_date:
            frappe.throw(_("Task Cutoff Date must be set before opening a reporting cycle."))

        self._validate_assessment_scheme_scope()

    def _validate_assessment_scheme_scope(self):
        if not getattr(self, "assessment_scheme", None):
            return

        scheme = frappe.db.get_value(
            "Assessment Scheme",
            self.assessment_scheme,
            ["school", "academic_year", "program", "course", "status"],
            as_dict=True,
        )
        if not scheme:
            frappe.throw(_("Assessment Scheme was not found."))
        if scheme.get("status") == "Retired":
            frappe.throw(_("Retired Assessment Schemes cannot be used for Reporting Cycles."))
        if scheme.get("school") and self.school and scheme.get("school") != self.school:
            frappe.throw(_("Assessment Scheme must belong to the same School as the Reporting Cycle."))
        if scheme.get("academic_year") and self.academic_year and scheme.get("academic_year") != self.academic_year:
            frappe.throw(_("Assessment Scheme must belong to the same Academic Year as the Reporting Cycle."))
        if scheme.get("program") and not self.program:
            frappe.throw(_("Program-specific Assessment Schemes require a Program-specific Reporting Cycle."))
        if scheme.get("program") and self.program and scheme.get("program") != self.program:
            frappe.throw(_("Assessment Scheme must belong to the same Program as the Reporting Cycle."))
        if scheme.get("course"):
            frappe.throw(
                _(
                    "Course-specific Assessment Schemes are resolved during calculation, not selected on Reporting Cycle."
                )
            )

    @frappe.whitelist()
    def recalculate_course_results(self):
        frappe.enqueue(
            "ifitwala_ed.assessment.term_reporting.recalculate_course_term_results",
            reporting_cycle=self.name,
            queue="long",
        )
        return {"queued": True}

    @frappe.whitelist()
    def generate_student_reports(self):
        from ifitwala_ed.assessment import term_reporting

        return term_reporting.generate_student_term_reports(self.name)


def on_doctype_update():
    # Helpful for querying cycles by scope
    frappe.db.add_index("Reporting Cycle", ["school", "academic_year", "term", "program"])
