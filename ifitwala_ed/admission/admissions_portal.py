# ifitwala_ed/admission/admissions_portal.py

from __future__ import annotations

import base64

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from ifitwala_ed.admission.admission_utils import get_applicant_document_slot_spec
from ifitwala_ed.utilities.governed_uploads import (
    _drive_upload_and_finalize,
    _resolve_upload_mime_type_hint,
    _workflow_result_payload,
)

ALLOWED_UPLOAD_SOURCES = {"Desk", "SPA", "API", "Job"}


def upload_applicant_document(
    *,
    student_applicant: str | None = None,
    document_type: str | None = None,
    applicant_document: str | None = None,
    applicant_document_item: str | None = None,
    item_key: str | None = None,
    item_label: str | None = None,
    client_request_id: str | None = None,
    upload_source: str | None = "API",
    is_private: int | None = 1,
    **kwargs,
):
    """
    Governed admissions upload endpoint.
    Creates Applicant Document (if needed) and stores file via dispatcher.
    """
    filename, content = _extract_upload(kwargs)
    doc = _resolve_applicant_document(
        applicant_document=applicant_document,
        student_applicant=student_applicant,
        document_type=document_type,
    )
    item_doc = _resolve_applicant_document_item(
        applicant_document=doc,
        applicant_document_item=applicant_document_item,
        item_key=item_key,
        item_label=item_label,
        fallback_label=filename,
    )

    doc_type_code = frappe.db.get_value("Applicant Document Type", doc.document_type, "code") or doc.document_type
    slot_spec = get_applicant_document_slot_spec(document_type=doc.document_type, doc_type_code=doc_type_code)
    if not slot_spec:
        frappe.throw(_("Applicant Document Type is missing upload classification settings: {0}.").format(doc_type_code))

    applicant_row = (
        frappe.db.get_value(
            "Student Applicant",
            doc.student_applicant,
            ["organization", "school"],
            as_dict=True,
        )
        or {}
    )
    if not applicant_row.get("organization") or not applicant_row.get("school"):
        frappe.throw(_("Student Applicant must have organization and school."))

    source = upload_source or "API"
    if source not in ALLOWED_UPLOAD_SOURCES:
        frappe.throw(_("Invalid upload_source."))

    user = (frappe.session.user or "Guest").strip() or "Guest"
    request_id = (client_request_id or "").strip() or None
    cache = frappe.cache()
    cache_key = None
    lock_key = f"ifitwala_ed:lock:admissions:upload:{doc.name}:{item_doc.name}"

    if request_id:
        cache_key = f"ifitwala_ed:admissions:upload:{user}:{doc.name}:{item_doc.name}:{request_id}"
        cached = cache.get_value(cache_key)
        if cached:
            return frappe.parse_json(cached)
        lock_key = f"{lock_key}:{request_id}"

    with cache.lock(lock_key, timeout=15):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return frappe.parse_json(cached)

        try:
            from ifitwala_drive.api import admissions as drive_admissions_api
        except ImportError as exc:
            frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))

        _session_response, finalize_response, file_doc = _drive_upload_and_finalize(
            create_session_callable=drive_admissions_api.upload_applicant_document,
            payload={
                "student_applicant": doc.student_applicant,
                "document_type": doc.document_type,
                "applicant_document": doc.name,
                "applicant_document_item": item_doc.name,
                "item_key": item_doc.item_key,
                "item_label": item_doc.item_label,
                "filename_original": filename,
                "mime_type_hint": _resolve_upload_mime_type_hint(
                    filename=filename,
                    explicit=kwargs.get("mime_type_hint") or kwargs.get("content_type"),
                ),
                "expected_size_bytes": len(content),
                "upload_source": source,
                "is_private": cint(is_private) if is_private is not None else 1,
            },
            content=content,
        )

        finalize_workflow_result = _workflow_result_payload(finalize_response)
        response = {
            "file": file_doc.name,
            "file_url": file_doc.file_url,
            "drive_file_id": finalize_response.get("drive_file_id"),
            "canonical_ref": finalize_response.get("canonical_ref"),
            "applicant_document": finalize_workflow_result.get("applicant_document") or doc.name,
            "applicant_document_item": finalize_workflow_result.get("applicant_document_item") or item_doc.name,
            "item_key": finalize_workflow_result.get("item_key") or item_doc.item_key,
            "item_label": finalize_workflow_result.get("item_label") or item_doc.item_label,
        }
        if cache_key:
            cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=60 * 10)
        return response


