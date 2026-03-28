# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

LEGACY_COURSE_WEBSITE_BLOCKS = {"course_intro", "learning_highlights"}
BLOCK_TYPE_VALIDATION_RE = re.compile(r'Block Type cannot be "([^"]+)"')


class Course(Document):
    def validate(self):
        self.validate_criteria_weighting()
        self.validate_duplicate_criteria()

    def after_insert(self):
        self._sync_default_website_profile()

    def on_update(self):
        if any(
            self.has_value_changed(fieldname)
            for fieldname in (
                "is_published",
                "school",
                "course_image",
                "description",
                "term_long",
            )
        ):
            self._sync_default_website_profile()

    def validate_duplicate_criteria(self):
        """Ensure no Assessment Criteria appears more than once on this course."""
        seen = set()
        for row in self.assessment_criteria or []:
            if not row.assessment_criteria:
                continue
            if row.assessment_criteria in seen:
                frappe.throw(
                    _("Assessment Criteria {0} appears more than once. Please remove duplicate entries.").format(
                        row.assessment_criteria
                    )
                )
            seen.add(row.assessment_criteria)

    def validate_criteria_weighting(self):
        """Ensure that total weighting over all criteria sums to 100% (with tolerance)."""
        if not self.assessment_criteria:
            return

        total_weight = 0.0
        for row in self.assessment_criteria:
            total_weight += float(row.criteria_weighting or 0)

        # Tolerance to avoid float weirdness (e.g. 99.999999 vs 100)
        if abs(total_weight - 100.0) > 0.001:
            frappe.throw(
                _(
                    "The sum of the Criteria Weighting is {0:.2f}%. It must be exactly 100%. Please adjust and try again."
                ).format(total_weight)
            )

    def get_learning_units(self):
        lu_data = []
        for unit in self.units:
            unit_doc = frappe.get_doc("Learning Unit", unit.learning_unit)
            if unit_doc.unit_name:
                lu_data.append(unit_doc)
        # lu_data = lu_data.sort(key=lambda x: x.start_date)
        return lu_data

    def _sync_default_website_profile(self):
        if int(self.is_published or 0) != 1 or not (self.school or "").strip():
            return

        from ifitwala_ed.website.bootstrap import ensure_default_course_website_profile

        try:
            ensure_default_course_website_profile(course_name=self.name)
        except frappe.ValidationError as exc:
            self._raise_course_website_profile_guidance(exc)

    def _raise_course_website_profile_guidance(self, exc: Exception):
        match = BLOCK_TYPE_VALIDATION_RE.search(cstr(exc))
        block_type = match.group(1).strip() if match else ""
        if block_type not in LEGACY_COURSE_WEBSITE_BLOCKS:
            raise exc

        frappe.throw(
            _(
                "Course cannot be published yet because the default Course Website Profile template is outdated. "
                "It is trying to use the legacy website block type '{0}', which this site no longer accepts. "
                "Ask a Website Manager or System Manager to update the Course Website Profile block configuration, "
                "then publish this Course again."
            ).format(block_type),
            title=_("Course Publish Blocked"),
            exc=frappe.ValidationError,
        )


@frappe.whitelist()
def add_course_to_programs(course, programs, mandatory=False):
    programs = json.loads(programs)
    for entry in programs:
        program = frappe.get_doc("Program", entry)
        program.append("courses", {"course": course, "course_name": course, "required": mandatory})
        program.flags.ignore_mandatory = True
        program.save()
    frappe.db.commit()
    frappe.msgprint(
        _("The Course {0} has been added to all the selected programs successfully.").format(frappe.bold(course)),
        title=_("Programs updated"),
        indicator="green",
    )


@frappe.whitelist()
def get_programs_without_course(course: str):
    """Return list of Program names that do NOT already include this course."""
    if not course:
        return []

    # All programs that already have this course via Program Course child table
    programs_with_course = frappe.get_all(
        "Program Course",
        filters={"course": course},
        pluck="parent",
        distinct=True,
    )

    # All other programs
    filters = {}
    if programs_with_course:
        filters["name"] = ["not in", programs_with_course]

    programs = frappe.get_all("Program", filters=filters, pluck="name")

    return programs
