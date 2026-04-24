from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import frappe
from frappe import _

_WORKFLOW_CONTRACT_VERSION = "1"


WorkflowContextResolver = Callable[[dict[str, Any]], dict[str, Any]]
FinalizeValidator = Callable[[Any], Optional[dict[str, Any]]]
AttachedFieldResolver = Callable[[Any], Optional[str]]
ContextOverrideResolver = Callable[[Any, dict[str, Any]], Optional[dict[str, Any]]]
BindingRoleResolver = Callable[[Any, dict[str, Any]], Optional[str]]
PostFinalizeHandler = Callable[[Any, Any], dict[str, Any]]


@dataclass(frozen=True)
class GovernedUploadSpec:
    workflow_id: str
    contract_version: str
    resolve_session_context: WorkflowContextResolver
    validate_finalize_context: FinalizeValidator
    resolve_attached_field_override: AttachedFieldResolver
    resolve_context_override: ContextOverrideResolver
    resolve_binding_role: BindingRoleResolver
    run_post_finalize: PostFinalizeHandler
    is_private: bool | None = None


def _throw_missing_field(fieldname: str) -> None:
    frappe.throw(_("Missing required field: {0}").format(fieldname))


def _as_non_empty_string(payload: dict[str, Any], fieldname: str) -> str:
    value = str(payload.get(fieldname) or "").strip()
    if not value:
        _throw_missing_field(fieldname)
    return value


def _validate_workflow_slot(payload: dict[str, Any], authoritative: dict[str, Any], *, label: str) -> None:
    provided_slot = str(payload.get("slot") or "").strip()
    if provided_slot and provided_slot != str(authoritative.get("slot") or "").strip():
        frappe.throw(_("{0} slot does not match the authoritative workflow context.").format(label))


def _no_attached_field_override(_upload_session_doc) -> str | None:
    return None


def _no_context_override(_upload_session_doc, _authoritative_context: dict[str, Any]) -> dict[str, Any] | None:
    return None


def _no_binding_role(_upload_session_doc, _authoritative_context: dict[str, Any]) -> str | None:
    return None


def _noop_post_finalize(_upload_session_doc, _created_file) -> dict[str, Any]:
    return {}


def _static_binding_role(value: str) -> BindingRoleResolver:
    def _resolver(_upload_session_doc, _authoritative_context: dict[str, Any]) -> str | None:
        return value

    return _resolver


def _resolve_task_submission_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import tasks

    task_submission = str(payload.get("task_submission") or payload.get("owner_name") or "").strip()
    if not task_submission:
        _throw_missing_field("task_submission")

    task_submission_doc = tasks.assert_task_submission_upload_access(task_submission, permission_type="write")
    authoritative = tasks.build_task_submission_upload_contract(task_submission_doc)
    _validate_workflow_slot(payload, authoritative, label=_("Task submission upload"))

    student = payload.get("student")
    if student not in (None, "", authoritative["primary_subject_id"]):
        frappe.throw(_("Student does not match the authoritative Task Submission owner context."))

    return authoritative


def _resolve_task_feedback_export_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import tasks

    task_submission = str(payload.get("task_submission") or payload.get("owner_name") or "").strip()
    if not task_submission:
        _throw_missing_field("task_submission")

    task_submission_doc = tasks.assert_task_submission_upload_access(task_submission, permission_type="write")
    authoritative = tasks.build_task_feedback_export_upload_contract(
        task_submission_doc,
        audience=payload.get("audience"),
    )
    _validate_workflow_slot(payload, authoritative, label=_("Task feedback export"))
    return authoritative


def _resolve_task_submission_context_override(
    upload_session_doc, authoritative_context: dict[str, Any]
) -> dict[str, Any] | None:
    from ifitwala_ed.integrations.drive import tasks

    owner_name = str(
        getattr(upload_session_doc, "owner_name", None) or authoritative_context.get("owner_name") or ""
    ).strip()
    return tasks.get_task_submission_context_override(owner_name)


