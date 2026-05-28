# ifitwala_ed/admission/api/portal/profile.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.api.portal.access import _as_text, _ensure_applicant_match, _require_admissions_applicant
from ifitwala_ed.admission.api.portal.contacts import _applicant_contact_prefill_payload
from ifitwala_ed.admission.api.portal.guardians import (
    APPLICANT_GUARDIAN_EMPLOYMENT_SECTOR_OPTIONS,
    APPLICANT_GUARDIAN_GENDER_OPTIONS,
    APPLICANT_GUARDIAN_RELATIONSHIP_OPTIONS,
    _apply_guardians_to_applicant,
    _guardian_salutation_options,
    _guardians_feature_enabled,
    _parse_guardians_payload,
    _serialize_applicant_guardians,
)
from ifitwala_ed.admission.api.portal.profile_images import (
    _build_admissions_profile_image_urls,
    _collect_guardian_image_authority_map,
    _resolve_applicant_profile_image_authority,
)
from ifitwala_ed.api.file_access import get_drive_file_thumbnail_ready_map

APPLICANT_PROFILE_FIELDS = (
    "student_preferred_name",
    "student_date_of_birth",
    "student_gender",
    "student_mobile_number",
    "student_joining_date",
    "student_first_language",
    "student_second_language",
    "student_nationality",
    "student_second_nationality",
    "residency_status",
    "address_line1",
    "address_line2",
    "city",
    "state",
    "postal_code",
    "country",
    "previous_school_name",
    "previous_grade_level",
    "previous_curriculum",
    "previous_school_city",
    "previous_school_country",
    "previous_language_of_instruction",
    "previous_school_year_completed",
    "previous_school_notes",
    "learning_support_status",
    "learning_needs",
    "effective_supports",
    "existing_support_plans",
    "social_emotional_needs",
    "physical_access_needs",
    "family_support_priorities",
    "student_strengths",
    "student_interests",
    "student_activities",
    "student_achievements",
    "student_motivators",
    "student_relationship_notes",
    "student_voice_notes",
)

APPLICANT_PROFILE_REQUIRED_FIELD_LABELS = (
    ("student_date_of_birth", "Date of Birth"),
    ("student_gender", "Student Gender"),
    ("student_mobile_number", "Mobile Number"),
    ("student_first_language", "First Language"),
    ("student_nationality", "Nationality"),
    ("residency_status", "Residency Status"),
    ("address_line1", "Address Line 1"),
    ("city", "City"),
    ("postal_code", "Postal Code"),
    ("country", "Country"),
)

APPLICANT_PROFILE_GENDER_OPTIONS = ("Female", "Male", "Other")
APPLICANT_PROFILE_RESIDENCY_OPTIONS = ("Local Resident", "Expat Resident", "Boarder", "Other")
APPLICANT_LEARNING_SUPPORT_STATUS_OPTIONS = (
    "No known support needs",
    "Support details provided",
    "Unsure / would like to discuss",
    "Prefer to discuss privately",
)


def _default_profile_payload() -> dict:
    return {fieldname: "" for fieldname in APPLICANT_PROFILE_FIELDS}


def _application_context_payload(row) -> dict:
    return {
        "organization": _as_text(row.get("organization")),
        "school": _as_text(row.get("school")),
        "academic_year": _as_text(row.get("academic_year")),
        "term": _as_text(row.get("term")),
        "program": _as_text(row.get("program")),
        "program_offering": _as_text(row.get("program_offering")),
    }


def _serialize_applicant_profile(row) -> dict:
    payload = _default_profile_payload()
    for fieldname in APPLICANT_PROFILE_FIELDS:
        payload[fieldname] = _as_text(row.get(fieldname)).strip()
    return payload


def _profile_completeness(profile_payload: dict) -> dict:
    required = [label for _, label in APPLICANT_PROFILE_REQUIRED_FIELD_LABELS]
    missing: list[str] = []
    for fieldname, label in APPLICANT_PROFILE_REQUIRED_FIELD_LABELS:
        value = _as_text(profile_payload.get(fieldname)).strip()
        if not value:
            missing.append(label)
    return {"ok": not missing, "missing": missing, "required": required}


