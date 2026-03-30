# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe


def _build_legacy_default_admissions_blocks(*, school) -> list[dict]:
    return [
        {
            "block_type": "admissions_overview",
            "props": {
                "heading": "Admissions",
                "content_html": f"<p>{school.school_name} welcomes families who value curiosity, care, and growth.</p>",
                "max_width": "normal",
            },
        },
        {
            "block_type": "admissions_steps",
            "props": {
                "steps": [
                    {
                        "key": "inquire",
                        "title": "Inquire",
                        "description": "Start the conversation.",
                        "icon": "mail",
                    },
                    {
                        "key": "visit",
                        "title": "Visit",
                        "description": "Experience our campus.",
                        "icon": "map",
                    },
                    {
                        "key": "apply",
                        "title": "Apply",
                        "description": "Begin the application.",
                        "icon": "file-text",
                    },
                ],
                "layout": "horizontal",
            },
        },
        {
            "block_type": "admission_cta",
            "props": {
                "intent": "inquire",
                "style": "primary",
                "label_override": (school.label_cta_inquiry or "").strip() or "Inquire",
            },
        },
        {
            "block_type": "admission_cta",
            "props": {
                "intent": "visit",
                "style": "secondary",
                "label_override": (school.label_cta_roi or "").strip() or "Visit",
            },
        },
        {
            "block_type": "admission_cta",
            "props": {
                "intent": "apply",
                "style": "outline",
            },
        },
    ]


def _normalize_page_blocks(page) -> list[dict]:
    blocks = []
    for row in page.blocks or []:
        try:
            props = json.loads((row.props or "").strip() or "{}")
        except Exception:
            return []
        blocks.append({"block_type": row.block_type, "props": props})
    return blocks


def _looks_like_legacy_default_admissions_page(*, page, school) -> bool:
    if (page.route or "").strip() != "admissions":
        return False
    if (page.page_type or "").strip() != "Admissions":
        return False
    return _normalize_page_blocks(page) == _build_legacy_default_admissions_blocks(school=school)


def execute():
    if not frappe.db.table_exists("School Website Page"):
        return

    from ifitwala_ed.website.bootstrap import _append_blocks, _build_admissions_blocks

    page_names = frappe.get_all(
        "School Website Page",
        filters={"route": "admissions", "page_type": "Admissions"},
        pluck="name",
        limit=100000,
    )
    for page_name in page_names:
        page = frappe.get_doc("School Website Page", page_name)
        school = frappe.get_doc("School", page.school)
        if not _looks_like_legacy_default_admissions_page(page=page, school=school):
            continue

        page.set("blocks", [])
        _append_blocks(page, _build_admissions_blocks(school=school))
        page.save(ignore_permissions=True)