def upload_applicant_profile_image(
    *,
    student_applicant: str,
    file_name: str,
    content,
    mime_type_hint: str | None = None,
    upload_source: str | None = "API",
):
    """Governed admissions applicant-profile image upload routed through Drive."""
    if not student_applicant:
        frappe.throw(_("student_applicant is required."))
    if not file_name:
        frappe.throw(_("file_name is required when sending raw content."))
    if content is None:
        frappe.throw(_("File content is required."))

    source = upload_source or "API"
    if source not in ALLOWED_UPLOAD_SOURCES:
        frappe.throw(_("Invalid upload_source."))

    try:
        from ifitwala_drive.api import admissions as drive_admissions_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))
    _session_response, finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=drive_admissions_api.upload_applicant_profile_image,
        payload={
            "student_applicant": student_applicant,
            "filename_original": file_name,
            "mime_type_hint": _resolve_upload_mime_type_hint(
                filename=file_name,
                explicit=mime_type_hint,
            ),
            "expected_size_bytes": len(content),
            "upload_source": source,
        },
        content=content,
    )

    finalize_workflow_result = _workflow_result_payload(finalize_response)
    return {
        "file": file_doc.name,
        "file_url": file_doc.file_url,
        "drive_file_id": finalize_response.get("drive_file_id"),
        "canonical_ref": finalize_response.get("canonical_ref"),
        "student_applicant": finalize_workflow_result.get("student_applicant") or student_applicant,
        "slot": finalize_workflow_result.get("slot"),
    }


def upload_applicant_guardian_image(
    *,
    student_applicant: str,
    guardian_row_name: str,
    file_name: str,
    content,
    mime_type_hint: str | None = None,
    upload_source: str | None = "API",
):
    """Governed admissions guardian image upload routed through Drive."""
    if not student_applicant:
        frappe.throw(_("student_applicant is required."))
    if not guardian_row_name:
        frappe.throw(_("guardian_row_name is required."))
    if not file_name:
        frappe.throw(_("file_name is required when sending raw content."))
    if content is None:
        frappe.throw(_("File content is required."))

    source = upload_source or "API"
    if source not in ALLOWED_UPLOAD_SOURCES:
        frappe.throw(_("Invalid upload_source."))

    try:
        from ifitwala_drive.api import admissions as drive_admissions_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))
    _session_response, finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=drive_admissions_api.upload_applicant_guardian_image,
        payload={
            "student_applicant": student_applicant,
            "guardian_row_name": guardian_row_name,
            "filename_original": file_name,
            "mime_type_hint": _resolve_upload_mime_type_hint(
                filename=file_name,
                explicit=mime_type_hint,
            ),
            "expected_size_bytes": len(content),
            "upload_source": source,
        },
        content=content,
    )

    finalize_workflow_result = _workflow_result_payload(finalize_response)
    return {
        "file": file_doc.name,
        "file_url": file_doc.file_url,
        "drive_file_id": finalize_response.get("drive_file_id"),
        "canonical_ref": finalize_response.get("canonical_ref"),
        "student_applicant": finalize_workflow_result.get("student_applicant") or student_applicant,
        "guardian_row_name": finalize_workflow_result.get("guardian_row_name") or guardian_row_name,
        "slot": finalize_workflow_result.get("slot"),
    }


