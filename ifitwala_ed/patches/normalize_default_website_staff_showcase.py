# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe

LEGACY_DEFAULT_TITLE = "Leadership & Administration"
LEGACY_DEFAULT_ROLES = ("Head", "Principal")
LEGACY_DEFAULT_KEYS = {"title", "roles", "limit"}
EXPECTED_LIMITS = {
    "/": 6,
    "about": 12,
}


def _looks_like_legacy_default_showcase_props(*, route: str, props: dict) -> bool:
    expected_limit = EXPECTED_LIMITS.get(route)
    if expected_limit is None:
        return False
    if set(props) - LEGACY_DEFAULT_KEYS:
        return False
    if (props.get("title") or "").strip() != LEGACY_DEFAULT_TITLE:
        return False
    if tuple(props.get("roles") or []) != LEGACY_DEFAULT_ROLES:
        return False
    return int(props.get("limit") or 0) == expected_limit


def execute():
    if not frappe.db.table_exists("School Website Page"):
        return

    from ifitwala_ed.website.bootstrap import build_default_staff_showcase_props

    page_names = frappe.get_all(
        "School Website Page",
        filters={"route": ["in", list(EXPECTED_LIMITS)]},
        pluck="name",
        limit=100000,
    )
    for page_name in page_names:
        page = frappe.get_doc("School Website Page", page_name)
        changed = False
        for row in page.blocks or []:
            if row.block_type != "leadership":
                continue
            try:
                props = json.loads((row.props or "").strip() or "{}")
            except Exception:
                continue
            if not isinstance(props, dict):
                continue
            if not _looks_like_legacy_default_showcase_props(route=page.route, props=props):
                continue

            row.props = json.dumps(build_default_staff_showcase_props(route=page.route), indent=2)
            changed = True

        if changed:
            page.save(ignore_permissions=True)
