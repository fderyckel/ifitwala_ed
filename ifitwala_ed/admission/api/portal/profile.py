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
)

APPLICANT_PROFILE_REQUIRED_FIELD_LABELS = (
    ("student_date_of_birth", "Date of Birth"),
    ("student_gender", "Student Gender"),
    ("student_mobile_number", "Mobile Number"),
    ("student_first_language", "First Language"),
    ("student_nationality", "Nationality"),
    ("residency_status", "Residency Status"),
)

APPLICANT_PROFILE_GENDER_OPTIONS = ("Female", "Male", "Other")
APPLICANT_PROFILE_RESIDENCY_OPTIONS = ("Local Resident", "Expat Resident", "Boarder", "Other")


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
    }

    applicant.update(updates)
    guardians_payload = _parse_guardians_payload(guardians)
    if guardians_payload is not None and _guardians_feature_enabled():
        _apply_guardians_to_applicant(applicant=applicant, guardians_payload=guardians_payload)
    applicant.save(ignore_permissions=True)
    payload = _build_profile_payload(applicant)
    payload["ok"] = True
    return payload
