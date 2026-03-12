# ifitwala_ed/patches/setup/p04_refresh_core_crm_permissions.py

from __future__ import annotations

from ifitwala_ed.setup.setup import grant_core_crm_permissions


def execute():
    grant_core_crm_permissions()
