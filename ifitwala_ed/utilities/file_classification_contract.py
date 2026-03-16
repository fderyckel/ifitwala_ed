# ifitwala_ed/utilities/file_classification_contract.py

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
    "Organization",
}

ORGANIZATION_MEDIA_SUBJECT_TYPE = "Organization"
ORGANIZATION_MEDIA_DATA_CLASS = "operational"
ORGANIZATION_MEDIA_PURPOSE = "organization_public_media"
ORGANIZATION_MEDIA_RETENTION_POLICY = "immediate_on_request"
ORGANIZATION_MEDIA_FILE_CATEGORY = "Organization Media"


def is_school_required_for_subject_type(subject_type: str | None) -> bool:
    return (subject_type or "").strip() not in OPTIONAL_SCHOOL_SUBJECT_TYPES
