from __future__ import annotations

from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.backfill_employee_contact_links import execute


class TestBackfillEmployeeContactLinks(FrappeTestCase):
    def test_execute_repairs_existing_employee_contact_links(self):
        employee_one = Mock()
        employee_two = Mock()

        with (
            patch("ifitwala_ed.patches.backfill_employee_contact_links.frappe.db.table_exists", return_value=True),
            patch(
                "ifitwala_ed.patches.backfill_employee_contact_links.frappe.get_all",
                return_value=["EMP-0001", "EMP-0002"],
            ) as mocked_get_all,
            patch(
                "ifitwala_ed.patches.backfill_employee_contact_links.frappe.get_doc",
                side_effect=[employee_one, employee_two],
            ) as mocked_get_doc,
        ):
            execute()

        mocked_get_all.assert_called_once_with(
            "Employee",
            filters={"user_id": ["is", "set"]},
            pluck="name",
            limit=100000,
        )
        mocked_get_doc.assert_any_call("Employee", "EMP-0001")
        mocked_get_doc.assert_any_call("Employee", "EMP-0002")
        employee_one._ensure_primary_contact.assert_called_once_with()
        employee_two._ensure_primary_contact.assert_called_once_with()
