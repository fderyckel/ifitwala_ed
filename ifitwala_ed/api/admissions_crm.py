# ifitwala_ed/api/admissions_crm.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.api.crm.activities import record_admission_crm_activity_impl
from ifitwala_ed.admission.api.crm.conversations import (
    _apply_identity_defaults,
    _candidate_conversation,
    _resolve_or_create_conversation,
    assign_admission_conversation_impl,
    link_admission_conversation_impl,
    update_admission_conversation_status_impl,
)
from ifitwala_ed.admission.api.crm.guards import (
    _assert_scope_allowed,
    _require_conversation_write,
    _require_doc_read,
    _require_inquiry_write,
    _validate_crm_assignee,
)
from ifitwala_ed.admission.api.crm.idempotency import (
    IDEMPOTENCY_TTL_SECONDS,
    _cache,
    _cache_key,
    _idempotency_key,
    _lock_key,
    _run_idempotent,
)
from ifitwala_ed.admission.api.crm.identities import confirm_admission_external_identity_impl
from ifitwala_ed.admission.api.crm.inquiry_actions import (
    archive_inquiry_from_inbox_impl,
    assign_inquiry_from_inbox_impl,
    invite_inquiry_to_apply_from_inbox_impl,
    mark_inquiry_contacted_from_inbox_impl,
    qualify_inquiry_from_inbox_impl,
)
from ifitwala_ed.admission.api.crm.intake import (
    _append_if_clean,
    _inquiry_payload_for_intake,
    _name_parts,
    _source_from_channel,
    _valid_activity_option,
    _valid_inquiry_option,
    create_admissions_intake_impl,
    create_inquiry_from_admission_conversation_impl,
)
from ifitwala_ed.admission.api.crm.messages import _log_admission_message, log_admission_message_impl
from ifitwala_ed.admission.api.crm.summaries import (
    _activity_summary,
    _applicant_summary,
    _conversation_summary,
    _inquiry_summary,
    _message_summary,
)

_CRM_COMPAT_EXPORTS = (
    IDEMPOTENCY_TTL_SECONDS,
    _cache,
    _cache_key,
    _lock_key,
    _idempotency_key,
    _run_idempotent,
    _require_doc_read,
    _assert_scope_allowed,
    _conversation_summary,
    _message_summary,
    _activity_summary,
    _inquiry_summary,
    _applicant_summary,
    _require_conversation_write,
    _require_inquiry_write,
    _validate_crm_assignee,
    _apply_identity_defaults,
    _candidate_conversation,
    _valid_inquiry_option,
    _valid_activity_option,
    _source_from_channel,
    _name_parts,
    _append_if_clean,
    _inquiry_payload_for_intake,
    _resolve_or_create_conversation,
    _log_admission_message,
)


