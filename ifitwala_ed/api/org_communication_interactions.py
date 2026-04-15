# ifitwala_ed/api/org_communication_interactions.py

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from ifitwala_ed.api.org_comm_utils import check_audience_match
from ifitwala_ed.setup.doctype.communication_interaction_entry.communication_interaction_entry import (
    DOCTYPE as ENTRY_DOCTYPE,
)
from ifitwala_ed.setup.doctype.communication_interaction_entry.communication_interaction_entry import (
    INTENT_REACTION_MAP,
    REACTION_INTENT_MAP,
)
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations
from ifitwala_ed.utilities.school_tree import get_descendant_schools

READ_RECEIPT_DOCTYPE = "Portal Read Receipt"
READ_RECEIPT_REFERENCE_DOCTYPE = "Org Communication"
READ_RECEIPT_DEADLOCK_RETRY_ATTEMPTS = 3
READ_RECEIPT_RETRY_BASE_DELAY_SEC = 0.05
REACTION_INTENTS = tuple(sorted(INTENT_REACTION_MAP.keys()))
STAFF_ROLES = {
    "Academic Admin",
    "Academic Staff",
    "Administrator",
    "Academic Assistant",
    "Employee",
    "Instructor",
    "System Manager",
}
INVALID_SESSION_USERS = {"guest", "none", "null", "undefined"}


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return get_datetime(value)
    except Exception:
        return None


def _session_user() -> str:
    user = _to_text(getattr(frappe.session, "user", None))
    if not user or user.lower() in INVALID_SESSION_USERS:
        return ""
    return user


def _expand_employee_visibility_context(employee: dict, roles: set[str]) -> dict:
    employee = dict(employee or {})
    if "Academic Admin" not in (roles or set()):
        return employee

    base_school = _to_text(employee.get("school"))
    if base_school:
        school_names = [school for school in (get_descendant_schools(base_school) or []) if _to_text(school)]
        if school_names:
            employee["school_names"] = school_names
        return employee

    base_organization = _to_text(employee.get("organization"))
    if not base_organization:
        return employee

    organization_names = [org for org in (get_descendant_organizations(base_organization) or []) if _to_text(org)]
    if organization_names:
        employee["organization_names"] = organization_names

    school_rows = frappe.get_all(
        "School",
        filters={"organization": ["in", organization_names]}
        if organization_names
        else {"organization": base_organization},
        pluck="name",
    )
    school_names = [school for school in (school_rows or []) if _to_text(school)]
    if school_names:
        employee["school_names"] = school_names

    return employee


