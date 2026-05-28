# ifitwala_ed/api/admissions_portal.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.access import (
    ADMISSIONS_ACCESS_MODE_FAMILY,
    ADMISSIONS_FAMILY_ROLE,
    get_admissions_access_mode,
    is_family_workspace_enabled,
)
from ifitwala_ed.admission.access import (
    ADMISSIONS_APPLICANT_ROLE as ADMISSIONS_ROLE,
)
from ifitwala_ed.admission.admission_utils import (
    ensure_admissions_permission,
    ensure_contact_dynamic_link,
    ensure_contact_for_email,
    get_contact_primary_email,
    normalize_email_value,
    sync_student_applicant_contact_binding,
    upsert_contact_email,
)
from ifitwala_ed.admission.api.common.request_payload import (
    _as_bool,
    _as_check,
    _has_bound_value,
    _parse_request_payload,
    _request_form_value,
    _request_json_payload,
)
from ifitwala_ed.admission.api.portal.access import (
    _ensure_applicant_match,
    _get_applicant_for_user,
    _require_admissions_applicant,
    _require_admissions_portal_user,
    _session_user,  # noqa: F401 - re-exported for old private import compatibility.
)
from ifitwala_ed.admission.api.portal.contacts import (
    _applicant_contact_prefill_payload,
    _get_inquiry_contact_for_applicant,
    _resolve_applicant_contact,
)
from ifitwala_ed.admission.api.portal.documents import (
    _load_drive_version_mime_map,
    _portal_document_requirement_state,
    _portal_required_document_count,
    _recommendation_target_document_types_for_applicant,
    _serialize_applicant_document_attachment,
    list_applicant_document_types_impl,
    list_applicant_documents_impl,
    upload_applicant_document_impl,
)
from ifitwala_ed.admission.api.portal.enrollment import (
    PORTAL_EDITABLE_STATUSES,
    PORTAL_STATUS_MAP,
    READ_ONLY_REASON_MAP,
    _empty_applicant_enrollment_choice_state,
    _portal_status_for,
    _read_only_for,
    _serialize_enrollment_offer,
    accept_enrollment_offer_impl,
    decline_enrollment_offer_impl,
    get_applicant_enrollment_choices_impl,
    update_applicant_enrollment_choices_impl,
)
from ifitwala_ed.admission.api.portal.guardians import (
    APPLICANT_CONTACT_GUARDIAN_ROW,
    APPLICANT_GUARDIAN_CHECK_FIELDS,
    APPLICANT_GUARDIAN_EMPLOYMENT_SECTOR_OPTIONS,
    APPLICANT_GUARDIAN_FIELDS,
    APPLICANT_GUARDIAN_GENDER_OPTIONS,
    APPLICANT_GUARDIAN_INVITE_REQUIRED_FIELDS,
    APPLICANT_GUARDIAN_RELATIONSHIP_OPTIONS,
    APPLICANT_GUARDIAN_REQUIRED_FIELDS,
    APPLICANT_GUARDIAN_TEXT_FIELDS,
    _applicant_guardian_required_field_label,
    _apply_guardians_to_applicant,
    _contact_is_linked_to_applicant,
    _create_or_update_guardian_contact,
    _guardian_contact_name_from_guardian_email,
    _guardian_row_display_name,
    _guardian_row_is_empty,
    _guardian_salutation_options,
    _guardian_signer_flag_from_primary_guardian,
    _guardians_feature_enabled,
    _hydrate_guardian_row_from_applicant_contact,
    _hydrate_guardian_row_from_guardian_doc,
    _normalize_guardian_row,
    _parse_guardians_payload,
    _serialize_applicant_guardians,
    _set_contact_primary_email,
    _set_contact_primary_mobile,
    _update_contact_identity_from_guardian_row,
    _validate_guardian_profile_row,
)
from ifitwala_ed.admission.api.portal.health import (
    APPLICANT_HEALTH_FIELDS,
    APPLICANT_HEALTH_VACCINATION_FIELDS,
    _coerce_vaccination_date,
    _decode_base64_content,
    _default_health_payload,
    _has_health_declaration_column,
    _normalize_vaccinations,
    _portal_health_state,
    _serialize_health_doc,
    _upload_vaccination_proof,
    get_applicant_health_impl,
    update_applicant_health_impl,
)
from ifitwala_ed.admission.api.portal.invites import (
    _applicant_invite_options_payload,
    _applicant_self_invite_blocked_reason,
    _bootstrap_applicant_contact_guardian_row,
    _call_user_method_if_available,
    _canonical_applicant_contact_for_invite,
    _clear_applicant_self_login_for_family_conversion,
    _contact_linked_to_applicant,
    _contact_linked_to_user,
    _ensure_admissions_applicant_role,
    _ensure_admissions_family_role,
    _ensure_family_guardian_user,
    _family_invite_options_payload,
    _get_applicant_guardian_row,
    _invite_contact_email_options,
    _invite_contact_primary_email,
    _remove_admissions_applicant_role,
    _require_family_workspace_mode,
    _require_scoped_staff_applicant_access,
    _required_family_acknowledgement_policy_labels,
    _send_applicant_invite_email,
    get_admissions_portal_invite_options_impl,
    get_family_invite_options_impl,
    get_invite_email_options_impl,
    invite_applicant_impl,
    invite_family_collaborator_impl,
)
from ifitwala_ed.admission.api.portal.policies import (
    _family_policy_blocked_reason,
    _find_family_guardian_context,
    _normalize_signature_name,
    _resolve_family_guardian_context,
    acknowledge_policy_impl,
    get_applicant_policies_impl,
)
from ifitwala_ed.admission.api.portal.profile import (
    APPLICANT_PROFILE_FIELDS,
    APPLICANT_PROFILE_GENDER_OPTIONS,
    APPLICANT_PROFILE_REQUIRED_FIELD_LABELS,
    APPLICANT_PROFILE_RESIDENCY_OPTIONS,
    _application_context_payload,
    _assert_record_modified_matches,
    _build_profile_payload,
    _default_profile_payload,
    _normalize_record_modified,
    _profile_completeness,
    _profile_reference_options,
    _serialize_applicant_profile,
    get_applicant_profile_impl,
    update_applicant_profile_impl,
)
from ifitwala_ed.admission.api.portal.profile_images import (
    _CURRENT_PROFILE_IMAGE_STATUSES,
    PROFILE_IMAGE_ALLOWED_ACCEPT_LABEL,
    PROFILE_IMAGE_ALLOWED_EXTENSIONS,
    PROFILE_IMAGE_MAX_BYTES,
    PROFILE_IMAGE_MAX_PIXELS,
    _applicant_image_open_url,
    _build_admissions_profile_image_urls,
    _collect_guardian_image_authority_map,
    _decode_profile_image_content,
    _file_is_scoped_to_applicant,
    _guardian_image_open_url,
    _guardian_profile_image_slot,
    _normalize_profile_image_bytes,
    _prepare_profile_image_upload,
    _profile_image_allowed_formats_message,
    _profile_image_extension,
    _profile_image_extension_mismatch_message,
    _profile_image_invalid_content_message,
    _profile_image_output_filename,
    _profile_image_pixel_limit_message,
    _profile_image_size_limit_message,
    _profile_image_to_rgb,
    _resolve_applicant_profile_image_authority,
    _resolve_applicant_profile_image_drive_file,
    _resolve_applicant_profile_image_file,
    _resolve_guardian_image_authority,
    _resolve_guardian_image_drive_file,
    _resolve_guardian_image_file,
    _resolve_profile_image_drive_file_from_file_row,
    _sniff_profile_image_format,
    upload_applicant_guardian_image_impl,
    upload_applicant_profile_image_impl,
)
from ifitwala_ed.admission.api.portal.session import (
    _applicant_summary_payload,
    _build_applicant_display_name,
    get_admissions_session_impl,
)
from ifitwala_ed.admission.api.portal.snapshot import (
    _completion_state_for_health,
    _completion_state_for_interviews,
    _completion_state_for_recommendations,
    _completion_state_for_requirement,
    _derive_next_actions,
    get_applicant_snapshot_impl,
)
from ifitwala_ed.admission.api.portal.submission import submit_application_impl, withdraw_application_impl
from ifitwala_ed.contacts.contact_privacy import (
    assert_user_can_access_student_applicant_contact,
    get_raw_contact_email_options_for_applicant_invite,
)
from ifitwala_ed.governance.policy_utils import (
    ADMISSIONS_POLICY_MODE_FAMILY,
    get_applicant_policy_status,
)

