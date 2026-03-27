from __future__ import annotations

from typing import Any

import frappe
from frappe import _

_HEALTH_VACCINATION_SLOT_PREFIX = "health_vaccination_proof_"
_APPLICANT_PROFILE_IMAGE_SLOT = "profile_image"
_GUARDIAN_PROFILE_IMAGE_SLOT_PREFIX = "guardian_profile_image__"
_ADMISSIONS_HEALTH_DATA_CLASS = "safeguarding"
_ADMISSIONS_HEALTH_PURPOSE = "medical_record"
_ADMISSIONS_HEALTH_RETENTION_POLICY = "until_school_exit_plus_6m"
_ADMISSIONS_PROFILE_IMAGE_DATA_CLASS = "identity_image"
_ADMISSIONS_PROFILE_IMAGE_PURPOSE = "applicant_profile_display"
_ADMISSIONS_PROFILE_IMAGE_RETENTION_POLICY = "until_school_exit_plus_6m"


def _build_health_vaccination_slot(
    *,
    vaccine_name: str | None,
    date_value: str | None,
    row_index: int | None = None,
) -> str:
    base = "_".join(part for part in [(vaccine_name or "").strip(), (date_value or "").strip()] if part).strip()
    if not base:
        index = int(row_index or 0)
        base = f"row_{index + 1}"
    return f"{_HEALTH_VACCINATION_SLOT_PREFIX}{frappe.scrub(base)[:80]}"


def _get_student_applicant_scope(student_applicant: str) -> dict[str, Any]:
    applicant_row = (
        frappe.db.get_value(
            "Student Applicant",
            student_applicant,
            ["organization", "school"],
            as_dict=True,
        )
        or {}
    )
    if not applicant_row.get("organization") or not applicant_row.get("school"):
        frappe.throw(_("Student Applicant must have organization and school."))
    return applicant_row


def _build_guardian_profile_image_slot(guardian_row_name: str) -> str:
    if not (guardian_row_name or "").strip():
        frappe.throw(_("Guardian row name is required for guardian image uploads."))
    return f"{_GUARDIAN_PROFILE_IMAGE_SLOT_PREFIX}{frappe.scrub(guardian_row_name)[:80]}"


def get_applicant_document_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.admission import admissions_portal as admission_api
    from ifitwala_ed.admission.admission_utils import get_applicant_document_slot_spec

    student_applicant = payload.get("student_applicant")
    document_type = payload.get("document_type")
    applicant_document_item = payload.get("applicant_document_item")
    item_key = payload.get("item_key")
    item_label = payload.get("item_label")

    if not student_applicant:
        frappe.throw(_("Missing required field: student_applicant"))
    if not document_type and not applicant_document_item:
        frappe.throw(_("Missing required field: document_type"))

    doc = admission_api._resolve_applicant_document(
        applicant_document=payload.get("applicant_document"),
        student_applicant=student_applicant,
        document_type=document_type,
    )
    item_doc = admission_api._resolve_applicant_document_item(
        applicant_document=doc,
        applicant_document_item=applicant_document_item,
        item_key=item_key,
        item_label=item_label,
        fallback_label=payload.get("filename_original"),
    )

    doc_type_code = frappe.db.get_value("Applicant Document Type", doc.document_type, "code") or doc.document_type
    slot_spec = get_applicant_document_slot_spec(document_type=doc.document_type, doc_type_code=doc_type_code)
    if not slot_spec:
        frappe.throw(_("Applicant Document Type is missing upload classification settings: {0}.").format(doc_type_code))

    applicant_row = _get_student_applicant_scope(doc.student_applicant)

    item_slot_key = f"{slot_spec['slot']}_{frappe.scrub(item_doc.item_key)[:80]}"
    return {
        "owner_doctype": "Student Applicant",
        "owner_name": doc.student_applicant,
        "attached_doctype": "Applicant Document Item",
        "attached_name": item_doc.name,
        "organization": applicant_row.get("organization"),
        "school": applicant_row.get("school"),
        "primary_subject_type": "Student Applicant",
        "primary_subject_id": doc.student_applicant,
        "data_class": slot_spec["data_class"],
        "purpose": slot_spec["purpose"],
        "retention_policy": slot_spec["retention_policy"],
        "slot": item_slot_key,
        "applicant_document": doc.name,
        "applicant_document_item": item_doc.name,
        "item_key": item_doc.item_key,
        "item_label": item_doc.item_label,
        "document_type": doc.document_type,
        "document_type_code": doc_type_code,
    }


