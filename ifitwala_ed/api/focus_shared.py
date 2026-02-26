# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus_shared.py

import frappe
from frappe import _

from ifitwala_ed.admission.applicant_review_workflow import (
    ASSIGNMENT_DOCTYPE,
    TARGET_DOCUMENT,
    TARGET_HEALTH,
)
from ifitwala_ed.api.policy_signature import get_active_employee_for_user

STUDENT_LOG_DOCTYPE = "Student Log"
FOLLOW_UP_DOCTYPE = "Student Log Follow Up"
INQUIRY_DOCTYPE = "Inquiry"
APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE = ASSIGNMENT_DOCTYPE
POLICY_VERSION_DOCTYPE = "Policy Version"

ACTION_STUDENT_LOG_SUBMIT = "student_log.follow_up.act.submit"
ACTION_STUDENT_LOG_REVIEW = "student_log.follow_up.review.decide"
ACTION_INQUIRY_FIRST_CONTACT = "inquiry.follow_up.act.first_contact"
ACTION_APPLICANT_REVIEW_SUBMIT = "applicant_review.assignment.decide"
ACTION_POLICY_STAFF_SIGN = "policy_acknowledgement.staff.sign"

# Focus action types (v1)
ACTION_MODE = {
    ACTION_STUDENT_LOG_SUBMIT: "assignee",
    ACTION_STUDENT_LOG_REVIEW: "author",
    ACTION_INQUIRY_FIRST_CONTACT: "assignee",
    ACTION_APPLICANT_REVIEW_SUBMIT: "assignee",
    ACTION_POLICY_STAFF_SIGN: "assignee",
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
    if reference_doctype == POLICY_VERSION_DOCTYPE:
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


def _active_employee_row(user: str) -> dict | None:
    return get_active_employee_for_user(user)


def _reviewer_matches_assignment(row: dict, *, user: str, roles: set[str]) -> bool:
    assigned_to_user = (row.get("assigned_to_user") or "").strip()
    assigned_to_role = (row.get("assigned_to_role") or "").strip()
    if assigned_to_user:
        return assigned_to_user == user
    if assigned_to_role:
        return assigned_to_role in roles
    return False


def _enabled_users_for_role(role: str | None) -> list[dict]:
    role_name = (role or "").strip()
    if not role_name:
        return []
    return frappe.db.sql(
        """
        select
            u.name,
            ifnull(nullif(trim(u.full_name), ''), u.name) as full_name
        from `tabUser` u
        join `tabHas Role` hr
          on hr.parent = u.name
        where hr.role = %(role)s
          and u.enabled = 1
        order by full_name asc, u.name asc
        """,
        {"role": role_name},
        as_dict=True,
    )


def _resolve_review_assignment_name(*, user: str, assignment: str | None, focus_item_id: str | None) -> str:
    assignment_name = (assignment or "").strip() or None
    focus_item = (focus_item_id or "").strip() or None

    if focus_item:
        parsed = _parse_focus_item_id(focus_item)
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
    return assignment_name


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


def _normalize_signature_name(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = (str(value or "").strip()).lower()
    return text in {"1", "true", "yes", "y", "on"}
