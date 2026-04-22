from __future__ import annotations

import types
from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillEmployeeUserLinks(TestCase):
    def test_execute_backfills_only_unambiguous_active_employee_user_links(self):
        employee_access = types.ModuleType("ifitwala_ed.hr.employee_access")
        sync_calls: list[str] = []
        employee_access.sync_user_access_from_employee = lambda employee_doc: sync_calls.append(employee_doc.name)

        employee_docs = {
            "EMP-OK": self._employee_doc("EMP-OK", primary_contact=None, contact_name="CONTACT-0001"),
            "EMP-NO-CONTACT": self._employee_doc("EMP-NO-CONTACT", primary_contact=None, contact_name=None),
        }
        updates: list[tuple[str, str, object, bool]] = []

        def table_exists(doctype: str) -> bool:
            return doctype in {"Employee", "User", "Contact"}

        def get_all(doctype: str, filters=None, fields=None, limit=None):
            if doctype == "Employee":
                return [
                    {"name": "EMP-OK", "user_id": "", "employee_professional_email": "ok@example.com"},
                    {"name": "EMP-NO-USER", "user_id": "", "employee_professional_email": "missing@example.com"},
                    {"name": "EMP-DUP-USER", "user_id": "", "employee_professional_email": "dup@example.com"},
                    {"name": "EMP-CONFLICT", "user_id": "", "employee_professional_email": "linked@example.com"},
                    {
                        "name": "EMP-HAS-LINK",
                        "user_id": "already@example.com",
                        "employee_professional_email": "already@example.com",
                    },
                    {"name": "EMP-NO-CONTACT", "user_id": "", "employee_professional_email": "nocontact@example.com"},
                ]
            if doctype == "User":
                email = (filters or {}).get("email")
                if email == "ok@example.com":
                    return [{"name": "ok@example.com"}]
                if email == "dup@example.com":
                    return [{"name": "dup-a@example.com"}, {"name": "dup-b@example.com"}]
                if email == "linked@example.com":
                    return [{"name": "linked@example.com"}]
                if email == "nocontact@example.com":
                    return [{"name": "nocontact@example.com"}]
                return []
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        def get_value(doctype: str, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee" and filters == {"user_id": "linked@example.com"} and fieldname == "name":
                return "EMP-OTHER"
            return None

        def set_value(doctype: str, name: str, fieldname_or_values, value=None, update_modified=False):
            payload = fieldname_or_values if value is None else {fieldname_or_values: value}
            updates.append((doctype, name, payload, update_modified))

        def get_doc(doctype: str, name: str):
            assert doctype == "Employee"
            return employee_docs[name]

        with stubbed_frappe(extra_modules={"ifitwala_ed.hr.employee_access": employee_access}) as frappe:
            frappe.db.table_exists = table_exists
            frappe.get_all = get_all
            frappe.db.get_value = get_value
            frappe.db.set_value = set_value
            frappe.get_doc = get_doc
            module = import_fresh("ifitwala_ed.patches.backfill_employee_user_links")

            module.execute()

        self.assertEqual(
            updates,
            [
                ("Employee", "EMP-OK", {"user_id": "ok@example.com"}, False),
                ("Employee", "EMP-NO-CONTACT", {"user_id": "nocontact@example.com"}, False),
            ],
        )
        self.assertEqual(sync_calls, ["EMP-OK", "EMP-NO-CONTACT"])
        employee_docs["EMP-OK"]._get_or_create_primary_contact.assert_called_once_with()
        employee_docs["EMP-OK"]._ensure_contact_employee_link.assert_called_once_with("CONTACT-0001")
        employee_docs["EMP-OK"].db_set.assert_called_once_with(
            "empl_primary_contact", "CONTACT-0001", update_modified=False
        )
        employee_docs["EMP-NO-CONTACT"]._get_or_create_primary_contact.assert_called_once_with()
        employee_docs["EMP-NO-CONTACT"]._ensure_contact_employee_link.assert_not_called()
        employee_docs["EMP-NO-CONTACT"].db_set.assert_not_called()

    def test_execute_returns_when_employee_or_user_table_is_missing(self):
        employee_access = types.ModuleType("ifitwala_ed.hr.employee_access")
        employee_access.sync_user_access_from_employee = lambda employee_doc: None

        with stubbed_frappe(extra_modules={"ifitwala_ed.hr.employee_access": employee_access}) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when Employee/User tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_employee_user_links")

            module.execute()

    @staticmethod
    def _employee_doc(name: str, *, primary_contact: str | None, contact_name: str | None):
        doc = Mock()
        doc.name = name
        doc.user_id = None
        doc.empl_primary_contact = primary_contact
        doc._get_or_create_primary_contact = Mock(return_value=contact_name)
        doc._ensure_contact_employee_link = Mock()
        doc.db_set = Mock()
        return doc