def _resolve_task_feedback_export_context_override(
    upload_session_doc, authoritative_context: dict[str, Any]
) -> dict[str, Any] | None:
    from ifitwala_ed.integrations.drive import tasks

    owner_name = str(
        getattr(upload_session_doc, "owner_name", None) or authoritative_context.get("owner_name") or ""
    ).strip()
    slot = str(getattr(upload_session_doc, "intended_slot", None) or authoritative_context.get("slot") or "").strip()
    return tasks.get_task_feedback_export_context_override(owner_name, slot)


def _validate_task_submission_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Task Submission":
        return None

    from ifitwala_ed.integrations.drive import tasks

    return tasks.validate_task_submission_finalize_context(upload_session_doc)


def _validate_task_feedback_export_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Task Submission":
        return None

    from ifitwala_ed.integrations.drive import tasks

    return tasks.validate_task_feedback_export_finalize_context(upload_session_doc)


def _resolve_supporting_material_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import materials

    material = _as_non_empty_string(payload, "material")
    material_doc = materials.assert_supporting_material_upload_access(material, permission_type="write")
    authoritative = materials.build_supporting_material_upload_contract(material_doc)
    _validate_workflow_slot(payload, authoritative, label=_("Supporting Material upload"))
    return authoritative


def _resolve_supporting_material_context_override(
    upload_session_doc, authoritative_context: dict[str, Any]
) -> dict[str, Any] | None:
    from ifitwala_ed.integrations.drive import materials

    owner_name = str(
        getattr(upload_session_doc, "owner_name", None) or authoritative_context.get("owner_name") or ""
    ).strip()
    slot = str(getattr(upload_session_doc, "intended_slot", None) or authoritative_context.get("slot") or "").strip()
    return materials.get_supporting_material_context_override(owner_name, slot)


def _resolve_supporting_material_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import materials

    return materials.run_material_post_finalize(upload_session_doc, created_file)


def _validate_supporting_material_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Supporting Material":
        return None

    from ifitwala_ed.integrations.drive import materials

    return materials.validate_supporting_material_finalize_context(upload_session_doc)


def _resolve_org_communication_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import org_communications

    org_communication = _as_non_empty_string(payload, "org_communication")
    row_name = payload.get("row_name")
    org_communication_doc = org_communications.assert_org_communication_upload_access(
        org_communication,
        permission_type="write",
    )
    authoritative = org_communications.build_org_communication_upload_contract(
        org_communication_doc,
        row_name=row_name,
    )
    _validate_workflow_slot(payload, authoritative, label=_("Org Communication attachment upload"))
    return authoritative


def _resolve_org_communication_context_override(
    upload_session_doc, authoritative_context: dict[str, Any]
) -> dict[str, Any] | None:
    from ifitwala_ed.integrations.drive import org_communications

    owner_name = str(
        getattr(upload_session_doc, "owner_name", None) or authoritative_context.get("owner_name") or ""
    ).strip()
    slot = str(getattr(upload_session_doc, "intended_slot", None) or authoritative_context.get("slot") or "").strip()
    return org_communications.get_org_communication_attachment_context_override(owner_name, slot)


def _resolve_org_communication_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import org_communications

    return org_communications.run_org_communication_attachment_post_finalize(upload_session_doc, created_file)


def _validate_org_communication_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Org Communication":
        return None

    from ifitwala_ed.integrations.drive import org_communications

    return org_communications.validate_org_communication_finalize_context(upload_session_doc)


def _resolve_employee_image_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import media

    employee = _as_non_empty_string(payload, "employee")
    employee_doc = frappe.get_doc("Employee", employee)
    employee_doc.check_permission("write")
    authoritative = media.build_employee_image_contract(employee_doc)
    _validate_workflow_slot(payload, authoritative, label=_("Employee profile image upload"))
    return authoritative


