# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.utilities.image_utils import (
    PROFILE_IMAGE_DERIVATIVE_SLOTS,
    ensure_employee_profile_image,
    get_employee_image_variants_map,
)
from ifitwala_ed.website.public_people import invalidate_public_people_cache


def execute():
    if not frappe.db.table_exists("Employee"):
        return

    employee_rows = frappe.get_all(
        "Employee",
        fields=["name", "employee_image"],
        filters={
            "show_on_website": 1,
            "employee_image": ["is", "set"],
        },
        order_by="creation asc, name asc",
        limit=0,
    )

    repaired_any = False
    for row in employee_rows or []:
        repaired_any = _backfill_public_employee_profile_image(row) or repaired_any

    if repaired_any:
        invalidate_public_people_cache()


def _backfill_public_employee_profile_image(row: dict) -> bool:
    employee_name = str(row.get("name") or "").strip()
    original_url = str(row.get("employee_image") or "").strip()
    if not employee_name or not original_url:
        return False

    try:
        ensured_url = ensure_employee_profile_image(
            employee_name,
            original_url=original_url,
            upload_source="Patch",
        )
        if not ensured_url:
            return False

        get_employee_image_variants_map(
            [employee_name],
            slots=PROFILE_IMAGE_DERIVATIVE_SLOTS,
            request_missing_derivatives=True,
        )
        return True
    except Exception:
        _log_public_employee_profile_image_backfill_failure(
            employee_name=employee_name,
            original_url=original_url,
            traceback=frappe.get_traceback(),
        )
        return False


def _log_public_employee_profile_image_backfill_failure(
    *,
    employee_name: str,
    original_url: str,
    traceback: str | None = None,
) -> None:
    frappe.log_error(
        frappe.as_json(
            {
                "error": "public_employee_profile_image_sync_failed",
                "employee": employee_name,
                "employee_image": original_url,
                "traceback": traceback,
            },
            indent=2,
        ),
        "Public Employee Profile Image Backfill Failed",
    )
