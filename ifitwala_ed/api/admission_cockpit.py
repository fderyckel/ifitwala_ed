# ifitwala_ed/api/admission_cockpit.py

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, nowdate

from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
)
from ifitwala_ed.admission.applicant_document_readiness import build_document_review_payload_batch
from ifitwala_ed.admission.doctype.student_applicant.student_applicant import STUDENT_PROFILE_REQUIRED_FIELD_LABELS
from ifitwala_ed.api.admissions_communication import get_admissions_thread_summaries_for_applicants
from ifitwala_ed.api.recommendation_intake import get_recommendation_status_batch_for_applicants
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import (
    ADMISSIONS_POLICY_MODE_FAMILY,
    ADMISSIONS_POLICY_MODE_OPTIONAL,
    ensure_policy_applies_to_storage,
    get_policy_admissions_acknowledgement_mode,
    institutional_policy_db_has_column,
    policy_applies_to_filter_sql,
)
from ifitwala_ed.utilities.employee_utils import get_schools_for_organization_scope
from ifitwala_ed.utilities.school_tree import get_descendant_schools

ALLOWED_COCKPIT_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager", "Administrator"}
TERMINAL_STATUSES = {"Rejected", "Withdrawn", "Promoted"}
COCKPIT_CACHE_TTL_SECONDS = 120
COCKPIT_CACHE_PREFIX = "admissions:cockpit:v2:"

KANBAN_COLUMNS = [
    ("draft", "Draft"),
    ("in_progress", "In Progress"),
    ("submitted", "Submitted"),
    ("under_review", "Under Review"),
    ("awaiting_decision", "Awaiting Decision"),
    ("accepted_pending_promotion", "Accepted (Pending Promotion)"),
]

BLOCKER_LABELS = {
    "missing_policies": "Missing Policies",
    "missing_documents": "Requirements Awaiting Submission",
    "documents_unapproved": "Requirements Needing Attention",
    "health_not_cleared": "Health Not Cleared",
    "profile_incomplete": "Profile Incomplete",
    "no_reviewer_assigned": "No Reviewer Assigned",
    "deposit_not_ready": "Deposit Not Ready",
}

INVALID_SESSION_USERS = {"guest", "none", "null", "undefined"}


def _ensure_cockpit_access(user: str | None = None) -> str:
    resolved_user = _to_text(user or frappe.session.user)
    if not resolved_user or resolved_user.lower() in INVALID_SESSION_USERS:
        frappe.throw(_("You need to sign in to access Admissions Cockpit."), frappe.PermissionError)

    roles = _get_roles_for_user(resolved_user)
    if roles & ALLOWED_COCKPIT_ROLES:
        return resolved_user

    frappe.throw(_("You do not have permission to access Admissions Cockpit."), frappe.PermissionError)
    return resolved_user


def _to_text(value) -> str:
    return str(value or "").strip()


def _get_roles_for_user(user: str) -> set[str]:
    try:
        return set(frappe.get_roles(user))
    except Exception as exc:
        message = _to_text(exc).lower()
        if "not found" in message and _to_text(user).lower() in INVALID_SESSION_USERS:
            frappe.throw(_("You need to sign in to access Admissions Cockpit."), frappe.PermissionError)
        raise


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


