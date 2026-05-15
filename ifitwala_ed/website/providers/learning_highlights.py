# ifitwala_ed/website/providers/learning_highlights.py

import frappe
from frappe import _

from ifitwala_ed.website.utils import build_image_variants


def _sort_key(row):
    raw = getattr(row, "display_order", None)
    if raw not in (None, ""):
        try:
            return (0, int(raw), int(getattr(row, "idx", 0) or 0))
        except Exception:
            pass
    return (1, int(getattr(row, "idx", 0) or 0), 0)


def get_context(*, school, page, block_props):
    if page.doctype != "Course Website Profile":
        frappe.throw(
            _("Learning Highlights block is only allowed on Course pages."),
            frappe.ValidationError,
        )

    limit = block_props.get("limit")
    try:
        limit = int(limit) if limit not in (None, "") else None
    except Exception:
        limit = None

    rows = sorted(page.learning_highlights or [], key=_sort_key)
    if limit and limit > 0:
        rows = rows[:limit]

    items = []
    for row in rows:
        title = (getattr(row, "title", None) or "").strip()
        if not title:
            continue
        summary = (getattr(row, "summary", None) or "").strip()
        items.append(
            {
                "title": title,
                "summary": summary,
                "image": build_image_variants(getattr(row, "image", None), "course")
                if getattr(row, "image", None)
                else None,
            }
        )

    return {
        "data": {
            "heading": (block_props.get("heading") or "Learning Highlights").strip(),
            "items": items,
        }
    }