def get_applicant_health_vaccination_context(payload: dict[str, Any]) -> dict[str, Any]:
    student_applicant = payload.get("student_applicant")
    applicant_health_profile = payload.get("applicant_health_profile")

    if not student_applicant:
        frappe.throw(_("Missing required field: student_applicant"))
    if not applicant_health_profile:
        frappe.throw(_("Missing required field: applicant_health_profile"))

    health_row = (
        frappe.db.get_value(
            "Applicant Health Profile",
            applicant_health_profile,
            ["name", "student_applicant"],
            as_dict=True,
        )
        or {}
    )
    if not health_row.get("name"):
        frappe.throw(_("Applicant Health Profile does not exist: {0}").format(applicant_health_profile))
    if health_row.get("student_applicant") != student_applicant:
        frappe.throw(
            _("Applicant Health Profile '{0}' does not belong to Student Applicant '{1}'.").format(
                applicant_health_profile, student_applicant
            )
        )

    applicant_row = _get_student_applicant_scope(student_applicant)

    return {
        "owner_doctype": "Student Applicant",
        "owner_name": student_applicant,
        "attached_doctype": "Applicant Health Profile",
        "attached_name": applicant_health_profile,
        "organization": applicant_row.get("organization"),
        "school": applicant_row.get("school"),
        "primary_subject_type": "Student Applicant",
        "primary_subject_id": student_applicant,
        "data_class": _ADMISSIONS_HEALTH_DATA_CLASS,
        "purpose": _ADMISSIONS_HEALTH_PURPOSE,
        "retention_policy": _ADMISSIONS_HEALTH_RETENTION_POLICY,
        "slot": _build_health_vaccination_slot(
            vaccine_name=payload.get("vaccine_name"),
            date_value=payload.get("date"),
            row_index=payload.get("row_index"),
        ),
    }


def get_applicant_profile_image_context(payload: dict[str, Any]) -> dict[str, Any]:
    student_applicant = payload.get("student_applicant")
    if not student_applicant:
        frappe.throw(_("Missing required field: student_applicant"))

    applicant_row = _get_student_applicant_scope(student_applicant)
    return {
        "owner_doctype": "Student Applicant",
        "owner_name": student_applicant,
        "attached_doctype": "Student Applicant",
        "attached_name": student_applicant,
        "organization": applicant_row.get("organization"),
        "school": applicant_row.get("school"),
        "primary_subject_type": "Student Applicant",
        "primary_subject_id": student_applicant,
        "data_class": _ADMISSIONS_PROFILE_IMAGE_DATA_CLASS,
        "purpose": _ADMISSIONS_PROFILE_IMAGE_PURPOSE,
        "retention_policy": _ADMISSIONS_PROFILE_IMAGE_RETENTION_POLICY,
        "slot": _APPLICANT_PROFILE_IMAGE_SLOT,
    }


def get_applicant_guardian_image_context(payload: dict[str, Any]) -> dict[str, Any]:
    student_applicant = payload.get("student_applicant")
    guardian_row_name = payload.get("guardian_row_name")

    if not student_applicant:
        frappe.throw(_("Missing required field: student_applicant"))
    if not guardian_row_name:
        frappe.throw(_("Missing required field: guardian_row_name"))

    guardian_row = (
        frappe.db.get_value(
            "Student Applicant Guardian",
            {
                "parenttype": "Student Applicant",
                "parent": student_applicant,
                "name": guardian_row_name,
            },
            ["name", "parent"],
            as_dict=True,
        )
        or {}
    )
    if not guardian_row.get("name"):
        frappe.throw(
            _("Guardian row '{0}' was not found on Student Applicant '{1}'.").format(
                guardian_row_name, student_applicant
            )
        )

    applicant_row = _get_student_applicant_scope(student_applicant)
    return {
        "owner_doctype": "Student Applicant",
        "owner_name": student_applicant,
        "attached_doctype": "Student Applicant Guardian",
        "attached_name": guardian_row_name,
        "organization": applicant_row.get("organization"),
        "school": applicant_row.get("school"),
        "primary_subject_type": "Student Applicant",
        "primary_subject_id": student_applicant,
        "data_class": _ADMISSIONS_PROFILE_IMAGE_DATA_CLASS,
        "purpose": _ADMISSIONS_PROFILE_IMAGE_PURPOSE,
        "retention_policy": _ADMISSIONS_PROFILE_IMAGE_RETENTION_POLICY,
        "slot": _build_guardian_profile_image_slot(str(guardian_row_name)),
    }


