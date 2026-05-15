from types import ModuleType
from unittest.mock import Mock, patch

from ifitwala_ed.patches.sync_core_crm_permissions import execute


def test_sync_core_crm_permissions_reapplies_canonical_seed():
    setup_module = ModuleType("ifitwala_ed.setup.setup")
    setup_module.grant_core_crm_permissions = Mock()

    with patch.dict("sys.modules", {"ifitwala_ed.setup.setup": setup_module}):
        execute()

    setup_module.grant_core_crm_permissions.assert_called_once_with()
