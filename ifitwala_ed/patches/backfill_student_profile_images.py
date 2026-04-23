# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.utilities.image_utils import ensure_student_profile_image


def execute():
    if not frappe.db.table_exists("Student"):
        return

    student_rows = frappe.get_all(
        "Student",
        fields=["name", "student_image"],
        filters={"student_image": ["is", "set"]},
        order_by="creation asc, name asc",
        limit=0,
    )
    for row in student_rows or []:
        student_name = str(row.get("name") or "").strip()
        original_url = str(row.get("student_image") or "").strip()
        if not student_name or not original_url:
            continue
        ensure_student_profile_image(student_name, original_url=original_url, upload_source="Patch")
