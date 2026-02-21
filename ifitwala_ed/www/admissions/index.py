# ifitwala_ed/www/admissions/index.py

import os

import frappe

from ifitwala_ed.routing.policy import (
    build_login_redirect,
    build_logout_then_login_redirect,
    canonical_path_for_section,
    has_staff_portal_access,
)
from ifitwala_ed.website.vite_utils import get_vite_assets

APP = "ifitwala_ed"
VITE_DIR = os.path.join(frappe.get_app_path(APP), "public", "vite")
MANIFEST_PATHS = [
    os.path.join(VITE_DIR, "manifest.json"),
    os.path.join(VITE_DIR, ".vite", "manifest.json"),
]
PUBLIC_BASE = f"/assets/{APP}/vite/"

ADMISSIONS_ROLE = "Admissions Applicant"
ADMISSIONS_ENTRY_KEYS = [
    "src/apps/admissions/main.ts",
    "src/apps/admissions/main.js",
    "index.html",
]


def _load_assets():
    return get_vite_assets(
        app_name=APP,
        manifest_paths=MANIFEST_PATHS,
        public_base=PUBLIC_BASE,
        entry_keys=ADMISSIONS_ENTRY_KEYS,
    )


def _redirect(to: str):
    frappe.local.flags.redirect_location = to
    raise frappe.Redirect


def _redirect_to_login(path: str, *, clear_session: bool = False):
    if clear_session:
        _redirect(build_logout_then_login_redirect(path))
    _redirect(build_login_redirect(path))


def _request_path(default: str) -> str:
    try:
        request = getattr(frappe, "request", None)
    except RuntimeError:
        return default
    return str(getattr(request, "path", default) or default)


def get_context(context):
    user = frappe.session.user
    path = _request_path("/admissions")

    if not user or user == "Guest":
        _redirect_to_login(path)

    roles = set(frappe.get_roles(user))
    if ADMISSIONS_ROLE not in roles:
        if has_staff_portal_access(user=user, roles=roles):
            _redirect(canonical_path_for_section("staff"))
        _redirect_to_login(path, clear_session=True)

    applicant = frappe.db.get_value(
        "Student Applicant",
        {"applicant_user": user},
        "name",
    )
    if not applicant:
        if has_staff_portal_access(user=user, roles=roles):
            _redirect(canonical_path_for_section("staff"))
        _redirect_to_login(path, clear_session=True)

    context.title = "Admissions Portal"
    context.applicant = applicant
    context.csrf_token = frappe.sessions.get_csrf_token()

    js_entry, css_files, preload_files = _load_assets()

    context.vite_js = js_entry
    context.vite_css = css_files
    context.vite_preload = preload_files
    return context
