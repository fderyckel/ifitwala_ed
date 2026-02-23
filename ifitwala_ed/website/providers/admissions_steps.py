# ifitwala_ed/website/providers/admissions_steps.py

import frappe
from frappe import _
from frappe.utils import strip_html

VALID_KEYS = {"inquire", "visit", "apply"}


def get_context(*, school, page, block_props):
    steps = block_props.get("steps") or []
    if len(steps) < 2:
        frappe.throw(
            _("Admissions Steps must include at least two steps."),
            frappe.ValidationError,
        )

    clean_steps = []
    for step in steps:
        key = (step.get("key") or "").strip()
        title = (step.get("title") or "").strip()
        if not key or key not in VALID_KEYS:
            frappe.throw(
                _("Invalid admissions step key: {0}").format(key),
                frappe.ValidationError,
            )
        if not title:
            frappe.throw(
                _("Admissions step title is required."),
                frappe.ValidationError,
            )

        description = strip_html(step.get("description") or "").strip()
        clean_steps.append(
            {
                "key": key,
                "title": title,
                "description": description,
                "icon": step.get("icon"),
            }
        )

    layout = block_props.get("layout") or "horizontal"
    if layout not in {"horizontal", "vertical"}:
        frappe.throw(
            _("Invalid admissions steps layout: {0}").format(layout),
            frappe.ValidationError,
        )

    return {
        "data": {
            "steps": clean_steps,
            "layout": layout,
        }
    }
