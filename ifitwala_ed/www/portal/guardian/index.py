# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/www/portal/guardian/index.py
# Guardian-specific portal entry point - forces guardian as default view

import os
import json
import frappe

APP = "ifitwala_ed"
VITE_DIR = os.path.join(frappe.get_app_path(APP), "public", "vite")
MANIFEST_PATHS = [
    os.path.join(VITE_DIR, "manifest.json"),
    os.path.join(VITE_DIR, ".vite", "manifest.json"),
]
PUBLIC_BASE = f"/assets/{APP}/vite/"

def _load_manifest() -> dict:
    for path in MANIFEST_PATHS:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _collect_assets(manifest: dict) -> tuple[str, list[str], list[str]]:
    candidates = ["index.html", "src/main.ts", "src/main.js"]
    entry = None
    for key in candidates:
        if key in manifest:
            entry = manifest[key]
            break
    if not entry:
        for _, v in manifest.items():
            if isinstance(v, dict) and v.get("isEntry"):
                entry = v
                break
    if not entry:
        return (f"{PUBLIC_BASE}main.js", [], [])

    def _url(p: str) -> str:
        return f"{PUBLIC_BASE}{p}"

    js_entry = _url(entry["file"])
    css_files = [_url(p) for p in entry.get("css", [])]

    preload = []
    seen = set()
    def walk(chunk: dict):
        for imp in (chunk.get("imports") or []):
            if imp in seen:
                continue
            seen.add(imp)
            sub = manifest.get(imp)
            if sub and "file" in sub:
                preload.append(_url(sub["file"]))
                walk(sub)
    if isinstance(entry, dict):
        walk(entry)
    return (js_entry, css_files, preload)

def _redirect(to: str):
    frappe.local.flags.redirect_location = to
    raise frappe.Redirect


def get_context(context):
    user = frappe.session.user
    path = frappe.request.path if hasattr(frappe, "request") else "/portal/guardian"

    if not user or user == "Guest":
        _redirect(f"/login?redirect-to={path}")

    user_roles = set(frappe.get_roles(user))

    # Check if user has Guardian role
    is_guardian = "Guardian" in user_roles

    # If user is not a guardian, they shouldn't be on this route
    # Redirect to main portal which will handle role-based routing
    if not is_guardian:
        _redirect("/portal")

    # Determine available portal sections for the user
    is_employee = (
        ("Employee" in user_roles)
        and bool(frappe.db.exists("Employee", {"user_id": user, "employment_status": "Active"}))
    )
    is_student = "Student" in user_roles

    portal_sections = []
    if is_employee:
        portal_sections.append("Staff")
    if is_student:
        portal_sections.append("Student")
    if is_guardian:
        portal_sections.append("Guardian")

    # Force guardian as default for this route
    context.default_portal = "guardian"
    context.portal_roles = portal_sections
    context.portal_roles_json = frappe.as_json(portal_sections)

    manifest = _load_manifest()
    js_entry, css_files, preload_files = _collect_assets(manifest)

    context.csrf_token = frappe.sessions.get_csrf_token()
    context.vite_js = js_entry
    context.vite_css = css_files
    context.vite_preload = preload_files
    return context