def _value_present(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(str(value).strip())


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


def _desk_route_slug(doctype: str) -> str:
    return frappe.scrub(doctype).replace("_", "-")


def _doc_url(doctype: str, name: str) -> str:
    return f"/desk/{_desk_route_slug(doctype)}/{quote(_to_text(name), safe='')}"


def _new_doc_url(doctype: str, params: dict[str, str] | None = None) -> str:
    slug = _desk_route_slug(doctype)
    base = f"/desk/{slug}/new-{slug}-1"
    if not params:
        return base

    query = "&".join(
        f"{quote(_to_text(key), safe='')}={quote(_to_text(value), safe='')}"
        for key, value in params.items()
        if _to_text(key) and _to_text(value)
    )
    if not query:
        return base
    return f"{base}?{query}"


def _target(
    *,
    doctype: str,
    name: str | None = None,
    target_label: str,
    params: dict[str, str] | None = None,
    is_new: bool = False,
) -> dict:
    if is_new:
        url = _new_doc_url(doctype, params=params)
    elif name:
        url = _doc_url(doctype, name)
    else:
        url = f"/desk/{_desk_route_slug(doctype)}"

    return {
        "target_doctype": doctype,
        "target_name": _to_text(name),
        "target_url": url,
        "target_label": target_label,
    }


def _applicant_workspace_target(
    *,
    applicant_name: str,
    target_label: str,
    document_type: str | None = None,
    applicant_document: str | None = None,
    document_item: str | None = None,
) -> dict:
    target = _target(
        doctype="Student Applicant",
        name=applicant_name,
        target_label=target_label,
    )
    target.update(
        {
            "workspace_mode": "applicant",
            "workspace_student_applicant": applicant_name,
            "workspace_document_type": _to_text(document_type) or None,
            "workspace_applicant_document": _to_text(applicant_document) or None,
            "workspace_document_item": _to_text(document_item) or None,
        }
    )
    return target


def _empty_readiness_snapshot() -> dict:
    return {
        "ready": False,
        "issues": [_("Readiness data unavailable")],
        "policies": {"ok": False, "missing": [], "required": [], "missing_rows": []},
        "documents": {
            "ok": False,
            "missing": [],
            "unapproved": [],
            "required": [],
            "missing_rows": [],
            "unapproved_rows": [],
        },
        "health": {
            "ok": False,
            "required_for_approval": True,
            "status": "missing",
            "profile_name": None,
            "review_status": None,
            "reviewed_by": None,
            "reviewed_on": None,
            "declared_complete": False,
            "declared_by": None,
            "declared_on": None,
        },
        "profile": {"ok": False, "missing": [], "required": []},
        "recommendations": {
            "ok": True,
            "required_total": 0,
            "received_total": 0,
            "requested_total": 0,
            "missing": [],
            "rows": [],
            "state": "optional",
            "counts": {},
            "review_rows": [],
            "pending_review_count": 0,
            "first_pending_review": None,
            "latest_submitted_on": None,
        },
    }


def invalidate_admissions_cockpit_cache() -> None:
    cache = frappe.cache()
    get_keys = getattr(cache, "get_keys", None)
    if not callable(get_keys):
        return

    for key in get_keys(f"{COCKPIT_CACHE_PREFIX}*"):
        cache.delete_value(key)


def _build_profile_state(applicant_row: dict) -> dict:
    missing_labels: list[str] = []
    required_labels: list[str] = []

    for fieldname, label in STUDENT_PROFILE_REQUIRED_FIELD_LABELS:
        required_labels.append(label)
        if not _value_present(applicant_row.get(fieldname)):
            missing_labels.append(label)

    return {
        "ok": not missing_labels,
        "missing": missing_labels,
        "required": required_labels,
    }


def _build_health_state(applicant_names: list[str]) -> dict[str, dict]:
    health_state_by_applicant: dict[str, dict] = {}

    if not applicant_names:
        return health_state_by_applicant

    rows = frappe.get_all(
        "Applicant Health Profile",
        filters={"student_applicant": ["in", applicant_names]},
        fields=[
            "name",
            "student_applicant",
            "review_status",
            "reviewed_by",
            "reviewed_on",
            "applicant_health_declared_complete",
            "applicant_health_declared_by",
            "applicant_health_declared_on",
            "modified",
        ],
        order_by="modified desc",
        limit=10000,
    )

    latest_by_applicant: dict[str, dict] = {}
    for row in rows:
        applicant_name = _to_text(row.get("student_applicant"))
        if not applicant_name or applicant_name in latest_by_applicant:
            continue
        latest_by_applicant[applicant_name] = row

    for applicant_name in applicant_names:
        profile_row = latest_by_applicant.get(applicant_name)
        if not profile_row:
            health_state_by_applicant[applicant_name] = {
                "ok": False,
                "required_for_approval": True,
                "status": "missing",
                "profile_name": None,
                "review_status": None,
                "reviewed_by": None,
                "reviewed_on": None,
                "declared_complete": False,
                "declared_by": None,
                "declared_on": None,
            }
            continue

        review_status = _to_text(profile_row.get("review_status"))
        if review_status == "Cleared":
            status = "complete"
            is_ok = True
        elif review_status == "Needs Follow-Up":
            status = "needs_follow_up"
            is_ok = False
        else:
            status = "pending"
            is_ok = False

        health_state_by_applicant[applicant_name] = {
            "ok": is_ok,
            "required_for_approval": True,
            "status": status,
            "profile_name": _to_text(profile_row.get("name")) or None,
            "review_status": review_status or None,
            "reviewed_by": _to_text(profile_row.get("reviewed_by")) or None,
            "reviewed_on": profile_row.get("reviewed_on"),
            "declared_complete": bool(cint(profile_row.get("applicant_health_declared_complete"))),
            "declared_by": _to_text(profile_row.get("applicant_health_declared_by")) or None,
            "declared_on": profile_row.get("applicant_health_declared_on"),
        }

    return health_state_by_applicant


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


def _build_documents_state(applicant_rows: list[dict], applicant_names: list[str]) -> dict[str, dict]:
    payload_by_applicant = build_document_review_payload_batch(applicant_rows)
    return {
        applicant_name: payload_by_applicant.get(applicant_name)
        or {
            "ok": False,
            "missing": [],
            "unapproved": [],
            "required": [],
            "required_rows": [],
            "uploaded_rows": [],
            "missing_rows": [],
            "unapproved_rows": [],
        }
        for applicant_name in applicant_names
    }


def _build_policy_state(applicant_rows: list[dict], applicant_names: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}

    schema_check = ensure_policy_applies_to_storage(caller="admission_cockpit.get_admissions_cockpit_data")
    if not schema_check.get("ok"):
        schema_message = _to_text(schema_check.get("message")) or _("Policy schema is not configured.")
        for applicant_name in applicant_names:
            out[applicant_name] = {
                "ok": False,
                "missing": [],
                "required": [],
                "missing_rows": [],
                "schema_error": schema_message,
            }
        return out

    org_ancestors_cache: dict[str, list[str]] = {}
    school_ancestors_cache: dict[str, list[str]] = {}
    all_ancestor_orgs: set[str] = set()
    all_school_ancestors: set[str] = set()

    for applicant_row in applicant_rows:
        organization = _to_text(applicant_row.get("organization"))
        school = _to_text(applicant_row.get("school"))

        if organization and organization not in org_ancestors_cache:
            org_ancestors_cache[organization] = get_organization_ancestors_including_self(organization) or []
            all_ancestor_orgs.update(org_ancestors_cache[organization])

        if school and school not in school_ancestors_cache:
            school_ancestors_cache[school] = get_school_ancestors_including_self(school) or []
            all_school_ancestors.update(school_ancestors_cache[school])

    policy_rows: list[dict] = []
    if all_ancestor_orgs:
        org_values = sorted(all_ancestor_orgs)
        org_placeholders = ", ".join(["%s"] * len(org_values))

        school_scope_sql = ""
        school_params: tuple[str, ...] = ()
        if all_school_ancestors:
            school_values = sorted(all_school_ancestors)
            school_placeholders = ", ".join(["%s"] * len(school_values))
            school_scope_sql = f" OR ip.school IN ({school_placeholders})"
            school_params = tuple(school_values)

        mode_select_sql = (
            "ip.admissions_acknowledgement_mode AS admissions_acknowledgement_mode,"
            if institutional_policy_db_has_column("admissions_acknowledgement_mode")
            else "'Child Acknowledgement' AS admissions_acknowledgement_mode,"
        )
        policy_rows = frappe.db.sql(
            f"""
            SELECT ip.name AS policy_name,
                   ip.policy_key AS policy_key,
                   ip.policy_title AS policy_title,
                   ip.organization AS policy_organization,
                   ip.school AS policy_school,
                   {mode_select_sql}
                   pv.name AS policy_version
              FROM `tabInstitutional Policy` ip
              JOIN `tabPolicy Version` pv
                ON pv.institutional_policy = ip.name
             WHERE ip.is_active = 1
               AND pv.is_active = 1
               AND ip.organization IN ({org_placeholders})
               AND (ip.school IS NULL OR ip.school = ''{school_scope_sql})
               AND {policy_applies_to_filter_sql(policy_alias="ip", audience_placeholder="%s")}
            """,
            (*org_values, *school_params, "Applicant"),
            as_dict=True,
        )

    policy_rows_by_applicant: dict[str, list[dict]] = {}
    all_policy_versions: set[str] = set()

    for applicant_row in applicant_rows:
        applicant_name = _to_text(applicant_row.get("name"))
        organization = _to_text(applicant_row.get("organization"))
        school = _to_text(applicant_row.get("school"))

        if not applicant_name:
            continue

        if not organization:
            out[applicant_name] = {
                "ok": False,
                "missing": [],
                "required": [],
                "missing_rows": [],
            }
            policy_rows_by_applicant[applicant_name] = []
            continue

        ancestor_orgs = org_ancestors_cache.get(organization) or []
        school_ancestors = school_ancestors_cache.get(school) or []

        if not ancestor_orgs:
            out[applicant_name] = {
                "ok": True,
                "missing": [],
                "required": [],
                "missing_rows": [],
            }
            policy_rows_by_applicant[applicant_name] = []
            continue

        candidate_rows = [
            row_policy
            for row_policy in policy_rows
            if _to_text(row_policy.get("policy_organization")) in ancestor_orgs
            and (
                not _to_text(row_policy.get("policy_school"))
                or _to_text(row_policy.get("policy_school")) in school_ancestors
            )
        ]

        nearest_rows = select_nearest_policy_rows_by_key(
            rows=candidate_rows,
            context_organization=organization,
            context_school=school,
            policy_key_field="policy_key",
            policy_organization_field="policy_organization",
            policy_school_field="policy_school",
        )

        policy_rows_by_applicant[applicant_name] = nearest_rows
        for row_policy in nearest_rows:
            policy_version = _to_text(row_policy.get("policy_version"))
            if policy_version:
                all_policy_versions.add(policy_version)

    applicant_acknowledgements_by_pair: dict[tuple[str, str], dict] = {}
    if all_policy_versions and applicant_names:
        acknowledgement_rows = frappe.get_all(
            "Policy Acknowledgement",
            filters={
                "policy_version": ["in", sorted(all_policy_versions)],
                "acknowledged_for": "Applicant",
                "context_doctype": "Student Applicant",
                "context_name": ["in", applicant_names],
            },
            fields=["context_name", "policy_version", "acknowledged_by", "acknowledged_at"],
            order_by="acknowledged_at desc",
            limit=10000,
        )

        for row_ack in acknowledgement_rows:
            applicant_name = _to_text(row_ack.get("context_name"))
            policy_version = _to_text(row_ack.get("policy_version"))
            if not applicant_name or not policy_version:
                continue
            key = (applicant_name, policy_version)
            if key in applicant_acknowledgements_by_pair:
                continue
            applicant_acknowledgements_by_pair[key] = row_ack

    applicant_names_by_guardian: dict[str, set[str]] = defaultdict(set)
    if applicant_names:
        guardian_rows = frappe.get_all(
            "Student Applicant Guardian",
            filters={
                "parent": ["in", applicant_names],
                "parenttype": "Student Applicant",
                "parentfield": "guardians",
                "can_consent": 1,
                "is_primary_guardian": 1,
            },
            fields=["parent", "guardian"],
            limit=10000,
        )
        for row_guardian in guardian_rows:
            applicant_name = _to_text(row_guardian.get("parent"))
            guardian_name = _to_text(row_guardian.get("guardian"))
            if not applicant_name or not guardian_name:
                continue
            applicant_names_by_guardian[guardian_name].add(applicant_name)

    guardian_acknowledgements_by_pair: dict[tuple[str, str], dict] = {}
    guardian_names = sorted(applicant_names_by_guardian)
    if all_policy_versions and guardian_names:
        guardian_acknowledgement_rows = frappe.get_all(
            "Policy Acknowledgement",
            filters={
                "policy_version": ["in", sorted(all_policy_versions)],
                "acknowledged_for": "Guardian",
                "context_doctype": "Guardian",
                "context_name": ["in", guardian_names],
            },
            fields=["context_name", "policy_version", "acknowledged_by", "acknowledged_at"],
            order_by="acknowledged_at desc",
            limit=10000,
        )
        for row_ack in guardian_acknowledgement_rows:
            guardian_name = _to_text(row_ack.get("context_name"))
            policy_version = _to_text(row_ack.get("policy_version"))
            if not guardian_name or not policy_version:
                continue
            for applicant_name in applicant_names_by_guardian.get(guardian_name, set()):
                key = (applicant_name, policy_version)
                if key in guardian_acknowledgements_by_pair:
                    continue
                guardian_acknowledgements_by_pair[key] = row_ack

    for applicant_name in applicant_names:
        if applicant_name in out:
            continue

        assigned_rows = policy_rows_by_applicant.get(applicant_name, [])
        if not assigned_rows:
            out[applicant_name] = {
                "ok": True,
                "missing": [],
                "required": [],
                "missing_rows": [],
            }
            continue

        required_labels: list[str] = []
        missing_labels: list[str] = []
        missing_rows: list[dict] = []

        for row_policy in assigned_rows:
            label = (
                _to_text(row_policy.get("policy_key"))
                or _to_text(row_policy.get("policy_title"))
                or _to_text(row_policy.get("policy_name"))
            )
            acknowledgement_mode = get_policy_admissions_acknowledgement_mode(policy_row=row_policy)
            is_required = acknowledgement_mode != ADMISSIONS_POLICY_MODE_OPTIONAL
            if is_required:
                required_labels.append(label)

            policy_version = _to_text(row_policy.get("policy_version"))
            if acknowledgement_mode == ADMISSIONS_POLICY_MODE_FAMILY:
                ack = guardian_acknowledgements_by_pair.get((applicant_name, policy_version))
            else:
                ack = applicant_acknowledgements_by_pair.get((applicant_name, policy_version))
            if ack or not is_required:
                continue

            missing_labels.append(label)
            missing_rows.append(
                {
                    "label": label,
                    "policy_name": _to_text(row_policy.get("policy_name")) or None,
                    "policy_version": policy_version or None,
                    "admissions_acknowledgement_mode": acknowledgement_mode,
                }
            )

        out[applicant_name] = {
            "ok": not missing_labels,
            "missing": missing_labels,
            "required": required_labels,
            "missing_rows": missing_rows,
        }

    return out


def _build_applicant_enrollment_plan_state(applicant_names: list[str]) -> dict[str, dict]:
    normalized_applicants = list(dict.fromkeys(name for name in applicant_names if _to_text(name)))
    state_by_applicant = {
        applicant_name: {
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
        for applicant_name in normalized_applicants
    }

    if not normalized_applicants or not frappe.db.table_exists("Applicant Enrollment Plan"):
        return state_by_applicant

    plan_rows = frappe.get_all(
        "Applicant Enrollment Plan",
        filters={"student_applicant": ["in", normalized_applicants]},
        fields=[
            "name",
            "student_applicant",
            "status",
            "offer_expires_on",
            "program_enrollment_request",
            "deposit_required",
            "deposit_amount",
            "deposit_due_date",
            "deposit_billable_offering",
            "deposit_terms_source",
            "deposit_override_status",
            "deposit_academic_approved_by",
            "deposit_finance_approved_by",
            "deposit_invoice",
            "creation",
            "modified",
        ],
        order_by="creation desc, modified desc",
        limit=10000,
    )

    latest_by_applicant: dict[str, dict] = {}
    request_names: set[str] = set()
    invoice_names: set[str] = set()
    for row in plan_rows:
        applicant_name = _to_text(row.get("student_applicant"))
        if not applicant_name or applicant_name in latest_by_applicant:
            continue

        latest_by_applicant[applicant_name] = row

        request_name = _to_text(row.get("program_enrollment_request"))
        if request_name:
            request_names.add(request_name)
        invoice_name = _to_text(row.get("deposit_invoice"))
        if invoice_name:
            invoice_names.add(invoice_name)

    existing_request_names: set[str] = set()
    if request_names and frappe.db.table_exists("Program Enrollment Request"):
        existing_request_names = set(
            frappe.get_all(
                "Program Enrollment Request",
                filters={"name": ["in", sorted(request_names)]},
                pluck="name",
            )
        )

    invoice_map: dict[str, dict] = {}
    if invoice_names and frappe.db.table_exists("Sales Invoice"):
        invoice_map = {
            _to_text(row.get("name")): row
            for row in frappe.get_all(
                "Sales Invoice",
                filters={"name": ["in", sorted(invoice_names)]},
                fields=[
                    "name",
                    "docstatus",
                    "status",
                    "grand_total",
                    "paid_amount",
                    "outstanding_amount",
                    "due_date",
                ],
                limit=max(len(invoice_names), 1),
            )
        }

    for applicant_name in normalized_applicants:
        row = latest_by_applicant.get(applicant_name)
        if not row:
            continue

        plan_name = _to_text(row.get("name"))
        status = _to_text(row.get("status")) or None
        request_name = _to_text(row.get("program_enrollment_request"))
        if request_name and existing_request_names and request_name not in existing_request_names:
            request_name = ""

        state_by_applicant[applicant_name] = {
            "has_plan": bool(plan_name),
            "name": plan_name or None,
            "status": status,
            "open_url": _doc_url("Applicant Enrollment Plan", plan_name) if plan_name else None,
            "offer_expires_on": row.get("offer_expires_on"),
            "program_enrollment_request": request_name or None,
            "program_enrollment_request_url": (
                _doc_url("Program Enrollment Request", request_name) if request_name else None
            ),
            "can_send_offer": status == "Committee Approved",
            "can_hydrate_request": status == "Offer Accepted" and not request_name,
            "deposit": _deposit_state_from_plan_row(row, invoice_map),
        }

    return state_by_applicant


def _empty_deposit_state() -> dict:
    return {
        "deposit_required": False,
        "deposit_amount": 0,
        "deposit_due_date": None,
        "deposit_billable_offering": None,
        "terms_source": "School Default",
        "override_status": "Not Required",
        "requires_override_approval": False,
        "academic_approved": False,
        "finance_approved": False,
        "invoice": None,
        "invoice_status": None,
        "docstatus": None,
        "amount": 0,
        "paid_amount": 0,
        "outstanding_amount": 0,
        "due_date": None,
        "is_overdue": False,
        "is_paid": False,
        "blocker_label": None,
        "can_generate_invoice": False,
    }


def _deposit_state_from_plan_row(row: dict, invoice_map: dict[str, dict]) -> dict:
    required = bool(cint(row.get("deposit_required") or 0))
    invoice_name = _to_text(row.get("deposit_invoice"))
    invoice = invoice_map.get(invoice_name) if invoice_name else None
    invoice_status = _to_text((invoice or {}).get("status")) or None
    docstatus = cint((invoice or {}).get("docstatus") or 0) if invoice else None
    outstanding = flt((invoice or {}).get("outstanding_amount") if invoice else row.get("deposit_amount") or 0)
    due_date = (invoice or {}).get("due_date") or row.get("deposit_due_date")
    due_date_text = str(due_date) if due_date else None
    is_paid = bool(docstatus == 1 and (invoice_status in {"Paid", "Credited"} or outstanding <= 0))
    is_overdue = bool(outstanding > 0 and due_date and getdate(due_date) < getdate(nowdate()))
    terms_source = _to_text(row.get("deposit_terms_source")) or "School Default"
    override_status = _to_text(row.get("deposit_override_status")) or "Not Required"
    requires_override = bool(required and terms_source == "Manual Override" and override_status != "Approved")

    blocker_label = None
    if required:
        if requires_override:
            blocker_label = _("Deposit terms need academic and finance approval")
        elif not invoice_name:
            blocker_label = _("Deposit not generated")
        elif invoice_status == "Draft":
            blocker_label = _("Deposit invoice pending finance review")
        elif is_paid:
            blocker_label = _("Deposit paid")
        elif is_overdue:
            blocker_label = _("Deposit overdue")
        elif outstanding > 0:
            blocker_label = _("Deposit unpaid")

    return {
        "deposit_required": required,
        "deposit_amount": flt(row.get("deposit_amount") or 0),
        "deposit_due_date": str(row.get("deposit_due_date")) if row.get("deposit_due_date") else None,
        "deposit_billable_offering": _to_text(row.get("deposit_billable_offering")) or None,
        "terms_source": terms_source,
        "override_status": override_status,
        "requires_override_approval": requires_override,
        "academic_approved": bool(_to_text(row.get("deposit_academic_approved_by"))),
        "finance_approved": bool(_to_text(row.get("deposit_finance_approved_by"))),
        "invoice": invoice_name or None,
        "invoice_status": invoice_status,
        "docstatus": docstatus,
        "amount": flt((invoice or {}).get("grand_total") if invoice else row.get("deposit_amount") or 0),
        "paid_amount": flt((invoice or {}).get("paid_amount") if invoice else 0),
        "outstanding_amount": outstanding,
        "due_date": due_date_text,
        "is_overdue": is_overdue,
        "is_paid": is_paid,
        "blocker_label": blocker_label,
        "can_generate_invoice": bool(required and not invoice_name and not requires_override),
    }


def _build_health_requirement_by_school(applicant_rows: list[dict]) -> dict[str, bool]:
    school_names = sorted({_to_text(row.get("school")) for row in applicant_rows if _to_text(row.get("school"))})
    if not school_names:
        return {}

    rows = frappe.get_all(
        "School",
        filters={"name": ["in", school_names]},
        fields=["name", "require_health_profile_for_approval"],
        limit=len(school_names),
    )

    out: dict[str, bool] = {}
    for row in rows:
        school_name = _to_text(row.get("name"))
        if not school_name:
            continue
        required_value = row.get("require_health_profile_for_approval")
        out[school_name] = True if required_value is None else bool(cint(required_value))
    return out


def _build_issues(
    *,
    policies: dict,
    documents: dict,
    health: dict,
    profile: dict,
    recommendations: dict,
    health_required_for_approval: bool,
) -> list[str]:
    issues: list[str] = []

    if not policies.get("ok"):
        schema_error = _to_text(policies.get("schema_error"))
        if schema_error:
            issues.append(schema_error)
        else:
            missing = policies.get("missing") or []
            if missing:
                issues.append(
                    _("Missing policy acknowledgements: {policies}.").format(
                        policies=", ".join(str(item) for item in missing)
                    )
                )
            else:
                issues.append(_("Missing required policy acknowledgements."))

    if health_required_for_approval and not health.get("ok"):
        status = _to_text(health.get("status")) or "missing"
        if status == "needs_follow_up":
            issues.append(_("Health review requires follow-up."))
        else:
            issues.append(_("Health profile is missing or not cleared."))

    if not documents.get("ok"):
        missing = documents.get("missing") or []
        unapproved = documents.get("unapproved") or []
        if missing:
            issues.append(
                _("Missing required documents: {documents}.").format(documents=", ".join(str(item) for item in missing))
            )
        if unapproved:
            issues.append(
                _("Required documents not approved: {documents}.").format(
                    documents=", ".join(str(item) for item in unapproved)
                )
            )

    if not profile.get("ok"):
        missing = profile.get("missing") or []
        if missing:
            issues.append(
                _("Missing profile information: {fields}.").format(fields=", ".join(str(item) for item in missing))
            )
        else:
            issues.append(_("Missing required profile information."))

    if not recommendations.get("ok"):
        missing = recommendations.get("missing") or []
        required_total = cint(recommendations.get("required_total") or 0)
        received_total = cint(recommendations.get("received_total") or 0)
        if missing:
            issues.append(
                _("Missing required recommendations: {recommendations}.").format(
                    recommendations=", ".join(str(item) for item in missing)
                )
            )
        elif required_total > 0:
            issues.append(
                _("Required recommendations received: {received_total} of {required_total}.").format(
                    received_total=received_total,
                    required_total=required_total,
                )
            )

    return issues


def _build_readiness_batch(applicant_rows: list[dict]) -> dict[str, dict]:
    applicant_names = [_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))]
    if not applicant_names:
        return {}

    policies_by_applicant = _build_policy_state(applicant_rows, applicant_names)
    documents_by_applicant = _build_documents_state(applicant_rows, applicant_names)
    health_by_applicant = _build_health_state(applicant_names)
    health_requirement_by_school = _build_health_requirement_by_school(applicant_rows)
    recommendations_by_applicant = get_recommendation_status_batch_for_applicants(
        applicant_rows=applicant_rows,
        include_confidential=True,
    )

    readiness_by_applicant: dict[str, dict] = {}

    for applicant_row in applicant_rows:
        applicant_name = _to_text(applicant_row.get("name"))
        if not applicant_name:
            continue

        policies = policies_by_applicant.get(applicant_name) or {
            "ok": False,
            "missing": [],
            "required": [],
            "missing_rows": [],
        }
        documents = documents_by_applicant.get(applicant_name) or {
            "ok": False,
            "missing": [],
            "unapproved": [],
            "required": [],
            "missing_rows": [],
            "unapproved_rows": [],
        }
        health = health_by_applicant.get(applicant_name) or {
            "ok": False,
            "required_for_approval": True,
            "status": "missing",
            "profile_name": None,
            "review_status": None,
            "reviewed_by": None,
            "reviewed_on": None,
            "declared_complete": False,
            "declared_by": None,
            "declared_on": None,
        }
        profile = _build_profile_state(applicant_row)
        recommendations = recommendations_by_applicant.get(applicant_name) or {
            "ok": True,
            "required_total": 0,
            "received_total": 0,
            "requested_total": 0,
            "missing": [],
            "rows": [],
            "state": "optional",
            "counts": {},
            "review_rows": [],
            "pending_review_count": 0,
            "first_pending_review": None,
            "latest_submitted_on": None,
        }
        school_name = _to_text(applicant_row.get("school"))
        health_required_for_approval = health_requirement_by_school.get(school_name, True)
        health = dict(health)
        health["required_for_approval"] = health_required_for_approval

        health_ok_for_approval = bool(health.get("ok")) if health_required_for_approval else True
        ready = bool(
            policies.get("ok")
            and documents.get("ok")
            and health_ok_for_approval
            and profile.get("ok")
            and recommendations.get("ok")
        )

        readiness_by_applicant[applicant_name] = {
            "policies": policies,
            "documents": documents,
            "health": health,
            "profile": profile,
            "recommendations": recommendations,
            "ready": ready,
            "issues": _build_issues(
                policies=policies,
                documents=documents,
                health=health,
                profile=profile,
                recommendations=recommendations,
                health_required_for_approval=health_required_for_approval,
            ),
        }

    return readiness_by_applicant


