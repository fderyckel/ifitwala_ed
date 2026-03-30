# ifitwala_ed/www/index.py

import frappe

from ifitwala_ed.website.renderer import build_render_context


def _redirect(to: str):
    frappe.local.flags.redirect_location = to
    raise frappe.Redirect


def get_context(context):
    path = frappe.request.path if hasattr(frappe, "request") else "/"
    preview = str(getattr(frappe, "form_dict", {}).get("preview") or "") == "1"
    context.no_cache = 1
    payload = build_render_context(route=path, preview=preview)
    redirect_location = (payload or {}).pop("redirect_location", None)
    if redirect_location:
        _redirect(redirect_location)
    context.update(payload)
    return context
