# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus.py

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.admission.applicant_review_workflow import (
    ASSIGNMENT_DOCTYPE,
    DECISION_OPTIONS_BY_TARGET,
    TARGET_APPLICATION,
    TARGET_DOCUMENT,
    TARGET_HEALTH,
    complete_assignment_decision,
)

STUDENT_LOG_DOCTYPE = "Student Log"
FOLLOW_UP_DOCTYPE = "Student Log Follow Up"
INQUIRY_DOCTYPE = "Inquiry"
APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE = ASSIGNMENT_DOCTYPE

ACTION_STUDENT_LOG_SUBMIT = "student_log.follow_up.act.submit"
ACTION_STUDENT_LOG_REVIEW = "student_log.follow_up.review.decide"
ACTION_INQUIRY_FIRST_CONTACT = "inquiry.follow_up.act.first_contact"
ACTION_APPLICANT_REVIEW_SUBMIT = "applicant_review.assignment.decide"

# Focus action types (v1)
ACTION_MODE = {
    ACTION_STUDENT_LOG_SUBMIT: "assignee",
    ACTION_STUDENT_LOG_REVIEW: "author",
    ACTION_INQUIRY_FIRST_CONTACT: "assignee",
    ACTION_APPLICANT_REVIEW_SUBMIT: "assignee",
}


def _get_user_full_names(user_ids: list[str]) -> dict[str, str]:
    """
    Batch map User.name -> User.full_name using raw SQL.
    Falls back to user id if full_name is missing.
    """
    ids = sorted({(u or "").strip() for u in (user_ids or []) if (u or "").strip()})
    if not ids:
        return {}

    rows = frappe.db.sql(
        """
        select
            name,
            ifnull(full_name, name) as full_name
        from `tabUser`
        where name in %(ids)s
        """,
        {"ids": tuple(ids)},
        as_dict=True,
    )

    out = {r["name"]: r["full_name"] for r in rows}

    # defensive fallback
    for u in ids:
        out.setdefault(u, u)

    return out


# ---------------------------------------------------------------------
# ID helpers (deterministic)
# ---------------------------------------------------------------------
def build_focus_item_id(
    workflow: str,
    reference_doctype: str,
    reference_name: str,
    action_type: str,
    user: str,
) -> str:
    """
    Deterministic FocusItem id.

    NOTE:
    - This is *the* stable contract between focus.list() and focus.get_context().
    - Do not change the format without a migration plan (it breaks deep links).
    """
    return f"{workflow}::{reference_doctype}::{reference_name}::{action_type}::{user}"


def _parse_focus_item_id(focus_item_id: str) -> dict:
    parts = (focus_item_id or "").split("::")
    if len(parts) != 5:
        frappe.throw(_("Invalid focus item id."), frappe.ValidationError)

    workflow, reference_doctype, reference_name, action_type, user = parts
    return {
        "workflow": workflow,
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "action_type": action_type,
        "user": user,
    }


def _resolve_mode(action_type: str | None, reference_doctype: str, doc) -> str:
    """
    Server remains authoritative for mode.
    - If action_type is provided, it must be known and maps to the mode.
    - Otherwise infer from the log + session user.
    """
    if action_type:
        mode = ACTION_MODE.get(action_type)
        if not mode:
            frappe.throw(_("Unknown focus action type."), frappe.ValidationError)
        return mode

    # fallback: infer from doc context
    if reference_doctype == STUDENT_LOG_DOCTYPE and doc.follow_up_person == frappe.session.user:
        return "assignee"
    if reference_doctype == INQUIRY_DOCTYPE and doc.assigned_to == frappe.session.user:
        return "assignee"

    return "author"


# ---------------------------------------------------------------------
# Focus list (Phase 1+: Student Log + Inquiry)
# ---------------------------------------------------------------------
def _badge_from_due_date(due_date: str | None) -> str | None:
    if not due_date:
        return None
    try:
        today = frappe.utils.today()
        if due_date == today:
            return "Today"
        # "Due soon" = within next 2 days (cheap, deterministic)
        if frappe.utils.date_diff(due_date, today) in (1, 2):
            return "Due soon"
    except Exception:
        return None
    return None


def _can_read_student_log(name: str) -> bool:
    """
    Permission-safe existence check without loading the full Document.

    We intentionally avoid frappe.has_permission(..., doc=frappe.get_doc(...)) here
    to prevent N doc loads in list_focus_items().

    Instead we use frappe.get_list(), which enforces permissions.
    If user can't read the doc, it will not be returned.
    """
    try:
        if not name:
            return False

        rows = frappe.get_list(
            STUDENT_LOG_DOCTYPE,
            filters={"name": name},
            fields=["name"],
            limit_page_length=1,
        )
        return bool(rows)
    except Exception:
        return False


def _can_read_inquiry(name: str) -> bool:
    try:
        if not name:
            return False

        rows = frappe.get_list(
            INQUIRY_DOCTYPE,
            filters={"name": name},
            fields=["name"],
            limit_page_length=1,
        )
        return bool(rows)
    except Exception:
        return False


def _normalize_roles(roles: list[str] | tuple[str, ...] | None) -> list[str]:
    return sorted({(role or "").strip() for role in (roles or []) if (role or "").strip()})


def _reviewer_matches_assignment(row: dict, *, user: str, roles: set[str]) -> bool:
    assigned_to_user = (row.get("assigned_to_user") or "").strip()
    assigned_to_role = (row.get("assigned_to_role") or "").strip()
    if assigned_to_user:
        return assigned_to_user == user
    if assigned_to_role:
        return assigned_to_role in roles
    return False