def _resolve_student_image_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import media

    student = _as_non_empty_string(payload, "student")
    student_doc = frappe.get_doc("Student", student)
    student_doc.check_permission("write")
    authoritative = media.build_student_image_contract(student_doc)
    _validate_workflow_slot(payload, authoritative, label=_("Student profile image upload"))
    return authoritative


def _resolve_guardian_image_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import media

    guardian = _as_non_empty_string(payload, "guardian")
    guardian_doc = frappe.get_doc("Guardian", guardian)
    guardian_doc.check_permission("write")
    authoritative = media.build_guardian_image_contract(guardian_doc)
    _validate_workflow_slot(payload, authoritative, label=_("Guardian profile image upload"))
    return authoritative


def _resolve_organization_logo_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import media
    from ifitwala_ed.utilities.organization_media import build_organization_logo_slot

    organization = _as_non_empty_string(payload, "organization")
    org_doc = frappe.get_doc("Organization", organization)
    org_doc.check_permission("write")
    authoritative = media.build_organization_media_contract(
        organization=org_doc.name,
        slot=build_organization_logo_slot(organization=org_doc.name),
        school=None,
        upload_source=str(payload.get("upload_source") or "Desk"),
    )
    _validate_workflow_slot(payload, authoritative, label=_("Organization logo upload"))
    return authoritative


def _resolve_school_logo_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import media
    from ifitwala_ed.utilities.organization_media import build_school_logo_slot

    school = _as_non_empty_string(payload, "school")
    school_doc = frappe.get_doc("School", school)
    school_doc.check_permission("write")
    if not getattr(school_doc, "organization", None):
        frappe.throw(_("Organization is required before uploading a school logo."))

    authoritative = media.build_organization_media_contract(
        organization=school_doc.organization,
        slot=build_school_logo_slot(school=school_doc.name),
        school=school_doc.name,
        upload_source=str(payload.get("upload_source") or "Desk"),
    )
    _validate_workflow_slot(payload, authoritative, label=_("School logo upload"))
    return authoritative


def _resolve_school_gallery_image_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import media
    from ifitwala_ed.utilities.organization_media import build_school_gallery_slot

    school = _as_non_empty_string(payload, "school")
    row_name = _as_non_empty_string(payload, "row_name")

    school_doc = frappe.get_doc("School", school)
    school_doc.check_permission("write")
    if not getattr(school_doc, "organization", None):
        frappe.throw(_("Organization is required before uploading a gallery image."))

    authoritative = media.build_organization_media_contract(
        organization=school_doc.organization,
        slot=build_school_gallery_slot(row_name=row_name),
        school=school_doc.name,
        upload_source=str(payload.get("upload_source") or "Desk"),
    )
    _validate_workflow_slot(payload, authoritative, label=_("School gallery image upload"))
    return authoritative


def _resolve_organization_media_asset_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import media
    from ifitwala_ed.utilities.organization_media import build_organization_media_slot

    organization = str(payload.get("organization") or "").strip()
    school = str(payload.get("school") or "").strip() or None
    scope = str(payload.get("scope") or "organization").strip().lower()

    if school and not organization:
        school_doc = frappe.get_doc("School", school)
        school_doc.check_permission("write")
        organization = str(getattr(school_doc, "organization", None) or "").strip()
    elif organization:
        org_doc = frappe.get_doc("Organization", organization)
        org_doc.check_permission("write")
        organization = org_doc.name

    if not organization:
        frappe.throw(_("Organization is required before uploading organization media."))
    if scope not in {"organization", "school"}:
        frappe.throw(_("Scope must be 'organization' or 'school'."))
    if scope == "school" and not school:
        frappe.throw(_("School is required for school-scoped organization media."))
    if scope == "organization":
        school = None

    media_key = str(payload.get("media_key") or "").strip()
    if not media_key:
        base_name = str(payload.get("filename_original") or "media").rsplit(".", 1)[0]
        media_key = f"{frappe.scrub(base_name) or 'media'}_{frappe.generate_hash(length=6)}"

    authoritative = media.build_organization_media_contract(
        organization=organization,
        slot=build_organization_media_slot(media_key=media_key),
        school=school,
        upload_source=str(payload.get("upload_source") or "Desk"),
    )
    authoritative["media_key"] = media_key
    authoritative["scope"] = scope
    _validate_workflow_slot(payload, authoritative, label=_("Organization media upload"))
    return authoritative