def upload_applicant_health_vaccination_proof(
    *,
    student_applicant: str,
    applicant_health_profile: str,
    vaccine_name: str | None = None,
    date: str | None = None,
    row_index: int | None = None,
    file_name: str,
    content,
    mime_type_hint: str | None = None,
    upload_source: str | None = "API",
):
    """Governed admissions health upload endpoint routed through Drive."""
    if not student_applicant:
        frappe.throw(_("student_applicant is required."))
    if not applicant_health_profile:
        frappe.throw(_("applicant_health_profile is required."))
    if not file_name:
        frappe.throw(_("file_name is required when sending raw content."))
    if content is None:
        frappe.throw(_("File content is required."))

    source = upload_source or "API"
    if source not in ALLOWED_UPLOAD_SOURCES:
        frappe.throw(_("Invalid upload_source."))

    try:
        from ifitwala_drive.api import admissions as drive_admissions_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))
    _session_response, finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=drive_admissions_api.upload_applicant_health_vaccination_proof,
        payload={
            "student_applicant": student_applicant,
            "applicant_health_profile": applicant_health_profile,
            "vaccine_name": vaccine_name,
            "date": date,
            "row_index": row_index,
            "filename_original": file_name,
            "mime_type_hint": _resolve_upload_mime_type_hint(
                filename=file_name,
                explicit=mime_type_hint,
            ),
            "expected_size_bytes": len(content),
            "upload_source": source,
        },
        content=content,
    )

    finalize_workflow_result = _workflow_result_payload(finalize_response)
    return {
        "file": file_doc.name,
        "file_url": file_doc.file_url,
        "drive_file_id": finalize_response.get("drive_file_id"),
        "canonical_ref": finalize_response.get("canonical_ref"),
        "student_applicant": finalize_workflow_result.get("student_applicant") or student_applicant,
        "applicant_health_profile": finalize_workflow_result.get("applicant_health_profile")
        or applicant_health_profile,
        "slot": finalize_workflow_result.get("slot"),
    }


