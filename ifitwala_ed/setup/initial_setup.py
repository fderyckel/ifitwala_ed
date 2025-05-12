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
    org_name=None, org_abbr=None, school_name=None, school_abbr=None,
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

    # Ensure root organization "All Organizations" exists
    root_org = frappe.db.exists("Organization", "All Organizations")
    if not root_org:
        root_org = frappe.get_doc({
            "doctype": "Organization",
            "organization_name": "All Organizations",
            "abbr": "ALL",
            "is_group": 1,
            "parent_organization": "",
            "lft": 1,
            "rgt": 2,
            "archived": 0
        }).insert(ignore_permissions=True)

    # ─── Create initial organization and school if provided ─────────────────
    if org_name and org_abbr:
        org = frappe.get_doc({
            "doctype": "Organization",
            "organization_name": org_name.strip(),
            "abbr": org_abbr.strip().upper(),
            "is_group": 1,
            "parent_organization": "All Organizations",
        }).insert(ignore_permissions=True)
    else:
        org = None

    if school_name and school_abbr:
        school = frappe.get_doc({
            "doctype": "School",
            "school_name": school_name.strip(),
            "abbr": school_abbr.strip().upper(),
            "is_group": 1,
            "organization": org.name if org else root_org.name,
        }).insert(ignore_permissions=True)
    else:
        school = None

    # ─── update Website Settings ─────────────────────────────────────────────
    ws = frappe.get_single("Website Settings")
    if app_logo:
        ws.app_logo = app_logo
    if brand_image:
        ws.brand_image = brand_image
    if any([app_logo, brand_image]):
        ws.save(ignore_permissions=True)

    # ─── mark setup done (only after all saves succeeded) ────────────────────
    frappe.db.set_single_value("System Settings", None, "ifitwala_initial_setup", 1)
    frappe.db.commit()

    # Return created docs and URLs for immediate UI use
    return {
        "organization": org.name if org else root_org.name,
        "school": school.name if school else None,
        "app_logo": ws.app_logo,
        "brand_image": ws.brand_image,
        "message": _("Organization, School and branding created successfully."),
    }