def _build_blockers(
    *,
    snapshot: dict,
    application_status: str,
    open_assignments: int,
    applicant_name: str,
    first_open_assignment: dict | None,
) -> list[dict]:
    blockers: list[dict] = []

    policies = snapshot.get("policies") or {}
    documents = snapshot.get("documents") or {}
    health = snapshot.get("health") or {}
    profile = snapshot.get("profile") or {}

    applicant_target = _target(
        doctype="Student Applicant",
        name=applicant_name,
        target_label=_("Open applicant"),
    )

    if not policies.get("ok"):
        missing = policies.get("missing") or []
        missing_rows = policies.get("missing_rows") or []
        first_missing = missing_rows[0] if missing_rows else {}
        policy_version = _to_text(first_missing.get("policy_version"))

        target = (
            _target(
                doctype="Policy Version",
                name=policy_version,
                target_label=_("Open policy version"),
            )
            if policy_version
            else applicant_target
        )

        label = _("Missing policies") if not missing else _("Missing policies: {count}").format(count=len(missing))
        blockers.append(
            {
                "kind": "missing_policies",
                "label": label,
                "items": [str(item) for item in missing],
                **target,
            }
        )

    if not documents.get("ok"):
        missing = documents.get("missing") or []
        unapproved = documents.get("unapproved") or []
        missing_rows = documents.get("missing_rows") or []
        unapproved_rows = documents.get("unapproved_rows") or []

        if missing:
            first_missing = missing_rows[0] if missing_rows else {}
            missing_type = _to_text(first_missing.get("document_type"))

            target = (
                _applicant_workspace_target(
                    applicant_name=applicant_name,
                    document_type=missing_type,
                    target_label=_("Open requirement"),
                )
                if missing_type
                else applicant_target
            )

            blockers.append(
                {
                    "kind": "missing_documents",
                    "label": _("Requirements awaiting submission: {count}").format(count=len(missing)),
                    "items": [str(item) for item in missing],
                    **target,
                }
            )

        if unapproved:
            first_unapproved = unapproved_rows[0] if unapproved_rows else {}
            applicant_document = _to_text(first_unapproved.get("applicant_document"))
            document_type = _to_text(first_unapproved.get("document_type"))
            document_item = _to_text(first_unapproved.get("applicant_document_item"))
            review_status = _to_text(first_unapproved.get("review_status"))

            if review_status == "Rejected":
                label = _("Requirements awaiting resubmission: {count}").format(count=len(unapproved))
                target_label = _("Open requirement")
                document_item = None
            else:
                label = _("Submitted files awaiting review: {count}").format(count=len(unapproved))
                target_label = _("Open submission review")

            target = (
                _applicant_workspace_target(
                    applicant_name=applicant_name,
                    document_type=document_type,
                    applicant_document=applicant_document,
                    document_item=document_item,
                    target_label=target_label,
                )
                if applicant_document or document_type
                else applicant_target
            )

            blockers.append(
                {
                    "kind": "documents_unapproved",
                    "label": label,
                    "items": [str(item) for item in unapproved],
                    **target,
                }
            )

    if bool(health.get("required_for_approval", True)) and not health.get("ok"):
        health_profile = _to_text(health.get("profile_name"))
        target = (
            _target(
                doctype="Applicant Health Profile",
                name=health_profile,
                target_label=_("Open health profile"),
            )
            if health_profile
            else _target(
                doctype="Applicant Health Profile",
                is_new=True,
                params={"student_applicant": applicant_name},
                target_label=_("Create health profile"),
            )
        )

        blockers.append(
            {
                "kind": "health_not_cleared",
                "label": _("Health profile is missing or not cleared"),
                "items": [],
                **target,
            }
        )

    if not profile.get("ok"):
        missing = profile.get("missing") or []
        blockers.append(
            {
                "kind": "profile_incomplete",
                "label": _("Profile information incomplete"),
                "items": [str(item) for item in missing],
                **applicant_target,
            }
        )

    status = _to_text(application_status)
    if status in {"Submitted", "Under Review"} and open_assignments == 0:
        if first_open_assignment and _to_text(first_open_assignment.get("name")):
            target = _target(
                doctype="Applicant Review Assignment",
                name=_to_text(first_open_assignment.get("name")),
                target_label=_("Open review assignment"),
            )
        else:
            target = _target(
                doctype="Applicant Review Assignment",
                is_new=True,
                params={
                    "target_type": "Student Applicant",
                    "target_name": applicant_name,
                    "student_applicant": applicant_name,
                },
                target_label=_("Create review assignment"),
            )

        blockers.append(
            {
                "kind": "no_reviewer_assigned",
                "label": _("No reviewer assignment is open"),
                "items": [],
                **target,
            }
        )

    return blockers


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


