import frappe

from ..index import (
    _load_manifest,
    _collect_assets,
    _has_access,
    _redirect,
)

no_cache = 1


def get_context(context):
    user = frappe.session.user
    if not _has_access(user):
        _redirect("/login?redirect-to=/portal/staff/student-groups")

    manifest = _load_manifest()
    js_entry, css_files, preload_files = _collect_assets(manifest)

    context.vite_js = js_entry
    context.vite_css = css_files
    context.vite_preload = preload_files
    return context
