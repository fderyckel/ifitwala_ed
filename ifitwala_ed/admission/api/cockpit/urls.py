# ifitwala_ed/admission/api/cockpit/urls.py

from __future__ import annotations

from urllib.parse import quote

import frappe

from ifitwala_ed.admission.api.cockpit.access import _to_text


def _desk_route_slug(doctype: str) -> str:
    return frappe.scrub(doctype).replace("_", "-")


def _doc_url(doctype: str, name: str) -> str:
    return f"/desk/{_desk_route_slug(doctype)}/{quote(_to_text(name), safe='')}"


def _new_doc_url(doctype: str, params: dict[str, str] | None = None) -> str:
    slug = _desk_route_slug(doctype)
    base = f"/desk/{slug}/new-{slug}-1"
    if not params:
        return base

    query = "&".join(
        f"{quote(_to_text(key), safe='')}={quote(_to_text(value), safe='')}"
        for key, value in params.items()
        if _to_text(key) and _to_text(value)
    )
    if not query:
        return base
    return f"{base}?{query}"


def _target(
    *,
    doctype: str,
    name: str | None = None,
    target_label: str,
    params: dict[str, str] | None = None,
    is_new: bool = False,
) -> dict:
    if is_new:
        url = _new_doc_url(doctype, params=params)
    elif name:
        url = _doc_url(doctype, name)
    else:
        url = f"/desk/{_desk_route_slug(doctype)}"

    return {
        "target_doctype": doctype,
        "target_name": _to_text(name),
        "target_url": url,
        "target_label": target_label,
    }


def _applicant_workspace_target(
    *,
    applicant_name: str,
    target_label: str,
    document_type: str | None = None,
    applicant_document: str | None = None,
    document_item: str | None = None,
) -> dict:
    target = _target(
        doctype="Student Applicant",
        name=applicant_name,
        target_label=target_label,
    )
    target.update(
        {
            "workspace_mode": "applicant",
            "workspace_student_applicant": applicant_name,
            "workspace_document_type": _to_text(document_type) or None,
            "workspace_applicant_document": _to_text(applicant_document) or None,
            "workspace_document_item": _to_text(document_item) or None,
        }
    )
    return target
