# ifitwala_ed/admission/api/portal/documents.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission import admissions_portal as admission_api
from ifitwala_ed.admission.admission_utils import (
    get_applicant_scope_ancestors,
    has_complete_applicant_document_type_classification,
    is_applicant_document_type_in_scope,
)
from ifitwala_ed.admission.api.common.request_payload import _request_form_value
from ifitwala_ed.admission.api.portal.access import _as_text, _ensure_applicant_match, _require_admissions_applicant
from ifitwala_ed.admission.api.recommendation_intake.templates import get_recommendation_template_rows_for_applicant
from ifitwala_ed.api.attachment_previews import extract_file_extension
from ifitwala_ed.api.attachment_rows import build_governed_attachment_row
from ifitwala_ed.api.file_access import (
    get_drive_file_thumbnail_ready_map,
    resolve_admissions_file_open_url,
    resolve_admissions_file_preview_url,
    resolve_admissions_file_thumbnail_url,
)
from ifitwala_ed.integrations.drive.authority import get_current_drive_files_for_attachments


def _load_drive_version_mime_map(version_ids: list[str]) -> dict[str, str]:
    resolved_version_ids = [version_id for version_id in dict.fromkeys(version_ids) if _as_text(version_id).strip()]
    if not resolved_version_ids:
        return {}

    rows = frappe.get_all(
        "Drive File Version",
        filters={"name": ["in", resolved_version_ids]},
        fields=["name", "mime_type"],
        limit=0,
    )
    return {
        _as_text(row.get("name")).strip(): _as_text(row.get("mime_type")).strip()
        for row in rows
        if _as_text(row.get("name")).strip()
    }


def _serialize_applicant_document_attachment(
    *,
    latest_drive_file: dict,
    student_applicant_name: str,
    thumbnail_ready_map: dict[str, bool],
    version_mime_map: dict[str, str],
) -> dict:
    drive_file_id = _as_text(latest_drive_file.get("name")).strip()
    compatibility_file_id = _as_text(latest_drive_file.get("file")).strip()
    canonical_ref = _as_text(latest_drive_file.get("canonical_ref")).strip() or None
    file_name = (
        _as_text(latest_drive_file.get("display_name")).strip()
        or _as_text(latest_drive_file.get("file_name")).strip()
        or compatibility_file_id
    )
    preview_status = _as_text(latest_drive_file.get("preview_status")).strip() or None
    open_url = resolve_admissions_file_open_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant_name,
    )
    preview_url = resolve_admissions_file_preview_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant_name,
        preview_ready=preview_status == "ready",
    )
    thumbnail_url = resolve_admissions_file_thumbnail_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant_name,
        thumbnail_ready=thumbnail_ready_map.get(drive_file_id, False),
    )
    mime_type = version_mime_map.get(_as_text(latest_drive_file.get("current_version")).strip())
    attachment = build_governed_attachment_row(
        row_id=drive_file_id or compatibility_file_id or file_name,
        surface="admissions.applicant_document",
        item_id=drive_file_id or compatibility_file_id or file_name,
        owner_doctype="Student Applicant",
        owner_name=student_applicant_name,
        file_id=drive_file_id or compatibility_file_id,
        display_name=file_name,
        mime_type=mime_type,
        extension=extract_file_extension(file_name=file_name, file_url=None),
        preview_status=preview_status,
        thumbnail_url=thumbnail_url,
        preview_url=preview_url,
        open_url=open_url,
        download_url=open_url,
        created_at=latest_drive_file.get("creation"),
    )
    return {
        "uploaded_at": latest_drive_file.get("creation"),
        "attachment": attachment,
    }


