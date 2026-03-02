# ifitwala_ed/patches/website/p12_move_admissions_to_canonical_namespaces.py

import frappe

WEB_FORM_ROUTE_MAP = {
    "inquiry": "apply/inquiry",
}

LEGACY_INQUIRY_ROUTES = {"", "/inquiry", "/apply/inquiry", "/admissions/inquiry"}
LEGACY_APPLY_ROUTES = {"", "/admissions", "/portal/admissions"}


def _reload_public_web_forms():
    for module, dt, docname in (("admission", "web_form", "inquiry"),):
        try:
            frappe.reload_doc(module, dt, docname)
        except Exception:
            # Some sites may already have synced metadata.
            pass


def _sync_web_form_routes():
    for web_form_name, web_form_route in WEB_FORM_ROUTE_MAP.items():
        if not frappe.db.exists("Web Form", web_form_name):
            continue

        frappe.db.set_value(
            "Web Form",
            web_form_name,
            {
                "anonymous": 1,
                "login_required": 0,
                "published": 1,
                "apply_document_permissions": 0,
                "route": web_form_route,
            },
            update_modified=False,
        )


def _sync_school_admissions_defaults():
    if not frappe.db.table_exists("School"):
        return

    has_inquiry_route = frappe.db.has_column("School", "admissions_inquiry_route")
    has_apply_route = frappe.db.has_column("School", "admissions_apply_route")
    if not has_inquiry_route and not has_apply_route:
        # Pre-model patch safety: columns may not exist yet on some sites.
        return

    fields = ["name"]
    if has_inquiry_route:
        fields.append("admissions_inquiry_route")
    if has_apply_route:
        fields.append("admissions_apply_route")

    schools = frappe.get_all("School", fields=fields)
    for school in schools:
        updates = {}
        current_inquiry = (school.get("admissions_inquiry_route") or "").strip()
        current_apply = (school.get("admissions_apply_route") or "").strip()

        if has_inquiry_route and current_inquiry in LEGACY_INQUIRY_ROUTES:
            updates["admissions_inquiry_route"] = "/apply/inquiry"
        if has_apply_route and current_apply in LEGACY_APPLY_ROUTES:
            updates["admissions_apply_route"] = "/admissions"

        if updates:
            frappe.db.set_value("School", school.name, updates, update_modified=False)


def execute():
    _reload_public_web_forms()
    _sync_web_form_routes()
    _sync_school_admissions_defaults()