_PRIVATE_COMPAT_EXPORTS = (
    _ensure_applicant_match,
    _get_applicant_for_user,
    _require_admissions_applicant,
    _require_admissions_portal_user,
    _applicant_contact_prefill_payload,
    _get_inquiry_contact_for_applicant,
    _resolve_applicant_contact,
    _as_bool,
    _as_check,
    _has_bound_value,
    _parse_request_payload,
    _request_form_value,
    _request_json_payload,
    APPLICANT_CONTACT_GUARDIAN_ROW,
    APPLICANT_GUARDIAN_CHECK_FIELDS,
    APPLICANT_GUARDIAN_EMPLOYMENT_SECTOR_OPTIONS,
    APPLICANT_GUARDIAN_FIELDS,
    APPLICANT_GUARDIAN_GENDER_OPTIONS,
    APPLICANT_GUARDIAN_INVITE_REQUIRED_FIELDS,
    APPLICANT_GUARDIAN_RELATIONSHIP_OPTIONS,
    APPLICANT_GUARDIAN_REQUIRED_FIELDS,
    APPLICANT_GUARDIAN_TEXT_FIELDS,
    _applicant_guardian_required_field_label,
    _apply_guardians_to_applicant,
    _contact_is_linked_to_applicant,
    _create_or_update_guardian_contact,
    _guardian_contact_name_from_guardian_email,
    _guardian_row_display_name,
    _guardian_row_is_empty,
    _guardian_salutation_options,
    _guardian_signer_flag_from_primary_guardian,
    _guardians_feature_enabled,
    _hydrate_guardian_row_from_applicant_contact,
    _hydrate_guardian_row_from_guardian_doc,
    _normalize_guardian_row,
    _parse_guardians_payload,
    _serialize_applicant_guardians,
    _set_contact_primary_email,
    _set_contact_primary_mobile,
    _update_contact_identity_from_guardian_row,
    _validate_guardian_profile_row,
    PORTAL_EDITABLE_STATUSES,
    PORTAL_STATUS_MAP,
    READ_ONLY_REASON_MAP,
    _empty_applicant_enrollment_choice_state,
    _portal_status_for,
    _read_only_for,
    _serialize_enrollment_offer,
    _load_drive_version_mime_map,
    _portal_document_requirement_state,
    _portal_required_document_count,
    _recommendation_target_document_types_for_applicant,
    _serialize_applicant_document_attachment,
    APPLICANT_PROFILE_FIELDS,
    APPLICANT_PROFILE_GENDER_OPTIONS,
    APPLICANT_PROFILE_REQUIRED_FIELD_LABELS,
    APPLICANT_PROFILE_RESIDENCY_OPTIONS,
    _application_context_payload,
    _assert_record_modified_matches,
    _build_profile_payload,
    _default_profile_payload,
    _normalize_record_modified,
    _profile_completeness,
    _profile_reference_options,
    _serialize_applicant_profile,
    PROFILE_IMAGE_ALLOWED_ACCEPT_LABEL,
    PROFILE_IMAGE_ALLOWED_EXTENSIONS,
    PROFILE_IMAGE_MAX_BYTES,
    PROFILE_IMAGE_MAX_PIXELS,
    _CURRENT_PROFILE_IMAGE_STATUSES,
    _applicant_image_open_url,
    _build_admissions_profile_image_urls,
    _collect_guardian_image_authority_map,
    _decode_profile_image_content,
    _file_is_scoped_to_applicant,
    _guardian_image_open_url,
    _guardian_profile_image_slot,
    _normalize_profile_image_bytes,
    _prepare_profile_image_upload,
    _profile_image_allowed_formats_message,
    _profile_image_extension,
    _profile_image_extension_mismatch_message,
    _profile_image_invalid_content_message,
    _profile_image_output_filename,
    _profile_image_pixel_limit_message,
    _profile_image_size_limit_message,
    _profile_image_to_rgb,
    _resolve_applicant_profile_image_authority,
    _resolve_applicant_profile_image_drive_file,
    _resolve_applicant_profile_image_file,
    _resolve_guardian_image_authority,
    _resolve_guardian_image_drive_file,
    _resolve_guardian_image_file,
    _resolve_profile_image_drive_file_from_file_row,
    _sniff_profile_image_format,
    _applicant_summary_payload,
    _build_applicant_display_name,
    _completion_state_for_health,
    _completion_state_for_interviews,
    _completion_state_for_recommendations,
    _completion_state_for_requirement,
    _derive_next_actions,
    _family_policy_blocked_reason,
    _find_family_guardian_context,
    _normalize_signature_name,
    _resolve_family_guardian_context,
    APPLICANT_HEALTH_FIELDS,
    APPLICANT_HEALTH_VACCINATION_FIELDS,
    _coerce_vaccination_date,
    _decode_base64_content,
    _default_health_payload,
    _has_health_declaration_column,
    _normalize_vaccinations,
    _portal_health_state,
    _serialize_health_doc,
    _upload_vaccination_proof,
    ADMISSIONS_ACCESS_MODE_FAMILY,
    ADMISSIONS_FAMILY_ROLE,
    ADMISSIONS_ROLE,
    get_admissions_access_mode,
    is_family_workspace_enabled,
    ensure_admissions_permission,
    ensure_contact_dynamic_link,
    ensure_contact_for_email,
    get_contact_primary_email,
    normalize_email_value,
    sync_student_applicant_contact_binding,
    upsert_contact_email,
    assert_user_can_access_student_applicant_contact,
    get_raw_contact_email_options_for_applicant_invite,
    ADMISSIONS_POLICY_MODE_FAMILY,
    get_applicant_policy_status,
    _applicant_invite_options_payload,
    _applicant_self_invite_blocked_reason,
    _bootstrap_applicant_contact_guardian_row,
    _call_user_method_if_available,
    _canonical_applicant_contact_for_invite,
    _clear_applicant_self_login_for_family_conversion,
    _contact_linked_to_applicant,
    _contact_linked_to_user,
    _ensure_admissions_applicant_role,
    _ensure_admissions_family_role,
    _ensure_family_guardian_user,
    _family_invite_options_payload,
    _get_applicant_guardian_row,
    _invite_contact_email_options,
    _invite_contact_primary_email,
    _remove_admissions_applicant_role,
    _require_family_workspace_mode,
    _require_scoped_staff_applicant_access,
    _required_family_acknowledgement_policy_labels,
    _send_applicant_invite_email,
)