def _cache_key_for_payload(payload: dict) -> str:
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"{COCKPIT_CACHE_PREFIX}{digest}"


def _require_applicant_enrollment_plan_name(applicant_enrollment_plan: str) -> str:
    plan_name = _to_text(applicant_enrollment_plan)
    if not plan_name:
        frappe.throw(_("Applicant Enrollment Plan is required."))
    return plan_name


@frappe.whitelist()
def send_admissions_cockpit_offer(applicant_enrollment_plan: str):
    _ensure_cockpit_access()
    plan_name = _require_applicant_enrollment_plan_name(applicant_enrollment_plan)
    plan = frappe.get_doc("Applicant Enrollment Plan", plan_name)
    result = plan.send_offer() or {}
    invalidate_admissions_cockpit_cache()
    return {
        "ok": bool(result.get("ok")),
        "applicant_enrollment_plan": plan.name,
        "status": _to_text(result.get("status")) or _to_text(plan.status),
        "open_url": _doc_url("Applicant Enrollment Plan", plan.name),
    }


@frappe.whitelist()
def hydrate_admissions_cockpit_request(applicant_enrollment_plan: str):
    _ensure_cockpit_access()
    plan_name = _require_applicant_enrollment_plan_name(applicant_enrollment_plan)
    from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
        hydrate_program_enrollment_request_from_applicant_plan,
    )

    result = hydrate_program_enrollment_request_from_applicant_plan(plan_name) or {}
    request_name = _to_text(result.get("name"))
    plan_status = _to_text(frappe.db.get_value("Applicant Enrollment Plan", plan_name, "status"))
    invalidate_admissions_cockpit_cache()
    return {
        "ok": True,
        "applicant_enrollment_plan": plan_name,
        "status": plan_status or "Hydrated",
        "program_enrollment_request": request_name or None,
        "program_enrollment_request_url": _doc_url("Program Enrollment Request", request_name)
        if request_name
        else None,
        "created": bool(result.get("created")),
    }


@frappe.whitelist()
def generate_admissions_cockpit_deposit_invoice(applicant_enrollment_plan: str):
    _ensure_cockpit_access()
    plan_name = _require_applicant_enrollment_plan_name(applicant_enrollment_plan)
    from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
        generate_deposit_invoice_from_offer,
    )

    result = generate_deposit_invoice_from_offer(plan_name) or {}
    invalidate_admissions_cockpit_cache()
    return {
        "ok": bool(result.get("ok")),
        "created": bool(result.get("created")),
        "applicant_enrollment_plan": plan_name,
        "deposit": result.get("deposit") or {},
        "invoice": result.get("invoice") or {},
    }


@frappe.whitelist()
def get_admissions_cockpit_data(filters=None):
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
