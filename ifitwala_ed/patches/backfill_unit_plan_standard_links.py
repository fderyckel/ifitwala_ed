# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import defaultdict

import frappe

from ifitwala_ed.curriculum import planning


def execute():
    if not frappe.db.table_exists("Learning Unit Standard Alignment"):
        return
    if not frappe.db.table_exists("Learning Standards"):
        return

    catalog_rows_by_name, catalog_rows_by_code = _learning_standard_catalog()
    alignment_rows = frappe.get_all(
        "Learning Unit Standard Alignment",
        fields=["name", "learning_standard", *planning.LEARNING_STANDARD_CATALOG_FIELDS],
        order_by="creation asc, name asc",
        limit=0,
    )
    for row in alignment_rows or []:
        updates = _repair_alignment_row(
            row=row,
            catalog_rows_by_name=catalog_rows_by_name,
            catalog_rows_by_code=catalog_rows_by_code,
        )
        if not updates:
            continue
        frappe.db.set_value(
            "Learning Unit Standard Alignment",
            planning.normalize_text(row.get("name")),
            updates,
            update_modified=False,
        )


def _learning_standard_catalog() -> tuple[dict[str, dict[str, str | None]], dict[str, list[dict[str, str | None]]]]:
    rows = frappe.get_all(
        "Learning Standards",
        fields=["name", *planning.LEARNING_STANDARD_CATALOG_FIELDS],
        order_by="name asc",
        limit=0,
    )
    by_name: dict[str, dict[str, str | None]] = {}
    by_code: dict[str, list[dict[str, str | None]]] = defaultdict(list)
    for row in rows or []:
        normalized = _normalize_catalog_row(row)
        learning_standard = normalized.get("learning_standard")
        if not learning_standard:
            continue
        by_name[learning_standard] = normalized
        standard_code = planning.normalize_text(normalized.get("standard_code"))
        if standard_code:
            by_code[standard_code].append(normalized)
    return by_name, dict(by_code)


def _normalize_catalog_row(row: dict | None) -> dict[str, str | None]:
    payload = {
        fieldname: planning.normalize_long_text((row or {}).get(fieldname))
        if fieldname == "standard_description"
        else planning.normalize_text((row or {}).get(fieldname)) or None
        for fieldname in planning.LEARNING_STANDARD_CATALOG_FIELDS
    }
    payload["learning_standard"] = (
        planning.normalize_text((row or {}).get("learning_standard") or (row or {}).get("name")) or None
    )
    return payload


def _catalog_rows_match(candidate: dict[str, str | None], row: dict[str, str | None]) -> bool:
    for fieldname in planning.LEARNING_STANDARD_CATALOG_FIELDS:
        expected = row.get(fieldname)
        if expected in (None, ""):
            continue
        if candidate.get(fieldname) != expected:
            return False
    return True


def _repair_alignment_row(
    *,
    row: dict,
    catalog_rows_by_name: dict[str, dict[str, str | None]],
    catalog_rows_by_code: dict[str, list[dict[str, str | None]]],
) -> dict[str, str | None] | None:
    normalized = _normalize_catalog_row(row)
    linked_name = normalized.get("learning_standard")
    if linked_name and linked_name in catalog_rows_by_name:
        return None

    candidate_codes = [
        candidate
        for candidate in (
            planning.normalize_text(linked_name),
            planning.normalize_text(normalized.get("standard_code")),
        )
        if candidate
    ]
    seen_candidates: set[str] = set()
    candidates: list[dict[str, str | None]] = []
    for code in candidate_codes:
        for candidate in catalog_rows_by_code.get(code, []):
            learning_standard = planning.normalize_text(candidate.get("learning_standard"))
            if not learning_standard or learning_standard in seen_candidates:
                continue
            candidates.append(candidate)
            seen_candidates.add(learning_standard)

    if not candidates:
        return None

    if len(candidates) > 1:
        candidates = [candidate for candidate in candidates if _catalog_rows_match(candidate, normalized)]
    if len(candidates) != 1:
        return None

    resolved = candidates[0]
    return {
        "learning_standard": resolved.get("learning_standard"),
        **{fieldname: resolved.get(fieldname) for fieldname in planning.LEARNING_STANDARD_CATALOG_FIELDS},
    }
