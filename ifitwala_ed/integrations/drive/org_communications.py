from __future__ import annotations

from typing import Any

from ifitwala_ed.setup.doctype.org_communication.attachments import (
    assert_org_communication_attachment_upload_access,
    build_org_communication_attachment_upload_contract,
    get_org_communication_context_override,
    run_org_communication_post_finalize,
    validate_org_communication_attachment_finalize_context,
)


def upload_org_communication_attachment_access(org_communication: str, *, permission_type: str = "write"):
    return assert_org_communication_attachment_upload_access(org_communication, permission_type=permission_type)


def build_org_communication_upload_contract(
    org_communication_doc,
    *,
    row_name: str | None = None,
) -> dict[str, Any]:
    return build_org_communication_attachment_upload_contract(org_communication_doc, row_name=row_name)


def assert_org_communication_upload_access(org_communication: str, *, permission_type: str = "write"):
    return assert_org_communication_attachment_upload_access(org_communication, permission_type=permission_type)


def validate_org_communication_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    return validate_org_communication_attachment_finalize_context(upload_session_doc)


def get_org_communication_attachment_context_override(
    owner_name: str | None, slot: str | None
) -> dict[str, Any] | None:
    return get_org_communication_context_override(owner_name, slot)


def run_org_communication_attachment_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    return run_org_communication_post_finalize(upload_session_doc, created_file)
