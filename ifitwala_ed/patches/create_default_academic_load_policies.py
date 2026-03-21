# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("School") or not frappe.db.table_exists("Academic Load Policy"):
        return

    from ifitwala_ed.school_settings.doctype.academic_load_policy.academic_load_policy import (
        ensure_default_policy_for_school,
    )

    for school in frappe.get_all("School", pluck="name"):
        ensure_default_policy_for_school(school, ignore_permissions=True)
