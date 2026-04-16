from __future__ import annotations

import json
from pathlib import Path

DEFAULT_SCHOOL_LETTER_HEAD_PATH = Path(__file__).resolve().parent / "default_school_letter_head.json"
DEFAULT_SCHOOL_LETTER_HEAD_TEMPLATE_PATH = Path(__file__).resolve().parent / "default_school_letter_head.html"
DEFAULT_SCHOOL_LETTER_HEAD_CSS_PATH = Path(__file__).resolve().parent / "default_school_letter_head.css"

MANAGED_LETTER_HEAD_FIELDS = (
    "align",
    "content",
    "disabled",
    "footer",
    "footer_align",
    "footer_script",
    "footer_source",
    "header_script",
    "is_default",
    "source",
)


def load_default_school_letter_head_payload() -> dict:
    payload = json.loads(DEFAULT_SCHOOL_LETTER_HEAD_PATH.read_text(encoding="utf-8"))
    template = DEFAULT_SCHOOL_LETTER_HEAD_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    css = DEFAULT_SCHOOL_LETTER_HEAD_CSS_PATH.read_text(encoding="utf-8").strip()
    payload["content"] = f"<style>\n{css}\n</style>\n{template}"
    payload["footer"] = (payload.get("footer") or "").strip()
    return payload


def get_default_school_letter_head_values() -> dict:
    payload = load_default_school_letter_head_payload()
    return {field: payload[field] for field in MANAGED_LETTER_HEAD_FIELDS}


def sync_default_school_letter_head() -> bool:
    import frappe

    payload = load_default_school_letter_head_payload()
    values = get_default_school_letter_head_values()
    name = payload["letter_head_name"]

    if frappe.db.exists("Letter Head", name):
        doc = frappe.get_doc("Letter Head", name)
        if not _reconcile_letter_head_fields(doc, values):
            return False

        doc.flags.ignore_permissions = True
        doc.save()
        return True

    doc = frappe.get_doc(
        {
            "doctype": "Letter Head",
            "letter_head_name": name,
            **values,
        }
    )
    doc.insert(ignore_permissions=True)

    # Frappe v16 normalizes new Letter Head rows toward Image source during insert.
    # Re-load and reconcile immediately so the first sync leaves the managed HTML record in place.
    doc = frappe.get_doc("Letter Head", name)
    if _reconcile_letter_head_fields(doc, values):
        doc.flags.ignore_permissions = True
        doc.save()
    return True


def ensure_print_settings_with_letterhead() -> bool:
    import frappe

    settings = frappe.get_single("Print Settings")
    if int(settings.with_letterhead or 0) == 1:
        return False

    settings.with_letterhead = 1
    settings.save(ignore_permissions=True)
    return True


def _reconcile_letter_head_fields(doc, values: dict) -> bool:
    changed = False
    for fieldname, value in values.items():
        if doc.get(fieldname) != value:
            doc.set(fieldname, value)
            changed = True
    return changed
