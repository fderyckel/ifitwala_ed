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

        teaching_plans_api = types.ModuleType("ifitwala_ed.api.teaching_plans")
        teaching_plans_api._validate_course_program_link = Mock()

        nestedset = types.ModuleType("frappe.utils.nestedset")
        nestedset.get_descendants_of = lambda doctype, name: []

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning,
                "ifitwala_ed.api.teaching_plans": teaching_plans_api,
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

        teaching_plans_api._validate_course_program_link.assert_called_once_with(
            course="COURSE-1",
            program=None,
        )
        planning.ensure_linked_unit_plan_standards.assert_called_once_with(doc)
        planning.next_unit_order.assert_not_called()
        self.assertEqual(doc.unit_order, 20)

    def test_validate_rejects_program_not_linked_to_course(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.normalize_text = lambda value: str(value or "").strip()
        planning.normalize_long_text = lambda value: value
        planning.get_course_plan_row = lambda course_plan: {"course": "COURSE-1", "school": "SCH-1"}
        planning.ensure_linked_unit_plan_standards = Mock()
        planning.next_unit_order = Mock(return_value=30)

        teaching_plans_api = types.ModuleType("ifitwala_ed.api.teaching_plans")
        teaching_plans_api._validate_course_program_link = Mock(side_effect=StubValidationError("Program MYP invalid"))

        nestedset = types.ModuleType("frappe.utils.nestedset")
        nestedset.get_descendants_of = lambda doctype, name: []

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning,
                "ifitwala_ed.api.teaching_plans": teaching_plans_api,
                "frappe.utils.nestedset": nestedset,
            }
        ):
            module = import_fresh("ifitwala_ed.curriculum.doctype.unit_plan.unit_plan")

            doc = module.UnitPlan()
            doc.name = "UNIT-PLAN-1"
            doc.course_plan = "COURSE-PLAN-1"
            doc.title = "Cells and Systems"
            doc.program = "MYP"
            doc.unit_order = 20

            with self.assertRaisesRegex(StubValidationError, "Program MYP invalid"):
                doc.validate()

        teaching_plans_api._validate_course_program_link.assert_called_once_with(
            course="COURSE-1",
            program="MYP",
        )
        planning.ensure_linked_unit_plan_standards.assert_not_called()

    def test_learning_standard_picker_drops_stale_program_filter(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.normalize_text = lambda value: str(value or "").strip()
        planning.normalize_long_text = lambda value: value

        teaching_plans_api = types.ModuleType("ifitwala_ed.api.teaching_plans")
        teaching_plans_api._validate_course_program_link = Mock()

        nestedset = types.ModuleType("frappe.utils.nestedset")
        nestedset.get_descendants_of = lambda doctype, name: []

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning,
                "ifitwala_ed.api.teaching_plans": teaching_plans_api,
                "frappe.utils.nestedset": nestedset,
            }
        ) as frappe:
            frappe.db.exists = lambda doctype, filters=None: (
                False if doctype == "Program" and filters == "LEGACY-PROGRAM" else None
            )
            frappe.db.get_value = lambda *args, **kwargs: None
            frappe.get_list = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_list should not run for a stale program filter")
            )
            module = import_fresh("ifitwala_ed.curriculum.doctype.unit_plan.unit_plan")

            payload = module.get_learning_standard_picker(program="LEGACY-PROGRAM")

        self.assertEqual(
            payload,
            {
                "filters": {
                    "unit_plan": None,
                    "framework_name": None,
                    "program": None,
                    "strand": None,
                    "substrand": None,
                    "search_text": None,
                },
                "options": {
                    "frameworks": [],
                    "programs": [],
                    "strands": [],
                    "substrands": [],
                    "has_blank_substrand": False,
                },
                "standards": [],
            },
        )