def _build_profile_payload(applicant) -> dict:
    profile = _serialize_applicant_profile(applicant)
    completeness = _profile_completeness(profile)
    guardians_enabled = _guardians_feature_enabled()
    applicant_name = _as_text(applicant.get("name")).strip()
    applicant_drive_file, applicant_file_row = _resolve_applicant_profile_image_authority(
        applicant_name=applicant_name,
        applicant_image=applicant.get("applicant_image"),
    )
    guardian_image_authority = _collect_guardian_image_authority_map(applicant) if guardians_enabled else {}
    drive_file_ids = [
        str((applicant_drive_file or {}).get("name") or "").strip(),
        *[
            str((drive_file or {}).get("name") or "").strip()
            for drive_file, _file_row in guardian_image_authority.values()
        ],
    ]
    thumbnail_ready_map = get_drive_file_thumbnail_ready_map(drive_file_ids)
    applicant_image_urls = _build_admissions_profile_image_urls(
        applicant_name=applicant_name,
        original_image=applicant.get("applicant_image"),
        drive_file=applicant_drive_file,
        file_row=applicant_file_row,
        thumbnail_ready=thumbnail_ready_map.get(str((applicant_drive_file or {}).get("name") or "").strip()),
    )
    return {
        "profile": profile,
        "completeness": completeness,
        "application_context": _application_context_payload(applicant),
        "options": _profile_reference_options(),
        "applicant_image": applicant_image_urls["image_url"],
        "applicant_image_open_url": applicant_image_urls["open_url"],
        "record_modified": _as_text(applicant.get("modified")).strip(),
        "guardian_section_enabled": guardians_enabled,
        "applicant_contact_prefill": _applicant_contact_prefill_payload(applicant),
        "guardians": _serialize_applicant_guardians(
            applicant,
            authority_map=guardian_image_authority,
            thumbnail_ready_map=thumbnail_ready_map,
        )
        if guardians_enabled
        else [],
    }


def _normalize_record_modified(value) -> str:
    return _as_text(value).strip()


def _assert_record_modified_matches(*, expected_modified, current_modified, section_label: str) -> None:
    if expected_modified is None:
        return
    expected = _normalize_record_modified(expected_modified)
    current = _normalize_record_modified(current_modified)
    if expected == current:
        return
    frappe.throw(
        _("{section} was updated by another user. Reload this page before saving again.").format(section=section_label),
        frappe.ValidationError,
    )


def _profile_reference_options() -> dict:
    language_rows = frappe.get_all(
        "Language Xtra",
        filters={"enabled": 1},
        fields=["name", "language_name"],
        order_by="language_name asc",
    )
    country_rows = frappe.get_all(
        "Country",
        fields=["name"],
        order_by="name asc",
    )
    return {
        "genders": list(APPLICANT_PROFILE_GENDER_OPTIONS),
        "residency_statuses": list(APPLICANT_PROFILE_RESIDENCY_OPTIONS),
        "learning_support_statuses": list(APPLICANT_LEARNING_SUPPORT_STATUS_OPTIONS),
        "languages": [
            {
                "value": _as_text(row.get("name")).strip(),
                "label": _as_text(row.get("language_name")).strip() or _as_text(row.get("name")).strip(),
            }
            for row in language_rows
            if _as_text(row.get("name")).strip()
        ],
        "countries": [
            {
                "value": _as_text(row.get("name")).strip(),
                "label": _as_text(row.get("name")).strip(),
            }
            for row in country_rows
            if _as_text(row.get("name")).strip()
        ],
        "guardian_relationships": list(APPLICANT_GUARDIAN_RELATIONSHIP_OPTIONS),
        "guardian_genders": list(APPLICANT_GUARDIAN_GENDER_OPTIONS),
        "guardian_employment_sectors": list(APPLICANT_GUARDIAN_EMPLOYMENT_SECTOR_OPTIONS),
        "salutations": _guardian_salutation_options(),
    }


