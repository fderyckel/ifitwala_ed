from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import (
    get_applicant_document_slot_spec,
    has_scoped_staff_access_to_student_applicant,
)

_WORKFLOW_EXPORTS = {
    "portfolio": {
        "purpose": "portfolio_export",
        "slot": "portfolio_export_pdf",
        "retention_policy": "immediate_on_request",
    },
    "journal": {
        "purpose": "journal_export",
        "slot": "journal_export_pdf",
        "retention_policy": "immediate_on_request",
    },
}
_HEALTH_VACCINATION_SLOT_PREFIX = "health_vaccination_proof_"


def _require_text(payload: dict[str, Any], fieldname: str) -> str:
    value = str(payload.get(fieldname) or "").strip()
    if not value:
        frappe.throw(_("Missing required field: {0}").format(fieldname))
    return value


def _load_workflow_payload(upload_session_doc) -> dict[str, Any]:
    raw = str(getattr(upload_session_doc, "upload_contract_json", None) or "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except Exception:
        return {}

    if not isinstance(parsed, dict):
        return {}
    workflow = parsed.get("workflow")
    if not isinstance(workflow, dict):
        return {}
    workflow_payload = workflow.get("workflow_payload")
    return workflow_payload if isinstance(workflow_payload, dict) else {}


def _validate_session_fields(upload_session_doc, authoritative: dict[str, Any], *, label: str) -> dict[str, Any]:
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
        if getattr(upload_session_doc, session_field, None) != authoritative.get(context_field):
            frappe.throw(
                _("Upload session no longer matches the authoritative {0} context for field '{1}'.").format(
                    label,
                    session_field,
                )
            )
    return authoritative


def _resolve_student_scope(student: str, *, permission_type: str | None = "write") -> dict[str, str]:
    student_doc = frappe.get_doc("Student", student)
    if permission_type:
        student_doc.check_permission(permission_type)

    school = str(getattr(student_doc, "anchor_school", None) or "").strip()
    if not school:
        frappe.throw(_("Student must have an anchor school before governed file uploads can continue."))

    organization = str(frappe.db.get_value("School", school, "organization") or "").strip()
    if not organization:
        frappe.throw(_("School must belong to an organization before governed file uploads can continue."))

    return {
        "student": student_doc.name,
        "school": school,
        "organization": organization,
    }


def _build_health_vaccination_slot(
    *,
    vaccine_name: str | None,
    date_value: str | None,
    row_index: int | None = None,
) -> str:
    base = "_".join(part for part in [(vaccine_name or "").strip(), (date_value or "").strip()] if part).strip()
    if not base:
        base = f"row_{int(row_index or 0) + 1}"
    return f"{_HEALTH_VACCINATION_SLOT_PREFIX}{frappe.scrub(base)[:80]}"


def get_student_export_context(payload: dict[str, Any]) -> dict[str, Any]:
    student = _require_text(payload, "student")
    export_kind = _require_text(payload, "export_kind").lower()
    export_contract = _WORKFLOW_EXPORTS.get(export_kind)
    if not export_contract:
        frappe.throw(_("Unsupported student export kind: {0}").format(export_kind))

    scope = _resolve_student_scope(student)
    return {
        "owner_doctype": "Student",
        "owner_name": scope["student"],
        "attached_doctype": "Student",
        "attached_name": scope["student"],
        "organization": scope["organization"],
        "school": scope["school"],
        "primary_subject_type": "Student",
        "primary_subject_id": scope["student"],
        "data_class": "academic",
        "purpose": export_contract["purpose"],
        "retention_policy": export_contract["retention_policy"],
        "slot": export_contract["slot"],
    }


def validate_student_export_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student":
        return None

    workflow_payload = _load_workflow_payload(upload_session_doc)
    if not workflow_payload:
        return None

    return _validate_session_fields(
        upload_session_doc,
        get_student_export_context(workflow_payload),
        label=_("student export"),
    )


def get_student_patient_vaccination_context(payload: dict[str, Any]) -> dict[str, Any]:
    student_patient = _require_text(payload, "student_patient")
    patient_doc = frappe.get_doc("Student Patient", student_patient)
    patient_doc.check_permission("write")

    student = str(getattr(patient_doc, "student", None) or "").strip()
    if not student:
        frappe.throw(_("Student Patient must be linked to a Student before governed file uploads can continue."))

    scope = _resolve_student_scope(student)
    return {
        "owner_doctype": "Student Patient",
        "owner_name": patient_doc.name,
        "attached_doctype": "Student Patient",
        "attached_name": patient_doc.name,
        "organization": scope["organization"],
        "school": scope["school"],
        "primary_subject_type": "Student",
        "primary_subject_id": scope["student"],
        "data_class": "safeguarding",
        "purpose": "medical_record",
        "retention_policy": "until_school_exit_plus_6m",
        "slot": _build_health_vaccination_slot(
            vaccine_name=str(payload.get("vaccine_name") or "").strip() or None,
            date_value=str(payload.get("date") or "").strip() or None,
            row_index=payload.get("row_index"),
        ),
    }


def get_student_artifact_attached_field_override(upload_session_doc) -> str | None:
    if (
        getattr(upload_session_doc, "owner_doctype", None) == "Student Patient"
        and getattr(upload_session_doc, "attached_doctype", None) == "Student Patient"
        and str(getattr(upload_session_doc, "intended_slot", "") or "").startswith(_HEALTH_VACCINATION_SLOT_PREFIX)
    ):
        return "vaccinations"
    return None


def validate_student_patient_vaccination_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student Patient":
        return None

    workflow_payload = _load_workflow_payload(upload_session_doc)
    if not workflow_payload:
        return None

    return _validate_session_fields(
        upload_session_doc,
        get_student_patient_vaccination_context(workflow_payload),
        label=_("student vaccination proof"),
    )


def get_promoted_admissions_document_context(payload: dict[str, Any]) -> dict[str, Any]:
    student = _require_text(payload, "student")
    student_applicant = _require_text(payload, "student_applicant")
    source_item_name = _require_text(payload, "source_applicant_document_item")

    student_applicant_for_student = str(frappe.db.get_value("Student", student, "student_applicant") or "").strip()
    if student_applicant_for_student != student_applicant:
        frappe.throw(
            _("Student '{student}' is not linked to Student Applicant '{student_applicant}'.").format(
                student=student,
                student_applicant=student_applicant,
            )
        )

    if not has_scoped_staff_access_to_student_applicant(
        user=frappe.session.user,
        student_applicant=student_applicant,
    ):
        frappe.throw(
            _("You do not have permission to copy admissions documents for this applicant."),
            frappe.PermissionError,
        )

    scope = _resolve_student_scope(student, permission_type=None)
    item_row = (
        frappe.db.get_value(
            "Applicant Document Item",
            source_item_name,
            ["applicant_document", "item_key", "item_label"],
            as_dict=True,
        )
        or {}
    )
    applicant_document = str(item_row.get("applicant_document") or "").strip()
    if not applicant_document:
        frappe.throw(
            _("Applicant Document Item '{0}' is missing its parent Applicant Document.").format(source_item_name)
        )

    document_row = (
        frappe.db.get_value(
            "Applicant Document",
            applicant_document,
            ["student_applicant", "document_type"],
            as_dict=True,
        )
        or {}
    )
    if str(document_row.get("student_applicant") or "").strip() != student_applicant:
        frappe.throw(
            _("Applicant Document Item '{0}' does not belong to Student Applicant '{1}'.").format(
                source_item_name,
                student_applicant,
            )
        )

    document_type = str(document_row.get("document_type") or "").strip()
    if not document_type:
        frappe.throw(_("Applicant Document '{0}' is missing its document type.").format(applicant_document))

    doc_type_code = frappe.db.get_value("Applicant Document Type", document_type, "code") or document_type
    slot_spec = get_applicant_document_slot_spec(document_type=document_type, doc_type_code=doc_type_code)
    if not slot_spec:
        frappe.throw(
            _("Applicant Document Type {0} is missing upload classification settings.").format(
                doc_type_code or document_type
            )
        )

    item_key = str(item_row.get("item_key") or source_item_name or "item").strip()
    return {
        "owner_doctype": "Student",
        "owner_name": scope["student"],
        "attached_doctype": "Student",
        "attached_name": scope["student"],
        "organization": scope["organization"],
        "school": scope["school"],
        "primary_subject_type": "Student",
        "primary_subject_id": scope["student"],
        "data_class": slot_spec["data_class"],
        "purpose": slot_spec["purpose"],
        "retention_policy": slot_spec["retention_policy"],
        "slot": f"admissions_{frappe.scrub(doc_type_code or 'document')}_{frappe.scrub(item_key)[:80]}",
    }


def validate_promoted_admissions_document_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student":
        return None

    workflow_payload = _load_workflow_payload(upload_session_doc)
    if not workflow_payload:
        return None

    return _validate_session_fields(
        upload_session_doc,
        get_promoted_admissions_document_context(workflow_payload),
        label=_("promoted admissions document"),
    )
