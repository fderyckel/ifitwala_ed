# ifitwala_ed/utilities/governed_file_contract.py

from __future__ import annotations

ALLOWED_PRIMARY_SUBJECT_TYPES = {
    "Student",
    "Guardian",
    "Employee",
    "Student Applicant",
    "Organization",
}

OPTIONAL_SCHOOL_SUBJECT_TYPES = {
    "Employee",
    "Guardian",
    "Organization",
}

TEXT_FILE_PURPOSE = "text"
LEARNING_RESOURCE_PURPOSE = "learning_resource"
ALLOWED_FILE_PURPOSES = (
    TEXT_FILE_PURPOSE,
    "identification_document",
    "contract",
    "assessment_submission",
    "assessment_feedback",
    "safeguarding_evidence",
    "medical_record",
    "visa_document",
    "policy_acknowledgement",
    "background_check",
    LEARNING_RESOURCE_PURPOSE,
    "academic_report",
    "employee_profile_display",
    "guardian_profile_display",
    "student_profile_display",
    "applicant_profile_display",
    "organization_public_media",
    "portfolio_evidence",
    "journal_attachment",
    "portfolio_export",
    "journal_export",
    "administrative",
    "other",
)
_ALLOWED_FILE_PURPOSES_SET = frozenset(ALLOWED_FILE_PURPOSES)

ORGANIZATION_MEDIA_SUBJECT_TYPE = "Organization"
ORGANIZATION_MEDIA_DATA_CLASS = "operational"
ORGANIZATION_MEDIA_PURPOSE = "organization_public_media"
ORGANIZATION_MEDIA_RETENTION_POLICY = "immediate_on_request"
ORGANIZATION_MEDIA_FILE_CATEGORY = "Organization Media"


def is_school_required_for_subject_type(subject_type: str | None) -> bool:
    return (subject_type or "").strip() not in OPTIONAL_SCHOOL_SUBJECT_TYPES


def is_allowed_file_purpose(purpose: str | None) -> bool:
    return str(purpose or "").strip() in _ALLOWED_FILE_PURPOSES_SET


def format_allowed_file_purposes() -> str:
    return '", "'.join(ALLOWED_FILE_PURPOSES)
