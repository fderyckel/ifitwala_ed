# ifitwala_ed/api/admissions_communication.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.api.communication.admin_context import (
    _administrator_context_preserving_request_session,
    _restore_request_session,
    _snapshot_request_session,
)
from ifitwala_ed.admission.api.communication.constants import (
    _LOCAL_ATTRS_RESET_BY_SET_USER,
    _MISSING_LOCAL_ATTR,
    ADMISSIONS_APPLICANT_ROLE,
    ADMISSIONS_FAMILY_ROLE,
    ALLOWED_STAFF_ROLES,
    INVALID_SESSION_USERS,
    MESSAGE_LIMIT,
    READ_RECEIPT_REFERENCE_DOCTYPE,
    SUPPORTED_CONTEXT_DOCTYPES,
    THREAD_COMMUNICATION_TYPE,
    THREAD_INTERACTION_MODE,
    THREAD_PORTAL_SURFACE,
    THREAD_STATUS,
)
from ifitwala_ed.admission.api.communication.context import (
    _ensure_applicant_match,
    _normalize_context,
    _require_actor_context,
    _resolve_student_applicant_row,
    _safe_datetime,
    _session_user,
    _to_text,
)
from ifitwala_ed.admission.api.communication.messages import (
    _fetch_latest_entry_for_sender,
    _save_case_interaction,
    _sender_direction,
    _serialize_message_row,
    _truncate_preview,
    get_admissions_case_thread_impl,
    send_admissions_case_message_impl,
)
from ifitwala_ed.admission.api.communication.read_receipts import (
    _count_unread_messages,
    _get_read_receipt_time,
    mark_admissions_case_thread_read_impl,
)
from ifitwala_ed.admission.api.communication.summaries import get_admissions_thread_summaries_for_applicants
from ifitwala_ed.admission.api.communication.threads import (
    _create_thread,
    _get_or_create_thread,
    _get_thread_name,
    _next_thread_title,
)
from ifitwala_ed.api.org_communication_interactions import (
    create_interaction_entry,
    get_latest_org_communication_entry_for_user,
    upsert_org_communication_read_receipt,
)
from ifitwala_ed.setup.doctype.communication_interaction_entry.communication_interaction_entry import (
    DOCTYPE as ENTRY_DOCTYPE,
)

_COMMUNICATION_COMPAT_EXPORTS = (
    ADMISSIONS_APPLICANT_ROLE,
    ADMISSIONS_FAMILY_ROLE,
    ALLOWED_STAFF_ROLES,
    SUPPORTED_CONTEXT_DOCTYPES,
    MESSAGE_LIMIT,
    THREAD_COMMUNICATION_TYPE,
    THREAD_INTERACTION_MODE,
    THREAD_STATUS,
    THREAD_PORTAL_SURFACE,
    INVALID_SESSION_USERS,
    READ_RECEIPT_REFERENCE_DOCTYPE,
    _LOCAL_ATTRS_RESET_BY_SET_USER,
    _MISSING_LOCAL_ATTR,
    _to_text,
    _snapshot_request_session,
    _restore_request_session,
    _administrator_context_preserving_request_session,
    _session_user,
    _normalize_context,
    _safe_datetime,
    _next_thread_title,
    _resolve_student_applicant_row,
    _require_actor_context,
    _get_thread_name,
    _create_thread,
    _get_or_create_thread,
    _sender_direction,
    _truncate_preview,
    _fetch_latest_entry_for_sender,
    _save_case_interaction,
    _serialize_message_row,
    _get_read_receipt_time,
    _count_unread_messages,
    _ensure_applicant_match,
    get_admissions_thread_summaries_for_applicants,
    create_interaction_entry,
    get_latest_org_communication_entry_for_user,
    upsert_org_communication_read_receipt,
    ENTRY_DOCTYPE,
)


@frappe.whitelist(allow_guest=True)
def send_admissions_case_message(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    body: str | None = None,
    applicant_visible: int | None = 1,
    client_request_id: str | None = None,
):
    return send_admissions_case_message_impl(
        context_doctype=context_doctype,
        context_name=context_name,
        body=body,
        applicant_visible=applicant_visible,
        client_request_id=client_request_id,
    )


@frappe.whitelist(allow_guest=True)
def get_admissions_case_thread(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    limit_start: int | None = 0,
    limit: int | None = 60,
):
    return get_admissions_case_thread_impl(
        context_doctype=context_doctype,
        context_name=context_name,
        limit_start=limit_start,
        limit=limit,
    )


@frappe.whitelist(allow_guest=True)
def mark_admissions_case_thread_read(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
):
    return mark_admissions_case_thread_read_impl(
        context_doctype=context_doctype,
        context_name=context_name,
    )


# Preserve allow_guest metadata for auth-guard tests and reflective callers.
send_admissions_case_message.allow_guest = True
get_admissions_case_thread.allow_guest = True
mark_admissions_case_thread_read.allow_guest = True