def _resolve_media_attached_field_override(upload_session_doc) -> str | None:
    from ifitwala_ed.integrations.drive import media

    return media.get_attached_field_override(upload_session_doc)


def _resolve_media_binding_role(upload_session_doc, authoritative_context: dict[str, Any]) -> str | None:
    owner_doctype = str(
        getattr(upload_session_doc, "owner_doctype", None) or authoritative_context.get("owner_doctype") or ""
    ).strip()
    return "organization_media" if owner_doctype == "Organization" else None


def _resolve_media_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import media

    return media.run_media_post_finalize(upload_session_doc, created_file)


def _validate_media_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    owner_doctype = getattr(upload_session_doc, "owner_doctype", None)
    if owner_doctype not in {"Employee", "Guardian", "Student", "Organization"}:
        return None

    from ifitwala_ed.integrations.drive import media

    return media.validate_media_finalize_context(upload_session_doc)


def _resolve_applicant_document_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import admissions

    return admissions.get_applicant_document_context(payload)


def _resolve_applicant_profile_image_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import admissions

    return admissions.get_applicant_profile_image_context(payload)


def _resolve_applicant_guardian_image_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import admissions

    return admissions.get_applicant_guardian_image_context(payload)


def _resolve_applicant_health_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import admissions

    return admissions.get_applicant_health_vaccination_context(payload)


def _resolve_admissions_attached_field_override(upload_session_doc) -> str | None:
    from ifitwala_ed.integrations.drive import admissions

    return admissions.get_admissions_attached_field_override(upload_session_doc)


def _resolve_admissions_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import admissions

    return admissions.run_admissions_post_finalize(upload_session_doc, created_file)


def _validate_applicant_document_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student Applicant":
        return None

    from ifitwala_ed.integrations.drive import admissions

    return admissions.validate_applicant_document_finalize_context(upload_session_doc)


def _validate_applicant_profile_image_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student Applicant":
        return None

    from ifitwala_ed.integrations.drive import admissions

    return admissions.validate_applicant_profile_image_finalize_context(upload_session_doc)


def _validate_applicant_guardian_image_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student Applicant":
        return None

    from ifitwala_ed.integrations.drive import admissions

    return admissions.validate_applicant_guardian_image_finalize_context(upload_session_doc)


def _validate_applicant_health_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student Applicant":
        return None

    from ifitwala_ed.integrations.drive import admissions

    return admissions.validate_applicant_health_finalize_context(upload_session_doc)


def _resolve_student_export_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import student_artifacts

    return student_artifacts.get_student_export_context(payload)


def _resolve_student_patient_vaccination_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import student_artifacts

    return student_artifacts.get_student_patient_vaccination_context(payload)


def _resolve_promoted_admissions_document_session_context(payload: dict[str, Any]) -> dict[str, Any]:
    from ifitwala_ed.integrations.drive import student_artifacts

    return student_artifacts.get_promoted_admissions_document_context(payload)


def _resolve_student_artifact_attached_field_override(upload_session_doc) -> str | None:
    from ifitwala_ed.integrations.drive import student_artifacts

    return student_artifacts.get_student_artifact_attached_field_override(upload_session_doc)


def _validate_student_export_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student":
        return None

    from ifitwala_ed.integrations.drive import student_artifacts

    return student_artifacts.validate_student_export_finalize_context(upload_session_doc)


