"""Re-apply canonical Contact/Address role permissions on existing sites."""


def execute():
    from ifitwala_ed.setup.setup import grant_core_crm_permissions

    grant_core_crm_permissions()
