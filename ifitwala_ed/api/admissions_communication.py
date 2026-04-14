# ifitwala_ed/api/admissions_communication.py

from __future__ import annotations

from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.api.admissions_portal import _ensure_applicant_match
from ifitwala_ed.api.org_communication_interactions import (
    create_interaction_entry,
    get_latest_org_communication_entry_for_user,
    upsert_org_communication_read_receipt,
)
from ifitwala_ed.setup.doctype.communication_interaction_entry.communication_interaction_entry import (
    DOCTYPE as ENTRY_DOCTYPE,
)

ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
ALLOWED_STAFF_ROLES = ADMISSIONS_ROLES | {
    "Academic Admin",
    "Academic Staff",
    "Administrator",
    "Academic Assistant",
    "Employee",
    "System Manager",
}
SUPPORTED_CONTEXT_DOCTYPES = {"Student Applicant"}
MESSAGE_LIMIT = 300
THREAD_COMMUNICATION_TYPE = "Information"
THREAD_INTERACTION_MODE = "Structured Feedback"
THREAD_STATUS = "Published"
THREAD_PORTAL_SURFACE = "Desk"
INVALID_SESSION_USERS = {"guest", "none", "null", "undefined"}
READ_RECEIPT_REFERENCE_DOCTYPE = "Org Communication"


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _session_user() -> str:
    user = _to_text(getattr(frappe.session, "user", None))
    if not user:
        return ""
    if user.lower() in INVALID_SESSION_USERS:
        return ""
    return user


def _normalize_context(context_doctype: str | None, context_name: str | None) -> tuple[str, str]:
    doctype = _to_text(context_doctype)
    name = _to_text(context_name)
    if doctype not in SUPPORTED_CONTEXT_DOCTYPES:
        frappe.throw(
            _("Unsupported admissions communication context: {doctype}.").format(doctype=doctype or _("(empty)"))
        )
    if not name:
        frappe.throw(_("context_name is required."))
    return doctype, name


def _safe_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return get_datetime(value)
    except Exception:
        return None


def _next_thread_title(context_doctype: str, context_name: str) -> str:
    base = f"Admissions Thread - {context_doctype} - {context_name}"
    candidate = base
    counter = 1
    while frappe.db.exists("Org Communication", {"title": candidate}):
        counter += 1
        candidate = f"{base} #{counter}"
    return candidate


