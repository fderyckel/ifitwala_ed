from unittest.mock import patch

from ifitwala_ed.patches.sync_core_crm_permissions import execute


def test_sync_core_crm_permissions_reapplies_canonical_seed():
    with patch("ifitwala_ed.setup.setup.grant_core_crm_permissions") as mocked:
        execute()

    mocked.assert_called_once_with()
