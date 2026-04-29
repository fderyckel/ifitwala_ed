from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api import calendar_invalidation


class TestCalendarInvalidation(TestCase):
    def test_active_employee_names_for_school_scope_includes_descendant_scope(self):
        calls = []

        def fake_get_all(doctype, **kwargs):
            calls.append((doctype, kwargs))
            return ["EMP-1", "EMP-2"]

        with (
            patch(
                "ifitwala_ed.api.calendar_invalidation.get_descendant_schools",
                return_value=["SCHOOL-1", "SCHOOL-2"],
            ),
            patch("ifitwala_ed.api.calendar_invalidation.frappe.get_all", side_effect=fake_get_all),
        ):
            employees = calendar_invalidation.active_employee_names_for_school_scope("SCHOOL-1")

        self.assertEqual(employees, ["EMP-1", "EMP-2"])
        self.assertEqual(calls[0][0], "Employee")
        self.assertEqual(calls[0][1]["filters"]["school"], ["in", ["SCHOOL-1", "SCHOOL-2"]])
        self.assertEqual(calls[0][1]["filters"]["employment_status"], ["!=", "Inactive"])
        self.assertEqual(calls[0][1]["limit"], 0)

    def test_invalidate_staff_calendar_for_users_resolves_employee_cache_keys(self):
        with (
            patch(
                "ifitwala_ed.api.calendar_invalidation.active_employee_names_for_users",
                return_value=["EMP-1", "EMP-2"],
            ) as resolver,
            patch("ifitwala_ed.api.calendar_invalidation.invalidate_staff_portal_calendar_cache") as invalidator,
        ):
            calendar_invalidation.invalidate_staff_calendar_for_users(["staff@example.com"])

        resolver.assert_called_once_with(["staff@example.com"])
        self.assertEqual([call.args[0] for call in invalidator.call_args_list], ["EMP-1", "EMP-2"])