@frappe.whitelist()
def log_admission_message(
    *,
    conversation: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    external_identity: str | None = None,
    channel_account: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    assigned_to: str | None = None,
    direction: str | None = "Inbound",
    body: str | None = None,
    message_type: str | None = "Text",
    delivery_status: str | None = None,
    message_at: str | None = None,
    external_message_id: str | None = None,
    external_conversation_id: str | None = None,
    dedupe_key: str | None = None,
    provider_payload_json: str | None = None,
    media_provider_id: str | None = None,
    media_mime_type: str | None = None,
    media_file_name: str | None = None,
    media_size: int | None = None,
    media_status: str | None = None,
    client_request_id: str | None = None,
):
    return log_admission_message_impl(
        conversation=conversation,
        inquiry=inquiry,
        student_applicant=student_applicant,
        external_identity=external_identity,
        channel_account=channel_account,
        organization=organization,
        school=school,
        assigned_to=assigned_to,
        direction=direction,
        body=body,
        message_type=message_type,
        delivery_status=delivery_status,
        message_at=message_at,
        external_message_id=external_message_id,
        external_conversation_id=external_conversation_id,
        dedupe_key=dedupe_key,
        provider_payload_json=provider_payload_json,
        media_provider_id=media_provider_id,
        media_mime_type=media_mime_type,
        media_file_name=media_file_name,
        media_size=media_size,
        media_status=media_status,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def record_admission_crm_activity(
    *,
    conversation: str | None = None,
    activity_type: str | None = None,
    outcome: str | None = None,
    note: str | None = None,
    next_action_on: str | None = None,
    activity_at: str | None = None,
    client_request_id: str | None = None,
):
    return record_admission_crm_activity_impl(
        conversation=conversation,
        activity_type=activity_type,
        outcome=outcome,
        note=note,
        next_action_on=next_action_on,
        activity_at=activity_at,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def link_admission_conversation(
    *,
    conversation: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    external_identity: str | None = None,
    channel_account: str | None = None,
    client_request_id: str | None = None,
):
    return link_admission_conversation_impl(
        conversation=conversation,
        inquiry=inquiry,
        student_applicant=student_applicant,
        external_identity=external_identity,
        channel_account=channel_account,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def confirm_admission_external_identity(
    *,
    external_identity: str | None = None,
    contact: str | None = None,
    guardian: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    match_status: str | None = "Confirmed",
    client_request_id: str | None = None,
):
    return confirm_admission_external_identity_impl(
        external_identity=external_identity,
        contact=contact,
        guardian=guardian,
        inquiry=inquiry,
        student_applicant=student_applicant,
        match_status=match_status,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def create_admissions_intake(
    *,
    organization: str | None = None,
    school: str | None = None,
    type_of_inquiry: str | None = None,
    source: str | None = None,
    activity_channel: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone_number: str | None = None,
    student_first_name: str | None = None,
    student_last_name: str | None = None,
    intended_academic_year: str | None = None,
    grade_level_interest: str | None = None,
    program_interest: str | None = None,
    student_name_or_id: str | None = None,
    relationship_to_student: str | None = None,
    organization_name: str | None = None,
    partnership_context: str | None = None,
    message: str | None = None,
    activity_type: str | None = None,
    outcome: str | None = None,
    note: str | None = None,
    next_action_on: str | None = None,
    assigned_to: str | None = None,
    assignment_lane: str | None = None,
    client_request_id: str | None = None,
):
    return create_admissions_intake_impl(
        organization=organization,
        school=school,
        type_of_inquiry=type_of_inquiry,
        source=source,
        activity_channel=activity_channel,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone_number=phone_number,
        student_first_name=student_first_name,
        student_last_name=student_last_name,
        intended_academic_year=intended_academic_year,
        grade_level_interest=grade_level_interest,
        program_interest=program_interest,
        student_name_or_id=student_name_or_id,
        relationship_to_student=relationship_to_student,
        organization_name=organization_name,
        partnership_context=partnership_context,
        message=message,
        activity_type=activity_type,
        outcome=outcome,
        note=note,
        next_action_on=next_action_on,
        assigned_to=assigned_to,
        assignment_lane=assignment_lane,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def assign_admission_conversation(
    *,
    conversation: str | None = None,
    assigned_to: str | None = None,
    client_request_id: str | None = None,
):
    return assign_admission_conversation_impl(
        conversation=conversation,
        assigned_to=assigned_to,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def update_admission_conversation_status(
    *,
    conversation: str | None = None,
    status: str | None = None,
    note: str | None = None,
    client_request_id: str | None = None,
):
    return update_admission_conversation_status_impl(
        conversation=conversation,
        status=status,
        note=note,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def create_inquiry_from_admission_conversation(
    *,
    conversation: str | None = None,
    type_of_inquiry: str | None = None,
    source: str | None = None,
    message: str | None = None,
    client_request_id: str | None = None,
):
    return create_inquiry_from_admission_conversation_impl(
        conversation=conversation,
        type_of_inquiry=type_of_inquiry,
        source=source,
        message=message,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def assign_inquiry_from_inbox(
    *,
    inquiry: str | None = None,
    assigned_to: str | None = None,
    assignment_lane: str | None = None,
    client_request_id: str | None = None,
):
    return assign_inquiry_from_inbox_impl(
        inquiry=inquiry,
        assigned_to=assigned_to,
        assignment_lane=assignment_lane,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def archive_inquiry_from_inbox(
    *,
    inquiry: str | None = None,
    reason: str | None = None,
    client_request_id: str | None = None,
):
    return archive_inquiry_from_inbox_impl(inquiry=inquiry, reason=reason, client_request_id=client_request_id)


@frappe.whitelist()
def mark_inquiry_contacted_from_inbox(
    *,
    inquiry: str | None = None,
    complete_todo: int | str | None = 0,
    client_request_id: str | None = None,
):
    return mark_inquiry_contacted_from_inbox_impl(
        inquiry=inquiry,
        complete_todo=complete_todo,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def qualify_inquiry_from_inbox(
    *,
    inquiry: str | None = None,
    client_request_id: str | None = None,
):
    return qualify_inquiry_from_inbox_impl(inquiry=inquiry, client_request_id=client_request_id)


@frappe.whitelist()
def invite_inquiry_to_apply_from_inbox(
    *,
    inquiry: str | None = None,
    school: str | None = None,
    organization: str | None = None,
    client_request_id: str | None = None,
):
    return invite_inquiry_to_apply_from_inbox_impl(
        inquiry=inquiry,
        school=school,
        organization=organization,
        client_request_id=client_request_id,
    )
