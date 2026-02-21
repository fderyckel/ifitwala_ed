# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/www/portal/index.py

import os

import frappe

from ifitwala_ed.routing.policy import (
    ADMISSIONS_APPLICANT_ROLE,
    build_login_redirect,
    canonical_path_for_section,
    has_staff_portal_access,
    log_legacy_portal_hit,
    portal_roles_for_client,
    resolve_default_portal_section,
    resolve_portal_sections,
    resolve_section_from_path,
    translate_legacy_portal_path,
)
from ifitwala_ed.website.vite_utils import get_vite_assets

APP = "ifitwala_ed"
VITE_DIR = os.path.join(frappe.get_app_path(APP), "public", "vite")
MANIFEST_PATHS = [
    os.path.join(VITE_DIR, "manifest.json"),
    os.path.join(VITE_DIR, ".vite", "manifest.json"),
]
PUBLIC_BASE = f"/assets/{APP}/vite/"


def _load_assets():
    return get_vite_assets(
        app_name=APP,
        manifest_paths=MANIFEST_PATHS,
        public_base=PUBLIC_BASE,
        entry_keys=["index.html", "src/apps/portal/main.ts", "src/apps/portal/main.js"],
    )


def _redirect(to: str):
    frappe.local.flags.redirect_location = to
    raise frappe.Redirect


def _request_path(default: str) -> str:
    try:
        request = getattr(frappe, "request", None)
    except RuntimeError:
        return default
    return str(getattr(request, "path", default) or default)


def get_context(context):
    user = frappe.session.user
    path = _request_path(canonical_path_for_section("student"))
    log_legacy_portal_hit(path=path, user=user)

    if not user or user == "Guest":
        target = translate_legacy_portal_path(path, default_section="student") or path
        _redirect(build_login_redirect(target))

    roles = set(frappe.get_roles(user))
    if ADMISSIONS_APPLICANT_ROLE in roles and not has_staff_portal_access(user=user, roles=roles):
        _redirect("/admissions")

    sections = resolve_portal_sections(user=user, roles=roles)
    requested_section = resolve_section_from_path(path)
    default_section = resolve_default_portal_section(
        allowed_sections=sections,
        requested_section=requested_section,
    )

    legacy_target = translate_legacy_portal_path(path, default_section=default_section)
    if legacy_target and legacy_target != path:
        _redirect(legacy_target)

    if not sections:
        _redirect(build_login_redirect(canonical_path_for_section(default_section)))

    if requested_section and requested_section not in sections:
        _redirect(canonical_path_for_section(default_section))

    context.default_portal = default_section
    context.portal_roles = portal_roles_for_client(sections)
    context.portal_roles_json = frappe.as_json(context.portal_roles)

    js_entry, css_files, preload_files = _load_assets()

    context.csrf_token = frappe.sessions.get_csrf_token()
    context.vite_js = js_entry
    context.vite_css = css_files
    context.vite_preload = preload_files
    return context