def _applicant_display_name_from_row(row: dict) -> str:
    parts = [
        (row.get("first_name") or "").strip(),
        (row.get("middle_name") or "").strip(),
        (row.get("last_name") or "").strip(),
    ]
    full_name = " ".join(part for part in parts if part).strip()
    return full_name or (row.get("student_applicant") or "")


def _assignment_title(row: dict) -> str:
    target_type = (row.get("target_type") or "").strip()
    applicant_name = _applicant_display_name_from_row(row)

    if target_type == TARGET_DOCUMENT:
        doc_label = (
            (row.get("document_label") or "").strip()
            or (row.get("document_type_code") or "").strip()
            or (row.get("document_type_name") or "").strip()
            or (row.get("document_type") or "").strip()
            or _("Document")
        )
        return _("Review {0} — Applicant {1}").format(doc_label, applicant_name)

    if target_type == TARGET_HEALTH:
        return _("Review Health Profile — Applicant {0}").format(applicant_name)

    return _("Review Application — Applicant {0}").format(applicant_name)


def _assignment_subtitle(row: dict) -> str:
    parts = []
    school = (row.get("school") or "").strip()
    program_offering = (row.get("program_offering") or "").strip()
    if school:
        parts.append(school)
    if program_offering:
        parts.append(program_offering)
    return " • ".join(parts) if parts else _("Admissions review")