def _resolve_applicant_document(
    *,
    applicant_document=None,
    student_applicant=None,
    document_type=None,
    applicant_document_item=None,
):
    if applicant_document:
        doc = frappe.get_doc("Applicant Document", applicant_document)
        if student_applicant and doc.student_applicant != student_applicant:
            frappe.throw(_("Applicant Document does not match the provided Student Applicant."))
        if document_type and doc.document_type != document_type:
            frappe.throw(_("Applicant Document does not match the provided Document Type."))
        return doc

    if applicant_document_item:
        item_doc = frappe.get_doc("Applicant Document Item", applicant_document_item)
        doc = frappe.get_doc("Applicant Document", item_doc.applicant_document)
        if student_applicant and doc.student_applicant != student_applicant:
            frappe.throw(_("Applicant Document does not match the provided Student Applicant."))
        if document_type and doc.document_type != document_type:
            frappe.throw(_("Applicant Document does not match the provided Document Type."))
        return doc

    if not student_applicant or not document_type:
        frappe.throw(_("student_applicant and document_type are required."))

    existing = frappe.db.get_value(
        "Applicant Document",
        {
            "student_applicant": student_applicant,
            "document_type": document_type,
        },
        "name",
    )
    if existing:
        return frappe.get_doc("Applicant Document", existing)

    doc = frappe.get_doc(
        {
            "doctype": "Applicant Document",
            "student_applicant": student_applicant,
            "document_type": document_type,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc


def _sanitize_item_key(value: str | None) -> str:
    return frappe.scrub((value or "").strip())[:80]


def _next_item_key(*, applicant_document: str, preferred: str | None = None) -> str:
    base = _sanitize_item_key(preferred) or "item"
    candidate = base
    index = 1
    while frappe.db.exists(
        "Applicant Document Item",
        {"applicant_document": applicant_document, "item_key": candidate},
    ):
        index += 1
        candidate = f"{base}_{index}"
    return candidate[:80]


def _resolve_applicant_document_item(
    *,
    applicant_document,
    applicant_document_item: str | None = None,
    item_key: str | None = None,
    item_label: str | None = None,
    fallback_label: str | None = None,
):
    doc_type_row = (
        frappe.db.get_value(
            "Applicant Document Type",
            applicant_document.document_type,
            ["is_repeatable", "code", "document_type_name"],
            as_dict=True,
        )
        or {}
    )
    is_repeatable = bool(cint(doc_type_row.get("is_repeatable")))
    default_single_item_key = (
        frappe.scrub((doc_type_row.get("code") or applicant_document.document_type or "document").strip())[:80]
        or "document"
    )

    if applicant_document_item:
        item_doc = frappe.get_doc("Applicant Document Item", applicant_document_item)
        if item_doc.applicant_document != applicant_document.name:
            frappe.throw(_("Applicant Document Item does not match the provided Applicant Document."))
        return item_doc

    if not is_repeatable:
        existing = frappe.get_all(
            "Applicant Document Item",
            filters={"applicant_document": applicant_document.name},
            fields=["name", "item_label"],
            order_by="modified desc",
            limit=1,
        )
        if existing:
            item_doc = frappe.get_doc("Applicant Document Item", existing[0].get("name"))
            requested_label = (item_label or "").strip() or (fallback_label or "").strip()
            if requested_label and requested_label != (item_doc.item_label or "").strip():
                frappe.db.set_value(
                    "Applicant Document Item",
                    item_doc.name,
                    "item_label",
                    requested_label,
                    update_modified=False,
                )
                item_doc.item_label = requested_label
            return item_doc

    requested_key = _sanitize_item_key(item_key)
    requested_label = (
        (item_label or "").strip()
        or (fallback_label or "").strip()
        or (doc_type_row.get("document_type_name") or "").strip()
        or _("Uploaded file")
    )

    if requested_key:
        existing = frappe.db.get_value(
            "Applicant Document Item",
            {"applicant_document": applicant_document.name, "item_key": requested_key},
            "name",
        )
        if existing:
            item_doc = frappe.get_doc("Applicant Document Item", existing)
            if requested_label and requested_label != (item_doc.item_label or "").strip():
                frappe.db.set_value(
                    "Applicant Document Item",
                    item_doc.name,
                    "item_label",
                    requested_label,
                    update_modified=False,
                )
                item_doc.item_label = requested_label
            return item_doc
        key_value = requested_key
    else:
        preferred_key = requested_label if is_repeatable else default_single_item_key
        key_value = _next_item_key(applicant_document=applicant_document.name, preferred=preferred_key)

    item_doc = frappe.get_doc(
        {
            "doctype": "Applicant Document Item",
            "applicant_document": applicant_document.name,
            "item_key": key_value,
            "item_label": requested_label,
        }
    )
    item_doc.insert(ignore_permissions=True)
    return item_doc


def _extract_upload(kwargs):
    if frappe.request and getattr(frappe.request, "files", None):
        upload = frappe.request.files.get("file")
        if upload:
            filename = upload.filename
            content = upload.read()
            if not filename:
                frappe.throw(_("Uploaded file name is required."))
            if not content:
                frappe.throw(_("Uploaded file content is empty."))
            return filename, content

    content = kwargs.get("content")
    filename = kwargs.get("file_name") or kwargs.get("filename")

    if content is None:
        frappe.throw(_("File content is required."))
    if not filename:
        frappe.throw(_("file_name is required when sending raw content."))

    if isinstance(content, str):
        try:
            content = base64.b64decode(content)
        except Exception:
            frappe.throw(_("content must be base64-encoded when provided as text."))

    if not content:
        frappe.throw(_("File content is empty."))

    return filename, content


def _append_document_upload_timeline(
    *,
    student_applicant: str,
    applicant_document: str,
    applicant_document_item: str,
    item_key: str,
    item_label: str,
    document_type: str,
    document_type_code: str,
    file_url: str | None,
    upload_source: str,
    action: str,
):
    if not student_applicant:
        return

    document_type_name = frappe.db.get_value("Applicant Document Type", document_type, "document_type_name")
    document_label = document_type_code or document_type_name or document_type
    message = _("Applicant document {0}: {1} ({2}) item {3} [{4}] ({5}) by {6} on {7} via {8}. File: {9}.").format(
        action,
        frappe.bold(document_label),
        frappe.bold(applicant_document),
        frappe.bold(item_label or item_key or applicant_document_item),
        frappe.bold(item_key or _("n/a")),
        frappe.bold(applicant_document_item),
        frappe.bold(frappe.session.user),
        now_datetime(),
        frappe.bold(upload_source),
        file_url or _("not available"),
    )

    try:
        applicant = frappe.get_doc("Student Applicant", student_applicant)
        applicant.add_comment("Comment", text=message)
    except Exception:
        frappe.log_error(
            message=frappe.as_json(
                {
                    "student_applicant": student_applicant,
                    "applicant_document": applicant_document,
                    "applicant_document_item": applicant_document_item,
                    "item_key": item_key,
                    "item_label": item_label,
                    "document_type": document_type,
                    "file_url": file_url,
                    "upload_source": upload_source,
                    "action": action,
                }
            ),
            title="Applicant document upload timeline write failed",
        )
