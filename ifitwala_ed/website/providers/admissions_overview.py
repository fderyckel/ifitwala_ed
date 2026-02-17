# ifitwala_ed/website/providers/admissions_overview.py

from ifitwala_ed.utilities.html_sanitizer import sanitize_html


def get_context(*, school, page, block_props):
    content = block_props.get("content_html") or ""
    return {
        "data": {
            "heading": block_props.get("heading"),
            "content": sanitize_html(content, allow_headings_from="h2"),
            "max_width": block_props.get("max_width") or "normal",
        }
    }
