# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

_LEGACY_ROLE = "general_reference"
_CANONICAL_ROLE = "supporting_material"
_MATERIAL_SLOT = "material_file"


def execute():
    if not frappe.db.table_exists("Drive Binding"):
        return

    active_primary_keys = _active_primary_supporting_material_keys()
    legacy_rows = frappe.get_all(
        "Drive Binding",
        filters={
            "binding_doctype": "Supporting Material",
            "binding_role": _LEGACY_ROLE,
            "slot": _MATERIAL_SLOT,
        },
        fields=["name", "drive_file", "binding_doctype", "binding_name", "slot", "is_primary", "status"],
        order_by="creation asc, name asc",
        limit=0,
    )
    for row in legacy_rows or []:
        binding_name = str(row.get("name") or "").strip()
        if not binding_name:
            continue

        key = _binding_identity(row)
        values = {
            "binding_role": _CANONICAL_ROLE,
            "primary_key": _build_primary_key(row, _CANONICAL_ROLE),
        }
        if _is_active_primary(row) and key in active_primary_keys:
            values.update(
                {
                    "status": "superseded",
                    "is_primary": 0,
                    "primary_key": None,
                }
            )

        frappe.db.set_value("Drive Binding", binding_name, values, update_modified=False)


def _active_primary_supporting_material_keys() -> set[tuple[str, str, str, str]]:
    rows = frappe.get_all(
        "Drive Binding",
        filters={
            "binding_doctype": "Supporting Material",
            "binding_role": _CANONICAL_ROLE,
            "slot": _MATERIAL_SLOT,
            "status": "active",
            "is_primary": 1,
        },
        fields=["drive_file", "binding_doctype", "binding_name", "slot"],
        limit=0,
    )
    return {_binding_identity(row) for row in rows or [] if all(_binding_identity(row))}


def _binding_identity(row: dict) -> tuple[str, str, str, str]:
    return (
        str(row.get("drive_file") or "").strip(),
        str(row.get("binding_doctype") or "").strip(),
        str(row.get("binding_name") or "").strip(),
        str(row.get("slot") or "").strip(),
    )


def _is_active_primary(row: dict) -> bool:
    return str(row.get("status") or "").strip() == "active" and int(row.get("is_primary") or 0) == 1


def _build_primary_key(row: dict, binding_role: str) -> str | None:
    if not _is_active_primary(row):
        return None

    parts = (
        str(row.get("drive_file") or "").strip(),
        str(row.get("binding_doctype") or "").strip(),
        str(row.get("binding_name") or "").strip(),
        binding_role,
        str(row.get("slot") or "").strip(),
    )
    if not all(parts):
        return None
    return "|".join(parts)
