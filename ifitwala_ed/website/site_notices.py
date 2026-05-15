from __future__ import annotations

import copy

import frappe
from frappe.utils.caching import redis_cache

from ifitwala_ed.utilities.html_sanitizer import sanitize_html


@redis_cache(ttl=300)
def _get_active_site_notice(school_name: str) -> dict[str, object] | None:
    rows = frappe.get_all(
        "Website Notice",
        filters={"school": school_name, "status": "Published"},
        fields=["name", "title", "style", "priority", "message_html", "button_label", "button_link"],
        order_by="priority desc, modified desc",
        limit=1,
    )
    if not rows:
        return None

    row = rows[0]
    return {
        "name": row.get("name"),
        "title": (row.get("title") or "").strip() or None,
        "style": (row.get("style") or "info").strip() or "info",
        "message_html": sanitize_html(row.get("message_html") or "", allow_headings_from="h3"),
        "button_label": (row.get("button_label") or "").strip() or None,
        "button_link": (row.get("button_link") or "").strip() or None,
    }


def invalidate_site_notice_cache(*_args, **_kwargs):
    clear_cache = getattr(_get_active_site_notice, "clear_cache", None)
    if callable(clear_cache):
        clear_cache()


def get_active_site_notice(*, school_name: str) -> dict[str, object] | None:
    if not (school_name or "").strip():
        return None
    return copy.deepcopy(_get_active_site_notice((school_name or "").strip()))
