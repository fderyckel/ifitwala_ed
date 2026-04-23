from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillCoursePlanAcademicYearScope(TestCase):
    def test_execute_remaps_unique_in_scope_course_plan_academic_years(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.normalize_text = lambda value: str(value or "").strip()

        teaching_plans_api = types.ModuleType("ifitwala_ed.api.teaching_plans")
        teaching_plans_api._academic_year_scope_for_school = lambda school: {"SCH-1": ["SCH-1"]}.get(
            str(school or "").strip(),
            [],
        )

        course_plan_module = types.ModuleType("ifitwala_ed.curriculum.doctype.course_plan.course_plan")
        course_plan_module.ACTIVATION_MODE_ACADEMIC_YEAR_START = "Academic Year Start"
        course_plan_module.ACTIVATION_MODE_MANUAL = "Manual"
        course_plan_module._resolve_course_school = lambda course, fallback=None: {"COURSE-1": "SCH-1"}.get(
            str(course or "").strip(),
            fallback,
        )

        updates: list[tuple[str, str, dict[str, str | None], bool]] = []

        def get_all(doctype: str, **kwargs):
            if doctype == "Academic Year":
                return [
                    {"name": "SCH-1 2026-2027", "academic_year_name": "2026-2027", "school": "SCH-1"},
                    {"name": "SCH-OTHER 2026-2027", "academic_year_name": "2026-2027", "school": "SCH-OTHER"},
                    {"name": "SCH-1 2026-2028", "academic_year_name": "2026-2028", "school": "SCH-1"},
                ]
            if doctype == "Course Plan":
                return [
                    {
                        "name": "PLAN-IN-SCOPE",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "SCH-1 2026-2027",
                        "activation_mode": "Manual",
                    },
                    {
                        "name": "PLAN-OUT-OF-SCOPE",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "SCH-OTHER 2026-2027",
                        "activation_mode": "Manual",
                    },
                    {
                        "name": "PLAN-FREE-TEXT",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "2026-2028",
                        "activation_mode": "Manual",
                    },
                ]
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning,
                "ifitwala_ed.api.teaching_plans": teaching_plans_api,
                "ifitwala_ed.curriculum.doctype.course_plan.course_plan": course_plan_module,
            }
        ) as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Course Plan", "Academic Year", "Course"}
            frappe.get_all = get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_course_plan_academic_year_scope")

            module.execute()

        self.assertEqual(
            updates,
            [
                ("Course Plan", "PLAN-OUT-OF-SCOPE", {"academic_year": "SCH-1 2026-2027"}, False),
                ("Course Plan", "PLAN-FREE-TEXT", {"academic_year": "SCH-1 2026-2028"}, False),
            ],
        )

    def test_execute_clears_unmappable_or_ambiguous_academic_years(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.normalize_text = lambda value: str(value or "").strip()

        teaching_plans_api = types.ModuleType("ifitwala_ed.api.teaching_plans")
        teaching_plans_api._academic_year_scope_for_school = lambda school: {
            "SCH-1": ["SCH-1", "SCH-ORG"],
            "SCH-2": ["SCH-2"],
        }.get(str(school or "").strip(), [])

        course_plan_module = types.ModuleType("ifitwala_ed.curriculum.doctype.course_plan.course_plan")
        course_plan_module.ACTIVATION_MODE_ACADEMIC_YEAR_START = "Academic Year Start"
        course_plan_module.ACTIVATION_MODE_MANUAL = "Manual"
        course_plan_module._resolve_course_school = lambda course, fallback=None: {
            "COURSE-1": "SCH-1",
            "COURSE-2": "SCH-2",
        }.get(str(course or "").strip(), fallback)

        updates: list[tuple[str, str, dict[str, str | None], bool]] = []

        def get_all(doctype: str, **kwargs):
            if doctype == "Academic Year":
                return [
                    {"name": "SCH-OTHER 2027-2028", "academic_year_name": "2027-2028", "school": "SCH-OTHER"},
                    {"name": "SCH-1 2027-2028", "academic_year_name": "2027-2028", "school": "SCH-1"},
                    {"name": "SCH-ORG 2027-2028", "academic_year_name": "2027-2028", "school": "SCH-ORG"},
                ]
            if doctype == "Course Plan":
                return [
                    {
                        "name": "PLAN-AMBIGUOUS",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "SCH-OTHER 2027-2028",
                        "activation_mode": "Academic Year Start",
                    },
                    {
                        "name": "PLAN-MISSING",
                        "course": "COURSE-2",
                        "school": "SCH-2",
                        "academic_year": "MISSING 2029-2030",
                        "activation_mode": "Manual",
                    },
                ]
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning,
                "ifitwala_ed.api.teaching_plans": teaching_plans_api,
                "ifitwala_ed.curriculum.doctype.course_plan.course_plan": course_plan_module,
            }
        ) as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Course Plan", "Academic Year", "Course"}
            frappe.get_all = get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_course_plan_academic_year_scope")

            module.execute()

        self.assertEqual(
            updates,
            [
                (
                    "Course Plan",
                    "PLAN-AMBIGUOUS",
                    {"academic_year": None, "activation_mode": "Manual"},
                    False,
                ),
                ("Course Plan", "PLAN-MISSING", {"academic_year": None}, False),
            ],
        )

    def test_execute_returns_when_required_tables_are_missing(self):
        planning = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning.normalize_text = lambda value: str(value or "").strip()

        teaching_plans_api = types.ModuleType("ifitwala_ed.api.teaching_plans")
        teaching_plans_api._academic_year_scope_for_school = lambda school: []

        course_plan_module = types.ModuleType("ifitwala_ed.curriculum.doctype.course_plan.course_plan")
        course_plan_module.ACTIVATION_MODE_ACADEMIC_YEAR_START = "Academic Year Start"
        course_plan_module.ACTIVATION_MODE_MANUAL = "Manual"
        course_plan_module._resolve_course_school = lambda course, fallback=None: fallback

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning,
                "ifitwala_ed.api.teaching_plans": teaching_plans_api,
                "ifitwala_ed.curriculum.doctype.course_plan.course_plan": course_plan_module,
            }
        ) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_course_plan_academic_year_scope")

            module.execute()
