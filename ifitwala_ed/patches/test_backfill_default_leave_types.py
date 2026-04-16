from __future__ import annotations

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.backfill_default_leave_types import execute


class TestBackfillDefaultLeaveTypes(FrappeTestCase):
    def test_execute_is_noop_without_leave_type_table(self):
        with (
            patch(
                "ifitwala_ed.patches.backfill_default_leave_types.frappe.db.table_exists",
                return_value=False,
            ) as mocked_table_exists,
            patch("ifitwala_ed.setup.setup.create_default_leave_types") as mocked_create_default_leave_types,
        ):
            execute()

        mocked_table_exists.assert_called_once_with("Leave Type")
        mocked_create_default_leave_types.assert_not_called()

    def test_execute_backfills_default_leave_types(self):
        with (
            patch(
                "ifitwala_ed.patches.backfill_default_leave_types.frappe.db.table_exists",
                return_value=True,
            ) as mocked_table_exists,
            patch("ifitwala_ed.setup.setup.create_default_leave_types") as mocked_create_default_leave_types,
        ):
            execute()

        mocked_table_exists.assert_called_once_with("Leave Type")
        mocked_create_default_leave_types.assert_called_once_with()
