# ifitwala_ed/admission/api/recommendation_intake/document_integration.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.api.recommendation_intake.constants import (
    RECOMMENDATION_REQUEST_DOCTYPE,
    RECOMMENDATION_UPLOAD_ALLOWED_EXTENSIONS,
    RECOMMENDATION_UPLOAD_ALLOWED_MIME_TYPES,
    RECOMMENDATION_UPLOAD_GENERIC_MIME_TYPES,
)
from ifitwala_ed.admission.api.recommendation_intake.dto import _text
from ifitwala_ed.api.attachment_previews import build_attachment_preview_item, extract_file_extension
from ifitwala_ed.api.file_access import (
    resolve_admissions_file_open_url,
    resolve_admissions_file_preview_url,
    resolve_admissions_file_thumbnail_url,
)


def _normalize_recommendation_upload_mime_type(value) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _recommendation_upload_extension(file_name: str | None) -> str:
    text = _text(file_name).lower()
    if "." not in text:
        return ""
    return f".{text.rsplit('.', 1)[-1]}"


def _recommendation_upload_type_message() -> str:
    return _("Recommendation attachments must be PDF or PNG files.")


def _resolve_recommendation_upload_mime_hint(*, file_name: str | None, content_type: str | None = None) -> str:
    mime_type = _normalize_recommendation_upload_mime_type(content_type)
    extension = _recommendation_upload_extension(file_name)
    expected_from_extension = RECOMMENDATION_UPLOAD_ALLOWED_EXTENSIONS.get(extension)

    if mime_type and mime_type not in RECOMMENDATION_UPLOAD_GENERIC_MIME_TYPES:
        if mime_type not in RECOMMENDATION_UPLOAD_ALLOWED_MIME_TYPES:
            frappe.throw(_recommendation_upload_type_message(), frappe.ValidationError)
        if expected_from_extension and expected_from_extension != mime_type:
            frappe.throw(
                _("The selected file extension does not match the uploaded file type. Upload a PDF or PNG file."),
                frappe.ValidationError,
            )

    if extension and not expected_from_extension:
        frappe.throw(_recommendation_upload_type_message(), frappe.ValidationError)

    resolved = expected_from_extension or (mime_type if mime_type in RECOMMENDATION_UPLOAD_ALLOWED_MIME_TYPES else None)
    if not resolved:
        frappe.throw(_recommendation_upload_type_message(), frappe.ValidationError)
    return resolved


def _load_drive_version_mime_map(version_ids: list[str]) -> dict[str, str]:
    resolved_version_ids = [version_id for version_id in dict.fromkeys(version_ids) if _text(version_id)]
    if not resolved_version_ids:
        return {}

    rows = frappe.get_all(
        "Drive File Version",
        filters={"name": ["in", resolved_version_ids]},
        fields=["name", "mime_type"],
        limit=0,
    )
    return {_text(row.get("name")): _text(row.get("mime_type")) for row in rows if _text(row.get("name"))}


def _serialize_recommendation_attachment(
    *,
    student_applicant: str,
    latest_drive_file: dict | None,
    thumbnail_ready_map: dict[str, bool],
    version_mime_map: dict[str, str],
) -> dict:
    drive_row = latest_drive_file or {}
    drive_file_id = _text(drive_row.get("name"))
    compatibility_file_id = _text(drive_row.get("file"))
    canonical_ref = _text(drive_row.get("canonical_ref")) or None
    file_name = (
        _text(drive_row.get("display_name")) or _text(drive_row.get("file_name")) or compatibility_file_id or None
    )
    preview_status = _text(drive_row.get("preview_status")) or None
    if not drive_file_id and not compatibility_file_id:
        return {
            "drive_file_id": None,
            "canonical_ref": None,
            "file_name": None,
            "open_url": None,
            "preview_url": None,
            "thumbnail_url": None,
            "preview_status": None,
            "attachment_preview": None,
        }

    open_url = resolve_admissions_file_open_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id or None,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant,
    )
    preview_url = resolve_admissions_file_preview_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id or None,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant,
        preview_ready=preview_status == "ready",
    )
    thumbnail_url = resolve_admissions_file_thumbnail_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id or None,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant,
        thumbnail_ready=thumbnail_ready_map.get(drive_file_id, False),
    )
    mime_type = version_mime_map.get(_text(drive_row.get("current_version"))) or None
    attachment_preview = build_attachment_preview_item(
        item_id=drive_file_id or compatibility_file_id or file_name,
        owner_doctype="Student Applicant",
        owner_name=student_applicant,
        file_id=drive_file_id or compatibility_file_id,
        display_name=file_name,
        mime_type=mime_type,
        extension=extract_file_extension(file_name=file_name, file_url=None),
        preview_status=preview_status,
        thumbnail_url=thumbnail_url,
        preview_url=preview_url,
        open_url=open_url,
        download_url=open_url,
    )
    return {
        "drive_file_id": drive_file_id or None,
        "canonical_ref": canonical_ref,
        "file_name": file_name,
        "open_url": open_url,
        "preview_url": preview_url,
        "thumbnail_url": thumbnail_url,
        "preview_status": preview_status,
        "attachment_preview": attachment_preview,
    }


def _new_item_key(student_applicant: str) -> str:
    base = "recommendation"
    for _index in range(30):
        candidate = f"{base}_{frappe.generate_hash(length=8)}"
        if not frappe.db.exists(
            RECOMMENDATION_REQUEST_DOCTYPE,
            {"student_applicant": student_applicant, "item_key": candidate},
        ):
            return candidate
    frappe.throw(_("Could not allocate a unique recommendation item key."))
    return ""


def _ensure_document_item_slot(
    *,
    student_applicant: str,
    target_document_type: str,
    item_key: str,
    item_label: str,
) -> tuple[str, str]:
    doc_name = frappe.db.get_value(
        "Applicant Document",
        {"student_applicant": student_applicant, "document_type": target_document_type},
        "name",
    )
    if not doc_name:
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": student_applicant,
                "document_type": target_document_type,
            }
        )
        doc.insert(ignore_permissions=True)
        doc_name = doc.name

    item_name = frappe.db.get_value(
        "Applicant Document Item",
        {"applicant_document": doc_name, "item_key": item_key},
        "name",
    )
    if not item_name:
        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": doc_name,
                "item_key": item_key,
                "item_label": item_label,
            }
        )
        item.insert(ignore_permissions=True)
        item_name = item.name
    else:
        frappe.db.set_value(
            "Applicant Document Item",
            item_name,
            "item_label",
            item_label,
            update_modified=False,
        )

    return doc_name, item_name
