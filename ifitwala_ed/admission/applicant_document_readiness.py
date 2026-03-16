# ifitwala_ed/admission/applicant_document_readiness.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.admission_utils import (
    get_applicant_scope_ancestors,
    is_applicant_document_type_in_scope,
)
from ifitwala_ed.api.file_access import resolve_admissions_file_open_url


def empty_document_review_payload() -> dict:
    return {
        "ok": False,
        "missing": [],
        "unapproved": [],
        "required": [],
        "required_rows": [],
        "uploaded_rows": [],
        "missing_rows": [],
        "unapproved_rows": [],
    }


def build_document_review_payload_for_applicant(
    *,
    student_applicant: str,
    organization: str | None = None,
    school: str | None = None,
) -> dict:
    applicant_name = _to_text(student_applicant)
    if not applicant_name:
        return empty_document_review_payload()

    payload_by_applicant = build_document_review_payload_batch(
        [
            {
                "name": applicant_name,
                "organization": _to_text(organization),
                "school": _to_text(school),
            }
        ]
    )
    return payload_by_applicant.get(applicant_name) or empty_document_review_payload()


def build_document_review_payload_batch(applicant_rows: list[dict]) -> dict[str, dict]:
    applicant_names = [_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))]
    if not applicant_names:
        return {}

    type_rows = frappe.get_all(
        "Applicant Document Type",
        filters={"is_active": 1},
        fields=[
            "name",
            "code",
            "document_type_name",
            "description",
            "is_required",
            "is_repeatable",
            "min_items_required",
            "organization",
            "school",
        ],
        limit_page_length=10000,
    )

    scope_cache: dict[tuple[str, str], tuple[set[str], set[str]]] = {}
    required_by_applicant: dict[str, list[dict]] = {}
    type_map_by_applicant: dict[str, dict[str, dict]] = {}
    out: dict[str, dict] = {}

    for applicant_row in applicant_rows:
        applicant_name = _to_text(applicant_row.get("name"))
        organization = _to_text(applicant_row.get("organization"))
        school = _to_text(applicant_row.get("school"))
        if not applicant_name:
            continue

        if not organization:
            out[applicant_name] = empty_document_review_payload()
            continue

        scope_key = (organization, school)
        if scope_key not in scope_cache:
            org_ancestors, school_ancestors = get_applicant_scope_ancestors(
                organization=organization,
                school=school,
            )
            scope_cache[scope_key] = (set(org_ancestors), set(school_ancestors))

        applicant_org_ancestors, applicant_school_ancestors = scope_cache[scope_key]
        in_scope_types = [
            row
            for row in type_rows
            if is_applicant_document_type_in_scope(
                document_type_organization=row.get("organization"),
                document_type_school=row.get("school"),
                applicant_org_ancestors=applicant_org_ancestors,
                applicant_school_ancestors=applicant_school_ancestors,
            )
        ]
        required_types = [row for row in in_scope_types if cint(row.get("is_required"))]

        required_by_applicant[applicant_name] = [
            {
                "document_type": _to_text(row.get("name")),
                "label": _document_requirement_label(row),
                "required_count": _required_count(row),
            }
            for row in required_types
            if _to_text(row.get("name"))
        ]
        type_map_by_applicant[applicant_name] = {
            _to_text(row.get("name")): row for row in in_scope_types if _to_text(row.get("name"))
        }

    document_rows = frappe.get_all(
        "Applicant Document",
        filters={"student_applicant": ["in", applicant_names]},
        fields=[
            "name",
            "student_applicant",
            "document_type",
            "document_label",
            "review_status",
            "reviewed_by",
            "reviewed_on",
            "requirement_override",
            "override_reason",
            "override_by",
            "override_on",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=10000,
    )

    document_rows_by_applicant: dict[str, list[dict]] = {name: [] for name in applicant_names}
    document_to_applicant: dict[str, str] = {}
    latest_document_by_applicant_type: dict[str, dict[str, dict]] = {name: {} for name in applicant_names}
    for row_doc in document_rows:
        applicant_name = _to_text(row_doc.get("student_applicant"))
        document_name = _to_text(row_doc.get("name"))
        document_type = _to_text(row_doc.get("document_type"))
        if not applicant_name:
            continue
        document_rows_by_applicant.setdefault(applicant_name, []).append(row_doc)
        if document_name:
            document_to_applicant[document_name] = applicant_name
        if applicant_name in latest_document_by_applicant_type and document_type:
            if document_type not in latest_document_by_applicant_type[applicant_name]:
                latest_document_by_applicant_type[applicant_name][document_type] = row_doc

    document_names = [_to_text(row.get("name")) for row in document_rows if _to_text(row.get("name"))]
    item_rows = (
        frappe.get_all(
            "Applicant Document Item",
            filters={"applicant_document": ["in", document_names]},
            fields=[
                "name",
                "applicant_document",
                "item_key",
                "item_label",
                "review_status",
                "reviewed_by",
                "reviewed_on",
                "modified",
            ],
            order_by="modified desc",
        )
        if document_names
        else []
    )

    item_names = [_to_text(row.get("name")) for row in item_rows if _to_text(row.get("name"))]
    latest_file_by_item: dict[str, dict] = {}
    if item_names:
        file_rows = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": ["in", item_names],
            },
            fields=["name", "attached_to_name", "file_url", "file_name", "creation", "owner"],
            order_by="creation desc",
        )
        for row_file in file_rows:
            item_name = _to_text(row_file.get("attached_to_name"))
            if not item_name or item_name in latest_file_by_item:
                continue
            latest_file_by_item[item_name] = row_file

    recommendation_submission_by_item: dict[str, dict] = {}
    if item_names and frappe.db.table_exists("Recommendation Submission"):
        recommendation_rows = frappe.get_all(
            "Recommendation Submission",
            filters={"applicant_document_item": ["in", item_names]},
            fields=[
                "name",
                "applicant_document_item",
                "recommender_name",
                "recommender_email",
                "submitted_on",
            ],
            order_by="submitted_on desc, modified desc",
        )
        for row_submission in recommendation_rows:
            item_name = _to_text(row_submission.get("applicant_document_item"))
            if not item_name or item_name in recommendation_submission_by_item:
                continue
            recommendation_submission_by_item[item_name] = row_submission

    items_by_document: dict[str, list[dict]] = {}
    for row_item in item_rows:
        parent_name = _to_text(row_item.get("applicant_document"))
        item_name = _to_text(row_item.get("name"))
        if not parent_name or not item_name:
            continue

        latest_file = latest_file_by_item.get(item_name, {})
        recommendation_submission = recommendation_submission_by_item.get(item_name, {})
        uploaded_by = (
            _to_text(recommendation_submission.get("recommender_name"))
            or _to_text(recommendation_submission.get("recommender_email"))
            or latest_file.get("owner")
        )
        uploaded_at = recommendation_submission.get("submitted_on") or latest_file.get("creation")
        items_by_document.setdefault(parent_name, []).append(
            {
                "name": item_name,
                "item_key": _to_text(row_item.get("item_key")) or None,
                "item_label": _to_text(row_item.get("item_label")) or None,
                "review_status": _to_text(row_item.get("review_status")) or "Pending",
                "reviewed_by": _to_text(row_item.get("reviewed_by")) or None,
                "reviewed_on": row_item.get("reviewed_on"),
                "uploaded_by": uploaded_by or None,
                "uploaded_at": uploaded_at,
                "file_url": _resolve_item_file_open_url(
                    student_applicant=document_to_applicant.get(parent_name, ""),
                    file_row=latest_file,
                ),
                "file_name": _to_text(latest_file.get("file_name")) or None,
                "has_uploaded_artifact": bool(latest_file.get("name") or recommendation_submission.get("name")),
                "modified": row_item.get("modified"),
            }
        )

    for applicant_name in applicant_names:
        if applicant_name in out:
            continue

        document_rows_for_applicant = document_rows_by_applicant.get(applicant_name, [])
        documents_by_type = latest_document_by_applicant_type.get(applicant_name, {})
        type_map = type_map_by_applicant.get(applicant_name, {})
        required_defs = required_by_applicant.get(applicant_name, [])

        missing: list[str] = []
        unapproved: list[str] = []
        missing_rows: list[dict] = []
        unapproved_rows: list[dict] = []
        required_rows: list[dict] = []

        for required_def in required_defs:
            document_type = _to_text(required_def.get("document_type"))
            label = _to_text(required_def.get("label")) or document_type
            required_count = max(1, cint(required_def.get("required_count") or 1))
            document_row = documents_by_type.get(document_type)

            if not document_row:
                missing.append(label)
                missing_rows.append(
                    {
                        "document_type": document_type,
                        "label": label,
                        "applicant_document": None,
                        "applicant_document_item": None,
                        "review_status": "Missing",
                    }
                )
                required_rows.append(
                    {
                        "applicant_document": None,
                        "document_type": document_type,
                        "label": label,
                        "is_required": True,
                        "required_count": required_count,
                        "uploaded_count": 0,
                        "approved_count": 0,
                        "review_status": "Missing",
                        "reviewed_by": None,
                        "reviewed_on": None,
                        "requirement_override": None,
                        "override_reason": None,
                        "override_by": None,
                        "override_on": None,
                        "uploaded_by": None,
                        "uploaded_at": None,
                        "file_url": None,
                        "file_name": None,
                        "modified": None,
                        "items": [],
                    }
                )
                continue

            item_group = sorted(
                list(items_by_document.get(_to_text(document_row.get("name")), [])),
                key=lambda row_item: (
                    row_item.get("uploaded_at") or "",
                    row_item.get("modified") or "",
                ),
                reverse=True,
            )
            uploaded_items = [row for row in item_group if row.get("has_uploaded_artifact")]
            approved_items = [row for row in uploaded_items if _to_text(row.get("review_status")) == "Approved"]
            rejected_items = [row for row in uploaded_items if _to_text(row.get("review_status")) == "Rejected"]
            pending_items = [row for row in uploaded_items if _to_text(row.get("review_status")) in {"", "Pending"}]

            uploaded_count = len(uploaded_items)
            approved_count = len(approved_items)
            requirement_override = _to_text(document_row.get("requirement_override")) or None
            override_satisfies_requirement = requirement_override in {"Waived", "Exception Approved"}

            if override_satisfies_requirement:
                requirement_status = requirement_override
            elif uploaded_count < required_count:
                missing.append(label)
                requirement_status = "Missing"
            elif approved_count >= required_count:
                requirement_status = "Approved"
            else:
                unapproved.append(label)
                requirement_status = "Rejected" if rejected_items else "Pending"

            if override_satisfies_requirement:
                reviewed_by = document_row.get("override_by")
                reviewed_on = document_row.get("override_on")
            else:
                reviewed_by = document_row.get("reviewed_by")
                reviewed_on = document_row.get("reviewed_on")

            latest_uploaded_item = uploaded_items[0] if uploaded_items else {}

            if requirement_status == "Missing":
                missing_rows.append(
                    {
                        "document_type": document_type,
                        "label": label,
                        "applicant_document": _to_text(document_row.get("name")) or None,
                        "applicant_document_item": None,
                        "review_status": requirement_status,
                    }
                )
            elif requirement_status not in {"Approved", "Waived", "Exception Approved"}:
                unapproved_rows.append(
                    {
                        "document_type": document_type,
                        "label": label,
                        "applicant_document": _to_text(document_row.get("name")) or None,
                        "applicant_document_item": _to_text((pending_items[0] or {}).get("name")) or None,
                        "review_status": requirement_status,
                    }
                )

            required_rows.append(
                {
                    "applicant_document": _to_text(document_row.get("name")) or None,
                    "document_type": document_type,
                    "label": label,
                    "is_required": True,
                    "required_count": required_count,
                    "uploaded_count": uploaded_count,
                    "approved_count": approved_count,
                    "review_status": requirement_status,
                    "reviewed_by": reviewed_by,
                    "reviewed_on": reviewed_on,
                    "requirement_override": requirement_override,
                    "override_reason": document_row.get("override_reason"),
                    "override_by": document_row.get("override_by"),
                    "override_on": document_row.get("override_on"),
                    "uploaded_by": latest_uploaded_item.get("uploaded_by"),
                    "uploaded_at": latest_uploaded_item.get("uploaded_at"),
                    "file_url": latest_uploaded_item.get("file_url"),
                    "file_name": latest_uploaded_item.get("file_name"),
                    "modified": document_row.get("modified"),
                    "items": item_group,
                }
            )

        uploaded_rows: list[dict] = []
        for document_row in document_rows_for_applicant:
            document_type = _to_text(document_row.get("document_type"))
            type_meta = type_map.get(document_type) or {}
            document_label = (
                _to_text(document_row.get("document_label"))
                or _to_text(type_meta.get("code"))
                or _to_text(type_meta.get("document_type_name"))
                or document_type
                or _to_text(document_row.get("name"))
            )
            required_count = _required_count(type_meta)

            item_group = sorted(
                list(items_by_document.get(_to_text(document_row.get("name")), [])),
                key=lambda row_item: (
                    row_item.get("uploaded_at") or "",
                    row_item.get("modified") or "",
                ),
                reverse=True,
            )
            uploaded_items = [row for row in item_group if row.get("has_uploaded_artifact")]
            approved_items = [row for row in uploaded_items if _to_text(row.get("review_status")) == "Approved"]

            for uploaded_item in uploaded_items:
                item_label = (
                    _to_text(uploaded_item.get("item_label"))
                    or _to_text(uploaded_item.get("item_key"))
                    or _to_text(uploaded_item.get("name"))
                )
                row_label = document_label
                if item_label and item_label.lower() != document_label.lower():
                    row_label = _("{0} — {1}").format(document_label, item_label)

                uploaded_rows.append(
                    {
                        "applicant_document": _to_text(document_row.get("name")) or None,
                        "applicant_document_item": _to_text(uploaded_item.get("name")) or None,
                        "document_type": document_type,
                        "label": row_label,
                        "document_label": document_label,
                        "item_key": uploaded_item.get("item_key"),
                        "item_label": uploaded_item.get("item_label"),
                        "is_required": bool(cint(type_meta.get("is_required"))),
                        "required_count": required_count if cint(type_meta.get("is_required")) else 0,
                        "uploaded_count": len(uploaded_items),
                        "approved_count": len(approved_items),
                        "is_repeatable": bool(cint(type_meta.get("is_repeatable"))),
                        "requirement_override": document_row.get("requirement_override"),
                        "override_reason": document_row.get("override_reason"),
                        "review_status": _to_text(uploaded_item.get("review_status")) or "Pending",
                        "reviewed_by": uploaded_item.get("reviewed_by"),
                        "reviewed_on": uploaded_item.get("reviewed_on"),
                        "uploaded_by": uploaded_item.get("uploaded_by"),
                        "uploaded_at": uploaded_item.get("uploaded_at"),
                        "file_url": uploaded_item.get("file_url"),
                        "file_name": uploaded_item.get("file_name"),
                        "modified": uploaded_item.get("modified") or document_row.get("modified"),
                    }
                )

        uploaded_rows.sort(
            key=lambda row: (
                row.get("uploaded_at") or "",
                row.get("modified") or "",
            ),
            reverse=True,
        )

        out[applicant_name] = {
            "ok": not missing and not unapproved,
            "missing": missing,
            "unapproved": unapproved,
            "required": [_to_text(row.get("label")) or _to_text(row.get("document_type")) for row in required_defs],
            "required_rows": required_rows,
            "uploaded_rows": uploaded_rows,
            "missing_rows": missing_rows,
            "unapproved_rows": unapproved_rows,
        }

    return out


def _resolve_item_file_open_url(*, student_applicant: str, file_row: dict | None) -> str | None:
    if not file_row:
        return None
    file_name = _to_text(file_row.get("name"))
    file_url = _to_text(file_row.get("file_url"))
    if not file_name and not file_url:
        return None
    return resolve_admissions_file_open_url(
        file_name=file_name or None,
        file_url=file_url or None,
        context_doctype="Student Applicant",
        context_name=student_applicant,
    )


def _required_count(document_type_row: dict | None) -> int:
    row = document_type_row or {}
    if not cint(row.get("is_repeatable")):
        return 1
    return max(1, cint(row.get("min_items_required") or 1))


def _document_requirement_label(document_type_row: dict) -> str:
    return (
        _to_text(document_type_row.get("code"))
        or _to_text(document_type_row.get("document_type_name"))
        or _to_text(document_type_row.get("name"))
    )


def _to_text(value) -> str:
    return str(value or "").strip()
