# ifitwala_ed/website/providers/faq.py

import json

import frappe
from frappe import _
from frappe.utils import strip_html

from ifitwala_ed.utilities.html_sanitizer import sanitize_html


def _is_published(page) -> bool:
    if hasattr(page, "status"):
        return page.status == "Published"
    if hasattr(page, "is_published"):
        return bool(page.is_published)
    return True


def get_context(*, school, page, block_props):
    items = block_props.get("items") or []
    if not items:
        frappe.throw(
            _("FAQ must contain at least one question."),
            frappe.ValidationError,
        )

    enable_schema = bool(block_props.get("enable_schema", True))
    collapsed = bool(block_props.get("collapsed_by_default", True))

    is_published = _is_published(page)
    clean_items = []
    for item in items:
        question = (item.get("question") or "").strip()
        answer_html = item.get("answer_html") or ""
        if is_published and (not question or not answer_html.strip()):
            frappe.throw(
                _("FAQ items require both question and answer."),
                frappe.ValidationError,
            )
        if not question and not answer_html.strip():
            continue

        clean_items.append(
            {
                "question": question,
                "answer_html": sanitize_html(answer_html, allow_headings_from="h3"),
            }
        )

    if enable_schema and len(clean_items) > 10:
        frappe.throw(
            _("FAQ schema limited to 10 items."),
            frappe.ValidationError,
        )

    schema_json = None
    if enable_schema and clean_items:
        schema_json = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": strip_html(item["answer_html"]),
                        },
                    }
                    for item in clean_items
                ],
            }
        )

    return {
        "data": {
            "items": clean_items,
            "enable_schema": enable_schema,
            "collapsed_by_default": collapsed,
            "schema_json": schema_json,
        }
    }
