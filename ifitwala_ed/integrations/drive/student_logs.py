from __future__ import annotations

from typing import Any

from ifitwala_ed.students.doctype.student_log.evidence import (
    assert_student_log_attachment_read_access,
    assert_student_log_attachment_upload_access,
    build_student_log_evidence_upload_contract,
    get_student_log_evidence_context_override,
    resolve_student_log_evidence_drive_file,
    run_student_log_evidence_post_finalize,
    validate_student_log_evidence_finalize_context,
)


def upload_student_log_evidence_access(student_log: str, *, permission_type: str = "write"):
    return assert_student_log_attachment_upload_access(student_log, permission_type=permission_type)


def build_student_log_evidence_contract(student_log_doc, *, row_name: str | None = None) -> dict[str, Any]:
    return build_student_log_evidence_upload_contract(student_log_doc, row_name=row_name)


def assert_student_log_upload_access(student_log: str, *, permission_type: str = "write"):
    return assert_student_log_attachment_upload_access(student_log, permission_type=permission_type)


def assert_student_log_evidence_read_access(student_log: str, row_name: str) -> dict[str, Any]:
    return assert_student_log_attachment_read_access(student_log, row_name)


def resolve_student_log_evidence_file(student_log: str, row_name: str) -> tuple[str, str | None]:
    return resolve_student_log_evidence_drive_file(student_log, row_name)


def validate_student_log_evidence_finalize_context_for_drive(upload_session_doc) -> dict[str, Any] | None:
    return validate_student_log_evidence_finalize_context(upload_session_doc)


def get_student_log_evidence_context_override_for_drive(
    owner_name: str | None,
    slot: str | None,
) -> dict[str, Any] | None:
    return get_student_log_evidence_context_override(owner_name, slot)


def run_student_log_evidence_post_finalize_for_drive(upload_session_doc, created_file) -> dict[str, Any]:
    return run_student_log_evidence_post_finalize(upload_session_doc, created_file)
