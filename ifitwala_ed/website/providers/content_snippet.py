# ifitwala_ed/website/providers/content_snippet.py

import frappe
from frappe import _

from ifitwala_ed.utilities.html_sanitizer import sanitize_html


def _find_snippet_name(filters: dict) -> str | None:
    rows = frappe.get_all(
        "Website Snippet",
        filters=filters,
        fields=["name"],
        order_by="modified desc",
        limit_page_length=2,
    )
    if len(rows) > 1:
        frappe.log_error(
            title="Website Snippet Scope Collision",
            message=(f"Multiple Website Snippets found for filters={filters}. Using most recently modified."),
        )
    return rows[0].name if rows else None


def _get_snippet(snippet_id: str, school):
    snippet_id = (snippet_id or "").strip()
    if not snippet_id:
        return None

    organization = school.organization if school else None

    if school:
        name = _find_snippet_name({"snippet_id": snippet_id, "scope_type": "School", "school": school.name})
        if name:
            return frappe.get_doc("Website Snippet", name)

    if organization:
        name = _find_snippet_name(
            {
                "snippet_id": snippet_id,
                "scope_type": "Organization",
                "organization": organization,
            }
        )
        if name:
            return frappe.get_doc("Website Snippet", name)

    name = _find_snippet_name({"snippet_id": snippet_id, "scope_type": "Global"})
    if name:
        return frappe.get_doc("Website Snippet", name)
    return None


def get_context(*, school, page, block_props):
    snippet_id = block_props.get("snippet_id")
    snippet = _get_snippet(snippet_id, school)
    if not snippet:
        frappe.throw(
            _("Content snippet not found or not available for this scope."),
            frappe.ValidationError,
        )

    content = sanitize_html(snippet.content or "", allow_headings_from="h2")
    return {
        "data": {
            "content": content,
        }
    }
