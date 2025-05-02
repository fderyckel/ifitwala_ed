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
def complete_initial_setup(
    org_name, org_abbr, school_name, school_abbr,
    app_logo=None, brand_image=None
):
    """Create root Organization & School and optionally set
    the login-logo and navbar-brand in Website Settings."""
    if is_setup_done():
        frappe.throw(_("Initial setup already completed."))

    # Validate image inputs
    if app_logo and not frappe.db.exists("File", app_logo):
        frappe.throw(_("App Logo file not found: {0}").format(app_logo))
    if brand_image and not frappe.db.exists("File", brand_image):
        frappe.throw(_("Navbar Brand Image file not found: {0}").format(brand_image))

    # ─── create org & school ─────────────────────────────────────────────────
    org = frappe.get_doc({
        "doctype": "Organization",
        "organization_name": org_name.strip(),
        "abbr": org_abbr.strip().upper(),
        "is_group": 1,
    }).insert(ignore_permissions=True)

    school = frappe.get_doc({
        "doctype": "School",
        "school_name": school_name.strip(),
        "abbr": school_abbr.strip().upper(),
        "is_group": 1,
        "organization": org.name,
    }).insert(ignore_permissions=True)

    # ─── update Website Settings ─────────────────────────────────────────────
    ws = frappe.get_single("Website Settings")
    if app_logo:
        ws.app_logo = app_logo
    if brand_image:
        ws.brand_image = brand_image
    if any([app_logo, brand_image]):
        ws.save(ignore_permissions=True)

    # ─── mark setup done (only after all saves succeeded) ────────────────────
    frappe.db.set_value("System Settings", None, "ifitwala_initial_setup", 1)
    frappe.db.commit()

    # Return created docs and URLs for immediate UI use
    return {
        "organization": org.name,
        "school": school.name,
        "app_logo": ws.app_logo,
        "brand_image": ws.brand_image,
        "message": _("Organization, School and branding created successfully."),
    }
