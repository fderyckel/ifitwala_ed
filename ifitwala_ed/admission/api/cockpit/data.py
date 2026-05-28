# ifitwala_ed/admission/api/cockpit/data.py

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, get_datetime

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.admission.api.cockpit.access import _ensure_cockpit_access, _get_roles_for_user, _to_text
from ifitwala_ed.admission.api.cockpit.blockers import BLOCKER_LABELS, _build_blockers
from ifitwala_ed.admission.api.cockpit.cache import COCKPIT_CACHE_TTL_SECONDS, _cache_key_for_payload
from ifitwala_ed.admission.api.cockpit.enrollment_plan import (
    _build_applicant_enrollment_plan_state,
    _empty_deposit_state,
)
from ifitwala_ed.admission.api.cockpit.readiness import _build_readiness_batch, _empty_readiness_snapshot
from ifitwala_ed.admission.api.cockpit.urls import _doc_url
from ifitwala_ed.admission.api.communication.summaries import get_admissions_thread_summaries_for_applicants
from ifitwala_ed.utilities.employee_utils import get_schools_for_organization_scope
from ifitwala_ed.utilities.school_tree import get_descendant_schools

TERMINAL_STATUSES = {"Rejected", "Withdrawn", "Promoted"}
KANBAN_COLUMNS = [
    ("draft", "Draft"),
    ("in_progress", "In Progress"),
    ("submitted", "Submitted"),
    ("under_review", "Under Review"),
    ("awaiting_decision", "Awaiting Decision"),
    ("accepted_pending_promotion", "Accepted (Pending Promotion)"),
]


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_str_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_to_text(value)] if _to_text(value) else []
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            text = _to_text(item)
            if text:
                out.append(text)
        return out
    return []


def _display_name(row: dict) -> str:
    parts = [
        _to_text(row.get("first_name")),
        _to_text(row.get("middle_name")),
        _to_text(row.get("last_name")),
    ]
    full_name = " ".join(part for part in parts if part).strip()
    return full_name or _to_text(row.get("name"))


