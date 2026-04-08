from __future__ import annotations

from typing import Any

from ifitwala_ed.integrations.drive import admissions, materials, media, org_communications, tasks


def reconcile_upload_session_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = tasks.reconcile_task_submission_session_payload(payload)
    return payload


def resolve_finalize_contract(upload_session_doc) -> dict[str, Any]:
    authoritative = tasks.validate_task_submission_finalize_context(upload_session_doc)
    if authoritative is not None:
        return {
            "workflow": "task_submission",
            "authoritative_context": authoritative,
            "attached_field_override": None,
            "context_override": tasks.get_task_submission_context_override(
                getattr(upload_session_doc, "owner_name", None)
            ),
            "binding_role": None,
        }

    authoritative = tasks.validate_task_resource_finalize_context(upload_session_doc)
    if authoritative is not None:
        return {
            "workflow": "task_resource",
            "authoritative_context": authoritative,
            "attached_field_override": None,
            "context_override": tasks.get_task_resource_context_override(
                getattr(upload_session_doc, "owner_name", None),
                getattr(upload_session_doc, "intended_slot", None),
            ),
            "binding_role": "task_resource",
        }

    authoritative = org_communications.validate_org_communication_finalize_context(upload_session_doc)
    if authoritative is not None:
        return {
            "workflow": "org_communication_attachment",
            "authoritative_context": authoritative,
            "attached_field_override": None,
            "context_override": org_communications.get_org_communication_attachment_context_override(
                getattr(upload_session_doc, "owner_name", None),
                getattr(upload_session_doc, "intended_slot", None),
            ),
            "binding_role": "communication_attachment",
        }

    authoritative = materials.validate_supporting_material_finalize_context(upload_session_doc)
    if authoritative is not None:
        return {
            "workflow": "supporting_material",
            "authoritative_context": authoritative,
            "attached_field_override": None,
            "context_override": materials.get_supporting_material_context_override(
                getattr(upload_session_doc, "owner_name", None),
                getattr(upload_session_doc, "intended_slot", None),
            ),
            "binding_role": "general_reference",
        }

    authoritative = media.validate_media_finalize_context(upload_session_doc)
    if authoritative is not None:
        return {
            "workflow": "media",
            "authoritative_context": authoritative,
            "attached_field_override": media.get_attached_field_override(upload_session_doc),
            "context_override": None,
            "binding_role": (
                "organization_media" if getattr(upload_session_doc, "owner_doctype", None) == "Organization" else None
            ),
        }

    authoritative = admissions.validate_applicant_document_finalize_context(upload_session_doc)
    if authoritative is not None:
        return {
            "workflow": "applicant_document",
            "authoritative_context": authoritative,
            "attached_field_override": admissions.get_admissions_attached_field_override(upload_session_doc),
            "context_override": None,
            "binding_role": None,
        }

    authoritative = admissions.validate_applicant_profile_image_finalize_context(upload_session_doc)
    if authoritative is not None:
        return {
            "workflow": "applicant_profile_image",
            "authoritative_context": authoritative,
            "attached_field_override": admissions.get_admissions_attached_field_override(upload_session_doc),
            "context_override": None,
            "binding_role": None,
        }

    authoritative = admissions.validate_applicant_guardian_image_finalize_context(upload_session_doc)
    if authoritative is not None:
        return {
            "workflow": "applicant_guardian_image",
            "authoritative_context": authoritative,
            "attached_field_override": admissions.get_admissions_attached_field_override(upload_session_doc),
            "context_override": None,
            "binding_role": None,
        }

    authoritative = admissions.validate_applicant_health_finalize_context(upload_session_doc)
    if authoritative is not None:
        return {
            "workflow": "applicant_health",
            "authoritative_context": authoritative,
            "attached_field_override": admissions.get_admissions_attached_field_override(upload_session_doc),
            "context_override": None,
            "binding_role": None,
        }

    return {
        "workflow": None,
        "authoritative_context": None,
        "attached_field_override": None,
        "context_override": None,
        "binding_role": None,
    }


def run_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    response: dict[str, Any] = {}
    response.update(tasks.run_task_post_finalize(upload_session_doc, created_file))
    response.update(org_communications.run_org_communication_attachment_post_finalize(upload_session_doc, created_file))
    response.update(materials.run_material_post_finalize(upload_session_doc, created_file))
    response.update(media.run_media_post_finalize(upload_session_doc, created_file))
    response.update(admissions.run_admissions_post_finalize(upload_session_doc, created_file))
    return response
