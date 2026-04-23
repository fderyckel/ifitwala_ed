from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillEmployeeManagedAccess(TestCase):
    def test_execute_reconciles_linked_employees_with_existing_users(self):
        employee_access = types.ModuleType("ifitwala_ed.hr.employee_access")
        sync_calls: list[str] = []
        employee_access.sync_user_access_from_employee = lambda employee_doc: sync_calls.append(employee_doc.name)

        with stubbed_frappe(extra_modules={"ifitwala_ed.hr.employee_access": employee_access}) as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Employee", "User"}
            frappe.get_all = lambda doctype, **kwargs: [
                {"name": "EMP-0001", "user_id": "staff1@example.com"},
                {"name": "EMP-0002", "user_id": "missing@example.com"},
                {"name": "EMP-0003", "user_id": "staff3@example.com"},
            ]
            frappe.db.exists = lambda doctype, name: (
                doctype == "User"
                and name
                in {
                    "staff1@example.com",
                    "staff3@example.com",
                }
            )
            frappe.get_doc = lambda doctype, name: types.SimpleNamespace(name=name)
            module = import_fresh("ifitwala_ed.patches.backfill_employee_managed_access")

            module.execute()

        self.assertEqual(sync_calls, ["EMP-0001", "EMP-0003"])

    def test_execute_returns_when_employee_or_user_table_is_missing(self):
        employee_access = types.ModuleType("ifitwala_ed.hr.employee_access")
        employee_access.sync_user_access_from_employee = lambda employee_doc: None

        with stubbed_frappe(extra_modules={"ifitwala_ed.hr.employee_access": employee_access}) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when Employee/User tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_employee_managed_access")

            module.execute()