def _validate_student_patient_vaccination_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student Patient":
        return None

    from ifitwala_ed.integrations.drive import student_artifacts

    return student_artifacts.validate_student_patient_vaccination_finalize_context(upload_session_doc)


def _validate_promoted_admissions_document_finalize_context(upload_session_doc) -> Optional[dict[str, Any]]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Student":
        return None

    from ifitwala_ed.integrations.drive import student_artifacts

    return student_artifacts.validate_promoted_admissions_document_finalize_context(upload_session_doc)


_WORKFLOW_SPECS: tuple[GovernedUploadSpec, ...] = (
    GovernedUploadSpec(
        workflow_id="task.submission",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_task_submission_session_context,
        validate_finalize_context=_validate_task_submission_finalize_context,
        resolve_attached_field_override=_no_attached_field_override,
        resolve_context_override=_resolve_task_submission_context_override,
        resolve_binding_role=_no_binding_role,
        run_post_finalize=_noop_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="task.feedback_export",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_task_feedback_export_session_context,
        validate_finalize_context=_validate_task_feedback_export_finalize_context,
        resolve_attached_field_override=_no_attached_field_override,
        resolve_context_override=_resolve_task_feedback_export_context_override,
        resolve_binding_role=_no_binding_role,
        run_post_finalize=_noop_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="supporting_material.file",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_supporting_material_session_context,
        validate_finalize_context=_validate_supporting_material_finalize_context,
        resolve_attached_field_override=_no_attached_field_override,
        resolve_context_override=_resolve_supporting_material_context_override,
        resolve_binding_role=_static_binding_role("supporting_material"),
        run_post_finalize=_resolve_supporting_material_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="admissions.applicant_document",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_applicant_document_session_context,
        validate_finalize_context=_validate_applicant_document_finalize_context,
        resolve_attached_field_override=_resolve_admissions_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_no_binding_role,
        run_post_finalize=_resolve_admissions_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="admissions.applicant_profile_image",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=True,
        resolve_session_context=_resolve_applicant_profile_image_session_context,
        validate_finalize_context=_validate_applicant_profile_image_finalize_context,
        resolve_attached_field_override=_resolve_admissions_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_no_binding_role,
        run_post_finalize=_resolve_admissions_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="admissions.applicant_guardian_image",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=True,
        resolve_session_context=_resolve_applicant_guardian_image_session_context,
        validate_finalize_context=_validate_applicant_guardian_image_finalize_context,
        resolve_attached_field_override=_resolve_admissions_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_no_binding_role,
        run_post_finalize=_resolve_admissions_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="admissions.applicant_health_vaccination",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_applicant_health_session_context,
        validate_finalize_context=_validate_applicant_health_finalize_context,
        resolve_attached_field_override=_resolve_admissions_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_no_binding_role,
        run_post_finalize=_resolve_admissions_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="student.export_file",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_student_export_session_context,
        validate_finalize_context=_validate_student_export_finalize_context,
        resolve_attached_field_override=_no_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_no_binding_role,
        run_post_finalize=_noop_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="student_patient.vaccination_proof",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_student_patient_vaccination_session_context,
        validate_finalize_context=_validate_student_patient_vaccination_finalize_context,
        resolve_attached_field_override=_resolve_student_artifact_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_no_binding_role,
        run_post_finalize=_noop_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="student.promoted_admissions_document",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_promoted_admissions_document_session_context,
        validate_finalize_context=_validate_promoted_admissions_document_finalize_context,
        resolve_attached_field_override=_no_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_no_binding_role,
        run_post_finalize=_noop_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="org_communication.attachment",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_org_communication_session_context,
        validate_finalize_context=_validate_org_communication_finalize_context,
        resolve_attached_field_override=_no_attached_field_override,
        resolve_context_override=_resolve_org_communication_context_override,
        resolve_binding_role=_static_binding_role("communication_attachment"),
        run_post_finalize=_resolve_org_communication_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="media.employee_profile_image",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=True,
        resolve_session_context=_resolve_employee_image_session_context,
        validate_finalize_context=_validate_media_finalize_context,
        resolve_attached_field_override=_resolve_media_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_resolve_media_binding_role,
        run_post_finalize=_resolve_media_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="media.student_profile_image",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=True,
        resolve_session_context=_resolve_student_image_session_context,
        validate_finalize_context=_validate_media_finalize_context,
        resolve_attached_field_override=_resolve_media_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_resolve_media_binding_role,
        run_post_finalize=_resolve_media_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="media.guardian_profile_image",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=True,
        resolve_session_context=_resolve_guardian_image_session_context,
        validate_finalize_context=_validate_media_finalize_context,
        resolve_attached_field_override=_resolve_media_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_resolve_media_binding_role,
        run_post_finalize=_resolve_media_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="organization_media.organization_logo",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_organization_logo_session_context,
        validate_finalize_context=_validate_media_finalize_context,
        resolve_attached_field_override=_resolve_media_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_resolve_media_binding_role,
        run_post_finalize=_resolve_media_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="organization_media.school_logo",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_school_logo_session_context,
        validate_finalize_context=_validate_media_finalize_context,
        resolve_attached_field_override=_resolve_media_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_resolve_media_binding_role,
        run_post_finalize=_resolve_media_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="organization_media.school_gallery_image",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_school_gallery_image_session_context,
        validate_finalize_context=_validate_media_finalize_context,
        resolve_attached_field_override=_resolve_media_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_resolve_media_binding_role,
        run_post_finalize=_resolve_media_post_finalize,
    ),
    GovernedUploadSpec(
        workflow_id="organization_media.asset",
        contract_version=_WORKFLOW_CONTRACT_VERSION,
        is_private=None,
        resolve_session_context=_resolve_organization_media_asset_session_context,
        validate_finalize_context=_validate_media_finalize_context,
        resolve_attached_field_override=_resolve_media_attached_field_override,
        resolve_context_override=_no_context_override,
        resolve_binding_role=_resolve_media_binding_role,
        run_post_finalize=_resolve_media_post_finalize,
    ),
)

