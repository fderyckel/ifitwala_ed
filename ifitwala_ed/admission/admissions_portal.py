# ifitwala_ed/admission/admissions_portal.py

from __future__ import annotations

import base64

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.admission_utils import get_applicant_document_slot_spec
from ifitwala_ed.utilities import file_dispatcher

ALLOWED_UPLOAD_SOURCES = {"Desk", "SPA", "API", "Job"}


@frappe.whitelist()
def upload_applicant_document(
    *,
    student_applicant: str | None = None,
    document_type: str | None = None,
    applicant_document: str | None = None,
    upload_source: str | None = "API",
    is_private: int | None = 1,
    ignore_permissions: int | None = 0,
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
        ignore_permissions=ignore_permissions,
    )

    doc_type_code = frappe.db.get_value("Applicant Document Type", doc.document_type, "code") or doc.document_type
    slot_spec = get_applicant_document_slot_spec(doc_type_code)
    if not slot_spec:
        frappe.throw(
            _("Applicant Document Type code is not mapped for file classification: {0}.").format(doc_type_code)
        )

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

    file_kwargs = {
        "attached_to_doctype": "Applicant Document",
        "attached_to_name": doc.name,
        "is_private": cint(is_private) if is_private is not None else 1,
        "file_name": filename,
        "content": content,
    }

    classification = {
        "primary_subject_type": "Student Applicant",
        "primary_subject_id": doc.student_applicant,
        "data_class": slot_spec["data_class"],
        "purpose": slot_spec["purpose"],
        "retention_policy": slot_spec["retention_policy"],
        "slot": slot_spec["slot"],
        "organization": applicant_row.get("organization"),
        "school": applicant_row.get("school"),
        "upload_source": source,
    }

    file_doc = file_dispatcher.create_and_classify_file(
        file_kwargs=file_kwargs,
        classification=classification,
    )

    classification_name = frappe.db.get_value(
        "File Classification",
        {"file": file_doc.name},
        "name",
    )

    return {
        "file": file_doc.name,
        "file_url": file_doc.file_url,
        "classification": classification_name,
        "applicant_document": doc.name,
    }


def _resolve_applicant_document(
    *, applicant_document=None, student_applicant=None, document_type=None, ignore_permissions=0
):
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
    doc.insert(ignore_permissions=bool(cint(ignore_permissions)))
    return doc


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
