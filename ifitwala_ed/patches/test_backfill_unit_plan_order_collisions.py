from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillUnitPlanOrderCollisions(TestCase):
    def test_execute_moves_only_later_collisions_to_next_available_slots(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        next_order_calls: list[str] = []

        def _next_unit_order(course_plan: str) -> int:
            next_order_calls.append(course_plan)
            return {1: 30, 2: 40}[len(next_order_calls)]

        planning.next_unit_order = _next_unit_order
        updates: list[tuple[str, str, dict[str, int], bool]] = []

        with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.planning": planning}) as frappe:
            frappe.db.table_exists = lambda doctype: doctype == "Unit Plan"
            frappe.get_all = lambda doctype, **kwargs: [
                {"name": "UNIT-1", "course_plan": "COURSE-PLAN-1", "unit_order": 10},
                {"name": "UNIT-2", "course_plan": "COURSE-PLAN-1", "unit_order": 10},
                {"name": "UNIT-3", "course_plan": "COURSE-PLAN-1", "unit_order": 20},
                {"name": "UNIT-4", "course_plan": "COURSE-PLAN-1", "unit_order": 20},
                {"name": "UNIT-5", "course_plan": "COURSE-PLAN-2", "unit_order": 10},
            ]
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_unit_plan_order_collisions")

            module.execute()

        self.assertEqual(next_order_calls, ["COURSE-PLAN-1", "COURSE-PLAN-1"])
        self.assertEqual(
            updates,
            [
                ("Unit Plan", "UNIT-2", {"unit_order": 30}, False),
                ("Unit Plan", "UNIT-4", {"unit_order": 40}, False),
            ],
        )

    def test_execute_returns_when_unit_plan_table_is_missing(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.next_unit_order = lambda course_plan: 10

        with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.planning": planning}) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when Unit Plan table is missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_unit_plan_order_collisions")

            module.execute()
