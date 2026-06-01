# ifitwala_ed/admission/api/timeline/endpoints.py

from __future__ import annotations

import frappe


@frappe.whitelist()
def get_admissions_timeline_context(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    limit: int | str | None = None,
) -> dict:
    from ifitwala_ed.admission.api.timeline.context import get_admissions_timeline_context_impl

    return get_admissions_timeline_context_impl(
        context_doctype=context_doctype,
        context_name=context_name,
        limit=limit,
    )


__all__ = [
    "get_admissions_timeline_context",
]
