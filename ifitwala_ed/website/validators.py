# ifitwala_ed/website/validators.py

import json

import frappe
from frappe import _

from ifitwala_ed.website.block_registry import get_allowed_block_types, get_block_definition_map
from ifitwala_ed.website.utils import parse_props, validate_props_schema


def normalize_block_props(*, block_type: str, props: dict) -> dict:
    """
    Backward-compatible prop aliases for legacy website records.
    Normalization happens before schema validation so old pages keep rendering.
    """
    normalized = dict(props or {})

    if block_type == "cta":
        if not normalized.get("button_label"):
            normalized["button_label"] = normalized.get("cta_label") or normalized.get("label") or ""
        if not normalized.get("button_link"):
            normalized["button_link"] = (
                normalized.get("cta_link") or normalized.get("url") or normalized.get("link") or ""
            )

    elif block_type == "rich_text":
        if not normalized.get("content_html") and normalized.get("content"):
            normalized["content_html"] = normalized.get("content")

    elif block_type == "admissions_overview":
        if not normalized.get("content_html") and normalized.get("content"):
            normalized["content_html"] = normalized.get("content")

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

    return normalized


def _sorted_enabled_blocks(page) -> list:
    rows = []
    for row in getattr(page, "blocks", None) or []:
        if int(getattr(row, "is_enabled", 0) or 0) != 1:
            continue
        rows.append(row)
    return sorted(rows, key=lambda row: ((row.order if row.order is not None else (row.idx or 0)), row.idx or 0))


def _validate_seo_h1_rules(*, blocks: list, definitions: dict):
    if not blocks:
        frappe.throw(
            _("Website Page must contain at least one content block."),
            frappe.ValidationError,
        )

    seo_roles = [definitions[block.block_type]["seo_role"] for block in blocks]
    owns_h1 = [role for role in seo_roles if role == "owns_h1"]
    if len(owns_h1) != 1:
        frappe.throw(
            _("Exactly one block must own the H1. Found {0}.").format(len(owns_h1)),
            frappe.ValidationError,
        )

    first_role = definitions[blocks[0].block_type]["seo_role"]
    if first_role != "owns_h1":
        frappe.throw(
            _("The first enabled block must own the H1."),
            frappe.ValidationError,
        )


def _get_parent_context(page) -> tuple[str, str]:
    parent_doctype = (getattr(page, "doctype", None) or "").strip()
    page_type = (getattr(page, "page_type", None) or "").strip()
    return parent_doctype, page_type


def _validate_context_allowed_blocks(*, page, blocks: list):
    parent_doctype, page_type = _get_parent_context(page)
    allowed_types = set(get_allowed_block_types(parent_doctype=parent_doctype, page_type=page_type))
    if not allowed_types:
        return

    disallowed = sorted(
        {(block.block_type or "").strip() for block in blocks if (block.block_type or "").strip() not in allowed_types}
    )
    if not disallowed:
        return

    context_label = parent_doctype or _("Unknown Parent")
    if parent_doctype == "School Website Page":
        context_label = _("{0} ({1})").format(
            parent_doctype,
            page_type or _("Standard"),
        )
    frappe.throw(
        _("Block type(s) not allowed for {0}: {1}").format(
            context_label,
            ", ".join(disallowed),
        ),
        frappe.ValidationError,
    )


def validate_page_blocks(page, *, normalize_legacy_props: bool = True):
    blocks = _sorted_enabled_blocks(page)
    definitions = get_block_definition_map()

    missing = sorted(
        {(block.block_type or "").strip() for block in blocks if (block.block_type or "").strip() not in definitions}
    )
    if missing:
        frappe.throw(
            _("Unknown block type: {0}").format(", ".join(missing)),
            frappe.ValidationError,
        )

    _validate_context_allowed_blocks(page=page, blocks=blocks)
    _validate_seo_h1_rules(blocks=blocks, definitions=definitions)

    for block in blocks:
        block_type = (block.block_type or "").strip()
        definition = definitions[block_type]

        props = parse_props(block.props)
        normalized = normalize_block_props(block_type=block_type, props=props)
        validate_props_schema(
            normalized,
            definition["props_schema"],
            block_type=block_type,
        )

        if normalize_legacy_props and normalized != props:
            block.props = json.dumps(normalized, indent=2)