def _as_text(value) -> str:
    if value is None:
        return ""
    return str(value)


@frappe.whitelist()
def get_admissions_session(student_applicant: str | None = None):
    return get_admissions_session_impl(student_applicant=student_applicant)


@frappe.whitelist()
def get_applicant_snapshot(student_applicant: str | None = None):
    return get_applicant_snapshot_impl(student_applicant=student_applicant)


@frappe.whitelist()
def get_applicant_enrollment_choices(student_applicant: str | None = None):
    return get_applicant_enrollment_choices_impl(student_applicant=student_applicant)


@frappe.whitelist()
def update_applicant_enrollment_choices(*, student_applicant: str | None = None, courses=None):
    return update_applicant_enrollment_choices_impl(student_applicant=student_applicant, courses=courses)


@frappe.whitelist()
def accept_enrollment_offer(student_applicant: str | None = None):
    return accept_enrollment_offer_impl(student_applicant=student_applicant)


@frappe.whitelist()
def decline_enrollment_offer(student_applicant: str | None = None):
    return decline_enrollment_offer_impl(student_applicant=student_applicant)


@frappe.whitelist()
def get_applicant_profile(student_applicant: str | None = None):
    return get_applicant_profile_impl(student_applicant=student_applicant)


@frappe.whitelist()
def update_applicant_profile(
    *,
    student_applicant: str | None = None,
    expected_modified: str | None = None,
    student_preferred_name: str | None = None,
    student_date_of_birth: str | None = None,
    student_gender: str | None = None,
    student_mobile_number: str | None = None,
    student_joining_date: str | None = None,
    student_first_language: str | None = None,
    student_second_language: str | None = None,
    student_nationality: str | None = None,
    student_second_nationality: str | None = None,
    residency_status: str | None = None,
    address_line1: str | None = None,
    address_line2: str | None = None,
    city: str | None = None,
    state: str | None = None,
    postal_code: str | None = None,
    country: str | None = None,
    applying_grade_level: str | None = None,
    previous_school_name: str | None = None,
    previous_grade_level: str | None = None,
    previous_curriculum: str | None = None,
    previous_school_city: str | None = None,
    previous_school_country: str | None = None,
    previous_language_of_instruction: str | None = None,
    previous_school_year_completed: str | None = None,
    previous_school_notes: str | None = None,
    guardians=None,
):
    return update_applicant_profile_impl(
        student_applicant=student_applicant,
        expected_modified=expected_modified,
        student_preferred_name=student_preferred_name,
        student_date_of_birth=student_date_of_birth,
        student_gender=student_gender,
        student_mobile_number=student_mobile_number,
        student_joining_date=student_joining_date,
        student_first_language=student_first_language,
        student_second_language=student_second_language,
        student_nationality=student_nationality,
        student_second_nationality=student_second_nationality,
        residency_status=residency_status,
        address_line1=address_line1,
        address_line2=address_line2,
        city=city,
        state=state,
        postal_code=postal_code,
        country=country,
        applying_grade_level=applying_grade_level,
        previous_school_name=previous_school_name,
        previous_grade_level=previous_grade_level,
        previous_curriculum=previous_curriculum,
        previous_school_city=previous_school_city,
        previous_school_country=previous_school_country,
        previous_language_of_instruction=previous_language_of_instruction,
        previous_school_year_completed=previous_school_year_completed,
        previous_school_notes=previous_school_notes,
        guardians=guardians,
    )


