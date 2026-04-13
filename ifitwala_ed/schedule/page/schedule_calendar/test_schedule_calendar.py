from __future__ import annotations

import types
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import StubPermissionError, import_fresh, stubbed_frappe


def _schedule_calendar_stub_modules():
    query_builder = types.ModuleType("frappe.query_builder")
    query_builder.DocType = lambda name: None

    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.getdate = lambda value: value

    schedule_utils = types.ModuleType("ifitwala_ed.schedule.schedule_utils")
    schedule_utils.current_academic_year = lambda: "AY-TEST"
    schedule_utils.get_block_colour = lambda value: "#000000"
    schedule_utils.get_course_block_colour = lambda value: "#111111"
    schedule_utils.get_rotation_dates = lambda *args, **kwargs: []

    school_tree = types.ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree.get_descendant_schools = lambda school: []

    return {
        "frappe.query_builder": query_builder,
        "frappe.utils": frappe_utils,
        "ifitwala_ed.schedule.schedule_utils": schedule_utils,
        "ifitwala_ed.utilities.school_tree": school_tree,
    }


def _prepare_frappe_for_schedule_calendar(frappe):
    frappe.get_cached_value = lambda *args, **kwargs: None


class TestScheduleCalendarAccess(TestCase):
    def test_resolve_access_context_scopes_observer_roles_to_school_descendants(self):
        with stubbed_frappe(extra_modules=_schedule_calendar_stub_modules()) as frappe:
            _prepare_frappe_for_schedule_calendar(frappe)
            frappe.get_roles = lambda user: ["Curriculum Coordinator"]
            frappe.db.get_value = lambda doctype, filters, fieldname=None, as_dict=False: (
                "SCHOOL-ROOT" if doctype == "Employee" else None
            )
            frappe.defaults = types.SimpleNamespace(get_user_default=lambda key, user=None: None)

            module = import_fresh("ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar")
            with (
                patch.object(
                    module,
                    "get_descendant_schools",
                    return_value=["SCHOOL-ROOT-CHILD", "SCHOOL-ROOT-GRANDCHILD"],
                ),
                patch.object(module, "_get_default_instructor", return_value=None),
            ):
                ctx = module._resolve_schedule_calendar_access_context("coordinator@example.com")

        self.assertEqual(ctx["mode"], "observer_scoped")
        self.assertEqual(
            ctx["school_scope"],
            ["SCHOOL-ROOT", "SCHOOL-ROOT-CHILD", "SCHOOL-ROOT-GRANDCHILD"],
        )

    def test_resolve_access_context_uses_default_school_when_employee_school_missing(self):
        with stubbed_frappe(extra_modules=_schedule_calendar_stub_modules()) as frappe:
            _prepare_frappe_for_schedule_calendar(frappe)
            frappe.get_roles = lambda user: ["Accreditation Visitor"]
            frappe.db.get_value = lambda doctype, filters, fieldname=None, as_dict=False: None
            frappe.defaults = types.SimpleNamespace(get_user_default=lambda key, user=None: "SCHOOL-DEFAULT")

            module = import_fresh("ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar")
            with (
                patch.object(module, "get_descendant_schools", return_value=["SCHOOL-CHILD"]),
                patch.object(module, "_get_default_instructor", return_value=None),
            ):
                ctx = module._resolve_schedule_calendar_access_context("visitor@example.com")

        self.assertEqual(ctx["mode"], "observer_scoped")
        self.assertEqual(ctx["base_school"], "SCHOOL-DEFAULT")
        self.assertEqual(ctx["school_scope"], ["SCHOOL-DEFAULT", "SCHOOL-CHILD"])

    def test_fetch_instructor_options_scopes_academic_assistant_results(self):
        class _Column:
            def __init__(self, name):
                self.name = name

            def isin(self, values):
                return ("isin", self.name, tuple(values))

            def like(self, value):
                return ("like", self.name, value)

        class _Instr:
            name = _Column("name")
            instructor_name = _Column("instructor_name")
            school = _Column("school")

        class _Query:
            def __init__(self):
                self.conditions = []

            def select(self, *args):
                return self

            def where(self, condition):
                self.conditions.append(condition)
                return self

            def limit(self, value):
                self.limit_value = value
                return self

            def offset(self, value):
                self.offset_value = value
                return self

            def run(self):
                return [["INST-001", "Ada Byron"]]

        query = _Query()

        with stubbed_frappe(extra_modules=_schedule_calendar_stub_modules()) as frappe:
            _prepare_frappe_for_schedule_calendar(frappe)
            frappe.session = types.SimpleNamespace(user="assistant@example.com")
            frappe.qb = types.SimpleNamespace(from_=lambda doctype: query)

            module = import_fresh("ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar")
            with (
                patch.object(
                    module,
                    "_resolve_schedule_calendar_access_context",
                    return_value={
                        "mode": "observer_scoped",
                        "school_scope": ["SCHOOL-1", "SCHOOL-1A"],
                    },
                ),
                patch.object(module, "DocType", return_value=_Instr),
            ):
                rows = module.fetch_instructor_options(txt="Ada", page_len=20, start=0)

        self.assertEqual(rows, [["INST-001", "Ada Byron"]])
        self.assertIn(("isin", "school", ("SCHOOL-1", "SCHOOL-1A")), query.conditions)
        self.assertIn(("like", "instructor_name", "%Ada%"), query.conditions)

    def test_ensure_instructor_visible_blocks_sibling_school_selection(self):
        with stubbed_frappe(extra_modules=_schedule_calendar_stub_modules()) as frappe:
            _prepare_frappe_for_schedule_calendar(frappe)
            frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: "SCHOOL-SIBLING"
            module = import_fresh("ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar")

            with self.assertRaises(StubPermissionError):
                module._ensure_instructor_visible_for_schedule_calendar(
                    "INST-OUTSIDE",
                    {
                        "mode": "observer_scoped",
                        "school_scope": ["SCHOOL-ROOT", "SCHOOL-CHILD"],
                    },
                )

    def test_get_instructor_events_blocks_out_of_scope_observer_request(self):
        with stubbed_frappe(extra_modules=_schedule_calendar_stub_modules()) as frappe:
            _prepare_frappe_for_schedule_calendar(frappe)
            frappe.session = types.SimpleNamespace(user="visitor@example.com")
            frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: "SCHOOL-SIBLING"

            module = import_fresh("ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar")
            with patch.object(
                module,
                "_resolve_schedule_calendar_access_context",
                return_value={
                    "mode": "observer_scoped",
                    "school_scope": ["SCHOOL-ROOT"],
                },
            ):
                with self.assertRaises(StubPermissionError):
                    module.get_instructor_events(
                        start="2026-04-01",
                        end="2026-04-30",
                        filters={"instructor": "INST-OUTSIDE"},
                    )
