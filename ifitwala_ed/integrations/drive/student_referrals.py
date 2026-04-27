from __future__ import annotations

from typing import Any

from ifitwala_ed.students.doctype.student_referral.attachments import (
    assert_self_referral_attachment_upload_access,
    build_student_referral_attachment_upload_contract,
    get_student_referral_attachment_context_override,
    run_student_referral_attachment_post_finalize,
    validate_student_referral_attachment_finalize_context,
)


def assert_student_referral_attachment_upload_access(student_referral: str):
    return assert_self_referral_attachment_upload_access(student_referral)


def build_student_referral_attachment_contract(student_referral_doc, *, slot: str) -> dict[str, Any]:
    return build_student_referral_attachment_upload_contract(student_referral_doc, slot=slot)


def validate_student_referral_attachment_finalize_context_for_drive(upload_session_doc) -> dict[str, Any] | None:
    return validate_student_referral_attachment_finalize_context(upload_session_doc)


def get_student_referral_attachment_context_override_for_drive(
    owner_name: str | None,
    slot: str | None,
) -> dict[str, Any] | None:
    return get_student_referral_attachment_context_override(owner_name, slot)


def run_student_referral_attachment_post_finalize_for_drive(upload_session_doc, created_file) -> dict[str, Any]:
    return run_student_referral_attachment_post_finalize(upload_session_doc, created_file)
