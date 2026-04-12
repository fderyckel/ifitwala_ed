from __future__ import annotations

import json
from pathlib import Path

STAFF_CALENDAR_PRINT_FORMAT_PATH = (
    Path(__file__).resolve().parent / "staff_calendar_print" / "staff_calendar_print.json"
)
STAFF_CALENDAR_TEMPLATE_PATH = Path(__file__).resolve().parent / "staff_calendar_print" / "staff_calendar_print.html"
STAFF_CALENDAR_CSS_PATH = Path(__file__).resolve().parent / "staff_calendar_print" / "staff_calendar_print.css"

MANAGED_PRINT_FORMAT_FIELDS = (
    "absolute_value",
    "align_labels_right",
    "css",
    "custom_format",
    "default_print_language",
    "disabled",
    "doc_type",
    "docstatus",
    "font_size",
    "html",
    "idx",
    "line_breaks",
    "margin_bottom",
    "margin_left",
    "margin_right",
    "margin_top",
    "module",
    "page_number",
    "pdf_generator",
    "print_format_builder",
    "print_format_builder_beta",
    "print_format_for",
    "print_format_type",
    "raw_printing",
    "show_section_headings",
    "standard",
)


def load_staff_calendar_print_format_payload() -> dict:
    payload = json.loads(STAFF_CALENDAR_PRINT_FORMAT_PATH.read_text(encoding="utf-8"))
    payload["html"] = STAFF_CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    payload["css"] = STAFF_CALENDAR_CSS_PATH.read_text(encoding="utf-8").strip()
    return payload


def get_staff_calendar_print_format_values() -> dict:
    payload = load_staff_calendar_print_format_payload()
    return {field: payload[field] for field in MANAGED_PRINT_FORMAT_FIELDS}


def sync_staff_calendar_print_format() -> bool:
    import frappe

    payload = load_staff_calendar_print_format_payload()
    values = get_staff_calendar_print_format_values()
    name = payload["name"]

    if frappe.db.exists("Print Format", name):
        doc = frappe.get_doc("Print Format", name)
        changed = False
        for fieldname, value in values.items():
            if doc.get(fieldname) != value:
                doc.set(fieldname, value)
                changed = True

        if not changed:
            return False

        doc.flags.ignore_permissions = True
        doc.save()
        return True

    doc = frappe.get_doc(
        {
            "doctype": "Print Format",
            "name": name,
            **values,
        }
    )
    doc.insert(ignore_permissions=True)
    return True