def _resolve_student_applicant_row(applicant_name: str) -> dict:
    row = frappe.db.get_value(
        "Student Applicant",
        applicant_name,
        ["name", "organization", "school", "applicant_user"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Student Applicant {applicant} was not found.").format(applicant=applicant_name))
    return {
        "name": _to_text(row.get("name")),
        "organization": _to_text(row.get("organization")),
        "school": _to_text(row.get("school")),
        "applicant_user": _to_text(row.get("applicant_user")),
    }


def _require_actor_context(*, context_doctype: str, context_name: str) -> dict:
    user = _session_user()
    if not user:
        frappe.throw(_("You need to sign in to access admissions communications."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    context_row: dict
    applicant_user = ""

    if context_doctype == "Student Applicant":
        context_row = _resolve_student_applicant_row(context_name)
        applicant_user = _to_text(context_row.get("applicant_user"))
    else:
        frappe.throw(_("Unsupported admissions communication context: {doctype}.").format(doctype=context_doctype))

    if ADMISSIONS_APPLICANT_ROLE in roles:
        if context_doctype != "Student Applicant":
            frappe.throw(
                _("Applicant portal users can only access Student Applicant communication."), frappe.PermissionError
            )
        _ensure_applicant_match(context_name, user)
        return {
            "user": user,
            "roles": roles,
            "actor": "applicant",
            "context": context_row,
            "applicant_user": applicant_user,
        }

    if roles & ALLOWED_STAFF_ROLES:
        if context_doctype == "Student Applicant":
            applicant_doc = frappe.get_doc("Student Applicant", context_name)
            if not frappe.has_permission("Student Applicant", ptype="read", doc=applicant_doc, user=user):
                frappe.throw(_("You do not have permission to access this applicant thread."), frappe.PermissionError)
        return {
            "user": user,
            "roles": roles,
            "actor": "staff",
            "context": context_row,
            "applicant_user": applicant_user,
        }

    frappe.throw(_("You do not have permission to access admissions communications."), frappe.PermissionError)
    return {}


def _get_thread_name(context_doctype: str, context_name: str) -> str | None:
    rows = frappe.get_all(
        "Org Communication",
        filters={
            "admission_context_doctype": context_doctype,
            "admission_context_name": context_name,
        },
        fields=["name"],
        order_by="creation asc",
        limit=1,
    )
    if not rows:
        return None
    return _to_text(rows[0].get("name")) or None


def _create_thread(*, context_doctype: str, context_name: str, context_row: dict) -> str:
    organization = _to_text(context_row.get("organization"))
    school = _to_text(context_row.get("school"))
    if not organization:
        frappe.throw(_("Student Applicant is missing organization; cannot create admissions communication thread."))
    if not school:
        frappe.throw(_("Student Applicant is missing school; cannot create admissions communication thread."))

    doc = frappe.new_doc("Org Communication")
    doc.title = _next_thread_title(context_doctype, context_name)
    doc.communication_type = THREAD_COMMUNICATION_TYPE
    doc.status = THREAD_STATUS
    doc.priority = "Normal"
    doc.organization = organization
    doc.school = school
    doc.portal_surface = THREAD_PORTAL_SURFACE
    doc.interaction_mode = THREAD_INTERACTION_MODE
    doc.allow_private_notes = 1
    doc.allow_public_thread = 1
    doc.admission_context_doctype = context_doctype
    doc.admission_context_name = context_name
    doc.message = _("Admissions case communication thread for {context_name}.").format(context_name=context_name)
    doc.append(
        "audiences",
        {
            "target_mode": "School Scope",
            "school": school,
            "include_descendants": 0,
            "to_students": 1,
            "to_staff": 0,
            "to_guardians": 0,
        },
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_or_create_thread(*, context_doctype: str, context_name: str, context_row: dict) -> str:
    existing = _get_thread_name(context_doctype, context_name)
    if existing:
        return existing

    lock_key = f"admissions:thread:create:{context_doctype}:{context_name}"
    with frappe.cache().lock(lock_key, timeout=10):
        existing = _get_thread_name(context_doctype, context_name)
        if existing:
            return existing
        current_user = _session_user()
        frappe.set_user("Administrator")
        try:
            return _create_thread(
                context_doctype=context_doctype,
                context_name=context_name,
                context_row=context_row,
            )
        finally:
            frappe.set_user(current_user or "Guest")


def _sender_direction(*, sender_user: str, applicant_user: str, visibility: str) -> str:
    if applicant_user and sender_user == applicant_user:
        return "ApplicantToStaff"
    if visibility == "Public to audience":
        return "StaffToApplicant"
    return "Internal"


def _truncate_preview(note: str, max_len: int = 120) -> str:
    text = " ".join((note or "").split())
    if len(text) <= max_len:
        return text
    return f"{text[:max_len].rstrip()}..."


def _fetch_latest_entry_for_sender(*, thread_name: str, sender_user: str) -> dict | None:
    return get_latest_org_communication_entry_for_user(
        org_communication=thread_name,
        user=sender_user,
    )


def _save_case_interaction(
    *,
    thread_name: str,
    actor_user: str,
    intent_type: str,
    note: str,
    visibility: str,
) -> dict:
    saved_row = create_interaction_entry(
        org_communication=thread_name,
        user=actor_user,
        intent_type=intent_type,
        note=note,
        visibility=visibility,
        surface="Other",
    )

    return {
        "name": _to_text(saved_row.get("name")),
        "user": _to_text(saved_row.get("user")),
        "note": _to_text(saved_row.get("note")),
        "visibility": _to_text(saved_row.get("visibility")),
        "creation": saved_row.get("creation"),
        "modified": saved_row.get("modified"),
    }


def _serialize_message_row(*, row: dict, applicant_user: str) -> dict:
    sender_user = _to_text(row.get("user"))
    visibility = _to_text(row.get("visibility"))
    note = _to_text(row.get("note"))
    direction = _sender_direction(
        sender_user=sender_user,
        applicant_user=applicant_user,
        visibility=visibility,
    )
    full_name = _to_text(row.get("full_name")) or _to_text(
        frappe.db.get_value("User", sender_user, "full_name") if sender_user else None
    )
    full_name = full_name or sender_user
    return {
        "name": _to_text(row.get("name")),
        "user": sender_user,
        "full_name": full_name,
        "body": note,
        "direction": direction,
        "visibility": visibility,
        "applicant_visible": bool(
            visibility == "Public to audience" or (applicant_user and sender_user == applicant_user)
        ),
        "created_at": row.get("creation"),
        "modified_at": row.get("modified"),
    }


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


@frappe.whitelist(allow_guest=True)
def send_admissions_case_message(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    body: str | None = None,
    applicant_visible: int | None = 1,
    client_request_id: str | None = None,
):
    context_doctype, context_name = _normalize_context(context_doctype, context_name)
    actor_ctx = _require_actor_context(context_doctype=context_doctype, context_name=context_name)

    note = _to_text(body)
    if not note:
        frappe.throw(_("Message body is required."))
    if len(note) > MESSAGE_LIMIT:
        frappe.throw(
            _("Message body cannot exceed {character_limit} characters.").format(character_limit=MESSAGE_LIMIT)
        )

    is_applicant = actor_ctx.get("actor") == "applicant"
    visible_to_applicant = True if is_applicant else bool(cint(applicant_visible))

    intent_type = "Question" if is_applicant else ("Other" if visible_to_applicant else "Concern")
    visibility = (
        "Private to school" if is_applicant else ("Public to audience" if visible_to_applicant else "Private to school")
    )

    thread_name = _get_or_create_thread(
        context_doctype=context_doctype,
        context_name=context_name,
        context_row=actor_ctx.get("context") or {},
    )

    user = _to_text(actor_ctx.get("user"))
    request_id = _to_text(client_request_id)
    cache_key = None
    if request_id:
        cache_key = f"admissions:message:{user}:{thread_name}:{request_id}"
        cached = frappe.cache().get_value(cache_key)
        if cached:
            parsed = frappe.parse_json(cached)
            if isinstance(parsed, dict):
                return parsed

    saved_row = _save_case_interaction(
        thread_name=thread_name,
        actor_user=user,
        intent_type=intent_type,
        note=note,
        visibility=visibility,
    )
    latest = _fetch_latest_entry_for_sender(thread_name=thread_name, sender_user=user) or saved_row

    response = {
        "thread_name": thread_name,
        "message": _serialize_message_row(
            row=latest,
            applicant_user=_to_text(actor_ctx.get("applicant_user")),
        ),
    }

    if cache_key:
        frappe.cache().set_value(cache_key, frappe.as_json(response), expires_in_sec=600)

    return response


@frappe.whitelist(allow_guest=True)
def get_admissions_case_thread(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    limit_start: int | None = 0,
    limit: int | None = 60,
):
    context_doctype, context_name = _normalize_context(context_doctype, context_name)
    actor_ctx = _require_actor_context(context_doctype=context_doctype, context_name=context_name)

    thread_name = _get_thread_name(context_doctype, context_name)
    if not thread_name:
        return {"thread_name": None, "messages": [], "unread_count": 0}

    start = max(0, cint(limit_start or 0))
    page_length = cint(limit or 60)
    page_length = 200 if page_length > 200 else page_length
    page_length = 1 if page_length < 1 else page_length

    actor_kind = _to_text(actor_ctx.get("actor"))
    actor_user = _to_text(actor_ctx.get("user"))
    applicant_user = _to_text(actor_ctx.get("applicant_user"))

    conditions = [
        "i.org_communication = %(thread_name)s",
        "COALESCE(TRIM(i.note), '') != ''",
        "i.visibility != 'Hidden'",
    ]
    values = {
        "thread_name": thread_name,
        "actor_user": actor_user,
        "start": start,
        "page_length": page_length,
    }
    if actor_kind == "applicant":
        conditions.append("(i.visibility = 'Public to audience' OR i.user = %(actor_user)s)")

    where_clause = " AND ".join(conditions)
    rows = frappe.db.sql(
        f"""
        SELECT
            i.name,
            i.user,
            i.note,
            i.visibility,
            i.creation,
            i.modified,
            u.full_name
        FROM `tab{ENTRY_DOCTYPE}` i
        LEFT JOIN `tabUser` u
          ON u.name = i.user
        WHERE {where_clause}
        ORDER BY i.creation ASC
        LIMIT %(start)s, %(page_length)s
        """,
        values,
        as_dict=True,
    )

    messages = [
        _serialize_message_row(
            row=row,
            applicant_user=applicant_user,
        )
        for row in (rows or [])
    ]

    unread_count = _count_unread_messages(
        thread_name=thread_name,
        applicant_user=applicant_user,
        actor_user=actor_user,
        actor_kind=actor_kind,
    )

    return {
        "thread_name": thread_name,
        "messages": messages,
        "unread_count": unread_count,
    }


@frappe.whitelist(allow_guest=True)
def mark_admissions_case_thread_read(
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


def get_admissions_thread_summaries_for_applicants(*, applicant_rows: list[dict], user: str) -> dict[str, dict]:
    """Return communication summaries keyed by Student Applicant name for Cockpit cards."""
    applicant_names = sorted({_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))})
    if not applicant_names:
        return {}

    applicant_user_by_name = {
        _to_text(row.get("name")): _to_text(row.get("applicant_user"))
        for row in applicant_rows
        if _to_text(row.get("name"))
    }

    summary_by_applicant = {
        applicant_name: {
            "thread_name": None,
            "unread_count": 0,
            "last_message_at": None,
            "last_message_preview": "",
            "last_message_from": None,
            "needs_reply": False,
        }
        for applicant_name in applicant_names
    }

    thread_rows = frappe.get_all(
        "Org Communication",
        filters={
            "admission_context_doctype": "Student Applicant",
            "admission_context_name": ["in", applicant_names],
        },
        fields=["name", "admission_context_name"],
        order_by="creation asc",
        limit=10000,
    )

    thread_by_applicant: dict[str, str] = {}
    applicant_by_thread: dict[str, str] = {}
    for row in thread_rows:
        applicant_name = _to_text(row.get("admission_context_name"))
        thread_name = _to_text(row.get("name"))
        if not applicant_name or not thread_name:
            continue
        if applicant_name in thread_by_applicant:
            continue
        thread_by_applicant[applicant_name] = thread_name
        applicant_by_thread[thread_name] = applicant_name
        summary_by_applicant[applicant_name]["thread_name"] = thread_name

    if not applicant_by_thread:
        return summary_by_applicant

    thread_names = sorted(applicant_by_thread.keys())
    read_rows = frappe.get_all(
        "Portal Read Receipt",
        filters={
            "user": user,
            "reference_doctype": "Org Communication",
            "reference_name": ["in", thread_names],
        },
        fields=["reference_name", "read_at"],
        limit=10000,
    )
    read_at_by_thread = {
        _to_text(row.get("reference_name")): _safe_datetime(row.get("read_at"))
        for row in read_rows
        if _to_text(row.get("reference_name"))
    }

    entry_rows = frappe.db.sql(
        f"""
        SELECT
            i.org_communication,
            i.user,
            i.note,
            i.visibility,
            i.creation,
            u.full_name
        FROM `tab{ENTRY_DOCTYPE}` i
        LEFT JOIN `tabUser` u
          ON u.name = i.user
        WHERE i.org_communication IN %(thread_names)s
          AND COALESCE(TRIM(i.note), '') != ''
          AND i.visibility != 'Hidden'
        ORDER BY i.creation DESC
        """,
        {"thread_names": tuple(thread_names)},
        as_dict=True,
    )

    latest_by_thread: dict[str, dict] = {}
    for row in entry_rows or []:
        thread_name = _to_text(row.get("org_communication"))
        if not thread_name:
            continue
        applicant_name = applicant_by_thread.get(thread_name)
        if not applicant_name:
            continue

        if thread_name not in latest_by_thread:
            latest_by_thread[thread_name] = row

        applicant_user = applicant_user_by_name.get(applicant_name, "")
        if not applicant_user:
            continue

        if _to_text(row.get("user")) != applicant_user:
            continue

        read_at = read_at_by_thread.get(thread_name)
        created_at = _safe_datetime(row.get("creation"))
        if read_at and created_at and created_at <= read_at:
            continue
        summary_by_applicant[applicant_name]["unread_count"] += 1

    for thread_name, latest in latest_by_thread.items():
        applicant_name = applicant_by_thread.get(thread_name)
        if not applicant_name:
            continue

        applicant_user = applicant_user_by_name.get(applicant_name, "")
        sender_user = _to_text(latest.get("user"))
        visibility = _to_text(latest.get("visibility"))
        direction = _sender_direction(
            sender_user=sender_user,
            applicant_user=applicant_user,
            visibility=visibility,
        )
        last_from = "applicant" if direction == "ApplicantToStaff" else "staff"
        unread_count = cint(summary_by_applicant[applicant_name]["unread_count"] or 0)

        summary_by_applicant[applicant_name]["last_message_at"] = latest.get("creation")
        summary_by_applicant[applicant_name]["last_message_preview"] = _truncate_preview(_to_text(latest.get("note")))
        summary_by_applicant[applicant_name]["last_message_from"] = last_from
        summary_by_applicant[applicant_name]["needs_reply"] = bool(unread_count > 0 and last_from == "applicant")

    return summary_by_applicant


# Preserve allow_guest metadata for auth-guard tests and reflective callers.
send_admissions_case_message.allow_guest = True
get_admissions_case_thread.allow_guest = True
mark_admissions_case_thread_read.allow_guest = True