def get_applicant_profile_impl(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    return _build_profile_payload(applicant)


def update_applicant_profile_impl(
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
    previous_school_name: str | None = None,
    previous_grade_level: str | None = None,
    previous_curriculum: str | None = None,
    previous_school_city: str | None = None,
    previous_school_country: str | None = None,
    previous_language_of_instruction: str | None = None,
    previous_school_year_completed: str | None = None,
    previous_school_notes: str | None = None,
    learning_support_status: str | None = None,
    learning_needs: str | None = None,
    effective_supports: str | None = None,
    existing_support_plans: str | None = None,
    social_emotional_needs: str | None = None,
    physical_access_needs: str | None = None,
    family_support_priorities: str | None = None,
    student_strengths: str | None = None,
    student_interests: str | None = None,
    student_activities: str | None = None,
    student_achievements: str | None = None,
    student_motivators: str | None = None,
    student_relationship_notes: str | None = None,
    student_voice_notes: str | None = None,
    guardians=None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    _assert_record_modified_matches(
        expected_modified=expected_modified,
        current_modified=applicant.get("modified"),
        section_label=_("Profile information"),
    )
    incoming_joining_date = _as_text(student_joining_date).strip() if student_joining_date is not None else None
    existing_joining_date = _as_text(applicant.get("student_joining_date")).strip()
    if incoming_joining_date is not None and incoming_joining_date != existing_joining_date:
        frappe.throw(_("Admission Date can only be set by the admissions office."), frappe.PermissionError)

    updates = {
        "student_preferred_name": _as_text(
            applicant.get("student_preferred_name") if student_preferred_name is None else student_preferred_name
        ).strip(),
        "student_date_of_birth": _as_text(
            applicant.get("student_date_of_birth") if student_date_of_birth is None else student_date_of_birth
        ).strip(),
        "student_gender": _as_text(
            applicant.get("student_gender") if student_gender is None else student_gender
        ).strip(),
        "student_mobile_number": _as_text(
            applicant.get("student_mobile_number") if student_mobile_number is None else student_mobile_number
        ).strip(),
        "student_joining_date": existing_joining_date,
        "student_first_language": _as_text(
            applicant.get("student_first_language") if student_first_language is None else student_first_language
        ).strip(),
        "student_second_language": _as_text(
            applicant.get("student_second_language") if student_second_language is None else student_second_language
        ).strip(),
        "student_nationality": _as_text(
            applicant.get("student_nationality") if student_nationality is None else student_nationality
        ).strip(),
        "student_second_nationality": _as_text(
            applicant.get("student_second_nationality")
            if student_second_nationality is None
            else student_second_nationality
        ).strip(),
        "residency_status": _as_text(
            applicant.get("residency_status") if residency_status is None else residency_status
        ).strip(),
        "address_line1": _as_text(applicant.get("address_line1") if address_line1 is None else address_line1).strip(),
        "address_line2": _as_text(applicant.get("address_line2") if address_line2 is None else address_line2).strip(),
        "city": _as_text(applicant.get("city") if city is None else city).strip(),
        "state": _as_text(applicant.get("state") if state is None else state).strip(),
        "postal_code": _as_text(applicant.get("postal_code") if postal_code is None else postal_code).strip(),
        "country": _as_text(applicant.get("country") if country is None else country).strip(),
        "previous_school_name": _as_text(
            applicant.get("previous_school_name") if previous_school_name is None else previous_school_name
        ).strip(),
        "previous_grade_level": _as_text(
            applicant.get("previous_grade_level") if previous_grade_level is None else previous_grade_level
        ).strip(),
        "previous_curriculum": _as_text(
            applicant.get("previous_curriculum") if previous_curriculum is None else previous_curriculum
        ).strip(),
        "previous_school_city": _as_text(
            applicant.get("previous_school_city") if previous_school_city is None else previous_school_city
        ).strip(),
        "previous_school_country": _as_text(
            applicant.get("previous_school_country") if previous_school_country is None else previous_school_country
        ).strip(),
        "previous_language_of_instruction": _as_text(
            applicant.get("previous_language_of_instruction")
            if previous_language_of_instruction is None
            else previous_language_of_instruction
        ).strip(),
        "previous_school_year_completed": _as_text(
            applicant.get("previous_school_year_completed")
            if previous_school_year_completed is None
            else previous_school_year_completed
        ).strip(),
        "previous_school_notes": _as_text(
            applicant.get("previous_school_notes") if previous_school_notes is None else previous_school_notes
        ).strip(),
        "learning_support_status": _as_text(
            applicant.get("learning_support_status") if learning_support_status is None else learning_support_status
        ).strip(),
        "learning_needs": _as_text(
            applicant.get("learning_needs") if learning_needs is None else learning_needs
        ).strip(),
        "effective_supports": _as_text(
            applicant.get("effective_supports") if effective_supports is None else effective_supports
        ).strip(),
        "existing_support_plans": _as_text(
            applicant.get("existing_support_plans") if existing_support_plans is None else existing_support_plans
        ).strip(),
        "social_emotional_needs": _as_text(
            applicant.get("social_emotional_needs") if social_emotional_needs is None else social_emotional_needs
        ).strip(),
        "physical_access_needs": _as_text(
            applicant.get("physical_access_needs") if physical_access_needs is None else physical_access_needs
        ).strip(),
        "family_support_priorities": _as_text(
            applicant.get("family_support_priorities")
            if family_support_priorities is None
            else family_support_priorities
        ).strip(),
        "student_strengths": _as_text(
            applicant.get("student_strengths") if student_strengths is None else student_strengths
        ).strip(),
        "student_interests": _as_text(
            applicant.get("student_interests") if student_interests is None else student_interests
        ).strip(),
        "student_activities": _as_text(
            applicant.get("student_activities") if student_activities is None else student_activities
        ).strip(),
        "student_achievements": _as_text(
            applicant.get("student_achievements") if student_achievements is None else student_achievements
        ).strip(),
        "student_motivators": _as_text(
            applicant.get("student_motivators") if student_motivators is None else student_motivators
        ).strip(),
        "student_relationship_notes": _as_text(
            applicant.get("student_relationship_notes")
            if student_relationship_notes is None
            else student_relationship_notes
        ).strip(),
        "student_voice_notes": _as_text(
            applicant.get("student_voice_notes") if student_voice_notes is None else student_voice_notes
        ).strip(),
    }

    applicant.update(updates)
    guardians_payload = _parse_guardians_payload(guardians)
    if guardians_payload is not None and _guardians_feature_enabled():
        _apply_guardians_to_applicant(applicant=applicant, guardians_payload=guardians_payload)
    applicant.save(ignore_permissions=True)
    payload = _build_profile_payload(applicant)
    payload["ok"] = True
    return payload
