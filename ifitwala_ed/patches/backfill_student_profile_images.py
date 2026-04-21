# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.utilities.image_utils import ensure_student_profile_image


def execute():
    if not frappe.db.table_exists("Student") or not frappe.db.table_exists("File"):
        return

    student_rows = frappe.get_all(
        "Student",
        filters={"student_image": ["is", "set"]},
        fields=["name", "student_image"],
        limit=100000,
    )

    for row in student_rows:
        student_name = str(row.get("name") or "").strip()
        student_image = str(row.get("student_image") or "").strip()
        if not student_name or not student_image:
            continue

        try:
            ensure_student_profile_image(
                student_name,
                original_url=student_image,
                upload_source="API",
            )
        except Exception:
            frappe.log_error(
                frappe.as_json(
                    {
                        "error": "student_profile_image_backfill_failed",
                        "student": student_name,
                        "student_image": student_image,
                    },
                    indent=2,
                ),
                "Student Profile Image Backfill Failed",
            )