@frappe.whitelist()
def upload_applicant_profile_image(
    *,
    student_applicant: str | None = None,
    file_name: str | None = None,
    content: str | None = None,
):
    return upload_applicant_profile_image_impl(
        student_applicant=student_applicant,
        file_name=file_name,
        content=content,
    )


@frappe.whitelist()
def upload_applicant_guardian_image(
    *,
    student_applicant: str | None = None,
    guardian_row_name: str | None = None,
    file_name: str | None = None,
    content: str | None = None,
):
    return upload_applicant_guardian_image_impl(
        student_applicant=student_applicant,
        guardian_row_name=guardian_row_name,
        file_name=file_name,
        content=content,
    )


@frappe.whitelist()
def get_applicant_health(student_applicant: str | None = None):
    return get_applicant_health_impl(student_applicant=student_applicant)


@frappe.whitelist()
def update_applicant_health(
    *,
    student_applicant: str | None = None,
    expected_modified: str | None = None,
    blood_group: str | None = None,
    allergies=None,
    food_allergies: str | None = None,
    insect_bites: str | None = None,
    medication_allergies: str | None = None,
    asthma: str | None = None,
    bladder__bowel_problems: str | None = None,
    diabetes: str | None = None,
    headache_migraine: str | None = None,
    high_blood_pressure: str | None = None,
    seizures: str | None = None,
    bone_joints_scoliosis: str | None = None,
    blood_disorder_info: str | None = None,
    fainting_spells: str | None = None,
    hearing_problems: str | None = None,
    recurrent_ear_infections: str | None = None,
    speech_problem: str | None = None,
    birth_defect: str | None = None,
    dental_problems: str | None = None,
    g6pd: str | None = None,
    heart_problems: str | None = None,
    recurrent_nose_bleeding: str | None = None,
    vision_problem: str | None = None,
    diet_requirements: str | None = None,
    medical_surgeries__hospitalizations: str | None = None,
    other_medical_information: str | None = None,
    applicant_health_declared_complete=None,
    vaccinations=None,
):
    return update_applicant_health_impl(
        student_applicant=student_applicant,
        expected_modified=expected_modified,
        blood_group=blood_group,
        allergies=allergies,
        food_allergies=food_allergies,
        insect_bites=insect_bites,
        medication_allergies=medication_allergies,
        asthma=asthma,
        bladder__bowel_problems=bladder__bowel_problems,
        diabetes=diabetes,
        headache_migraine=headache_migraine,
        high_blood_pressure=high_blood_pressure,
        seizures=seizures,
        bone_joints_scoliosis=bone_joints_scoliosis,
        blood_disorder_info=blood_disorder_info,
        fainting_spells=fainting_spells,
        hearing_problems=hearing_problems,
        recurrent_ear_infections=recurrent_ear_infections,
        speech_problem=speech_problem,
        birth_defect=birth_defect,
        dental_problems=dental_problems,
        g6pd=g6pd,
        heart_problems=heart_problems,
        recurrent_nose_bleeding=recurrent_nose_bleeding,
        vision_problem=vision_problem,
        diet_requirements=diet_requirements,
        medical_surgeries__hospitalizations=medical_surgeries__hospitalizations,
        other_medical_information=other_medical_information,
        applicant_health_declared_complete=applicant_health_declared_complete,
        vaccinations=vaccinations,
    )


