# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.utilities.image_utils import ensure_guardian_profile_image


def execute():
    if not frappe.db.table_exists("Guardian") or not frappe.db.table_exists("File"):
        return

    guardian_rows = frappe.get_all(
        "Guardian",
        filters={"guardian_image": ["is", "set"]},
        fields=["name", "guardian_image", "organization"],
        limit=100000,
    )

    for row in guardian_rows:
        guardian_name = str(row.get("name") or "").strip()
        guardian_image = str(row.get("guardian_image") or "").strip()
        if not guardian_name or not guardian_image:
            continue

        try:
            ensure_guardian_profile_image(
                guardian_name,
                original_url=guardian_image,
                organization=row.get("organization"),
                upload_source="API",
            )
        except Exception:
            frappe.log_error(
                frappe.as_json(
                    {
                        "error": "guardian_profile_image_backfill_failed",
                        "guardian": guardian_name,
                        "guardian_image": guardian_image,
                    },
                    indent=2,
                ),
                "Guardian Profile Image Backfill Failed",
            )