@frappe.whitelist()
def list_focus_items(open_only: int = 1, limit: int = 20, offset: int = 0):
    """
    Return FocusItem[] for the current user.

    V1: Student Log + Inquiry.
    - "action" items: ToDo allocated to user for Student Log follow-up work
    - "review" items: log owner, submitted follow-up exists, log not completed

    Performance:
    - No N+1 doc loads
    - Batched queries
    - Uses ToDo for assignee visibility (single-open ToDo policy)
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    # ----------------------------
    # 1) Validate/coerce args ONLY
    # ----------------------------
    open_only = frappe.utils.cint(open_only)

    limit = frappe.utils.cint(limit) or 20
    offset = frappe.utils.cint(offset) or 0

    limit = min(max(limit, 1), 50)
    offset = max(offset, 0)

    items: list[dict] = []

    # ------------------------------------------------------------
    # A) Assignee action items (ToDo -> Student Log)
    # ------------------------------------------------------------
    # IMPORTANT:
    # - "Assigned by" must be the person who created/assigned the ToDo.
    #   In Frappe, this is ToDo.assigned_by (with assigned_by_full_name).
    # - We keep a fallback to ToDo.owner for older rows/edge-cases.
    action_rows = frappe.db.sql(
        """
        select
            t.reference_name as log_name,
            t.date as todo_due_date,

            -- canonical assigner identity (can differ from Student Log.owner)
            nullif(trim(ifnull(t.assigned_by, '')), '') as todo_assigned_by,
            nullif(trim(ifnull(t.assigned_by_full_name, '')), '') as todo_assigned_by_full_name,

            -- fallback (older ToDo rows)
            nullif(trim(ifnull(t.owner, '')), '') as todo_owner,

            s.student_name,
            s.next_step,
            s.requires_follow_up,
            s.follow_up_status,
            s.follow_up_person
        from `tabToDo` t
        join `tabStudent Log` s
          on s.name = t.reference_name
        where t.allocated_to = %(user)s
          and t.reference_type = %(ref_type)s
          and (%(open_only)s = 0 or t.status = 'Open')
          and ifnull(s.requires_follow_up, 0) = 1
          and lower(ifnull(s.follow_up_status, '')) != 'completed'
          and not exists (
                select 1
                from `tabStudent Log Follow Up` f
                where f.student_log = s.name
                  and f.docstatus = 1
          )
        order by t.date asc, t.modified desc
        limit %(limit)s offset %(offset)s
        """,
        {
            "user": user,
            "ref_type": STUDENT_LOG_DOCTYPE,
            "open_only": open_only,
            "limit": limit,
            "offset": offset,
        },
        as_dict=True,
    )

    # Resolve next-step titles in one batch (optional enrichment)
    next_step_names = sorted({r.get("next_step") for r in action_rows if r.get("next_step")})
    next_step_title_by_name = {}
    if next_step_names:
        ns = frappe.get_all(
            "Student Log Next Step",
            filters={"name": ["in", next_step_names]},
            fields=["name", "next_step"],
            limit_page_length=1000,
            ignore_permissions=True,
        )
        next_step_title_by_name = {x["name"]: x.get("next_step") for x in ns}

    # Resolve assigner display names in one batch (only for rows where ToDo didn't already carry full name)
    # We may have:
    # - todo_assigned_by_full_name already (prefer it)
    # - else resolve user.full_name via SQL
    assigner_ids_to_resolve: set[str] = set()
    for r in action_rows:
        if r.get("todo_assigned_by_full_name"):
            continue
        assigner = r.get("todo_assigned_by") or r.get("todo_owner")
        if assigner:
            assigner_ids_to_resolve.add(assigner)

    assigner_name_by_id = _get_user_full_names(sorted(assigner_ids_to_resolve))

    for r in action_rows:
        log_name = r.get("log_name")
        if not log_name:
            continue

        # Hard permission gate (doc-level)
        if not _can_read_student_log(log_name):
            continue

        due = str(r.get("todo_due_date")) if r.get("todo_due_date") else None
        badge = _badge_from_due_date(due)

        next_step_title = None
        if r.get("next_step"):
            next_step_title = next_step_title_by_name.get(r.get("next_step"))

        title = "Follow up"
        subtitle = f"{r.get('student_name') or log_name}"
        if next_step_title:
            subtitle = f"{subtitle} • Next step: {next_step_title}"

        # Assigned-by (ToDo assigner) — keep in payload always.
        # Prefer ToDo.assigned_by; fallback to ToDo.owner if missing.
        assigned_by = (r.get("todo_assigned_by") or r.get("todo_owner") or "").strip() or None

        # Prefer ToDo.assigned_by_full_name if present, else resolve via SQL.
        assigned_by_name = (r.get("todo_assigned_by_full_name") or "").strip() or None
        if not assigned_by_name and assigned_by:
            assigned_by_name = assigner_name_by_id.get(assigned_by) or assigned_by

        action_type = ACTION_STUDENT_LOG_SUBMIT
        items.append(
            {
                "id": build_focus_item_id("student_log", STUDENT_LOG_DOCTYPE, log_name, action_type, user),
                "kind": "action",
                "title": title,
                "subtitle": subtitle,
                "badge": badge,
                "priority": 80,
                "due_date": due,
                "action_type": action_type,
                "reference_doctype": STUDENT_LOG_DOCTYPE,
                "reference_name": log_name,
                "payload": {
                    "student_name": r.get("student_name"),
                    "next_step": r.get("next_step"),
                    "assigned_by": assigned_by,
                    "assigned_by_name": assigned_by_name,
                },
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # B) Assignee action items (ToDo -> Inquiry)
    # ------------------------------------------------------------
    inquiry_rows = frappe.db.sql(
        """
        select
            t.reference_name as inquiry_name,
            t.date as todo_due_date,

            nullif(trim(ifnull(t.assigned_by, '')), '') as todo_assigned_by,
            nullif(trim(ifnull(t.assigned_by_full_name, '')), '') as todo_assigned_by_full_name,
            nullif(trim(ifnull(t.owner, '')), '') as todo_owner,

            i.first_name,
            i.last_name,
            i.school,
            i.organization,
            i.workflow_state,
            i.assigned_to,
            i.followup_due_on
        from `tabToDo` t
        join `tabInquiry` i
          on i.name = t.reference_name
        where t.allocated_to = %(user)s
          and t.reference_type = %(ref_type)s
          and (%(open_only)s = 0 or t.status = 'Open')
          and ifnull(i.assigned_to, '') = %(user)s
          and ifnull(i.workflow_state, '') = 'Assigned'
        order by ifnull(i.followup_due_on, t.date) asc, t.modified desc
        limit %(limit)s offset %(offset)s
        """,
        {
            "user": user,
            "ref_type": INQUIRY_DOCTYPE,
            "open_only": open_only,
            "limit": limit,
            "offset": offset,
        },
        as_dict=True,
    )

    inquiry_assigner_ids_to_resolve: set[str] = set()
    for r in inquiry_rows:
        if r.get("todo_assigned_by_full_name"):
            continue
        assigner = r.get("todo_assigned_by") or r.get("todo_owner")
        if assigner:
            inquiry_assigner_ids_to_resolve.add(assigner)

    inquiry_assigner_name_by_id = _get_user_full_names(sorted(inquiry_assigner_ids_to_resolve))

    for r in inquiry_rows:
        inquiry_name = r.get("inquiry_name")
        if not inquiry_name:
            continue

        if not _can_read_inquiry(inquiry_name):
            continue

        due_source = r.get("followup_due_on") or r.get("todo_due_date")
        due = str(due_source) if due_source else None
        badge = _badge_from_due_date(due)

        subject_name = " ".join(
            filter(
                None,
                [
                    (r.get("first_name") or "").strip(),
                    (r.get("last_name") or "").strip(),
                ],
            )
        )
        subject_name = subject_name or inquiry_name

        subtitle_parts = [subject_name]
        if r.get("school"):
            subtitle_parts.append(f"School: {r.get('school')}")
        elif r.get("organization"):
            subtitle_parts.append(f"Org: {r.get('organization')}")
        subtitle = " • ".join(subtitle_parts)

        assigned_by = (r.get("todo_assigned_by") or r.get("todo_owner") or "").strip() or None
        assigned_by_name = (r.get("todo_assigned_by_full_name") or "").strip() or None
        if not assigned_by_name and assigned_by:
            assigned_by_name = inquiry_assigner_name_by_id.get(assigned_by) or assigned_by

        action_type = ACTION_INQUIRY_FIRST_CONTACT
        items.append(
            {
                "id": build_focus_item_id("inquiry", INQUIRY_DOCTYPE, inquiry_name, action_type, user),
                "kind": "action",
                "title": "First contact",
                "subtitle": subtitle,
                "badge": badge,
                "priority": 75,
                "due_date": due,
                "action_type": action_type,
                "reference_doctype": INQUIRY_DOCTYPE,
                "reference_name": inquiry_name,
                "payload": {
                    "subject_name": subject_name,
                    "assigned_by": assigned_by,
                    "assigned_by_name": assigned_by_name,
                    "school": r.get("school"),
                    "organization": r.get("organization"),
                },
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # C) Author review items
    # ------------------------------------------------------------
    review_rows = frappe.db.sql(
        """
        select
            s.name as log_name,
            s.student_name
        from `tabStudent Log` s
        where s.owner = %(user)s
          and ifnull(s.requires_follow_up, 0) = 1
          and lower(ifnull(s.follow_up_status, '')) != 'completed'
          and exists (
                select 1
                from `tabStudent Log Follow Up` f
                where f.student_log = s.name
                  and f.docstatus = 1
          )
        order by s.modified desc
        limit 200
        """,
        {"user": user},
        as_dict=True,
    )

    for r in review_rows:
        log_name = r.get("log_name")
        if not log_name:
            continue

        if not _can_read_student_log(log_name):
            continue

        action_type = ACTION_STUDENT_LOG_REVIEW
        items.append(
            {
                "id": build_focus_item_id("student_log", STUDENT_LOG_DOCTYPE, log_name, action_type, user),
                "kind": "review",
                "title": "Review outcome",
                "subtitle": f"{r.get('student_name') or log_name} • Decide: close or continue follow-up",
                "badge": None,
                "priority": 70,
                "due_date": None,
                "action_type": action_type,
                "reference_doctype": STUDENT_LOG_DOCTYPE,
                "reference_name": log_name,
                "payload": {"student_name": r.get("student_name")},
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # D) Admissions applicant review assignments
    # ------------------------------------------------------------
    user_roles = _normalize_roles(frappe.get_roles(user))
    assignment_rows = frappe.db.sql(
        """
        select
            a.name,
            a.target_type,
            a.target_name,
            a.student_applicant,
            a.assigned_to_user,
            a.assigned_to_role,
            a.modified,
            sa.first_name,
            sa.middle_name,
            sa.last_name,
            sa.school,
            sa.program_offering,
            ad.document_type,
            ad.document_label,
            adt.document_type_name,
            adt.code as document_type_code
        from `tabApplicant Review Assignment` a
        join `tabStudent Applicant` sa
          on sa.name = a.student_applicant
        left join `tabApplicant Document` ad
          on a.target_type = 'Applicant Document'
         and ad.name = a.target_name
        left join `tabApplicant Document Type` adt
          on adt.name = ad.document_type
        where (%(open_only)s = 0 or a.status = 'Open')
          and (
                a.assigned_to_user = %(user)s
             or (
                    ifnull(a.assigned_to_role, '') != ''
                and a.assigned_to_role in %(roles)s
             )
          )
        order by a.modified desc
        limit %(limit)s offset %(offset)s
        """,
        {
            "open_only": open_only,
            "user": user,
            "roles": tuple(user_roles) or ("",),
            "limit": limit,
            "offset": offset,
        },
        as_dict=True,
    )

    for row in assignment_rows:
        items.append(
            {
                "id": build_focus_item_id(
                    "applicant_review",
                    APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
                    row.get("name"),
                    ACTION_APPLICANT_REVIEW_SUBMIT,
                    user,
                ),
                "kind": "action",
                "title": _assignment_title(row),
                "subtitle": _assignment_subtitle(row),
                "badge": None,
                "priority": 90,
                "due_date": None,
                "action_type": ACTION_APPLICANT_REVIEW_SUBMIT,
                "reference_doctype": APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
                "reference_name": row.get("name"),
                "payload": {
                    "applicant_name": _applicant_display_name_from_row(row),
                    "student_applicant": row.get("student_applicant"),
                    "target_type": row.get("target_type"),
                    "target_name": row.get("target_name"),
                },
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # Sort + slice
    # ------------------------------------------------------------
    def _sort_key(x):
        kind_rank = 0 if x.get("kind") == "action" else 1
        pr = x.get("priority") or 0
        due = x.get("due_date") or "9999-12-31"
        return (kind_rank, -pr, due)

    items.sort(key=_sort_key)
    return items[:limit]


# ---------------------------------------------------------------------
# Context endpoint (used by FocusRouterOverlay)
# ---------------------------------------------------------------------
@frappe.whitelist()
def get_focus_context(
    focus_item_id: str | None = None,
    reference_doctype: str | None = None,
    reference_name: str | None = None,
    action_type: str | None = None,
):
    """
    Resolve routing + workflow context for a single Focus item.

    Accepted inputs:
    - focus_item_id (preferred, deterministic, user-bound)
    - OR reference_doctype + reference_name (+ optional action_type)

    SECURITY INVARIANTS:
    - focus_item_id, if provided, must belong to frappe.session.user
    - Doc-level read permission is always enforced
    """
    # ------------------------------------------------------------
    # 1) Resolve reference from focus_item_id (authoritative path)
    # ------------------------------------------------------------
    if focus_item_id:
        parsed = _parse_focus_item_id(focus_item_id)

        reference_doctype = parsed["reference_doctype"]
        reference_name = parsed["reference_name"]
        action_type = parsed["action_type"]

        # Hard guard: focus item must belong to current user
        if parsed.get("user") != frappe.session.user:
            frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

    # ------------------------------------------------------------
    # 2) Validate reference
    # ------------------------------------------------------------
    if not reference_doctype or not reference_name:
        frappe.throw(_("Missing reference information."), frappe.ValidationError)

    if reference_doctype == STUDENT_LOG_DOCTYPE:
        # ------------------------------------------------------------
        # 3) Load document ONCE (permission + payload)
        # ------------------------------------------------------------
        log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, reference_name)

        # ------------------------------------------------------------
        # 4) Enforce doc-level permission (authoritative)
        # ------------------------------------------------------------
        if not frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", doc=log_doc):
            frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

        # ------------------------------------------------------------
        # 5) Resolve workflow mode (author vs assignee)
        # ------------------------------------------------------------
        mode = _resolve_mode(action_type, STUDENT_LOG_DOCTYPE, log_doc)

        # ------------------------------------------------------------
        # 5b) Resolve original log author (Student Log.owner) name
        # ------------------------------------------------------------
        log_author = (log_doc.owner or "").strip() or None
        log_author_name_by_id = _get_user_full_names([log_author] if log_author else [])

        # ------------------------------------------------------------
        # 6) Fetch recent follow-ups (bounded)
        # ------------------------------------------------------------
        follow_up_rows = frappe.get_all(
            FOLLOW_UP_DOCTYPE,
            filters={"student_log": reference_name},
            fields=["name", "date", "follow_up_author", "follow_up", "docstatus"],
            order_by="modified desc",
            limit_page_length=20,
        )

        follow_ups = [
            {
                "name": row.get("name"),
                "date": str(row.get("date")) if row.get("date") else None,
                "follow_up_author": row.get("follow_up_author"),
                "follow_up_html": row.get("follow_up") or "",
                "docstatus": row.get("docstatus"),
            }
            for row in follow_up_rows
        ]

        return {
            "focus_item_id": focus_item_id,
            "action_type": action_type,
            "reference_doctype": STUDENT_LOG_DOCTYPE,
            "reference_name": reference_name,
            "mode": mode,
            "log": {
                "name": log_doc.name,
                "student": log_doc.student,
                "student_name": log_doc.student_name,
                "school": log_doc.school,
                "log_type": log_doc.log_type,
                "next_step": log_doc.next_step,
                "follow_up_person": log_doc.follow_up_person,
                "follow_up_role": log_doc.follow_up_role,
                "date": str(log_doc.date) if log_doc.date else None,
                "follow_up_status": log_doc.follow_up_status,
                "log_html": log_doc.log or "",
                "log_author": log_author,
                "log_author_name": log_author_name_by_id.get(log_author) if log_author else None,
            },
            "inquiry": None,
            "follow_ups": follow_ups,
        }

    if reference_doctype == INQUIRY_DOCTYPE:
        inquiry_doc = frappe.get_doc(INQUIRY_DOCTYPE, reference_name)

        if not frappe.has_permission(INQUIRY_DOCTYPE, ptype="read", doc=inquiry_doc):
            frappe.throw(_("You are not permitted to view this inquiry."), frappe.PermissionError)

        mode = _resolve_mode(action_type, INQUIRY_DOCTYPE, inquiry_doc)
        subject_name = " ".join(
            filter(
                None,
                [
                    (inquiry_doc.first_name or "").strip(),
                    (inquiry_doc.last_name or "").strip(),
                ],
            )
        )

        return {
            "focus_item_id": focus_item_id,
            "action_type": action_type,
            "reference_doctype": INQUIRY_DOCTYPE,
            "reference_name": reference_name,
            "mode": mode,
            "log": None,
            "inquiry": {
                "name": inquiry_doc.name,
                "subject_name": subject_name or inquiry_doc.name,
                "first_name": inquiry_doc.first_name,
                "last_name": inquiry_doc.last_name,
                "email": inquiry_doc.email,
                "phone_number": inquiry_doc.phone_number,
                "school": inquiry_doc.school,
                "organization": inquiry_doc.organization,
                "type_of_inquiry": inquiry_doc.type_of_inquiry,
                "workflow_state": inquiry_doc.workflow_state,
                "assigned_to": inquiry_doc.assigned_to,
                "followup_due_on": str(inquiry_doc.followup_due_on) if inquiry_doc.followup_due_on else None,
                "sla_status": inquiry_doc.sla_status,
            },
            "follow_ups": [],
        }

    if reference_doctype == APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE:
        assignment_doc = frappe.get_doc(APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE, reference_name)
        assignment_row = assignment_doc.as_dict()
        user_roles = set(frappe.get_roles(frappe.session.user))

        if (assignment_doc.status or "").strip() != "Open":
            frappe.throw(_("This review assignment is no longer open."), frappe.ValidationError)

        if not _reviewer_matches_assignment(
            assignment_row,
            user=frappe.session.user,
            roles=user_roles,
        ):
            frappe.throw(_("You are not assigned to this review item."), frappe.PermissionError)

        student_applicant_row = (
            frappe.db.get_value(
                "Student Applicant",
                assignment_doc.student_applicant,
                [
                    "name",
                    "first_name",
                    "middle_name",
                    "last_name",
                    "organization",
                    "school",
                    "program_offering",
                    "application_status",
                ],
                as_dict=True,
            )
            or {}
        )

        preview = {}
        target_type = (assignment_doc.target_type or "").strip()
        if target_type == TARGET_DOCUMENT:
            document_row = frappe.db.sql(
                """
                select
                    d.name,
                    d.document_type,
                    d.document_label,
                    d.review_status,
                    d.review_notes,
                    ifnull(dt.document_type_name, '') as document_type_name,
                    ifnull(dt.code, '') as document_type_code
                from `tabApplicant Document` d
                left join `tabApplicant Document Type` dt
                  on dt.name = d.document_type
                where d.name = %(name)s
                """,
                {"name": assignment_doc.target_name},
                as_dict=True,
            )
            doc_row = document_row[0] if document_row else {}
            file_rows = frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": TARGET_DOCUMENT,
                    "attached_to_name": assignment_doc.target_name,
                },
                fields=["file_url", "file_name", "creation"],
                order_by="creation desc",
                limit_page_length=1,
            )
            file_row = file_rows[0] if file_rows else {}
            preview = {
                "document_type": doc_row.get("document_type"),
                "document_label": (
                    (doc_row.get("document_label") or "").strip()
                    or (doc_row.get("document_type_code") or "").strip()
                    or (doc_row.get("document_type_name") or "").strip()
                    or (doc_row.get("document_type") or "").strip()
                    or assignment_doc.target_name
                ),
                "review_status": doc_row.get("review_status"),
                "review_notes": doc_row.get("review_notes"),
                "file_url": file_row.get("file_url"),
                "file_name": file_row.get("file_name"),
                "uploaded_at": str(file_row.get("creation")) if file_row.get("creation") else None,
            }
        elif target_type == TARGET_HEALTH:
            health_row = (
                frappe.db.get_value(
                    TARGET_HEALTH,
                    assignment_doc.target_name,
                    [
                        "review_status",
                        "review_notes",
                        "applicant_health_declared_complete",
                        "applicant_health_declared_by",
                        "applicant_health_declared_on",
                    ],
                    as_dict=True,
                )
                or {}
            )
            preview = {
                "review_status": health_row.get("review_status"),
                "review_notes": health_row.get("review_notes"),
                "declared_complete": bool(health_row.get("applicant_health_declared_complete")),
                "declared_by": health_row.get("applicant_health_declared_by"),
                "declared_on": str(health_row.get("applicant_health_declared_on"))
                if health_row.get("applicant_health_declared_on")
                else None,
            }
        elif target_type == TARGET_APPLICATION:
            preview = {
                "application_status": student_applicant_row.get("application_status"),
            }

        previous_rows = frappe.get_all(
            APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
            filters={
                "target_type": assignment_doc.target_type,
                "target_name": assignment_doc.target_name,
                "status": "Done",
            },
            fields=["name", "assigned_to_user", "assigned_to_role", "decision", "notes", "decided_by", "decided_on"],
            order_by="decided_on desc, modified desc",
            limit_page_length=10,
        )
        user_name_map = _get_user_full_names(
            [row.get("assigned_to_user") for row in previous_rows if (row.get("assigned_to_user") or "").strip()]
            + [row.get("decided_by") for row in previous_rows if (row.get("decided_by") or "").strip()]
        )
        previous_reviews = []
        for row in previous_rows:
            reviewer_user = (row.get("assigned_to_user") or "").strip()
            reviewer_role = (row.get("assigned_to_role") or "").strip()
            decided_by = (row.get("decided_by") or "").strip()
            previous_reviews.append(
                {
                    "assignment": row.get("name"),
                    "reviewer": reviewer_role or user_name_map.get(reviewer_user) or reviewer_user or None,
                    "decision": row.get("decision"),
                    "notes": row.get("notes"),
                    "decided_by": user_name_map.get(decided_by) or decided_by or None,
                    "decided_on": str(row.get("decided_on")) if row.get("decided_on") else None,
                }
            )

        return {
            "focus_item_id": focus_item_id,
            "action_type": action_type,
            "reference_doctype": APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
            "reference_name": assignment_doc.name,
            "mode": "assignee",
            "log": None,
            "inquiry": None,
            "follow_ups": [],
            "review_assignment": {
                "name": assignment_doc.name,
                "target_type": assignment_doc.target_type,
                "target_name": assignment_doc.target_name,
                "student_applicant": assignment_doc.student_applicant,
                "applicant_name": _applicant_display_name_from_row(student_applicant_row),
                "organization": student_applicant_row.get("organization"),
                "school": student_applicant_row.get("school"),
                "program_offering": student_applicant_row.get("program_offering"),
                "assigned_to_user": assignment_doc.assigned_to_user,
                "assigned_to_role": assignment_doc.assigned_to_role,
                "source_event": assignment_doc.source_event,
                "decision_options": DECISION_OPTIONS_BY_TARGET.get(target_type, []),
                "preview": preview,
                "previous_reviews": previous_reviews,
            },
        }

    frappe.throw(
        _("Only Student Log, Inquiry, and Applicant Review Assignment focus items are supported."),
        frappe.ValidationError,
    )


# ---------------------------------------------------------------------
# Workflow action endpoints (Vue should call these, not frappe.client.*)
# ---------------------------------------------------------------------
def _require_login() -> str:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)
    return user


def _cache():
    return frappe.cache()


def _idempotency_key(user: str, focus_item_id: str, client_request_id: str, suffix: str | None = None) -> str:
    sfx = f":{suffix}" if suffix else ""
    return f"ifitwala_ed:focus:{user}:{focus_item_id}:{client_request_id}{sfx}"


def _lock_key(user: str, focus_item_id: str, suffix: str | None = None) -> str:
    sfx = f":{suffix}" if suffix else ""
    return f"ifitwala_ed:lock:focus:{user}:{focus_item_id}{sfx}"


@frappe.whitelist()
def submit_student_log_follow_up(
    focus_item_id: str,
    follow_up: str,
    client_request_id: str | None = None,
):
    """
    Submit a Student Log Follow Up as a Focus workflow action.

    Client (Vue) sends:
    - focus_item_id
    - follow_up
    - client_request_id (optional but recommended)

    Server guarantees:
    - focus_item_id belongs to session user
    - action_type is the submit action
    - doc-level permission enforced on the Student Log
    - log not Completed
    - idempotent against rapid double submits
    - creates + submits Student Log Follow Up (so your controller side effects run)
    """
    user = _require_login()

    focus_item_id = (focus_item_id or "").strip()
    follow_up = (follow_up or "").strip()
    client_request_id = (client_request_id or "").strip() or None

    if not focus_item_id:
        frappe.throw(_("Missing focus_item_id."))
    if not follow_up or len(follow_up) < 5:
        frappe.throw(_("Follow-up text is too short."))

    parsed = _parse_focus_item_id(focus_item_id)

    # Hard guard: focus item must belong to current user
    if parsed.get("user") != user:
        frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

    # Hard guard: must be Student Log submit action
    if parsed.get("reference_doctype") != STUDENT_LOG_DOCTYPE:
        frappe.throw(_("Invalid focus item reference."), frappe.ValidationError)

    action_type = parsed.get("action_type")
    if action_type != ACTION_STUDENT_LOG_SUBMIT:
        frappe.throw(_("This focus item is not a follow-up submission action."), frappe.PermissionError)

    log_name = parsed.get("reference_name")
    if not log_name:
        frappe.throw(_("Invalid focus item reference name."), frappe.ValidationError)

    # Load log ONCE (permission + state)
    log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, log_name)

    # Doc-level permission (authoritative)
    if not frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", doc=log_doc):
        frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

    # State guard
    if (log_doc.follow_up_status or "").lower() == "completed":
        frappe.throw(_("This Student Log is already <b>Completed</b>."))

    cache = _cache()

    # Idempotency (schema-free)
    if client_request_id:
        key = _idempotency_key(user, focus_item_id, client_request_id, "submit_follow_up")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "log_name": log_name,
                "follow_up_name": existing,
            }

    lock_name = _lock_key(user, focus_item_id, "submit_follow_up")
    with cache.lock(lock_name, timeout=10):
        # re-check inside lock
        if client_request_id:
            key = _idempotency_key(user, focus_item_id, client_request_id, "submit_follow_up")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "log_name": log_name,
                    "follow_up_name": existing,
                }

        # Create + submit follow-up: triggers your StudentLogFollowUp controller side effects
        fu = frappe.get_doc(
            {
                "doctype": FOLLOW_UP_DOCTYPE,
                "student_log": log_name,
                "follow_up": follow_up,
            }
        )
        fu.insert(ignore_permissions=False)
        fu.submit()

        if client_request_id:
            cache.set_value(key, fu.name, expires_in_sec=60 * 10)

        return {
            "ok": True,
            "idempotent": False,
            "status": "created",
            "log_name": log_name,
            "follow_up_name": fu.name,
        }


@frappe.whitelist()
def review_student_log_outcome(
    focus_item_id: str,
    decision: str,
    follow_up_person: str | None = None,
    client_request_id: str | None = None,
):
    """
    Author review action for "student_log.follow_up.review.decide".

    decisions:
    - "complete"  -> completes the parent log
    - "reassign"  -> reassigns follow_up_person (and ToDo) via Student Log controller

    Why focus_item_id:
    - user-bound, deterministic
    - prevents spoofing log_name/action_type
    """
    user = _require_login()

    focus_item_id = (focus_item_id or "").strip()
    decision = (decision or "").strip().lower()
    follow_up_person = (follow_up_person or "").strip() or None
    client_request_id = (client_request_id or "").strip() or None

    if not focus_item_id:
        frappe.throw(_("Missing focus_item_id."))

    if decision not in ("complete", "reassign"):
        frappe.throw(_("Invalid decision."), frappe.ValidationError)

    parsed = _parse_focus_item_id(focus_item_id)

    # Hard guard: focus item must belong to current user
    if parsed.get("user") != user:
        frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

    # Hard guard: must be Student Log review action
    if parsed.get("reference_doctype") != STUDENT_LOG_DOCTYPE:
        frappe.throw(_("Invalid focus item reference."), frappe.ValidationError)

    action_type = parsed.get("action_type")
    if action_type != ACTION_STUDENT_LOG_REVIEW:
        frappe.throw(_("This focus item is not a review action."), frappe.PermissionError)

    log_name = parsed.get("reference_name")
    if not log_name:
        frappe.throw(_("Invalid focus item reference name."), frappe.ValidationError)

    # Load log ONCE (permission + state)
    log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, log_name)

    # Doc-level permission (authoritative)
    if not frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", doc=log_doc):
        frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

    # Strong semantic guard: review outcome is for log owner
    if (log_doc.owner or "") != user:
        frappe.throw(_("Only the log author can review the outcome."), frappe.PermissionError)

    # State guard
    if (log_doc.follow_up_status or "").lower() == "completed":
        frappe.throw(_("This Student Log is already <b>Completed</b>."))

    if decision == "reassign" and not follow_up_person:
        frappe.throw(_("Missing follow_up_person."), frappe.ValidationError)

    cache = _cache()

    # Idempotency
    if client_request_id:
        key = _idempotency_key(user, focus_item_id, client_request_id, f"review_{decision}")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "log_name": log_name,
                "result": existing,
            }

    lock_name = _lock_key(user, focus_item_id, f"review_{decision}")
    with cache.lock(lock_name, timeout=10):
        # re-check inside lock
        if client_request_id:
            key = _idempotency_key(user, focus_item_id, client_request_id, f"review_{decision}")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "log_name": log_name,
                    "result": existing,
                }

        # Delegate to Student Log controller APIs (authoritative ToDo handling)
        from ifitwala_ed.students.doctype.student_log.student_log import assign_follow_up, complete_log

        if decision == "complete":
            complete_log(log_name=log_name)
            result = "completed"
        else:
            assign_follow_up(log_name=log_name, user=follow_up_person)
            result = f"reassigned:{follow_up_person}"

        if client_request_id:
            cache.set_value(key, result, expires_in_sec=60 * 10)

        return {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "log_name": log_name,
            "result": result,
        }


@frappe.whitelist()
def mark_inquiry_contacted(
    focus_item_id: str,
    complete_todo: int = 1,
    client_request_id: str | None = None,
):
    user = _require_login()

    focus_item_id = (focus_item_id or "").strip()
    client_request_id = (client_request_id or "").strip() or None
    complete_todo = frappe.utils.cint(complete_todo)

    if not focus_item_id:
        frappe.throw(_("Missing focus_item_id."))

    parsed = _parse_focus_item_id(focus_item_id)

    if parsed.get("user") != user:
        frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

    if parsed.get("reference_doctype") != INQUIRY_DOCTYPE:
        frappe.throw(_("Invalid focus item reference."), frappe.ValidationError)

    action_type = parsed.get("action_type")
    if action_type != ACTION_INQUIRY_FIRST_CONTACT:
        frappe.throw(_("This focus item is not an inquiry follow-up action."), frappe.PermissionError)

    inquiry_name = parsed.get("reference_name")
    if not inquiry_name:
        frappe.throw(_("Invalid focus item reference name."), frappe.ValidationError)

    cache = _cache()

    # Idempotency must short-circuit before state/assignee checks because
    # a successful first call mutates both workflow_state and assigned_to.
    if client_request_id:
        key = _idempotency_key(user, focus_item_id, client_request_id, "inquiry_mark_contacted")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "inquiry_name": inquiry_name,
                "result": existing,
            }

    inquiry_doc = frappe.get_doc(INQUIRY_DOCTYPE, inquiry_name)

    if not frappe.has_permission(INQUIRY_DOCTYPE, ptype="read", doc=inquiry_doc):
        frappe.throw(_("You are not permitted to view this inquiry."), frappe.PermissionError)

    current_state = (inquiry_doc.workflow_state or "").strip()
    if current_state == "Contacted":
        result = "contacted"
        if client_request_id:
            key = _idempotency_key(user, focus_item_id, client_request_id, "inquiry_mark_contacted")
            cache.set_value(key, result, expires_in_sec=60 * 10)
        return {
            "ok": True,
            "idempotent": True,
            "status": "already_processed",
            "inquiry_name": inquiry_name,
            "result": result,
        }

    if (inquiry_doc.assigned_to or "").strip() != user:
        frappe.throw(_("Only the assigned user can complete this inquiry follow-up."), frappe.PermissionError)

    if current_state != "Assigned":
        frappe.throw(_("This Inquiry is not in Assigned state."))

    lock_name = _lock_key(user, focus_item_id, "inquiry_mark_contacted")
    with cache.lock(lock_name, timeout=10):
        if client_request_id:
            key = _idempotency_key(user, focus_item_id, client_request_id, "inquiry_mark_contacted")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "inquiry_name": inquiry_name,
                    "result": existing,
                }

        inquiry_doc.mark_contacted(complete_todo=1 if complete_todo else 0)
        result = "contacted"

        if client_request_id:
            cache.set_value(key, result, expires_in_sec=60 * 10)

        return {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "inquiry_name": inquiry_name,
            "result": result,
        }


@frappe.whitelist()
def submit_applicant_review_assignment(
    assignment: str | None = None,
    decision: str | None = None,
    notes: str | None = None,
    focus_item_id: str | None = None,
    client_request_id: str | None = None,
):
    user = _require_login()
    user_roles = set(frappe.get_roles(user))

    decision = (decision or "").strip()
    notes = (notes or "").strip() or None
    assignment_name = (assignment or "").strip() or None
    focus_item_id = (focus_item_id or "").strip() or None
    client_request_id = (client_request_id or "").strip() or None

    if focus_item_id:
        parsed = _parse_focus_item_id(focus_item_id)
        if parsed.get("user") != user:
            frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)
        if parsed.get("reference_doctype") != APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE:
            frappe.throw(_("Invalid focus item reference."), frappe.ValidationError)
        if parsed.get("action_type") != ACTION_APPLICANT_REVIEW_SUBMIT:
            frappe.throw(_("This focus item is not an applicant review action."), frappe.PermissionError)
        if not assignment_name:
            assignment_name = (parsed.get("reference_name") or "").strip() or None

    if not assignment_name:
        frappe.throw(_("Missing assignment."))
    if not decision:
        frappe.throw(_("Decision is required."))

    cache = _cache()
    lock_target = focus_item_id or assignment_name

    if client_request_id:
        key = _idempotency_key(user, lock_target, client_request_id, "applicant_review_assignment_submit")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "assignment": assignment_name,
                "decision": existing,
            }

    lock_name = _lock_key(user, lock_target, "applicant_review_assignment_submit")
    with cache.lock(lock_name, timeout=10):
        if client_request_id:
            key = _idempotency_key(user, lock_target, client_request_id, "applicant_review_assignment_submit")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "assignment": assignment_name,
                    "decision": existing,
                }

        assignment_doc = frappe.get_doc(APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE, assignment_name)
        if not _reviewer_matches_assignment(assignment_doc.as_dict(), user=user, roles=user_roles):
            frappe.throw(_("You are not assigned to this review item."), frappe.PermissionError)

        if (assignment_doc.status or "").strip() == "Done":
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "assignment": assignment_doc.name,
                "decision": assignment_doc.decision,
            }

        if (assignment_doc.status or "").strip() != "Open":
            frappe.throw(_("This review assignment is not open."), frappe.ValidationError)

        complete_assignment_decision(
            assignment_doc=assignment_doc,
            decision=decision,
            notes=notes,
            decided_by=user,
        )

        if client_request_id:
            cache.set_value(key, decision, expires_in_sec=60 * 10)

        frappe.publish_realtime(
            event="focus:invalidate",
            message={
                "assignment": assignment_doc.name,
                "target_type": assignment_doc.target_type,
                "target_name": assignment_doc.target_name,
                "decided_by": user,
                "decided_on": str(now_datetime()),
            },
            user=user,
        )

        return {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "assignment": assignment_doc.name,
            "target_type": assignment_doc.target_type,
            "target_name": assignment_doc.target_name,
            "decision": decision,
        }
