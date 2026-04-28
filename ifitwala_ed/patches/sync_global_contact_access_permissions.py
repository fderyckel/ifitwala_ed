"""Re-apply Contact/Address permissions after global admissions/marketing access update."""


def execute():
    from ifitwala_ed.setup.setup import grant_core_crm_permissions

    grant_core_crm_permissions()
