# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.utilities.image_utils import (
    PROFILE_IMAGE_DERIVATIVE_SLOTS,
    ensure_employee_profile_image,
    get_employee_image_variants_map,
    get_employee_user_avatar_url,
)


def execute():
    if not frappe.db.table_exists("Employee") or not frappe.db.table_exists("User"):
        return

    employee_rows = frappe.get_all(
        "Employee",
        fields=["name", "user_id", "employee_image"],
        filters={
            "user_id": ["is", "set"],
            "employee_image": ["is", "set"],
        },
        order_by="creation asc, name asc",
        limit=0,
    )
    for row in employee_rows or []:
        _sync_employee_user_avatar(row)


def _sync_employee_user_avatar(row: dict) -> None:
    employee_name = str(row.get("name") or "").strip()
    user_id = str(row.get("user_id") or "").strip()
    original_url = str(row.get("employee_image") or "").strip()
    if not employee_name or not user_id or not original_url:
        return

    try:
        ensure_employee_profile_image(employee_name, original_url=original_url, upload_source="Patch")
        get_employee_image_variants_map(
            [employee_name],
            slots=PROFILE_IMAGE_DERIVATIVE_SLOTS,
            request_missing_derivatives=True,
        )
        avatar_url = get_employee_user_avatar_url(employee_name, original_url=original_url)
        if not avatar_url:
            return
        if not frappe.db.exists("User", user_id):
            _log_employee_user_avatar_backfill_failure(
                employee_name=employee_name,
                user_id=user_id,
                original_url=original_url,
                error="linked_user_missing",
            )
            return

        current_user_image = frappe.db.get_value("User", user_id, "user_image")
        if current_user_image == avatar_url:
            return

        frappe.db.set_value(
            "User",
            user_id,
            "user_image",
            avatar_url,
            update_modified=False,
        )
    except Exception:
        _log_employee_user_avatar_backfill_failure(
            employee_name=employee_name,
            user_id=user_id,
            original_url=original_url,
            error="sync_failed",
            traceback=frappe.get_traceback(),
        )


def _log_employee_user_avatar_backfill_failure(
    *,
    employee_name: str,
    user_id: str,
    original_url: str,
    error: str,
    traceback: str | None = None,
) -> None:
    frappe.log_error(
        frappe.as_json(
            {
                "error": error,
                "employee": employee_name,
                "user": user_id,
                "employee_image": original_url,
                "traceback": traceback,
            },
            indent=2,
        ),
        "Employee User Avatar Backfill Failed",
    )
