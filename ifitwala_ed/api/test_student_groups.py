# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _student_groups_stub_modules(resolve_employee=None):
    attendance_utils = types.ModuleType("ifitwala_ed.schedule.attendance_utils")
    attendance_utils.get_student_group_students = lambda *args, **kwargs: []

    calendar_core = types.ModuleType("ifitwala_ed.api.calendar_core")
    calendar_core._resolve_employee_for_user = resolve_employee or (
        lambda user, fields=None, employment_status_filter=None: None
    )

    return {
        "ifitwala_ed.schedule.attendance_utils": attendance_utils,
        "ifitwala_ed.api.calendar_core": calendar_core,
    }


class TestStudentGroupsApi(TestCase):
    def test_instructor_with_academic_staff_still_uses_group_scope(self):
        with stubbed_frappe(extra_modules=_student_groups_stub_modules()) as frappe:
            frappe.session.user = "teacher@example.com"
            frappe.get_roles = lambda user: ["Instructor", "Academic Staff"]

            module = import_fresh("ifitwala_ed.api.student_groups")

            self.assertFalse(module._has_broad_group_access(set(frappe.get_roles("teacher@example.com"))))

    def test_academic_assistant_instructor_override_keeps_broad_group_access(self):
        with stubbed_frappe(extra_modules=_student_groups_stub_modules()) as frappe:
            frappe.session.user = "assistant@example.com"
            frappe.get_roles = lambda user: ["Instructor", "Academic Assistant"]

            module = import_fresh("ifitwala_ed.api.student_groups")

            self.assertTrue(module._has_broad_group_access(set(frappe.get_roles("assistant@example.com"))))

    def test_instructor_group_names_uses_internal_membership_resolution(self):
        observed_calls = []

        def fake_get_all(doctype, filters=None, pluck=None, ignore_permissions=False, **kwargs):
            observed_calls.append(
                {
                    "doctype": doctype,
                    "filters": dict(filters or {}),
                    "pluck": pluck,
                    "ignore_permissions": ignore_permissions,
                }
            )

            if doctype == "Student Group Instructor":
                if filters.get("user_id") == "teacher@example.com":
                    return []
                if filters.get("employee") == "EMP-001":
                    return []
                if filters.get("instructor") == ["in", ["INS-001"]]:
                    return ["SG-0001"]
                return []

            if doctype == "Instructor":
                if filters.get("linked_user_id") == "teacher@example.com":
                    return []
                if filters.get("employee") == "EMP-001":
                    return ["INS-001"]
                return []

            return []

        with stubbed_frappe(
            extra_modules=_student_groups_stub_modules(
                resolve_employee=lambda user, fields=None, employment_status_filter=None: {"name": "EMP-001"}
            )
        ) as frappe:
            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.student_groups")
            group_names = module._instructor_group_names("teacher@example.com")

        self.assertEqual(group_names, {"SG-0001"})

        instructor_calls = [call for call in observed_calls if call["doctype"] == "Instructor"]
        membership_calls = [call for call in observed_calls if call["doctype"] == "Student Group Instructor"]

        self.assertEqual(len(instructor_calls), 2)
        self.assertEqual(len(membership_calls), 3)
        for call in observed_calls:
            self.assertTrue(call["ignore_permissions"])
        for call in membership_calls:
            self.assertEqual(call["filters"].get("parenttype"), "Student Group")
