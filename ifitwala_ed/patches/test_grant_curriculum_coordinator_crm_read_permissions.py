from __future__ import annotations

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.grant_curriculum_coordinator_crm_read_permissions import execute


class TestGrantCurriculumCoordinatorCrmReadPermissions(FrappeTestCase):
    def test_execute_is_noop_without_custom_docperm_table(self):
        with (
            patch(
                "ifitwala_ed.patches.grant_curriculum_coordinator_crm_read_permissions.frappe.db.table_exists",
                return_value=False,
            ) as mocked_table_exists,
            patch("ifitwala_ed.setup.setup.grant_core_crm_permissions") as mocked_grant_permissions,
        ):
            execute()

        mocked_table_exists.assert_called_once_with("Custom DocPerm")
        mocked_grant_permissions.assert_not_called()

    def test_execute_reapplies_canonical_crm_permissions(self):
        with (
            patch(
                "ifitwala_ed.patches.grant_curriculum_coordinator_crm_read_permissions.frappe.db.table_exists",
                return_value=True,
            ) as mocked_table_exists,
            patch("ifitwala_ed.setup.setup.grant_core_crm_permissions") as mocked_grant_permissions,
        ):
            execute()

        mocked_table_exists.assert_called_once_with("Custom DocPerm")
        mocked_grant_permissions.assert_called_once_with()