def _actor_context() -> tuple[str, set[str], dict]:
    user = _session_user()
    if not user:
        frappe.throw(_("You need to sign in to interact with communications."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    employee = (
        frappe.db.get_value(
            "Employee",
            {"user_id": user, "employment_status": "Active"},
            ["name", "school", "organization"],
            as_dict=True,
        )
        or {}
    )
    employee = _expand_employee_visibility_context(employee, roles)
    return user, roles, employee


def _is_staff_user(roles: set[str]) -> bool:
    return bool(roles & STAFF_ROLES)


def _ensure_visible_org_communication(org_communication: str, *, user: str, roles: set[str], employee: dict) -> None:
    if not _to_text(org_communication):
        frappe.throw(_("org_communication is required."))

    if not frappe.db.exists("Org Communication", org_communication):
        frappe.throw(
            _("Org Communication {org_communication} was not found.").format(org_communication=org_communication)
        )

    if not check_audience_match(org_communication, user, roles, employee, allow_owner=True):
        frappe.throw(_("You do not have permission to access this communication."), frappe.PermissionError)


def _normalize_comm_names(comm_names) -> list[str]:
    if isinstance(comm_names, str):
        try:
            comm_names = frappe.parse_json(comm_names)
        except Exception:
            comm_names = [comm_names]

    if not isinstance(comm_names, (list, tuple)):
        comm_names = [comm_names]

    cleaned: list[str] = []
    seen = set()
    for value in comm_names:
        name = _to_text(value)
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append(name)
    return cleaned


def _visible_names_for_user(comm_names: list[str], *, user: str, roles: set[str], employee: dict) -> list[str]:
    visible: list[str] = []
    for name in comm_names:
        if check_audience_match(name, user, roles, employee, allow_owner=True):
            visible.append(name)
    return visible


def _entry_visibility_sql(*, is_staff: bool, include_self: bool = True) -> tuple[str, dict]:
    if is_staff:
        return "i.visibility != 'Hidden'", {}
    if include_self:
        return "(i.visibility = 'Public to audience' OR i.user = %(viewer_user)s)", {}
    return "i.visibility = 'Public to audience'", {}


def _reaction_row_query(comm_names: list[str], *, is_staff: bool, user: str) -> list[dict]:
    visibility_sql, _ = _entry_visibility_sql(is_staff=is_staff, include_self=True)
    rows = frappe.db.sql(
        f"""
        SELECT
            i.name,
            i.org_communication,
            i.user,
            i.audience_type,
            i.surface,
            i.intent_type,
            i.reaction_code,
            i.note,
            i.visibility,
            i.is_teacher_reply,
            i.is_pinned,
            i.is_resolved,
            i.creation,
            i.modified
        FROM `tab{ENTRY_DOCTYPE}` i
        WHERE i.org_communication IN %(comms)s
          AND {visibility_sql}
          AND (
              COALESCE(TRIM(i.reaction_code), '') != ''
              OR i.intent_type IN %(reaction_intents)s
          )
        ORDER BY i.org_communication ASC, i.user ASC, i.creation DESC, i.modified DESC, i.name DESC
        """,
        {
            "comms": tuple(comm_names),
            "viewer_user": user,
            "reaction_intents": REACTION_INTENTS,
        },
        as_dict=True,
    )
    latest_by_key: dict[tuple[str, str], dict] = {}
    for row in rows or []:
        key = (_to_text(row.get("org_communication")), _to_text(row.get("user")))
        if not key[0] or not key[1] or key in latest_by_key:
            continue
        latest_by_key[key] = row
    return list(latest_by_key.values())


def _latest_user_rows(comm_names: list[str], *, user: str) -> dict[str, dict]:
    rows = frappe.db.sql(
        f"""
        SELECT
            i.name,
            i.org_communication,
            i.user,
            i.audience_type,
            i.surface,
            i.intent_type,
            i.reaction_code,
            i.note,
            i.visibility,
            i.is_teacher_reply,
            i.is_pinned,
            i.is_resolved,
            i.creation,
            i.modified
        FROM `tab{ENTRY_DOCTYPE}` i
        WHERE i.org_communication IN %(comms)s
          AND i.user = %(user)s
        ORDER BY i.org_communication ASC, i.creation DESC, i.modified DESC, i.name DESC
        """,
        {"comms": tuple(comm_names), "user": user},
        as_dict=True,
    )
    latest: dict[str, dict] = {}
    for row in rows or []:
        comm_name = _to_text(row.get("org_communication"))
        if not comm_name or comm_name in latest:
            continue
        latest[comm_name] = row
    return latest


def _comment_counts(comm_names: list[str], *, is_staff: bool, user: str) -> dict[str, int]:
    visibility_sql, _ = _entry_visibility_sql(is_staff=is_staff, include_self=True)
    rows = frappe.db.sql(
        f"""
        SELECT i.org_communication, COUNT(*) AS cnt
        FROM `tab{ENTRY_DOCTYPE}` i
        WHERE i.org_communication IN %(comms)s
          AND {visibility_sql}
          AND i.intent_type = 'Comment'
          AND COALESCE(TRIM(i.note), '') != ''
          AND i.visibility != 'Hidden'
        GROUP BY i.org_communication
        """,
        {"comms": tuple(comm_names), "viewer_user": user},
        as_dict=True,
    )
    return {_to_text(row.get("org_communication")): cint(row.get("cnt") or 0) for row in (rows or [])}


def _serialize_self_row(row: dict | None, reaction_row: dict | None = None) -> dict | None:
    if not row:
        return None

    reaction_code = _to_text((reaction_row or {}).get("reaction_code")) or _to_text(row.get("reaction_code"))
    if not reaction_code:
        reaction_code = INTENT_REACTION_MAP.get(
            _to_text((reaction_row or {}).get("intent_type"))
        ) or INTENT_REACTION_MAP.get(_to_text(row.get("intent_type")))

    return {
        "name": _to_text(row.get("name")),
        "org_communication": _to_text(row.get("org_communication")),
        "user": _to_text(row.get("user")),
        "audience_type": _to_text(row.get("audience_type")) or None,
        "surface": _to_text(row.get("surface")) or None,
        "school": None,
        "program": None,
        "student_group": None,
        "reaction_code": reaction_code or None,
        "intent_type": _to_text(row.get("intent_type")) or None,
        "note": _to_text(row.get("note")) or None,
        "visibility": _to_text(row.get("visibility")) or None,
        "is_teacher_reply": cint(row.get("is_teacher_reply") or 0),
        "is_pinned": cint(row.get("is_pinned") or 0),
        "is_resolved": cint(row.get("is_resolved") or 0),
        "creation": row.get("creation"),
        "modified": row.get("modified"),
    }


def _is_query_deadlock_error(exc: Exception) -> bool:
    if exc.__class__.__name__ == "QueryDeadlockError":
        return True
    return _to_text(getattr(exc, "exc_type", "")).lower() == "querydeadlockerror"


def _upsert_portal_read_receipt(*, user: str, reference_name: str, read_at: datetime) -> None:
    values = {
        "name": frappe.generate_hash(length=10),
        "created_at": read_at,
        "modified_at": read_at,
        "modified_by": user,
        "owner": user,
        "user": user,
        "reference_doctype": READ_RECEIPT_REFERENCE_DOCTYPE,
        "reference_name": reference_name,
        "read_at": read_at,
    }
    lock_key = f"org-communication:read:{user}:{reference_name}"
    with frappe.cache().lock(lock_key, timeout=8):
        for attempt in range(1, READ_RECEIPT_DEADLOCK_RETRY_ATTEMPTS + 1):
            values["name"] = frappe.generate_hash(length=10)
            try:
                frappe.db.sql(
                    """
                    INSERT INTO `tabPortal Read Receipt`
                        (`name`, `creation`, `modified`, `modified_by`, `owner`, `docstatus`, `idx`,
                         `user`, `reference_doctype`, `reference_name`, `read_at`)
                    VALUES
                        (%(name)s, %(created_at)s, %(modified_at)s, %(modified_by)s, %(owner)s, 0, 0,
                         %(user)s, %(reference_doctype)s, %(reference_name)s, %(read_at)s)
                    ON DUPLICATE KEY UPDATE
                        `read_at` = VALUES(`read_at`),
                        `modified` = VALUES(`modified`),
                        `modified_by` = VALUES(`modified_by`)
                    """,
                    values,
                )
                return
            except Exception as exc:
                if not _is_query_deadlock_error(exc):
                    raise
                if attempt >= READ_RECEIPT_DEADLOCK_RETRY_ATTEMPTS:
                    raise
                time.sleep(READ_RECEIPT_RETRY_BASE_DELAY_SEC * attempt)


def get_seen_org_communication_names(*, user: str, communication_names: list[str]) -> set[str]:
    names = [_to_text(name) for name in communication_names if _to_text(name)]
    if not names:
        return set()

    seen_rows = frappe.get_all(
        READ_RECEIPT_DOCTYPE,
        filters={
            "user": user,
            "reference_doctype": READ_RECEIPT_REFERENCE_DOCTYPE,
            "reference_name": ["in", names],
        },
        fields=["reference_name"],
        limit=10000,
    )
    seen_names = {_to_text(row.get("reference_name")) for row in seen_rows if _to_text(row.get("reference_name"))}

    interaction_rows = frappe.get_all(
        ENTRY_DOCTYPE,
        filters={"user": user, "org_communication": ["in", names]},
        fields=["org_communication"],
        limit=10000,
    )
    for row in interaction_rows:
        comm_name = _to_text(row.get("org_communication"))
        if comm_name:
            seen_names.add(comm_name)

    return seen_names


def create_interaction_entry(
    *,
    org_communication: str,
    user: str,
    intent_type: str | None = None,
    reaction_code: str | None = None,
    note: str | None = None,
    surface: str | None = None,
    visibility: str | None = None,
) -> dict:
    doc = frappe.new_doc(ENTRY_DOCTYPE)
    doc.org_communication = org_communication
    doc.user = user
    doc.intent_type = _to_text(intent_type) or None
    doc.reaction_code = _to_text(reaction_code) or None
    doc.note = _to_text(note) or None
    doc.surface = _to_text(surface) or None
    doc.visibility = _to_text(visibility) or None
    doc.insert(ignore_permissions=True)
    return {
        "name": _to_text(doc.name),
        "org_communication": _to_text(doc.org_communication),
        "intent_type": _to_text(doc.intent_type) or None,
        "reaction_code": _to_text(doc.reaction_code) or None,
        "note": _to_text(doc.note) or None,
        "visibility": _to_text(doc.visibility) or None,
        "creation": doc.creation,
        "modified": doc.modified,
        "user": _to_text(doc.user),
    }


def get_latest_org_communication_entry_for_user(*, org_communication: str, user: str) -> dict | None:
    rows = frappe.get_all(
        ENTRY_DOCTYPE,
        filters={"org_communication": org_communication, "user": user},
        fields=[
            "name",
            "org_communication",
            "user",
            "audience_type",
            "surface",
            "intent_type",
            "reaction_code",
            "note",
            "visibility",
            "is_teacher_reply",
            "is_pinned",
            "is_resolved",
            "creation",
            "modified",
        ],
        order_by="creation desc, modified desc",
        limit=1,
    )
    if not rows:
        return None
    return rows[0]


def upsert_org_communication_read_receipt(*, user: str, org_communication: str, read_at: datetime) -> None:
    _upsert_portal_read_receipt(user=user, reference_name=org_communication, read_at=read_at)


@frappe.whitelist()
def get_org_communication_interaction_summary(comm_names=None):
    user, roles, employee = _actor_context()
    requested_names = _normalize_comm_names(comm_names)
    visible_names = _visible_names_for_user(requested_names, user=user, roles=roles, employee=employee)
    if not visible_names:
        return {}

    is_staff = _is_staff_user(roles)
    summary = {
        name: {
            "counts": {},
            "reaction_counts": {code: 0 for code in REACTION_INTENT_MAP},
            "reactions_total": 0,
            "comments_total": 0,
            "self": None,
        }
        for name in visible_names
    }

    latest_reaction_rows = _reaction_row_query(visible_names, is_staff=is_staff, user=user)
    latest_reaction_by_key = {
        (_to_text(row.get("org_communication")), _to_text(row.get("user"))): row for row in latest_reaction_rows
    }
    latest_reaction_for_user = {
        _to_text(comm_name): row for (comm_name, row_user), row in latest_reaction_by_key.items() if row_user == user
    }

    for row in latest_reaction_rows:
        comm_name = _to_text(row.get("org_communication"))
        if comm_name not in summary:
            continue
        intent_type = _to_text(row.get("intent_type"))
        reaction_code = _to_text(row.get("reaction_code")) or INTENT_REACTION_MAP.get(intent_type, "")
        if reaction_code:
            summary[comm_name]["reaction_counts"][reaction_code] = (
                summary[comm_name]["reaction_counts"].get(reaction_code, 0) + 1
            )
        if intent_type:
            summary[comm_name]["counts"][intent_type] = summary[comm_name]["counts"].get(intent_type, 0) + 1

    comment_counts = _comment_counts(visible_names, is_staff=is_staff, user=user)
    latest_self_rows = _latest_user_rows(visible_names, user=user)

    for comm_name, data in summary.items():
        comments_total = comment_counts.get(comm_name, 0)
        data["comments_total"] = comments_total
        data["counts"]["Comment"] = comments_total
        data["reactions_total"] = sum(int(value or 0) for value in (data.get("reaction_counts") or {}).values())
        data["self"] = _serialize_self_row(
            latest_self_rows.get(comm_name),
            latest_reaction_for_user.get(comm_name),
        )

    return summary


@frappe.whitelist()
def get_org_communication_thread(org_communication: str, limit_start: int = 0, limit: int = 20):
    user, roles, employee = _actor_context()
    _ensure_visible_org_communication(org_communication, user=user, roles=roles, employee=employee)

    try:
        limit_start = int(limit_start or 0)
        limit = int(limit or 20)
    except ValueError:
        limit_start = 0
        limit = 20

    parent = frappe.get_cached_doc("Org Communication", org_communication)
    mode = (parent.interaction_mode or "None").strip() or "None"
    is_staff = _is_staff_user(roles)

    if mode == "Structured Feedback" and not is_staff:
        return []

    conditions = [
        "i.org_communication = %(comm)s",
        "i.intent_type = 'Comment'",
        "COALESCE(TRIM(i.note), '') != ''",
        "i.visibility != 'Hidden'",
    ]

    params = {
        "comm": org_communication,
        "user": user,
        "limit_start": limit_start,
        "limit": limit,
        "ts_fmt": "%Y-%m-%d %H:%i:%s",
    }

    if mode == "Staff Comments":
        if not is_staff:
            return []
    elif mode == "Student Q&A":
        if not is_staff:
            conditions.append("(i.visibility = 'Public to audience' OR i.user = %(user)s)")
    elif mode == "Structured Feedback":
        if not is_staff:
            return []
    else:
        return []

    where_clause = " AND ".join(conditions)
    return (
        frappe.db.sql(
            f"""
            SELECT
                i.name,
                i.user,
                u.full_name,
                i.audience_type,
                i.intent_type,
                i.reaction_code,
                i.note,
                i.visibility,
                i.is_teacher_reply,
                i.is_pinned,
                i.is_resolved,
                DATE_FORMAT(CONVERT_TZ(i.creation, 'UTC', @@session.time_zone), %(ts_fmt)s) AS creation,
                i.modified
            FROM `tab{ENTRY_DOCTYPE}` i
            LEFT JOIN `tabUser` u ON u.name = i.user
            WHERE {where_clause}
            ORDER BY i.is_pinned DESC, i.creation ASC
            LIMIT %(limit_start)s, %(limit)s
            """,
            params,
            as_dict=True,
        )
        or []
    )


@frappe.whitelist()
def react_to_org_communication(org_communication: str, reaction_code: str, surface: str | None = None):
    user, roles, employee = _actor_context()
    _ensure_visible_org_communication(org_communication, user=user, roles=roles, employee=employee)

    reaction = _to_text(reaction_code)
    if reaction not in REACTION_INTENT_MAP:
        frappe.throw(_("Unsupported reaction code: {reaction}.").format(reaction=reaction or _("(empty)")))

    response = create_interaction_entry(
        org_communication=org_communication,
        user=user,
        reaction_code=reaction,
        intent_type=REACTION_INTENT_MAP[reaction],
        surface=_to_text(surface) or None,
    )
    return response


@frappe.whitelist()
def post_org_communication_comment(org_communication: str, note: str, surface: str | None = None):
    user, roles, employee = _actor_context()
    _ensure_visible_org_communication(org_communication, user=user, roles=roles, employee=employee)

    body = _to_text(note)
    if not body:
        frappe.throw(_("Please add a comment before posting."))

    parent = frappe.get_cached_doc("Org Communication", org_communication)
    mode = _to_text(getattr(parent, "interaction_mode", None)) or "None"
    intent_type = "Comment"
    if mode == "Structured Feedback":
        intent_type = "Other"

    response = create_interaction_entry(
        org_communication=org_communication,
        user=user,
        intent_type=intent_type,
        note=body,
        surface=_to_text(surface) or None,
    )
    return response


@frappe.whitelist()
def mark_org_communication_read(org_communication: str):
    user, roles, employee = _actor_context()
    _ensure_visible_org_communication(org_communication, user=user, roles=roles, employee=employee)

    read_at = now_datetime()
    _upsert_portal_read_receipt(user=user, reference_name=org_communication, read_at=read_at)
    return {"ok": True, "org_communication": org_communication, "read_at": read_at}