def get_admissions_attached_field_override(upload_session_doc) -> str | None:
    if (
        getattr(upload_session_doc, "owner_doctype", None) == "Student Applicant"
        and getattr(upload_session_doc, "attached_doctype", None) == "Applicant Health Profile"
        and str(getattr(upload_session_doc, "intended_slot", "") or "").startswith(_HEALTH_VACCINATION_SLOT_PREFIX)
    ):
        return "vaccinations"

    if (
        getattr(upload_session_doc, "owner_doctype", None) == "Student Applicant"
        and getattr(upload_session_doc, "attached_doctype", None) == "Student Applicant"
        and getattr(upload_session_doc, "intended_slot", None) == _APPLICANT_PROFILE_IMAGE_SLOT
    ):
        return "applicant_image"

    if (
        getattr(upload_session_doc, "owner_doctype", None) == "Student Applicant"
        and getattr(upload_session_doc, "attached_doctype", None) == "Student Applicant Guardian"
        and str(getattr(upload_session_doc, "intended_slot", "") or "").startswith(_GUARDIAN_PROFILE_IMAGE_SLOT_PREFIX)
    ):
        return "guardian_image"

    return None


def validate_applicant_document_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if (
        getattr(upload_session_doc, "owner_doctype", None) != "Student Applicant"
        or getattr(upload_session_doc, "attached_doctype", None) != "Applicant Document Item"
    ):
        return None

    context = get_applicant_document_context(
        {
            "student_applicant": upload_session_doc.owner_name,
            "applicant_document_item": upload_session_doc.attached_name,
        }
    )
    field_map = {
        "owner_doctype": "owner_doctype",
        "owner_name": "owner_name",
        "attached_doctype": "attached_doctype",
        "attached_name": "attached_name",
        "organization": "organization",
        "school": "school",
        "intended_primary_subject_type": "primary_subject_type",
        "intended_primary_subject_id": "primary_subject_id",
        "intended_data_class": "data_class",
        "intended_purpose": "purpose",
        "intended_retention_policy": "retention_policy",
        "intended_slot": "slot",
    }
    for session_field, context_field in field_map.items():
        if getattr(upload_session_doc, session_field, None) != context.get(context_field):
            frappe.throw(
                _("Upload session no longer matches the authoritative admissions context for field '{0}'.").format(
                    session_field
                )
            )
    return context


def validate_applicant_profile_image_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if (
        getattr(upload_session_doc, "owner_doctype", None) != "Student Applicant"
        or getattr(upload_session_doc, "attached_doctype", None) != "Student Applicant"
        or getattr(upload_session_doc, "intended_slot", None) != _APPLICANT_PROFILE_IMAGE_SLOT
    ):
        return None

    context = get_applicant_profile_image_context(
        {
            "student_applicant": upload_session_doc.owner_name,
        }
    )
    field_map = {
        "owner_doctype": "owner_doctype",
        "owner_name": "owner_name",
        "attached_doctype": "attached_doctype",
        "attached_name": "attached_name",
        "organization": "organization",
        "school": "school",
        "intended_primary_subject_type": "primary_subject_type",
        "intended_primary_subject_id": "primary_subject_id",
        "intended_data_class": "data_class",
        "intended_purpose": "purpose",
        "intended_retention_policy": "retention_policy",
        "intended_slot": "slot",
    }
    for session_field, context_field in field_map.items():
        if getattr(upload_session_doc, session_field, None) != context.get(context_field):
            frappe.throw(
                _("Upload session no longer matches the authoritative admissions context for field '{0}'.").format(
                    session_field
                )
            )
    return context


def validate_applicant_guardian_image_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if (
        getattr(upload_session_doc, "owner_doctype", None) != "Student Applicant"
        or getattr(upload_session_doc, "attached_doctype", None) != "Student Applicant Guardian"
        or not str(getattr(upload_session_doc, "intended_slot", "") or "").startswith(
            _GUARDIAN_PROFILE_IMAGE_SLOT_PREFIX
        )
    ):
        return None

    context = get_applicant_guardian_image_context(
        {
            "student_applicant": upload_session_doc.owner_name,
            "guardian_row_name": upload_session_doc.attached_name,
        }
    )
    field_map = {
        "owner_doctype": "owner_doctype",
        "owner_name": "owner_name",
        "attached_doctype": "attached_doctype",
        "attached_name": "attached_name",
        "organization": "organization",
        "school": "school",
        "intended_primary_subject_type": "primary_subject_type",
        "intended_primary_subject_id": "primary_subject_id",
        "intended_data_class": "data_class",
        "intended_purpose": "purpose",
        "intended_retention_policy": "retention_policy",
        "intended_slot": "slot",
    }
    for session_field, context_field in field_map.items():
        if getattr(upload_session_doc, session_field, None) != context.get(context_field):
            frappe.throw(
                _("Upload session no longer matches the authoritative admissions context for field '{0}'.").format(
                    session_field
                )
            )
    return context


