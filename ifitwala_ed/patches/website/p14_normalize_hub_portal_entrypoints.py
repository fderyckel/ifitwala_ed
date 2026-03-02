# ifitwala_ed/patches/website/p14_normalize_hub_portal_entrypoints.py

import frappe

from ifitwala_ed.routing.policy import canonical_path_for_section

PORTAL_SECTION_SUFFIXES = {"/staff", "/student", "/guardian"}

ROLE_HOME_PAGES = {
    "Desk User": canonical_path_for_section("staff"),
    "Employee": canonical_path_for_section("staff"),
    "Student": canonical_path_for_section("student"),
    "Guardian": canonical_path_for_section("guardian"),
}

LEGACY_PATH_MAP = {
    "/portal": "/hub",
    "/portal/hub": "/hub",
    "/portal/staff": canonical_path_for_section("staff"),
    "/portal/student": canonical_path_for_section("student"),
    "/portal/guardian": canonical_path_for_section("guardian"),
    "/portal/hub/staff": canonical_path_for_section("staff"),
    "/portal/hub/student": canonical_path_for_section("student"),
    "/portal/hub/guardian": canonical_path_for_section("guardian"),
    "/portal/admissions": "/admissions",
    "/staff": canonical_path_for_section("staff"),
    "/student": canonical_path_for_section("student"),
    "/guardian": canonical_path_for_section("guardian"),
}


def _normalize_path(path: str | None) -> str:
    value = (path or "").strip()
    if not value:
        return ""

    if not value.startswith("/"):
        value = f"/{value}"
    if len(value) > 1 and value.endswith("/"):
        value = value[:-1]

    if value in LEGACY_PATH_MAP:
        return LEGACY_PATH_MAP[value]

    if value.startswith("/portal/hub/"):
        suffix = value[len("/portal/hub") :]
        if suffix in PORTAL_SECTION_SUFFIXES:
            return f"/hub{suffix}"

    if value.startswith("/portal/"):
        suffix = value[len("/portal") :]
        if suffix in PORTAL_SECTION_SUFFIXES:
            return f"/hub{suffix}"

    return value


def _sync_role_home_pages() -> None:
    if not frappe.db.table_exists("Role") or not frappe.db.has_column("Role", "home_page"):
        return

    for role_name, canonical_path in ROLE_HOME_PAGES.items():
        if not frappe.db.exists("Role", role_name):
            continue

        current = (frappe.db.get_value("Role", role_name, "home_page") or "").strip()
        target = _normalize_path(current) or canonical_path
        if target != current:
            frappe.db.set_value("Role", role_name, "home_page", target, update_modified=False)


def _sync_user_home_pages() -> None:
    if not frappe.db.table_exists("User") or not frappe.db.has_column("User", "home_page"):
        return

    users = frappe.get_all(
        "User",
        fields=["name", "home_page"],
        filters={"home_page": ["!=", ""]},
        limit_page_length=0,
    )
    for row in users:
        current = (row.get("home_page") or "").strip()
        if not current:
            continue

        target = _normalize_path(current)
        if target != current:
            frappe.db.set_value("User", row["name"], "home_page", target, update_modified=False)


def _sync_workspace_shortcuts() -> None:
    if not frappe.db.table_exists("Workspace Shortcut") or not frappe.db.has_column("Workspace Shortcut", "url"):
        return

    filters = {}
    if frappe.db.has_column("Workspace Shortcut", "type"):
        filters["type"] = "URL"

    rows = frappe.get_all(
        "Workspace Shortcut",
        fields=["name", "url"],
        filters=filters,
        limit_page_length=0,
    )
    for row in rows:
        current = (row.get("url") or "").strip()
        if not current:
            continue

        target = _normalize_path(current)
        if target != current:
            frappe.db.set_value("Workspace Shortcut", row["name"], "url", target, update_modified=False)


def _sync_website_route_redirects() -> None:
    if not frappe.db.exists("DocType", "Website Route Redirect"):
        return
    if not frappe.db.has_column("Website Route Redirect", "source"):
        return
    if not frappe.db.has_column("Website Route Redirect", "target"):
        return

    redirects = frappe.get_all(
        "Website Route Redirect",
        fields=["name", "source", "target"],
        limit_page_length=0,
    )
    for row in redirects:
        updates = {}
        source = (row.get("source") or "").strip()
        target = (row.get("target") or "").strip()

        if source:
            normalized_source = _normalize_path(source)
            if normalized_source != source:
                updates["source"] = normalized_source

        if target:
            normalized_target = _normalize_path(target)
            if normalized_target != target:
                updates["target"] = normalized_target

        if updates:
            frappe.db.set_value("Website Route Redirect", row["name"], updates, update_modified=False)


def execute():
    _sync_role_home_pages()
    _sync_user_home_pages()
    _sync_workspace_shortcuts()
    _sync_website_route_redirects()
