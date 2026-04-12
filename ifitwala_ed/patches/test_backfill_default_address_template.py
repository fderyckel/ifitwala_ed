from __future__ import annotations

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.backfill_default_address_template import execute


class TestBackfillDefaultAddressTemplate(FrappeTestCase):
    def test_execute_is_noop_without_address_template_table(self):
        with (
            patch(
                "ifitwala_ed.patches.backfill_default_address_template.frappe.db.table_exists",
                return_value=False,
            ) as mocked_table_exists,
            patch("ifitwala_ed.setup.setup.ensure_default_address_template") as mocked_ensure_default,
        ):
            execute()

        mocked_table_exists.assert_called_once_with("Address Template")
        mocked_ensure_default.assert_not_called()

    def test_execute_backfills_missing_default_template(self):
        with (
            patch(
                "ifitwala_ed.patches.backfill_default_address_template.frappe.db.table_exists",
                return_value=True,
            ) as mocked_table_exists,
            patch("ifitwala_ed.setup.setup.ensure_default_address_template") as mocked_ensure_default,
        ):
            execute()

        mocked_table_exists.assert_called_once_with("Address Template")
        mocked_ensure_default.assert_called_once_with()