def validate_applicant_health_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if (
        getattr(upload_session_doc, "owner_doctype", None) != "Student Applicant"
        or getattr(upload_session_doc, "attached_doctype", None) != "Applicant Health Profile"
        or not str(getattr(upload_session_doc, "intended_slot", "") or "").startswith(_HEALTH_VACCINATION_SLOT_PREFIX)
    ):
        return None

    context = get_applicant_health_vaccination_context(
        {
            "student_applicant": upload_session_doc.owner_name,
            "applicant_health_profile": upload_session_doc.attached_name,
            "filename_original": getattr(upload_session_doc, "filename_original", None),
            "row_index": 0,
        }
    )
    field_map = {
        "owner_doctype": "owner_doctype",
        "owner_name": "owner_name",
        "attached_doctype": "attached_doctype",
        "attached_name": "attached_name",
        "organization": "organization",
        "school": "school",
        "intended_primary_subject_type": "primary_subject_type",
        "intended_primary_subject_id": "primary_subject_id",
        "intended_data_class": "data_class",
        "intended_purpose": "purpose",
        "intended_retention_policy": "retention_policy",
        "intended_slot": "slot",
    }
    for session_field, context_field in field_map.items():
        if getattr(upload_session_doc, session_field, None) != context.get(context_field):
            frappe.throw(
                _("Upload session no longer matches the authoritative admissions context for field '{0}'.").format(
                    session_field
                )
            )
    return context


def run_admissions_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    file_url = getattr(created_file, "file_url", None) or frappe.db.get_value("File", created_file.name, "file_url")
    classification_name = frappe.db.get_value("File Classification", {"file": created_file.name}, "name")

    if getattr(upload_session_doc, "attached_doctype", None) == "Applicant Document Item":
        from ifitwala_ed.admission import admissions_portal as admission_api
        from ifitwala_ed.admission.applicant_review_workflow import (
            materialize_document_item_review_assignments,
        )
        from ifitwala_ed.admission.doctype.applicant_document.applicant_document import (
            sync_applicant_document_review_from_items,
        )

        item_row = (
            frappe.db.get_value(
                "Applicant Document Item",
                upload_session_doc.attached_name,
                ["applicant_document", "item_key", "item_label"],
                as_dict=True,
            )
            or {}
        )
        frappe.db.set_value(
            "Applicant Document Item",
            upload_session_doc.attached_name,
            {
                "file": file_url,
                "file_name": getattr(created_file, "file_name", None)
                or frappe.db.get_value("File", created_file.name, "file_name"),
                "file_size": getattr(created_file, "file_size", None)
                or frappe.db.get_value("File", created_file.name, "file_size"),
                "review_status": "pending_review",
            },
            update_modified=False,
        )
        if item_row.get("applicant_document"):
            sync_applicant_document_review_from_items(applicant_document=item_row["applicant_document"])
            materialize_document_item_review_assignments(applicant_document=item_row["applicant_document"])
        admission_api._append_document_upload_timeline(
            student_applicant=upload_session_doc.owner_name,
            applicant_document=item_row.get("applicant_document"),
            applicant_document_item=upload_session_doc.attached_name,
            file=created_file.name,
            classification=classification_name,
            upload_source=getattr(upload_session_doc, "upload_source", None),
        )
        return {
            "classification": classification_name,
            "file_url": file_url,
            "applicant_document": item_row.get("applicant_document"),
            "applicant_document_item": upload_session_doc.attached_name,
            "item_key": item_row.get("item_key"),
            "item_label": item_row.get("item_label"),
        }

    if getattr(upload_session_doc, "attached_doctype", None) == "Student Applicant":
        frappe.db.set_value(
            "Student Applicant",
            upload_session_doc.owner_name,
            "applicant_image",
            file_url,
            update_modified=False,
        )
        return {
            "classification": classification_name,
            "file_url": file_url,
            "student_applicant": upload_session_doc.owner_name,
        }

    if getattr(upload_session_doc, "attached_doctype", None) == "Student Applicant Guardian":
        frappe.db.set_value(
            "Student Applicant Guardian",
            upload_session_doc.attached_name,
            "guardian_image",
            file_url,
            update_modified=False,
        )
        return {
            "classification": classification_name,
            "file_url": file_url,
            "student_applicant": upload_session_doc.owner_name,
            "guardian_row_name": upload_session_doc.attached_name,
        }

    if getattr(upload_session_doc, "attached_doctype", None) == "Applicant Health Profile":
        return {
            "classification": classification_name,
            "file_url": file_url,
            "student_applicant": upload_session_doc.owner_name,
            "applicant_health_profile": upload_session_doc.attached_name,
        }

    return {}
