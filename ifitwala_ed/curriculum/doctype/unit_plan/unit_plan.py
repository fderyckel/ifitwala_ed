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
        planning.ensure_linked_unit_plan_standards(self)

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


@frappe.whitelist()
def get_learning_standard_picker(
    framework_name: str | None = None,
    program: str | None = None,
    strand: str | None = None,
    substrand: str | None = None,
    search_text: str | None = None,
):
    filters = {}
    framework_name = planning.normalize_text(framework_name)
    program = planning.normalize_text(program)
    strand = planning.normalize_text(strand)
    substrand = planning.normalize_text(substrand)
    search_text = planning.normalize_text(search_text)

    if framework_name:
        filters["framework_name"] = framework_name
    if program:
        filters["program"] = program
    if strand:
        filters["strand"] = strand
    if substrand and substrand != "[No Substrand]":
        filters["substrand"] = substrand

    rows = frappe.get_list(
        "Learning Standards",
        filters=filters,
        fields=[
            "name",
            "framework_name",
            "framework_version",
            "subject_area",
            "program",
            "strand",
            "substrand",
            "standard_code",
            "standard_description",
            "alignment_type",
        ],
        order_by="framework_name asc, program asc, strand asc, substrand asc, standard_code asc",
        limit=0,
    )
    if substrand == "[No Substrand]":
        rows = [row for row in rows if not planning.normalize_text(row.get("substrand"))]

    if search_text:
        needle = search_text.lower()
        rows = [
            row
            for row in rows
            if needle in planning.normalize_text(row.get("standard_code")).lower()
            or needle in planning.normalize_text(row.get("standard_description")).lower()
        ]

    frameworks = sorted(
        {
            planning.normalize_text(row.get("framework_name"))
            for row in rows
            if planning.normalize_text(row.get("framework_name"))
        }
    )
    programs = sorted(
        {planning.normalize_text(row.get("program")) for row in rows if planning.normalize_text(row.get("program"))}
    )
    strands = sorted(
        {planning.normalize_text(row.get("strand")) for row in rows if planning.normalize_text(row.get("strand"))}
    )
    substrands = sorted(
        {planning.normalize_text(row.get("substrand")) for row in rows if planning.normalize_text(row.get("substrand"))}
    )
    has_blank_substrand = any(not planning.normalize_text(row.get("substrand")) for row in rows)

    standards = [
        {
            "learning_standard": row.get("name"),
            "framework_name": row.get("framework_name"),
            "framework_version": row.get("framework_version"),
            "subject_area": row.get("subject_area"),
            "program": row.get("program"),
            "strand": row.get("strand"),
            "substrand": row.get("substrand"),
            "standard_code": row.get("standard_code"),
            "standard_description": row.get("standard_description"),
            "alignment_type": row.get("alignment_type"),
        }
        for row in rows
    ]

    return {
        "filters": {
            "framework_name": framework_name or None,
            "program": program or None,
            "strand": strand or None,
            "substrand": substrand or None,
            "search_text": search_text or None,
        },
        "options": {
            "frameworks": frameworks,
            "programs": programs,
            "strands": strands,
            "substrands": substrands,
            "has_blank_substrand": has_blank_substrand,
        },
        "standards": standards,
    }
