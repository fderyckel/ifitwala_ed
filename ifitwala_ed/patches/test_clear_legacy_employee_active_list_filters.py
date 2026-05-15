from __future__ import annotations

import json
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestClearLegacyEmployeeActiveListFilters(TestCase):
    def test_execute_removes_legacy_active_filters_from_employee_user_settings(self):
        updates: list[tuple[str, str, str, str, bool]] = []

        def get_all(doctype: str, filters=None, fields=None, limit=None):
            self.assertEqual(doctype, "User Settings")
            self.assertEqual(filters, {"doctype": "Employee"})
            self.assertEqual(fields, ["name", "data"])
            self.assertEqual(limit, 0)
            return [
                {
                    "name": "settings-1",
                    "data": json.dumps(
                        {
                            "filters": [
                                ["Employee", "employment_status", "=", "Active"],
                                ["Employee", "department", "=", "Science"],
                                {"fieldname": "employment_status", "operator": "!=", "value": "Left"},
                            ],
                            "list_view": {
                                "filters": [
                                    {"field": "employment_status", "condition": "=", "value": "Active"},
                                    ["designation", "=", "Teacher"],
                                ]
                            },
                        }
                    ),
                },
                {"name": "settings-2", "data": json.dumps({"filters": [["department", "=", "Arts"]]})},
                {"name": "settings-bad", "data": "{not json"},
            ]

        def set_value(doctype, name, fieldname, value, update_modified=False):
            updates.append((doctype, name, fieldname, value, update_modified))

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype == "User Settings"
            frappe.get_all = get_all
            frappe.db.set_value = set_value
            module = import_fresh("ifitwala_ed.patches.clear_legacy_employee_active_list_filters")

            module.execute()

        self.assertEqual(len(updates), 1)
        doctype, name, fieldname, value, update_modified = updates[0]
        self.assertEqual((doctype, name, fieldname, update_modified), ("User Settings", "settings-1", "data", False))
        self.assertEqual(
            json.loads(value),
            {
                "filters": [
                    ["Employee", "department", "=", "Science"],
                    {"fieldname": "employment_status", "operator": "!=", "value": "Left"},
                ],
                "list_view": {"filters": [["designation", "=", "Teacher"]]},
            },
        )

    def test_execute_returns_when_user_settings_table_is_missing(self):
        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when User Settings is missing")
            )
            module = import_fresh("ifitwala_ed.patches.clear_legacy_employee_active_list_filters")

            module.execute()

    def test_cleaner_handles_root_filter_shapes(self):
        with stubbed_frappe():
            module = import_fresh("ifitwala_ed.patches.clear_legacy_employee_active_list_filters")

            cleaned, changed = module._clean_legacy_employee_filters(["employment_status", "=", "Active"])

        self.assertTrue(changed)
        self.assertEqual(cleaned, {})
