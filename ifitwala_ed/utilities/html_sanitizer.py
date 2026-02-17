# ifitwala_ed/utilities/html_sanitizer.py

import re

from frappe.utils import sanitize_html as frappe_sanitize_html

_HEADING_RE = re.compile(r"<(\/?)(h[1-6])\b", re.IGNORECASE)


def _demote_headings(html: str, allow_headings_from: str) -> str:
    if allow_headings_from not in {"h2", "h3", "h4", "h5", "h6"}:
        return html

    min_level = int(allow_headings_from[1])

    def _replace(match: re.Match) -> str:
        slash, tag = match.groups()
        level = int(tag[1])
        if level < min_level:
            return f"<{slash}h{min_level}"
        return match.group(0)

    return _HEADING_RE.sub(_replace, html)


def sanitize_html(html: str, *, allow_headings_from: str = "h2") -> str:
    """
    Sanitize rich HTML and enforce heading floors (no H1 in body content).
    """
    cleaned = frappe_sanitize_html(html or "")
    return _demote_headings(cleaned, allow_headings_from)