@frappe.whitelist()
def list_applicant_documents(student_applicant: str | None = None):
    return list_applicant_documents_impl(student_applicant=student_applicant)


@frappe.whitelist()
def list_applicant_document_types(student_applicant: str | None = None):
    return list_applicant_document_types_impl(student_applicant=student_applicant)


@frappe.whitelist()
def upload_applicant_document(
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
    return upload_applicant_document_impl(
        student_applicant=student_applicant,
        document_type=document_type,
        applicant_document_item=applicant_document_item,
        item_key=item_key,
        item_label=item_label,
        client_request_id=client_request_id,
        file_name=file_name,
        content=content,
    )


@frappe.whitelist()
def get_applicant_policies(student_applicant: str | None = None):
    return get_applicant_policies_impl(student_applicant=student_applicant)


@frappe.whitelist()
def acknowledge_policy(
    *,
    policy_version: str | None = None,
    student_applicant: str | None = None,
    typed_signature_name: str | None = None,
    attestation_confirmed: int | str | bool | None = None,
    checked_clause_names=None,
):
    return acknowledge_policy_impl(
        policy_version=policy_version,
        student_applicant=student_applicant,
        typed_signature_name=typed_signature_name,
        attestation_confirmed=attestation_confirmed,
        checked_clause_names=checked_clause_names,
    )


@frappe.whitelist()
def submit_application(student_applicant: str | None = None):
    return submit_application_impl(student_applicant=student_applicant)


@frappe.whitelist()
def withdraw_application(
    *,
    student_applicant: str | None = None,
    reason: str | None = None,
):
    return withdraw_application_impl(student_applicant=student_applicant, reason=reason)


@frappe.whitelist()
def get_family_invite_options(*, student_applicant: str | None = None) -> dict:
    return get_family_invite_options_impl(student_applicant=student_applicant)


@frappe.whitelist()
def invite_family_collaborator(
    *,
    student_applicant: str | None = None,
    guardian_row: str | None = None,
    email: str | None = None,
) -> dict:
    return invite_family_collaborator_impl(
        student_applicant=student_applicant,
        guardian_row=guardian_row,
        email=email,
    )


@frappe.whitelist()
def get_invite_email_options(*, student_applicant: str | None = None) -> dict:
    return get_invite_email_options_impl(student_applicant=student_applicant)


@frappe.whitelist()
def get_admissions_portal_invite_options(*, student_applicant: str | None = None) -> dict:
    return get_admissions_portal_invite_options_impl(student_applicant=student_applicant)


@frappe.whitelist()
def invite_applicant(*, student_applicant: str | None = None, email: str | None = None) -> dict:
    return invite_applicant_impl(student_applicant=student_applicant, email=email)
