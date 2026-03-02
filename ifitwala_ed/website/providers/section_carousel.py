# ifitwala_ed/website/providers/section_carousel.py

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.utilities.html_sanitizer import sanitize_html
from ifitwala_ed.website.utils import build_image_variants, validate_cta_link

LAYOUTS = {"content_left", "content_right"}


def get_context(*, school, page, block_props):
    items = []
    for row in block_props.get("items") or []:
        image_url = (row.get("image") or "").strip()
        if not image_url:
            continue
        items.append(
            {
                "image": build_image_variants(image_url, "school"),
                "alt": row.get("alt") or row.get("caption") or block_props.get("heading") or _("Section image"),
                "caption": row.get("caption"),
            }
        )

    if not items:
        frappe.throw(
            _("Section Carousel requires at least one image item."),
            frappe.ValidationError,
        )

    layout = (block_props.get("layout") or "content_left").strip()
    if layout not in LAYOUTS:
        layout = "content_left"

    return {
        "data": {
            "heading": block_props.get("heading"),
            "content": sanitize_html(block_props.get("content_html") or "", allow_headings_from="h3"),
            "layout": layout,
            "items": items,
            "autoplay": bool(block_props.get("autoplay", True)),
            "interval": max(cint(block_props.get("interval") or 5000), 1000),
            "cta_label": block_props.get("cta_label"),
            "cta_link": validate_cta_link(block_props.get("cta_link")),
        }
    }
