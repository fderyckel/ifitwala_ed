# ifitwala_ed/patches/website/p15_normalize_website_block_props_to_current_contract.py

import json
import re
from typing import Any

import frappe

from ifitwala_ed.website.block_registry import get_block_definition_map

BOOLEAN_TRUE_VALUES = {"1", "true"}
BOOLEAN_FALSE_VALUES = {"0", "false"}
INTEGER_PATTERN = re.compile(r"^-?\d+$")


def _primary_type(schema: dict[str, Any] | None) -> str | None:
    if not isinstance(schema, dict):
        return None

    raw_type = schema.get("type")
    if isinstance(raw_type, list):
        for value in raw_type:
            if value != "null":
                return value
        return raw_type[0] if raw_type else None
    if isinstance(raw_type, str):
        return raw_type
    return None


def _coerce_boolean(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in BOOLEAN_TRUE_VALUES:
            return True
        if normalized in BOOLEAN_FALSE_VALUES:
            return False
    return value


def _coerce_integer(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if INTEGER_PATTERN.fullmatch(normalized):
            return int(normalized)
    return value


def _normalize_legacy_aliases(block_type: str, props: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(props)

    if block_type == "cta":
        if not normalized.get("button_label"):
            normalized["button_label"] = normalized.get("cta_label") or normalized.get("label") or ""
        if not normalized.get("button_link"):
            normalized["button_link"] = (
                normalized.get("cta_link") or normalized.get("url") or normalized.get("link") or ""
            )
        for legacy_key in ("cta_label", "cta_link", "label", "url", "link"):
            normalized.pop(legacy_key, None)

    elif block_type in {"rich_text", "admissions_overview"}:
        if not normalized.get("content_html") and normalized.get("content"):
            normalized["content_html"] = normalized.get("content")
        normalized.pop("content", None)

    elif block_type == "hero":
        primary_cta = normalized.get("primary_cta")
        cta = normalized.get("cta")
        if isinstance(primary_cta, dict):
            if not normalized.get("cta_label"):
                normalized["cta_label"] = primary_cta.get("label")
            if not normalized.get("cta_link"):
                normalized["cta_link"] = primary_cta.get("link") or primary_cta.get("url")
        if isinstance(cta, dict):
            if not normalized.get("cta_label"):
                normalized["cta_label"] = cta.get("label")
            if not normalized.get("cta_link"):
                normalized["cta_link"] = cta.get("link") or cta.get("url")
        normalized.pop("primary_cta", None)
        normalized.pop("cta", None)

    return normalized


def _coerce_props_to_schema(props: dict[str, Any], schema: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return props

    normalized = dict(props)
    properties = schema.get("properties") or {}
    for key, prop_schema in properties.items():
        if key not in normalized:
            continue

        primary_type = _primary_type(prop_schema)
        if primary_type == "boolean":
            normalized[key] = _coerce_boolean(normalized[key])
        elif primary_type == "integer":
            normalized[key] = _coerce_integer(normalized[key])

    return normalized


def _normalize_row_props(
    *, block_type: str, raw_props: str, definitions: dict[str, dict[str, Any]]
) -> tuple[str | None, str | None]:
    try:
        parsed = json.loads(raw_props)
    except Exception:
        return None, "invalid_json"

    if not isinstance(parsed, dict):
        return None, "not_object"

    normalized = _normalize_legacy_aliases(block_type, parsed)
    definition = definitions.get(block_type) or {}
    normalized = _coerce_props_to_schema(normalized, definition.get("props_schema"))

    if normalized == parsed:
        return None, None

    return json.dumps(normalized, indent=2), None


def execute():
    if not frappe.db.table_exists("School Website Page Block"):
        return
    if not frappe.db.has_column("School Website Page Block", "block_type"):
        return
    if not frappe.db.has_column("School Website Page Block", "props"):
        return
    if not frappe.db.exists("DocType", "School Website Page Block"):
        return

    definitions = get_block_definition_map()
    rows = frappe.get_all(
        "School Website Page Block",
        fields=["name", "block_type", "props"],
        filters={"props": ["!=", ""]},
        limit_page_length=0,
    )

    normalized_count = 0
    skipped_invalid_json = 0
    skipped_non_object = 0

    for row in rows:
        block_type = (row.get("block_type") or "").strip()
        raw_props = row.get("props")
        if not block_type or not raw_props or block_type not in definitions:
            continue

        normalized_props, error_code = _normalize_row_props(
            block_type=block_type,
            raw_props=raw_props,
            definitions=definitions,
        )
        if error_code == "invalid_json":
            skipped_invalid_json += 1
            continue
        if error_code == "not_object":
            skipped_non_object += 1
            continue
        if normalized_props is None:
            continue

        frappe.db.set_value(
            "School Website Page Block",
            row["name"],
            "props",
            normalized_props,
            update_modified=False,
        )
        normalized_count += 1

    frappe.logger("ifitwala_ed.website", allow_site=True).info(
        "Patch p15 normalized website block props to current contract: "
        "normalized=%s skipped_invalid_json=%s skipped_non_object=%s",
        normalized_count,
        skipped_invalid_json,
        skipped_non_object,
    )
