from __future__ import annotations

import types
from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


class TestUnitPlanRuntime(TestCase):
    def test_validate_rejects_duplicate_unit_order_in_same_course_plan(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.normalize_text = lambda value: str(value or "").strip()
        planning.normalize_long_text = lambda value: value
        planning.get_course_plan_row = lambda course_plan: {"course": "COURSE-1", "school": "SCH-1"}
        planning.ensure_linked_unit_plan_standards = Mock()
        planning.next_unit_order = Mock(return_value=30)

        nestedset = types.ModuleType("frappe.utils.nestedset")
        nestedset.get_descendants_of = lambda doctype, name: []

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning,
                "frappe.utils.nestedset": nestedset,
            }
        ) as frappe:

            def _exists(doctype, filters=None):
                if doctype != "Unit Plan":
                    return None
                if filters == {
                    "course_plan": "COURSE-PLAN-1",
                    "unit_order": 20,
                    "name": ["!=", "UNIT-PLAN-1"],
                }:
                    return "UNIT-PLAN-2"
                if filters == {
                    "course_plan": "COURSE-PLAN-1",
                    "title": "Cells and Systems",
                    "name": ["!=", "UNIT-PLAN-1"],
                }:
                    return None
                return None

            frappe.db.exists = _exists
            module = import_fresh("ifitwala_ed.curriculum.doctype.unit_plan.unit_plan")

        doc = module.UnitPlan()
        doc.name = "UNIT-PLAN-1"
        doc.course_plan = "COURSE-PLAN-1"
        doc.title = "Cells and Systems"
        doc.unit_order = 20

        with self.assertRaisesRegex(StubValidationError, "Unit Order 20"):
            doc.validate()

        planning.ensure_linked_unit_plan_standards.assert_called_once_with(doc)
        planning.next_unit_order.assert_not_called()
        self.assertEqual(doc.unit_order, 20)
