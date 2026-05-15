# ifitwala_ed/website/providers/rich_text.py

from ifitwala_ed.utilities.html_sanitizer import sanitize_html


def get_context(*, school, page, block_props):
    """
    Rich text editorial content. Sanitized, no H1 allowed.
    """
    content = block_props.get("content_html") or block_props.get("content") or ""
    return {
        "data": {
            "content": sanitize_html(content, allow_headings_from="h2"),
            "max_width": block_props.get("max_width") or "normal",
        }
    }