def list_applicant_documents_impl(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    student_applicant_name = (row.get("name") or "").strip()
    hidden_document_types = _recommendation_target_document_types_for_applicant(student_applicant_name)

    documents = frappe.get_all(
        "Applicant Document",
        filters={"student_applicant": row.get("name")},
        fields=[
            "name",
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
    )
    if hidden_document_types:
        documents = [doc for doc in documents if (doc.get("document_type") or "").strip() not in hidden_document_types]

    if not documents:
        return {"documents": []}

    name_list = [d["name"] for d in documents]
    item_rows = frappe.get_all(
        "Applicant Document Item",
        filters={"applicant_document": ["in", name_list]},
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
    item_names = [row_item.get("name") for row_item in item_rows if row_item.get("name")]

    latest_drive_file_by_item: dict[str, dict] = {}
    if item_names:
        drive_rows = get_current_drive_files_for_attachments(
            attached_doctype="Applicant Document Item",
            attached_names=item_names,
            fields=[
                "name",
                "attached_name",
                "file",
                "canonical_ref",
                "display_name",
                "preview_status",
                "current_version",
                "creation",
            ],
            statuses=("active", "processing", "blocked"),
        )
        for drive_row in drive_rows:
            parent = drive_row.get("attached_name")
            if not parent or parent in latest_drive_file_by_item:
                continue
            latest_drive_file_by_item[parent] = drive_row

    drive_thumbnail_ready_map = get_drive_file_thumbnail_ready_map(
        [
            _as_text(row_drive.get("name")).strip()
            for row_drive in latest_drive_file_by_item.values()
            if _as_text(row_drive.get("name")).strip()
        ]
    )
    drive_version_mime_map = _load_drive_version_mime_map(
        [
            _as_text(row_drive.get("current_version")).strip()
            for row_drive in latest_drive_file_by_item.values()
            if _as_text(row_drive.get("current_version")).strip()
        ]
    )

    doc_type_names = sorted({doc.get("document_type") for doc in documents if doc.get("document_type")})
    doc_type_meta: dict[str, dict] = {}
    if doc_type_names:
        for row_type in frappe.get_all(
            "Applicant Document Type",
            filters={"name": ["in", doc_type_names]},
            fields=[
                "name",
                "code",
                "document_type_name",
                "description",
                "is_required",
                "is_repeatable",
                "min_items_required",
            ],
        ):
            doc_type_meta[row_type.get("name")] = row_type

    items_by_document: dict[str, list[dict]] = {}
    for row_item in item_rows:
        parent = row_item.get("applicant_document")
        if not parent:
            continue
        latest_drive_file = latest_drive_file_by_item.get(row_item.get("name"), {})
        attachment = (
            _serialize_applicant_document_attachment(
                latest_drive_file=latest_drive_file,
                student_applicant_name=student_applicant_name,
                thumbnail_ready_map=drive_thumbnail_ready_map,
                version_mime_map=drive_version_mime_map,
            )
            if latest_drive_file
            else {
                "uploaded_at": None,
                "attachment": None,
            }
        )
        items_by_document.setdefault(parent, []).append(
            {
                "name": row_item.get("name"),
                "item_key": row_item.get("item_key"),
                "item_label": row_item.get("item_label"),
                "review_status": row_item.get("review_status") or "Pending",
                "reviewed_by": row_item.get("reviewed_by"),
                "reviewed_on": row_item.get("reviewed_on"),
                "uploaded_at": attachment.get("uploaded_at"),
                "attachment": attachment.get("attachment"),
            }
        )

    payload = []
    for doc in documents:
        doc_name = doc.get("name")
        type_meta = doc_type_meta.get(doc.get("document_type")) or {}
        items = items_by_document.get(doc_name, [])

        latest_uploaded_at = None
        if items:
            sorted_items = sorted(
                items,
                key=lambda row_item: row_item.get("uploaded_at") or "",
                reverse=True,
            )
            latest_uploaded_at = sorted_items[0].get("uploaded_at")

        is_required = bool(type_meta.get("is_required"))
        is_repeatable = bool(type_meta.get("is_repeatable"))
        required_count = _portal_required_document_count(type_meta)
        uploaded_count = len([item for item in items if (item.get("attachment") or {}).get("open_url")])
        approved_count = len(
            [
                item
                for item in items
                if (item.get("attachment") or {}).get("open_url") and item.get("review_status") == "Approved"
            ]
        )
        rejected_count = len(
            [
                item
                for item in items
                if (item.get("attachment") or {}).get("open_url") and item.get("review_status") == "Rejected"
            ]
        )
        pending_count = len(
            [
                item
                for item in items
                if (item.get("attachment") or {}).get("open_url")
                and (item.get("review_status") or "Pending").strip() not in {"Approved", "Rejected"}
            ]
        )
        override_status = (doc.get("requirement_override") or "").strip() or None
        state_key, state_label = _portal_document_requirement_state(
            is_required=is_required,
            required_count=required_count,
            uploaded_count=uploaded_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            pending_count=pending_count,
            override_status=override_status,
        )

        payload.append(
            {
                "name": doc_name,
                "document_type": doc.get("document_type"),
                "label": (
                    (doc.get("document_label") or "").strip()
                    or (type_meta.get("document_type_name") or "").strip()
                    or (type_meta.get("code") or "").strip()
                    or (doc.get("document_type") or "").strip()
                    or doc_name
                ),
                "description": type_meta.get("description") or "",
                "is_required": is_required,
                "is_repeatable": is_repeatable,
                "required_count": required_count,
                "uploaded_count": uploaded_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "pending_count": pending_count,
                "requirement_state": state_key,
                "requirement_state_label": state_label,
                "requirement_override": override_status,
                "override_reason": doc.get("override_reason"),
                "override_by": doc.get("override_by"),
                "override_on": doc.get("override_on"),
                "review_status": doc.get("review_status") or "Pending",
                "reviewed_by": doc.get("reviewed_by"),
                "reviewed_on": doc.get("reviewed_on"),
                "uploaded_at": latest_uploaded_at,
                "items": items,
            }
        )

    return {"documents": payload}


def _recommendation_target_document_types_for_applicant(student_applicant: str) -> set[str]:
    template_rows = get_recommendation_template_rows_for_applicant(
        student_applicant=student_applicant,
        include_confidential=True,
        fields=["target_document_type"],
    )
    return {
        (row.get("target_document_type") or "").strip()
        for row in template_rows
        if (row.get("target_document_type") or "").strip()
    }


def _portal_required_document_count(row_type: dict | None) -> int:
    if not row_type or not row_type.get("is_required"):
        return 0
    if not cint(row_type.get("is_repeatable")):
        return 1
    return max(1, cint(row_type.get("min_items_required") or 1))


def _portal_document_requirement_state(
    *,
    is_required: bool,
    required_count: int,
    uploaded_count: int,
    approved_count: int,
    rejected_count: int,
    pending_count: int,
    override_status: str | None,
) -> tuple[str, str]:
    if override_status == "Waived":
        return "waived", _("Waived by admissions")
    if override_status == "Exception Approved":
        return "exception_approved", _("Exception approved by admissions")

    needed_count = required_count if is_required else max(1, uploaded_count)
    if uploaded_count <= 0:
        return "not_started", _("Not started")
    if approved_count >= needed_count and needed_count > 0:
        return "complete", _("Complete")
    if rejected_count > 0:
        return "changes_requested", _("Changes requested")
    if pending_count > 0 or uploaded_count > 0:
        return "waiting_review", _("Uploaded - waiting for review")
    return "not_started", _("Not started")


def list_applicant_document_types_impl(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    hidden_document_types = _recommendation_target_document_types_for_applicant((row.get("name") or "").strip())

    organization = row.get("organization")
    school = row.get("school")

    if not organization:
        return {"document_types": []}

    applicant_org_ancestors, applicant_school_ancestors = get_applicant_scope_ancestors(
        organization=organization,
        school=school,
    )
    applicant_org_ancestors = set(applicant_org_ancestors)
    applicant_school_ancestors = set(applicant_school_ancestors)

    rows = frappe.get_all(
        "Applicant Document Type",
        filters={"is_active": 1},
        fields=[
            "name",
            "code",
            "document_type_name",
            "belongs_to",
            "is_required",
            "is_repeatable",
            "min_items_required",
            "description",
            "school",
            "organization",
        ],
        order_by="is_required desc, document_type_name asc",
    )

    payload = []
    for row_type in rows:
        if (row_type.get("name") or "").strip() in hidden_document_types:
            continue
        if not is_applicant_document_type_in_scope(
            document_type_organization=row_type.get("organization"),
            document_type_school=row_type.get("school"),
            applicant_org_ancestors=applicant_org_ancestors,
            applicant_school_ancestors=applicant_school_ancestors,
        ):
            continue
        payload.append(
            {
                "name": row_type.get("name"),
                "code": row_type.get("code"),
                "document_type_name": row_type.get("document_type_name"),
                "belongs_to": row_type.get("belongs_to") or "",
                "is_required": bool(row_type.get("is_required")),
                "is_repeatable": bool(row_type.get("is_repeatable")),
                "min_items_required": cint(row_type.get("min_items_required") or 1),
                "description": row_type.get("description") or "",
            }
        )

    return {"document_types": payload}


def upload_applicant_document_impl(
    *,
    student_applicant: str | None = None,
    document_type: str | None = None,
    applicant_document_item: str | None = None,
    item_key: str | None = None,
    item_label: str | None = None,
    client_request_id: str | None = None,
    file_name: str | None = None,
    content: str | None = None,
):
    student_applicant = _request_form_value("student_applicant", student_applicant)
    document_type = _request_form_value("document_type", document_type)
    applicant_document_item = _request_form_value("applicant_document_item", applicant_document_item)
    item_key = _request_form_value("item_key", item_key)
    item_label = _request_form_value("item_label", item_label)
    client_request_id = _request_form_value("client_request_id", client_request_id)
    file_name = _request_form_value("file_name", file_name)
    content = _request_form_value("content", content)

    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    hidden_document_types = _recommendation_target_document_types_for_applicant((row.get("name") or "").strip())

    if not document_type:
        frappe.throw(_("document_type is required."))
    if (document_type or "").strip() in hidden_document_types:
        frappe.throw(_("Recommendation submissions are managed through referee links and cannot be uploaded here."))

    if not content and not (getattr(frappe.request, "files", None) and frappe.request.files.get("file")):
        frappe.throw(_("File content is required."))

    doc_type_row = frappe.db.get_value(
        "Applicant Document Type",
        document_type,
        [
            "organization",
            "school",
            "is_active",
            "code",
            "classification_slot",
            "classification_data_class",
            "classification_purpose",
            "classification_retention_policy",
        ],
        as_dict=True,
    )
    if not doc_type_row or not doc_type_row.get("is_active"):
        frappe.throw(_("Invalid or inactive document type."))

    applicant_org_ancestors, applicant_school_ancestors = get_applicant_scope_ancestors(
        organization=row.get("organization"),
        school=row.get("school"),
    )
    applicant_org_ancestors = set(applicant_org_ancestors)
    applicant_school_ancestors = set(applicant_school_ancestors)
    if not is_applicant_document_type_in_scope(
        document_type_organization=doc_type_row.get("organization"),
        document_type_school=doc_type_row.get("school"),
        applicant_org_ancestors=applicant_org_ancestors,
        applicant_school_ancestors=applicant_school_ancestors,
    ):
        frappe.throw(_("Document type is outside the Applicant scope."))

    if not has_complete_applicant_document_type_classification(doc_type_row):
        missing_labels = []
        for fieldname, label in (
            ("classification_slot", "slot"),
            ("classification_data_class", "data class"),
            ("classification_purpose", "purpose"),
            ("classification_retention_policy", "retention policy"),
        ):
            if not _as_text(doc_type_row.get(fieldname)).strip():
                missing_labels.append(label)
        doc_type_label = _as_text(doc_type_row.get("code") or document_type).strip() or _("Unknown")
        if missing_labels:
            frappe.throw(
                _(
                    "This document type is not configured for uploads ({document_type}). Missing: {missing_fields}."
                ).format(
                    document_type=doc_type_label,
                    missing_fields=", ".join(missing_labels),
                )
            )
        frappe.throw(
            _("This document type is not configured for uploads ({document_type}).").format(
                document_type=doc_type_label
            )
        )

    payload = {
        "student_applicant": row.get("name"),
        "document_type": document_type,
        "applicant_document_item": applicant_document_item,
        "item_key": _as_text(item_key).strip() or None,
        "item_label": _as_text(item_label).strip() or None,
        "client_request_id": _as_text(client_request_id).strip() or None,
        "upload_source": "SPA",
        "is_private": 1,
    }

    if content:
        payload["content"] = content
    if file_name:
        payload["file_name"] = file_name

    upload_result = admission_api.upload_applicant_document(**payload)
    resolved_drive_file_id = _as_text(upload_result.get("drive_file_id")).strip() or None
    resolved_canonical_ref = _as_text(upload_result.get("canonical_ref")).strip() or None
    preview_status = (
        _as_text(frappe.db.get_value("Drive File", resolved_drive_file_id, "preview_status")).strip()
        if resolved_drive_file_id
        else ""
    )
    thumbnail_ready = (
        get_drive_file_thumbnail_ready_map([resolved_drive_file_id]).get(resolved_drive_file_id, False)
        if resolved_drive_file_id
        else False
    )
    open_url = resolve_admissions_file_open_url(
        file_name=upload_result.get("file"),
        file_url=None,
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype="Student Applicant",
        context_name=row.get("name"),
    )
    preview_url = resolve_admissions_file_preview_url(
        file_name=upload_result.get("file"),
        file_url=None,
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype="Student Applicant",
        context_name=row.get("name"),
        preview_ready=preview_status == "ready",
    )
    thumbnail_url = resolve_admissions_file_thumbnail_url(
        file_name=upload_result.get("file"),
        file_url=None,
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype="Student Applicant",
        context_name=row.get("name"),
        thumbnail_ready=thumbnail_ready,
    )
    resolved_file_name = (
        _as_text(upload_result.get("file_name")).strip()
        or _as_text(file_name).strip()
        or _as_text(upload_result.get("file")).strip()
        or None
    )
    attachment = build_governed_attachment_row(
        row_id=resolved_drive_file_id or upload_result.get("file") or resolved_file_name,
        surface="admissions.applicant_document",
        item_id=resolved_drive_file_id or upload_result.get("file") or resolved_file_name,
        owner_doctype="Student Applicant",
        owner_name=row.get("name"),
        file_id=resolved_drive_file_id or upload_result.get("file"),
        display_name=upload_result.get("item_label") or item_label or resolved_file_name,
        extension=extract_file_extension(file_name=resolved_file_name, file_url=None),
        preview_status=preview_status or None,
        thumbnail_url=thumbnail_url,
        preview_url=preview_url,
        open_url=open_url,
        download_url=open_url,
    )
    return {
        "ok": True,
        "file": upload_result.get("file"),
        "file_name": resolved_file_name,
        "drive_file_id": resolved_drive_file_id,
        "canonical_ref": resolved_canonical_ref,
        "attachment": attachment,
        "applicant_document": upload_result.get("applicant_document"),
        "applicant_document_item": upload_result.get("applicant_document_item"),
        "item_key": upload_result.get("item_key"),
        "item_label": upload_result.get("item_label"),
    }
