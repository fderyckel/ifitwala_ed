# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def is_setup_done():
    """Return True‹bool› if at least one Organization exists OR the flag is set."""
    return bool(frappe.db.exists("Organization")) or frappe.db.get_single_value(
        "System Settings", "ifitwala_initial_setup"
    )

@frappe.whitelist()
def complete_initial_setup(org_name, org_abbr, school_name, school_abbr):
    """Create root Organization & School exactly once."""
    if is_setup_done():
        frappe.throw(_("Initial setup already completed."))

    # ---- ROOT ORGANIZATION ---------------------------------------------------
    org = frappe.get_doc({
        "doctype": "Organization",
        "organization_name": org_name.strip(),
        "abbr": org_abbr.strip().upper(),
        "is_group": 1,
    }).insert(ignore_permissions=True)

    # ---- ROOT SCHOOL ---------------------------------------------------------
    school = frappe.get_doc({
        "doctype": "School",
        "school_name": school_name.strip(),
        "abbr": school_abbr.strip().upper(),
        "is_group": 1,
        "organization": org.name,
    }).insert(ignore_permissions=True)

    # ---- Mark wizard as done -------------------------------------------------
    frappe.db.set_value("System Settings", None, "ifitwala_initial_setup", 1)

    frappe.db.commit()
    return {
        "organization": org.name,
        "school": school.name,
        "message": _("Organization and School created successfully."),
    }
