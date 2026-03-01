# ifitwala_ed/www/admissions/recommendation/index.py

import frappe


def _token_from_path(path: str | None) -> str:
    text = (path or "").rstrip("/")
    if not text:
        return ""
    segments = [segment for segment in text.split("/") if segment]
    for index, segment in enumerate(segments):
        if segment != "recommendation":
            continue
        if index + 1 >= len(segments):
            return ""
        return "/".join(segments[index + 1 :]).strip()
    return ""


def get_context(context):
    path = frappe.request.path if hasattr(frappe, "request") else ""
    token = _token_from_path(path)

    context.no_cache = 1
    context.noindex = 1
    context.title = "Recommendation Intake"
    context.recommendation_token = token
    context.token_missing = not bool(token)
    return context
