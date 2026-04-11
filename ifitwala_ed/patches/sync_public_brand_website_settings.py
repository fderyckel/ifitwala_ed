from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Organization") or not frappe.db.table_exists("Website Settings"):
        return

    from ifitwala_ed.website.public_brand import sync_public_brand_website_settings

    sync_public_brand_website_settings()
