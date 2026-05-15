from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillUnitPlanProgramScope(TestCase):
    def test_execute_clears_missing_archived_and_unlinked_unit_programs(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.normalize_text = lambda value: str(value or "").strip()

        updates: list[tuple[str, str, dict[str, str | None], bool]] = []

        def get_all(doctype: str, **kwargs):
            if doctype == "Course Plan":
                return [{"name": "COURSE-PLAN-1", "course": "COURSE-1"}]
            if doctype == "Program":
                return [
                    {"name": "MYP", "archive": 0},
                    {"name": "PYP", "archive": 1},
                ]
            if doctype == "Program Course":
                return [{"parent": "MYP", "course": "COURSE-1"}]
            if doctype == "Unit Plan":
                return [
                    {"name": "UNIT-VALID", "course_plan": "COURSE-PLAN-1", "course": "COURSE-1", "program": "MYP"},
                    {
                        "name": "UNIT-ARCHIVED",
                        "course_plan": "COURSE-PLAN-1",
                        "course": "COURSE-1",
                        "program": "PYP",
                    },
                    {
                        "name": "UNIT-MISSING",
                        "course_plan": "COURSE-PLAN-1",
                        "course": "COURSE-1",
                        "program": "DP",
                    },
                    {
                        "name": "UNIT-UNLINKED",
                        "course_plan": "COURSE-PLAN-1",
                        "course": "COURSE-OTHER",
                        "program": "MYP",
                    },
                    {
                        "name": "UNIT-FALLBACK-COURSE",
                        "course_plan": "COURSE-PLAN-1",
                        "course": "",
                        "program": "MYP",
                    },
                ]
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.planning": planning}) as frappe:
            frappe.db.table_exists = lambda doctype: (
                doctype in {"Unit Plan", "Program", "Program Course", "Course Plan"}
            )
            frappe.get_all = get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_unit_plan_program_scope")

            module.execute()

        self.assertEqual(
            updates,
            [
                ("Unit Plan", "UNIT-ARCHIVED", {"program": None}, False),
                ("Unit Plan", "UNIT-MISSING", {"program": None}, False),
                ("Unit Plan", "UNIT-UNLINKED", {"program": None}, False),
            ],
        )

    def test_execute_returns_when_required_tables_are_missing(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.normalize_text = lambda value: str(value or "").strip()

        with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.planning": planning}) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_unit_plan_program_scope")

            module.execute()
