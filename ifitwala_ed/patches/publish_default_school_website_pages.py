# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("School") or not frappe.db.table_exists("School Website Page"):
        return

    from ifitwala_ed.website.bootstrap import ensure_default_school_website

    school_names = frappe.get_all(
        "School",
        filters={"is_published": 1},
        pluck="name",
        limit=100000,
    )
    for school_name in school_names:
        ensure_default_school_website(
            school_name=school_name,
            set_default_organization=True,
        )
