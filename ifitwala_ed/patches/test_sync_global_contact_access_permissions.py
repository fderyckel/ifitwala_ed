from types import ModuleType
from unittest.mock import Mock, patch

from ifitwala_ed.patches.sync_global_contact_access_permissions import execute


def test_sync_global_contact_access_permissions_reapplies_canonical_seed():
    setup_module = ModuleType("ifitwala_ed.setup.setup")
    setup_module.grant_core_crm_permissions = Mock()

    with patch.dict("sys.modules", {"ifitwala_ed.setup.setup": setup_module}):
        execute()

    setup_module.grant_core_crm_permissions.assert_called_once_with()
