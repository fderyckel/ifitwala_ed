from __future__ import annotations

import frappe

from ifitwala_ed.website.public_brand import get_public_brand_identity


def update_website_context(context):
    request = getattr(frappe.local, "request", None)
    path = str(getattr(request, "path", "") or "").strip()
    if path != "/login" and context.get("for_test") != "login.html":
        return {}

    brand = get_public_brand_identity()
    return {
        "app_name": brand["brand_name"],
        "logo": brand["brand_logo"],
    }
