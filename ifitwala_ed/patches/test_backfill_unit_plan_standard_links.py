from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillUnitPlanStandardLinks(TestCase):
    def test_execute_relinks_only_unambiguous_legacy_rows(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.LEARNING_STANDARD_CATALOG_FIELDS = (
            "framework_name",
            "framework_version",
            "subject_area",
            "program",
            "strand",
            "substrand",
            "standard_code",
            "standard_description",
            "alignment_type",
        )
        planning.normalize_text = lambda value: str(value or "").strip()
        planning.normalize_long_text = lambda value: str(value or "").strip() or None

        updates: list[tuple[str, str, dict[str, str | None], bool]] = []

        def get_all(doctype: str, **kwargs):
            if doctype == "Learning Standards":
                return [
                    {
                        "name": "STD-NGSS-1",
                        "framework_name": "NGSS",
                        "framework_version": None,
                        "subject_area": None,
                        "program": None,
                        "strand": "Life Science",
                        "substrand": None,
                        "standard_code": "NG-1",
                        "standard_description": "Describe cell function.",
                        "alignment_type": "Knowledge",
                    },
                    {
                        "name": "STD-ELA-1",
                        "framework_name": "Common Core ELA",
                        "framework_version": None,
                        "subject_area": None,
                        "program": None,
                        "strand": "Reading",
                        "substrand": None,
                        "standard_code": "CC-1",
                        "standard_description": "Analyze evidence in a text.",
                        "alignment_type": "Skill",
                    },
                    {
                        "name": "STD-MATH-1",
                        "framework_name": "Common Core Math",
                        "framework_version": None,
                        "subject_area": None,
                        "program": None,
                        "strand": "Algebra",
                        "substrand": None,
                        "standard_code": "CC-1",
                        "standard_description": "Solve linear equations.",
                        "alignment_type": "Skill",
                    },
                ]
            if doctype == "Learning Unit Standard Alignment":
                return [
                    {
                        "name": "ALIGN-VALID",
                        "learning_standard": "STD-NGSS-1",
                        "standard_code": "NG-1",
                        "framework_name": "NGSS",
                        "strand": "Life Science",
                        "standard_description": "Describe cell function.",
                        "alignment_type": "Knowledge",
                    },
                    {
                        "name": "ALIGN-CODE-ID",
                        "learning_standard": "NG-1",
                        "standard_code": "",
                        "framework_name": "",
                        "strand": "",
                        "standard_description": "",
                        "alignment_type": "",
                    },
                    {
                        "name": "ALIGN-NARROWED",
                        "learning_standard": "",
                        "standard_code": "CC-1",
                        "framework_name": "Common Core ELA",
                        "strand": "Reading",
                        "standard_description": "Analyze evidence in a text.",
                        "alignment_type": "Skill",
                    },
                    {
                        "name": "ALIGN-AMBIGUOUS",
                        "learning_standard": "",
                        "standard_code": "CC-1",
                        "framework_name": "",
                        "strand": "",
                        "standard_description": "",
                        "alignment_type": "",
                    },
                    {
                        "name": "ALIGN-UNKNOWN",
                        "learning_standard": "legacy-missing",
                        "standard_code": "MISSING",
                        "framework_name": "",
                        "strand": "",
                        "standard_description": "",
                        "alignment_type": "",
                    },
                ]
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.planning": planning}) as frappe:
            frappe.db.table_exists = lambda doctype: (
                doctype in {"Learning Unit Standard Alignment", "Learning Standards"}
            )
            frappe.get_all = get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_unit_plan_standard_links")

            module.execute()

        self.assertEqual(
            updates,
            [
                (
                    "Learning Unit Standard Alignment",
                    "ALIGN-CODE-ID",
                    {
                        "learning_standard": "STD-NGSS-1",
                        "framework_name": "NGSS",
                        "framework_version": None,
                        "subject_area": None,
                        "program": None,
                        "strand": "Life Science",
                        "substrand": None,
                        "standard_code": "NG-1",
                        "standard_description": "Describe cell function.",
                        "alignment_type": "Knowledge",
                    },
                    False,
                ),
                (
                    "Learning Unit Standard Alignment",
                    "ALIGN-NARROWED",
                    {
                        "learning_standard": "STD-ELA-1",
                        "framework_name": "Common Core ELA",
                        "framework_version": None,
                        "subject_area": None,
                        "program": None,
                        "strand": "Reading",
                        "substrand": None,
                        "standard_code": "CC-1",
                        "standard_description": "Analyze evidence in a text.",
                        "alignment_type": "Skill",
                    },
                    False,
                ),
            ],
        )

    def test_execute_returns_when_required_tables_are_missing(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.LEARNING_STANDARD_CATALOG_FIELDS = ("standard_code",)
        planning.normalize_text = lambda value: str(value or "").strip()
        planning.normalize_long_text = lambda value: str(value or "").strip() or None

        with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.planning": planning}) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_unit_plan_standard_links")

            module.execute()
