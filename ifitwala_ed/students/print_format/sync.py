# ifitwala_ed/students/print_format/sync.py

from __future__ import annotations

import json
from pathlib import Path

STUDENT_PROFILE_PRINT_FORMAT_PATH = Path(__file__).resolve().parent / "student_profile" / "student_profile.json"

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


def load_student_profile_print_format_payload() -> dict:
    return json.loads(STUDENT_PROFILE_PRINT_FORMAT_PATH.read_text(encoding="utf-8"))


def get_student_profile_print_format_values() -> dict:
    payload = load_student_profile_print_format_payload()
    return {field: payload[field] for field in MANAGED_PRINT_FORMAT_FIELDS}


def sync_student_profile_print_format() -> bool:
    import frappe

    payload = load_student_profile_print_format_payload()
    values = get_student_profile_print_format_values()
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
