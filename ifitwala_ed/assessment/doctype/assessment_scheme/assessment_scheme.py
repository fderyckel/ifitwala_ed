# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

CALCULATION_METHODS = {
    "Weighted Categories",
    "Total Points",
    "Weighted Tasks",
    "Category + Task Weight Hybrid",
    "Criteria-Based",
    "Manual Final",
}
WEIGHTED_CATEGORY_METHODS = {"Weighted Categories", "Category + Task Weight Hybrid"}


class AssessmentScheme(Document):
    def validate(self):
        if self.calculation_method not in CALCULATION_METHODS:
            frappe.throw(_("Invalid Assessment Scheme calculation method."))
        self._validate_rows()
        self._validate_active_scope()

    def _validate_rows(self):
        rows = self.get("categories") or []
        seen = set()
        active_final_total = 0.0
        active_final_count = 0

        for row in rows:
            category = (row.assessment_category or "").strip()
            if not category:
                continue
            if category in seen:
                frappe.throw(_("Duplicate Assessment Categories are not allowed in an Assessment Scheme."))
            seen.add(category)

            try:
                weight = float(row.weight or 0)
            except Exception:
                frappe.throw(_("Assessment Scheme category weights must be numeric."))
            if weight < 0:
                frappe.throw(_("Assessment Scheme category weights cannot be negative."))

            if int(row.active or 0) == 1 and int(row.include_in_final_grade or 0) == 1:
                active_final_total += weight
                active_final_count += 1

        if self.calculation_method in WEIGHTED_CATEGORY_METHODS:
            if active_final_count == 0:
                frappe.throw(_("Weighted category schemes require at least one active final-grade category."))
            if abs(active_final_total - 100.0) > 0.01:
                frappe.throw(
                    _("Weighted category schemes must total 100%. Current total: {0:.2f}%.").format(active_final_total)
                )

    def _validate_active_scope(self):
        if self.status != "Active":
            return

        existing = frappe.db.sql(
            """
            SELECT name
            FROM `tabAssessment Scheme`
            WHERE status = 'Active'
                AND school = %(school)s
                AND name != %(name)s
                AND COALESCE(academic_year, '') = %(academic_year)s
                AND COALESCE(program, '') = %(program)s
                AND COALESCE(course, '') = %(course)s
            LIMIT 1
            """,
            {
                "school": self.school,
                "name": self.name or "",
                "academic_year": (self.academic_year or "").strip(),
                "program": (self.program or "").strip(),
                "course": (self.course or "").strip(),
            },
            as_dict=True,
        )
        if existing:
            frappe.throw(_("An active Assessment Scheme already exists for this exact scope."))


def on_doctype_update():
    frappe.db.add_index("Assessment Scheme", ["school", "academic_year", "program", "course", "status"])
