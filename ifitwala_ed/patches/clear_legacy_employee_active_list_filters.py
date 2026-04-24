from __future__ import annotations

import json
from typing import Any

import frappe


def execute():
    if not frappe.db.table_exists("User Settings"):
        return

    rows = frappe.get_all(
        "User Settings",
        filters={"doctype": "Employee"},
        fields=["name", "data"],
        limit=0,
    )

    for row in rows:
        settings_name = str(row.get("name") or "").strip()
        if not settings_name:
            continue

        payload = _parse_settings_payload(row.get("data"))
        if payload is None:
            continue

        cleaned, changed = _clean_legacy_employee_filters(payload)
        if not changed:
            continue

        frappe.db.set_value(
            "User Settings",
            settings_name,
            "data",
            json.dumps(cleaned, separators=(",", ":")),
            update_modified=False,
        )


def _parse_settings_payload(value: Any) -> Any | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return json.loads(value)
        except ValueError:
            return None
    if isinstance(value, (dict, list)):
        return value
    return None


def _clean_legacy_employee_filters(payload: Any) -> tuple[Any, bool]:
    cleaned, changed, remove_self = _clean_value(payload)
    if remove_self:
        return {}, True
    return cleaned, changed


def _clean_value(value: Any) -> tuple[Any, bool, bool]:
    if _is_legacy_employee_active_filter(value):
        return None, True, True

    if isinstance(value, list):
        cleaned_items = []
        changed = False
        for item in value:
            cleaned_item, item_changed, remove_item = _clean_value(item)
            changed = changed or item_changed
            if remove_item:
                continue
            cleaned_items.append(cleaned_item)
        return cleaned_items, changed or len(cleaned_items) != len(value), False

    if isinstance(value, dict):
        cleaned_items = {}
        changed = False
        for key, item in value.items():
            cleaned_item, item_changed, remove_item = _clean_value(item)
            changed = changed or item_changed
            if remove_item:
                continue
            cleaned_items[key] = cleaned_item
        return cleaned_items, changed or len(cleaned_items) != len(value), False

    return value, False, False


def _is_legacy_employee_active_filter(value: Any) -> bool:
    parsed = _parse_filter(value)
    return bool(
        parsed
        and parsed["fieldname"] == "employment_status"
        and parsed["operator"] == "="
        and parsed["value"] == "Active"
    )


def _parse_filter(value: Any) -> dict[str, str] | None:
    if isinstance(value, list):
        if len(value) >= 4:
            fieldname = str(value[1] or "").strip()
            operator = str(value[2] or "").strip()
            filter_value = str(value[3] or "").strip()
            if fieldname:
                return {"fieldname": fieldname, "operator": operator, "value": filter_value}

        if len(value) == 3:
            fieldname = str(value[0] or "").strip()
            operator = str(value[1] or "").strip()
            filter_value = str(value[2] or "").strip()
            if fieldname:
                return {"fieldname": fieldname, "operator": operator, "value": filter_value}

    if isinstance(value, dict):
        fieldname = str(value.get("fieldname") or value.get("field") or "").strip()
        operator = str(value.get("operator") or value.get("condition") or "").strip()
        filter_value = str(value.get("value") or "").strip()
        if fieldname:
            return {"fieldname": fieldname, "operator": operator, "value": filter_value}

    return None
