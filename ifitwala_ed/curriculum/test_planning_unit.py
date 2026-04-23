from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


class FakeUnitDoc:
    def __init__(self, rows):
        self.standards = rows

    def get(self, fieldname):
        return getattr(self, fieldname)

    def set(self, fieldname, value):
        setattr(self, fieldname, value)


class TestPlanningUnit(TestCase):
    def test_ensure_linked_unit_plan_standards_rewrites_snapshot_from_linked_catalog_row(self):
        student_groups = types.ModuleType("ifitwala_ed.api.student_groups")
        student_groups._instructor_group_names = lambda user: []

        html_sanitizer = types.ModuleType("ifitwala_ed.utilities.html_sanitizer")
        html_sanitizer.sanitize_html = lambda value, **kwargs: value

        def get_all(doctype: str, **kwargs):
            if doctype == "Learning Standards":
                self.assertEqual(kwargs.get("filters"), {"name": ["in", ["STD-1"]]})
                return [
                    {
                        "name": "STD-1",
                        "framework_name": "NGSS",
                        "framework_version": None,
                        "subject_area": None,
                        "program": None,
                        "strand": "Life Science",
                        "substrand": None,
                        "standard_code": "NG-1",
                        "standard_description": "Describe cell function.",
                        "alignment_type": "Knowledge",
                    }
                ]
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.api.student_groups": student_groups,
                "ifitwala_ed.utilities.html_sanitizer": html_sanitizer,
            }
        ) as frappe:
            frappe.get_all = get_all
            frappe.db.get_value = lambda *args, **kwargs: None
            module = import_fresh("ifitwala_ed.curriculum.planning")

            doc = FakeUnitDoc(
                [
                    {
                        "name": "ALIGN-ROW-1",
                        "learning_standard": "STD-1",
                        "framework_name": "Wrong Framework",
                        "standard_code": "WRONG",
                        "coverage_level": "Introduced",
                        "alignment_strength": "Exact",
                        "notes": "Use during the first lab.",
                    }
                ]
            )

            module.ensure_linked_unit_plan_standards(doc)

        self.assertEqual(
            doc.standards,
            [
                {
                    "learning_standard": "STD-1",
                    "framework_name": "NGSS",
                    "framework_version": None,
                    "subject_area": None,
                    "program": None,
                    "strand": "Life Science",
                    "substrand": None,
                    "standard_code": "NG-1",
                    "standard_description": "Describe cell function.",
                    "alignment_type": "Knowledge",
                    "coverage_level": "Introduced",
                    "alignment_strength": "Exact",
                    "notes": "Use during the first lab.",
                }
            ],
        )

    def test_ensure_linked_unit_plan_standards_rejects_broken_link_without_self_heal(self):
        student_groups = types.ModuleType("ifitwala_ed.api.student_groups")
        student_groups._instructor_group_names = lambda user: []

        html_sanitizer = types.ModuleType("ifitwala_ed.utilities.html_sanitizer")
        html_sanitizer.sanitize_html = lambda value, **kwargs: value

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.api.student_groups": student_groups,
                "ifitwala_ed.utilities.html_sanitizer": html_sanitizer,
            }
        ) as frappe:
            frappe.get_all = lambda doctype, **kwargs: []
            frappe.db.get_value = lambda *args, **kwargs: None
            module = import_fresh("ifitwala_ed.curriculum.planning")

            doc = FakeUnitDoc(
                [
                    {
                        "name": "ALIGN-ROW-2",
                        "learning_standard": "broken-link-value",
                        "framework_name": "IB MYP",
                        "program": "MYP",
                        "strand": "Identity",
                        "substrand": "Narrative",
                        "standard_code": "MYP-1",
                        "standard_description": "Analyze how narrative voice shapes meaning.",
                        "alignment_type": "Skill",
                        "coverage_level": "Introduced",
                    }
                ]
            )

            with self.assertRaisesRegex(StubValidationError, "Re-select it from the picker"):
                module.ensure_linked_unit_plan_standards(doc)