def _get_descendant_organizations(root_org: str) -> list[str]:
    root_org = _to_text(root_org)
    if not root_org:
        return []

    bounds = frappe.db.get_value("Organization", root_org, ["lft", "rgt"], as_dict=True)
    if not bounds:
        return []

    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabOrganization`
        WHERE lft >= %(lft)s AND rgt <= %(rgt)s
        ORDER BY lft ASC, name ASC
        """,
        {"lft": bounds.lft, "rgt": bounds.rgt},
        as_list=True,
    )
    return [row[0] for row in rows]


def _resolve_stage(application_status: str, ready: bool) -> str:
    status = _to_text(application_status)
    if status == "Draft":
        return "draft"
    if status in {"Invited", "In Progress", "Missing Info"}:
        return "in_progress"
    if status == "Submitted":
        return "submitted"
    if status == "Under Review":
        return "awaiting_decision" if ready else "under_review"
    if status == "Approved":
        return "accepted_pending_promotion"
    return "in_progress"


def _interview_sort_key(row: dict) -> tuple:
    interview_start = row.get("interview_start")
    if interview_start:
        try:
            return (get_datetime(interview_start), get_datetime(row.get("modified") or interview_start))
        except Exception:
            pass

    interview_date = _to_text(row.get("interview_date"))
    if interview_date:
        date_value = f"{interview_date} 00:00:00"
        try:
            return (get_datetime(date_value), get_datetime(row.get("modified") or date_value))
        except Exception:
            pass

    modified_value = row.get("modified")
    if modified_value:
        try:
            modified_dt = get_datetime(modified_value)
            return (modified_dt, modified_dt)
        except Exception:
            pass

    fallback = get_datetime("1900-01-01 00:00:00")
    return (fallback, fallback)


def _interview_feedback_status_label(submitted_count: int, expected_count: int) -> str:
    if expected_count <= 0:
        return _("No interviewers assigned")
    return _("{submitted_count}/{expected_count} submitted").format(
        submitted_count=submitted_count,
        expected_count=expected_count,
    )


def _build_interview_state(applicant_names: list[str]) -> dict[str, dict]:
    normalized_applicants = list(dict.fromkeys(name for name in applicant_names if _to_text(name)))
    interview_state_by_applicant = {
        applicant_name: {"count": 0, "latest": None} for applicant_name in normalized_applicants
    }

    if not normalized_applicants or not frappe.db.table_exists("Applicant Interview"):
        return interview_state_by_applicant

    interview_rows = frappe.get_all(
        "Applicant Interview",
        filters={"student_applicant": ["in", normalized_applicants]},
        fields=[
            "name",
            "student_applicant",
            "interview_type",
            "interview_date",
            "interview_start",
            "interview_end",
            "mode",
            "modified",
        ],
        order_by="modified desc",
    )

    counts_by_applicant: dict[str, int] = defaultdict(int)
    latest_by_applicant: dict[str, dict] = {}

    for row in interview_rows:
        applicant_name = _to_text(row.get("student_applicant"))
        if not applicant_name:
            continue

        counts_by_applicant[applicant_name] += 1
        current_latest = latest_by_applicant.get(applicant_name)
        if current_latest is None or _interview_sort_key(row) > _interview_sort_key(current_latest):
            latest_by_applicant[applicant_name] = row

    latest_interview_names = [row.get("name") for row in latest_by_applicant.values() if _to_text(row.get("name"))]

    interviewer_rows: list[dict] = []
    if latest_interview_names and frappe.db.table_exists("Applicant Interviewer"):
        interviewer_rows = frappe.get_all(
            "Applicant Interviewer",
            filters={
                "parent": ["in", latest_interview_names],
                "parenttype": "Applicant Interview",
                "parentfield": "interviewers",
            },
            fields=["parent", "interviewer", "idx"],
            order_by="parent asc, idx asc",
        )

    interviewer_ids = sorted(
        {_to_text(row.get("interviewer")) for row in interviewer_rows if _to_text(row.get("interviewer"))}
    )
    interviewer_label_by_user: dict[str, str] = {}
    if interviewer_ids:
        user_rows = frappe.get_all(
            "User",
            filters={"name": ["in", interviewer_ids]},
            fields=["name", "full_name"],
        )
        for user_row in user_rows:
            user_id = _to_text(user_row.get("name"))
            if not user_id:
                continue
            interviewer_label_by_user[user_id] = _to_text(user_row.get("full_name")) or user_id

    interviewers_by_interview: dict[str, list[dict[str, str]]] = {}
    for interviewer_row in interviewer_rows:
        interview_name = _to_text(interviewer_row.get("parent"))
        interviewer_user = _to_text(interviewer_row.get("interviewer"))
        if not interview_name or not interviewer_user:
            continue
        interviewers_by_interview.setdefault(interview_name, []).append(
            {
                "user": interviewer_user,
                "label": interviewer_label_by_user.get(interviewer_user) or interviewer_user,
            }
        )

    feedback_rows: list[dict] = []
    if latest_interview_names and frappe.db.table_exists("Applicant Interview Feedback"):
        feedback_rows = frappe.get_all(
            "Applicant Interview Feedback",
            filters={
                "applicant_interview": ["in", latest_interview_names],
                "feedback_status": "Submitted",
            },
            fields=["applicant_interview", "interviewer_user"],
        )

    submitted_users_by_interview: dict[str, set[str]] = {}
    for feedback_row in feedback_rows:
        interview_name = _to_text(feedback_row.get("applicant_interview"))
        interviewer_user = _to_text(feedback_row.get("interviewer_user"))
        if not interview_name or not interviewer_user:
            continue
        submitted_users_by_interview.setdefault(interview_name, set()).add(interviewer_user)

    for applicant_name in normalized_applicants:
        count = counts_by_applicant.get(applicant_name, 0)
        latest_row = latest_by_applicant.get(applicant_name)
        latest_payload = None

        if latest_row:
            interview_name = _to_text(latest_row.get("name"))
            interviewers = list(interviewers_by_interview.get(interview_name, []))
            assigned_users = {row.get("user") for row in interviewers if row.get("user")}
            submitted_users = submitted_users_by_interview.get(interview_name, set())
            submitted_count = len(assigned_users & submitted_users)
            expected_count = len(assigned_users)

            latest_payload = {
                "name": interview_name,
                "open_url": _doc_url("Applicant Interview", interview_name),
                "interview_type": latest_row.get("interview_type"),
                "interview_date": latest_row.get("interview_date"),
                "interview_start": latest_row.get("interview_start"),
                "interview_end": latest_row.get("interview_end"),
                "mode": latest_row.get("mode"),
                "interviewer_labels": [row.get("label") for row in interviewers if row.get("label")],
                "feedback_submitted_count": submitted_count,
                "feedback_expected_count": expected_count,
                "feedback_complete": bool(expected_count and submitted_count >= expected_count),
                "feedback_status_label": _interview_feedback_status_label(submitted_count, expected_count),
            }

        interview_state_by_applicant[applicant_name] = {
            "count": count,
            "latest": latest_payload,
        }

    return interview_state_by_applicant


def _empty_payload(organizations: list[str], schools: list[str], *, can_create_inquiry: bool = False) -> dict:
    return {
        "config": {
            "organizations": organizations,
            "schools": schools,
            "can_create_inquiry": bool(can_create_inquiry),
            "columns": [{"id": col_id, "title": title} for col_id, title in KANBAN_COLUMNS],
        },
        "counts": {
            "active_applications": 0,
            "blocked_applications": 0,
            "ready_for_decision": 0,
            "accepted_pending_promotion": 0,
            "my_open_assignments": 0,
            "unread_applicant_replies": 0,
        },
        "blockers": [],
        "columns": [{"id": col_id, "title": title, "items": []} for col_id, title in KANBAN_COLUMNS],
        "generated_at": frappe.utils.now_datetime(),
    }


def get_admissions_cockpit_data_impl(filters=None):
    user = _ensure_cockpit_access()
    user_roles = _get_roles_for_user(user)
    can_create_inquiry = (
        user == "Administrator" or "System Manager" in user_roles or bool(user_roles & ADMISSIONS_ROLES)
    )

    filters = frappe.parse_json(filters) or {}
    organization_filter = _to_text(filters.get("organization"))
    school_filter = _to_text(filters.get("school"))
    include_terminal = bool(cint(filters.get("include_terminal")))
    assigned_to_me_only = bool(cint(filters.get("assigned_to_me")))
    status_filters = sorted(_as_str_list(filters.get("application_statuses")))

    limit = _to_int(filters.get("limit"), 120)
    if limit < 1:
        limit = 1
    if limit > 250:
        limit = 250

    cache_payload = {
        "user": user,
        "organization": organization_filter,
        "school": school_filter,
        "include_terminal": int(include_terminal),
        "assigned_to_me": int(assigned_to_me_only),
        "application_statuses": status_filters,
        "limit": limit,
    }
    cache = frappe.cache()
    cache_key = _cache_key_for_payload(cache_payload)
    cached_payload = cache.get_value(cache_key)
    if cached_payload:
        try:
            parsed = frappe.parse_json(cached_payload)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    organization_scope = _get_descendant_organizations(organization_filter) if organization_filter else []
    if organization_filter and not organization_scope:
        response = _empty_payload([], [], can_create_inquiry=can_create_inquiry)
        cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
        return response

    all_organizations = [
        row[0] for row in frappe.db.sql("SELECT name FROM `tabOrganization` ORDER BY lft ASC, name ASC", as_list=True)
    ]

    school_scope = get_descendant_schools(school_filter) if school_filter else []
    if school_filter and not school_scope:
        response = _empty_payload(all_organizations, [], can_create_inquiry=can_create_inquiry)
        cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
        return response

    if organization_scope:
        all_schools = get_schools_for_organization_scope(organization_scope)
    else:
        schools = frappe.get_all("School", fields=["name"], order_by="lft asc, name asc")
        all_schools = [row.get("name") for row in schools if row.get("name")]

    applicant_filters: dict = {}
    if organization_scope:
        applicant_filters["organization"] = ["in", organization_scope]
    if school_scope:
        applicant_filters["school"] = ["in", school_scope]
    if status_filters:
        applicant_filters["application_status"] = ["in", status_filters]
    elif not include_terminal:
        applicant_filters["application_status"] = ["not in", sorted(TERMINAL_STATUSES)]

    fetch_limit = limit * 4 if assigned_to_me_only else limit
    if fetch_limit > 600:
        fetch_limit = 600

    applicant_rows = frappe.get_all(
        "Student Applicant",
        filters=applicant_filters,
        fields=[
            "name",
            "first_name",
            "middle_name",
            "last_name",
            "application_status",
            "organization",
            "school",
            "program_offering",
            "student",
            "modified",
            "student_date_of_birth",
            "student_gender",
            "student_mobile_number",
            "student_first_language",
            "student_nationality",
            "residency_status",
            "applicant_user",
        ],
        order_by="modified desc",
        limit=fetch_limit,
    )

    if not applicant_rows:
        response = _empty_payload(all_organizations, all_schools)
        cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
        return response

    applicant_names = [_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))]
    assignment_rows = frappe.get_all(
        "Applicant Review Assignment",
        filters={
            "status": "Open",
            "student_applicant": ["in", applicant_names],
        },
        fields=[
            "name",
            "student_applicant",
            "target_type",
            "target_name",
            "assigned_to_user",
            "assigned_to_role",
            "modified",
        ],
        order_by="modified desc",
        limit=10000,
    )

    assignment_summary = {name: {"open_total": 0, "open_for_me": 0} for name in applicant_names}
    first_open_assignment_by_applicant: dict[str, dict] = {}
    for row_assignment in assignment_rows:
        applicant_name = _to_text(row_assignment.get("student_applicant"))
        if not applicant_name or applicant_name not in assignment_summary:
            continue

        assignment_summary[applicant_name]["open_total"] += 1
        if applicant_name not in first_open_assignment_by_applicant:
            first_open_assignment_by_applicant[applicant_name] = row_assignment

        assigned_user = _to_text(row_assignment.get("assigned_to_user"))
        assigned_role = _to_text(row_assignment.get("assigned_to_role"))
        if assigned_user and assigned_user == user:
            assignment_summary[applicant_name]["open_for_me"] += 1
            continue
        if assigned_role and assigned_role in user_roles:
            assignment_summary[applicant_name]["open_for_me"] += 1

    if assigned_to_me_only:
        applicant_rows = [
            row
            for row in applicant_rows
            if assignment_summary.get(_to_text(row.get("name")), {}).get("open_for_me", 0) > 0
        ]

    applicant_rows = applicant_rows[:limit]
    if not applicant_rows:
        response = _empty_payload(all_organizations, all_schools)
        cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
        return response

    readiness_by_applicant: dict[str, dict]
    try:
        readiness_by_applicant = _build_readiness_batch(applicant_rows)
    except Exception:
        frappe.logger("admissions_cockpit", allow_site=True).exception("Admissions cockpit readiness batch failed.")
        readiness_by_applicant = {}

    comms_summary_by_applicant: dict[str, dict]
    try:
        comms_summary_by_applicant = get_admissions_thread_summaries_for_applicants(
            applicant_rows=applicant_rows,
            user=user,
        )
    except Exception:
        frappe.logger("admissions_cockpit", allow_site=True).exception(
            "Admissions cockpit communication summary failed."
        )
        comms_summary_by_applicant = {}

    interview_summary_by_applicant: dict[str, dict]
    try:
        interview_summary_by_applicant = _build_interview_state(
            [_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))]
        )
    except Exception:
        frappe.logger("admissions_cockpit", allow_site=True).exception("Admissions cockpit interview summary failed.")
        interview_summary_by_applicant = {}

    enrollment_plan_state_by_applicant: dict[str, dict]
    try:
        enrollment_plan_state_by_applicant = _build_applicant_enrollment_plan_state(
            [_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))]
        )
    except Exception:
        frappe.logger("admissions_cockpit", allow_site=True).exception(
            "Admissions cockpit enrollment plan summary failed."
        )
        enrollment_plan_state_by_applicant = {}

    columns = {col_id: {"id": col_id, "title": title, "items": []} for col_id, title in KANBAN_COLUMNS}
    blocker_counts = {key: 0 for key in BLOCKER_LABELS}
    counts = {
        "active_applications": 0,
        "blocked_applications": 0,
        "ready_for_decision": 0,
        "accepted_pending_promotion": 0,
        "my_open_assignments": 0,
        "unread_applicant_replies": 0,
    }

    for row in applicant_rows:
        applicant_name = _to_text(row.get("name"))
        if not applicant_name:
            continue

        assignee_stats = assignment_summary.get(applicant_name, {"open_total": 0, "open_for_me": 0})
        snapshot = readiness_by_applicant.get(applicant_name) or _empty_readiness_snapshot()
        comms_summary = comms_summary_by_applicant.get(applicant_name) or {}
        recommendations = snapshot.get("recommendations") or {}
        enrollment_plan = enrollment_plan_state_by_applicant.get(applicant_name) or {
            "has_plan": False,
            "name": None,
            "status": None,
            "open_url": None,
            "offer_expires_on": None,
            "program_enrollment_request": None,
            "program_enrollment_request_url": None,
            "can_send_offer": False,
            "can_hydrate_request": False,
            "deposit": _empty_deposit_state(),
        }

        ready = bool(snapshot.get("ready"))
        stage = _resolve_stage(_to_text(row.get("application_status")), ready)

        blockers = _build_blockers(
            snapshot=snapshot,
            application_status=_to_text(row.get("application_status")),
            open_assignments=assignee_stats.get("open_total", 0),
            applicant_name=applicant_name,
            first_open_assignment=first_open_assignment_by_applicant.get(applicant_name),
        )
        deposit_state = enrollment_plan.get("deposit") or _empty_deposit_state()
        deposit_blocker_label = _to_text(deposit_state.get("blocker_label"))
        if deposit_blocker_label and not bool(deposit_state.get("is_paid")):
            blockers.append(
                {
                    "kind": "deposit_not_ready",
                    "label": deposit_blocker_label,
                    "target_doctype": "Applicant Enrollment Plan",
                    "target_name": enrollment_plan.get("name"),
                    "target_url": enrollment_plan.get("open_url"),
                    "target_label": enrollment_plan.get("name"),
                }
            )

        for blocker in blockers:
            kind = blocker.get("kind")
            if kind in blocker_counts:
                blocker_counts[kind] += 1

        if blockers:
            counts["blocked_applications"] += 1

        if stage == "awaiting_decision":
            counts["ready_for_decision"] += 1
        if stage == "accepted_pending_promotion":
            counts["accepted_pending_promotion"] += 1

        counts["active_applications"] += 1
        counts["my_open_assignments"] += assignee_stats.get("open_for_me", 0)
        if bool(comms_summary.get("needs_reply")):
            counts["unread_applicant_replies"] += cint(comms_summary.get("unread_count") or 0)

        health_payload = snapshot.get("health") or {}
        health_required_for_approval = bool(health_payload.get("required_for_approval", True))
        health_ok_for_approval = bool(health_payload.get("ok")) if health_required_for_approval else True

        card = {
            "name": applicant_name,
            "display_name": _display_name(row),
            "application_status": _to_text(row.get("application_status")),
            "organization": _to_text(row.get("organization")),
            "school": _to_text(row.get("school")),
            "program_offering": _to_text(row.get("program_offering")),
            "open_assignments": assignee_stats.get("open_total", 0),
            "open_assignments_for_me": assignee_stats.get("open_for_me", 0),
            "ready": ready,
            "readiness": {
                "profile_ok": bool((snapshot.get("profile") or {}).get("ok")),
                "policies_ok": bool((snapshot.get("policies") or {}).get("ok")),
                "documents_ok": bool((snapshot.get("documents") or {}).get("ok")),
                "health_ok": health_ok_for_approval,
                "health_required_for_approval": health_required_for_approval,
                "recommendations_ok": bool(recommendations.get("ok")),
            },
            "recommendations": {
                "required_total": cint(recommendations.get("required_total") or 0),
                "received_total": cint(recommendations.get("received_total") or 0),
                "requested_total": cint(recommendations.get("requested_total") or 0),
                "pending_review_count": cint(recommendations.get("pending_review_count") or 0),
                "latest_submitted_on": recommendations.get("latest_submitted_on"),
                "first_pending_review": recommendations.get("first_pending_review"),
            },
            "top_blockers": [
                {
                    "kind": row_blocker.get("kind"),
                    "label": row_blocker.get("label"),
                    "target_doctype": row_blocker.get("target_doctype"),
                    "target_name": row_blocker.get("target_name"),
                    "target_url": row_blocker.get("target_url"),
                    "target_label": row_blocker.get("target_label"),
                    "workspace_mode": row_blocker.get("workspace_mode"),
                    "workspace_student_applicant": row_blocker.get("workspace_student_applicant"),
                    "workspace_document_type": row_blocker.get("workspace_document_type"),
                    "workspace_applicant_document": row_blocker.get("workspace_applicant_document"),
                    "workspace_document_item": row_blocker.get("workspace_document_item"),
                }
                for row_blocker in blockers[:2]
                if row_blocker.get("label")
            ],
            "blockers": blockers,
            "issues": [str(item) for item in (snapshot.get("issues") or [])],
            "open_url": _doc_url("Student Applicant", applicant_name),
            "aep": enrollment_plan,
            "interviews": interview_summary_by_applicant.get(applicant_name)
            or {
                "count": 0,
                "latest": None,
            },
            "comms": {
                "thread_name": _to_text(comms_summary.get("thread_name")) or None,
                "unread_count": cint(comms_summary.get("unread_count") or 0),
                "last_message_at": comms_summary.get("last_message_at"),
                "last_message_preview": _to_text(comms_summary.get("last_message_preview")),
                "last_message_from": _to_text(comms_summary.get("last_message_from")) or None,
                "needs_reply": bool(comms_summary.get("needs_reply")),
            },
        }

        if stage in columns:
            columns[stage]["items"].append(card)

    blocker_tiles = []
    for kind, label in BLOCKER_LABELS.items():
        count = blocker_counts.get(kind, 0)
        if count <= 0:
            continue
        blocker_tiles.append({"kind": kind, "label": label, "count": count})

    blocker_tiles.sort(key=lambda row_blocker: row_blocker.get("count", 0), reverse=True)

    response = {
        "config": {
            "organizations": all_organizations,
            "schools": all_schools,
            "can_create_inquiry": can_create_inquiry,
            "columns": [{"id": col_id, "title": title} for col_id, title in KANBAN_COLUMNS],
        },
        "counts": counts,
        "blockers": blocker_tiles,
        "columns": [columns[col_id] for col_id, _ in KANBAN_COLUMNS],
        "generated_at": frappe.utils.now_datetime(),
    }

    cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
    return response
