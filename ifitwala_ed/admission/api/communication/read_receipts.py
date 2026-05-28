from __future__ import annotations

from datetime import datetime

import frappe
from frappe.utils import cint, now_datetime

from ifitwala_ed.admission.api.communication.constants import READ_RECEIPT_REFERENCE_DOCTYPE
from ifitwala_ed.admission.api.communication.context import (
    _normalize_context,
    _require_actor_context,
    _safe_datetime,
    _to_text,
)
from ifitwala_ed.admission.api.communication.threads import _get_thread_name
from ifitwala_ed.api.org_communication_interactions import upsert_org_communication_read_receipt
from ifitwala_ed.setup.doctype.communication_interaction_entry.communication_interaction_entry import (
    DOCTYPE as ENTRY_DOCTYPE,
)


def _get_read_receipt_time(user: str, thread_name: str) -> datetime | None:
    read_at = frappe.db.get_value(
        "Portal Read Receipt",
        {
            "user": user,
            "reference_doctype": READ_RECEIPT_REFERENCE_DOCTYPE,
            "reference_name": thread_name,
        },
        "read_at",
    )
    return _safe_datetime(read_at)


def _count_unread_messages(*, thread_name: str, applicant_user: str, actor_user: str, actor_kind: str) -> int:
    read_at = _get_read_receipt_time(actor_user, thread_name)

    conditions = [
        "i.org_communication = %(thread_name)s",
        "COALESCE(TRIM(i.note), '') != ''",
        "i.visibility != 'Hidden'",
    ]
    values = {
        "thread_name": thread_name,
        "applicant_user": applicant_user,
    }

    if actor_kind == "staff":
        if not applicant_user:
            return 0
        conditions.append("i.user = %(applicant_user)s")
    else:
        if not applicant_user:
            return 0
        conditions.append("i.user != %(applicant_user)s")
        conditions.append("i.visibility = 'Public to audience'")

    if read_at:
        conditions.append("i.creation > %(read_at)s")
        values["read_at"] = read_at

    where_clause = " AND ".join(conditions)
    count_row = frappe.db.sql(
        f"""
        SELECT COUNT(*) AS unread_count
        FROM `tab{ENTRY_DOCTYPE}` i
        WHERE {where_clause}
        """,
        values,
        as_dict=True,
    )
    if not count_row:
        return 0
    return cint((count_row[0] or {}).get("unread_count") or 0)


def mark_admissions_case_thread_read_impl(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
):
    context_doctype, context_name = _normalize_context(context_doctype, context_name)
    actor_ctx = _require_actor_context(context_doctype=context_doctype, context_name=context_name)
    actor_user = _to_text(actor_ctx.get("user"))

    thread_name = _get_thread_name(context_doctype, context_name)
    if not thread_name:
        return {"ok": True, "thread_name": None}

    read_at = now_datetime()
    upsert_org_communication_read_receipt(
        user=actor_user,
        org_communication=thread_name,
        read_at=read_at,
    )

    return {"ok": True, "thread_name": thread_name, "read_at": read_at}