_WORKFLOW_SPEC_BY_ID = {spec.workflow_id: spec for spec in _WORKFLOW_SPECS}
_WORKFLOW_ID_ALIASES = {
    "supporting_material": "supporting_material.file",
    "task_submission": "task.submission",
    "applicant_document": "admissions.applicant_document",
    "applicant_profile_image": "admissions.applicant_profile_image",
    "applicant_guardian_image": "admissions.applicant_guardian_image",
    "applicant_health": "admissions.applicant_health_vaccination",
    "org_communication_attachment": "org_communication.attachment",
}


def normalize_workflow_id(workflow_id: str | None) -> str | None:
    value = str(workflow_id or "").strip()
    if not value:
        return None
    return _WORKFLOW_ID_ALIASES.get(value, value)


def get_upload_spec(workflow_id: str) -> GovernedUploadSpec:
    normalized = normalize_workflow_id(workflow_id)
    if not normalized or normalized not in _WORKFLOW_SPEC_BY_ID:
        frappe.throw(_("Unknown governed upload workflow: {0}").format(workflow_id or _("unknown")))
    return _WORKFLOW_SPEC_BY_ID[normalized]


def iter_upload_specs() -> tuple[GovernedUploadSpec, ...]:
    return _WORKFLOW_SPECS


def build_upload_session_context(workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        frappe.throw(_("workflow_payload must be a dict."))

    spec = get_upload_spec(workflow_id)
    resolved = dict(spec.resolve_session_context(dict(payload)))
    if spec.is_private is not None:
        resolved["is_private"] = int(bool(spec.is_private))
    resolved["workflow_id"] = spec.workflow_id
    resolved["contract_version"] = spec.contract_version
    return resolved
