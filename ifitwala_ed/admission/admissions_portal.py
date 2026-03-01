# ifitwala_ed/admission/admissions_portal.py

from __future__ import annotations

import base64

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from ifitwala_ed.admission.admission_utils import get_applicant_document_slot_spec
from ifitwala_ed.admission.applicant_review_workflow import materialize_document_item_review_assignments
from ifitwala_ed.admission.doctype.applicant_document.applicant_document import (
    sync_applicant_document_review_from_items,
)
from ifitwala_ed.utilities import file_dispatcher

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

        had_existing_file = bool(
            frappe.db.exists(
                "File",
                {
                    "attached_to_doctype": "Applicant Document Item",
                    "attached_to_name": item_doc.name,
                },
            )
        )

        file_kwargs = {
            "attached_to_doctype": "Applicant Document Item",
            "attached_to_name": item_doc.name,
            "is_private": cint(is_private) if is_private is not None else 1,
            "file_name": filename,
            "content": content,
        }

        item_slot_key = f"{slot_spec['slot']}_{frappe.scrub(item_doc.item_key)[:80]}"
        classification = {
            "primary_subject_type": "Student Applicant",
            "primary_subject_id": doc.student_applicant,
            "data_class": slot_spec["data_class"],
            "purpose": slot_spec["purpose"],
            "retention_policy": slot_spec["retention_policy"],
            "slot": item_slot_key,
            "organization": applicant_row.get("organization"),
            "school": applicant_row.get("school"),
            "upload_source": source,
        }

        file_doc = file_dispatcher.create_and_classify_file(
            file_kwargs=file_kwargs,
            classification=classification,
        )

        frappe.db.set_value(
            "Applicant Document Item",
            item_doc.name,
            {
                "review_status": "Pending",
                "review_notes": None,
                "reviewed_by": None,
                "reviewed_on": None,
            },
            update_modified=False,
        )
        sync_applicant_document_review_from_items(doc.name)

        classification_name = frappe.db.get_value(
            "File Classification",
            {"file": file_doc.name},
            "name",
        )

        _append_document_upload_timeline(
            student_applicant=doc.student_applicant,
            applicant_document=doc.name,
            applicant_document_item=item_doc.name,
            item_key=item_doc.item_key,
            item_label=item_doc.item_label,
            document_type=doc.document_type,
            document_type_code=doc_type_code,
            file_url=file_doc.file_url,
            upload_source=source,
            action="replaced" if had_existing_file else "uploaded",
        )
        materialize_document_item_review_assignments(
            applicant_document_item=item_doc.name,
            source_event="document_item_uploaded",
        )

        response = {
            "file": file_doc.name,
            "file_url": file_doc.file_url,
            "classification": classification_name,
            "applicant_document": doc.name,
            "applicant_document_item": item_doc.name,
            "item_key": item_doc.item_key,
            "item_label": item_doc.item_label,
        }
        if cache_key:
            cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=60 * 10)
        return response


def _resolve_applicant_document(*, applicant_document=None, student_applicant=None, document_type=None):
    if applicant_document:
        doc = frappe.get_doc("Applicant Document", applicant_document)
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
    doc.insert()
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
    if applicant_document_item:
        item_doc = frappe.get_doc("Applicant Document Item", applicant_document_item)
        if item_doc.applicant_document != applicant_document.name:
            frappe.throw(_("Applicant Document Item does not match the provided Applicant Document."))
        return item_doc

    requested_key = _sanitize_item_key(item_key)
    requested_label = (item_label or "").strip() or (fallback_label or "").strip() or _("Uploaded file")

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
        key_value = _next_item_key(
            applicant_document=applicant_document.name,
            preferred=requested_label,
        )

    item_doc = frappe.get_doc(
        {
            "doctype": "Applicant Document Item",
            "applicant_document": applicant_document.name,
            "item_key": key_value,
            "item_label": requested_label,
        }
    )
    item_doc.insert()
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
