# ifitwala_ed/api/admission_cockpit.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.utilities.school_tree import get_descendant_schools

ALLOWED_COCKPIT_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager", "Administrator"}
TERMINAL_STATUSES = {"Rejected", "Withdrawn", "Promoted"}

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
    "missing_documents": "Missing Documents",
    "documents_unapproved": "Documents Pending Review",
    "health_not_cleared": "Health Not Cleared",
    "profile_incomplete": "Profile Incomplete",
    "no_reviewer_assigned": "No Reviewer Assigned",
}


def _ensure_cockpit_access(user: str | None = None) -> str:
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to access Admissions Cockpit."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & ALLOWED_COCKPIT_ROLES:
        return user

    frappe.throw(_("You do not have permission to access Admissions Cockpit."), frappe.PermissionError)
    return user


def _to_text(value) -> str:
    return str(value or "").strip()


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


def _build_blockers(snapshot: dict, application_status: str, open_assignments: int, applicant_name: str) -> list[dict]:
    blockers: list[dict] = []

    policies = snapshot.get("policies") or {}
    documents = snapshot.get("documents") or {}
    health = snapshot.get("health") or {}
    profile = snapshot.get("profile") or {}

    if not policies.get("ok"):
        missing = policies.get("missing") or []
        label = _("Missing policies") if not missing else _("Missing policies: {0}").format(len(missing))
        blockers.append(
            {
                "kind": "missing_policies",
                "label": label,
                "items": [str(item) for item in missing],
                "target_url": f"/app/student-applicant/{applicant_name}",
            }
        )

    if not documents.get("ok"):
        missing = documents.get("missing") or []
        unapproved = documents.get("unapproved") or []
        if missing:
            blockers.append(
                {
                    "kind": "missing_documents",
                    "label": _("Missing required documents: {0}").format(len(missing)),
                    "items": [str(item) for item in missing],
                    "target_url": f"/app/student-applicant/{applicant_name}",
                }
            )
        if unapproved:
            blockers.append(
                {
                    "kind": "documents_unapproved",
                    "label": _("Required documents pending review: {0}").format(len(unapproved)),
                    "items": [str(item) for item in unapproved],
                    "target_url": f"/app/student-applicant/{applicant_name}",
                }
            )

    if not health.get("ok"):
        blockers.append(
            {
                "kind": "health_not_cleared",
                "label": _("Health profile is missing or not cleared"),
                "items": [],
                "target_url": f"/app/student-applicant/{applicant_name}",
            }
        )

    if not profile.get("ok"):
        missing = profile.get("missing") or []
        blockers.append(
            {
                "kind": "profile_incomplete",
                "label": _("Profile information incomplete"),
                "items": [str(item) for item in missing],
                "target_url": f"/app/student-applicant/{applicant_name}",
            }
        )

    status = _to_text(application_status)
    if status in {"Submitted", "Under Review"} and open_assignments == 0:
        blockers.append(
            {
                "kind": "no_reviewer_assigned",
                "label": _("No reviewer assignment is open"),
                "items": [],
                "target_url": f"/app/student-applicant/{applicant_name}",
            }
        )

    return blockers


def _empty_payload(organizations: list[str], schools: list[str]) -> dict:
    return {
        "config": {
            "organizations": organizations,
            "schools": schools,
            "columns": [{"id": col_id, "title": title} for col_id, title in KANBAN_COLUMNS],
        },
        "counts": {
            "active_applications": 0,
            "blocked_applications": 0,
            "ready_for_decision": 0,
            "accepted_pending_promotion": 0,
            "my_open_assignments": 0,
        },
        "blockers": [],
        "columns": [{"id": col_id, "title": title, "items": []} for col_id, title in KANBAN_COLUMNS],
        "generated_at": frappe.utils.now_datetime(),
    }


@frappe.whitelist()
def get_admissions_cockpit_data(filters=None):
    user = _ensure_cockpit_access()
    user_roles = set(frappe.get_roles(user))

    filters = frappe.parse_json(filters) or {}
    organization_filter = _to_text(filters.get("organization"))
    school_filter = _to_text(filters.get("school"))
    include_terminal = bool(cint(filters.get("include_terminal")))
    assigned_to_me_only = bool(cint(filters.get("assigned_to_me")))
    status_filters = _as_str_list(filters.get("application_statuses"))

    limit = _to_int(filters.get("limit"), 120)
    if limit < 1:
        limit = 1
    if limit > 250:
        limit = 250

    organization_scope = _get_descendant_organizations(organization_filter) if organization_filter else []
    if organization_filter and not organization_scope:
        return _empty_payload([], [])

    school_scope = get_descendant_schools(school_filter) if school_filter else []
    if school_filter and not school_scope:
        organizations = [
            row[0] for row in frappe.db.sql("SELECT name FROM `tabOrganization` ORDER BY lft ASC, name ASC")
        ]
        return _empty_payload(organizations, [])

    all_organizations = [
        row[0] for row in frappe.db.sql("SELECT name FROM `tabOrganization` ORDER BY lft ASC, name ASC", as_list=True)
    ]

    if organization_scope:
        schools = frappe.get_all(
            "School",
            filters={"organization": ["in", organization_scope]},
            fields=["name"],
            order_by="lft asc, name asc",
        )
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
        ],
        order_by="modified desc",
        limit_page_length=fetch_limit,
    )

    if not applicant_rows:
        return _empty_payload(all_organizations, all_schools)

    applicant_names = [row.get("name") for row in applicant_rows if row.get("name")]
    assignment_rows = frappe.get_all(
        "Applicant Review Assignment",
        filters={
            "status": "Open",
            "student_applicant": ["in", applicant_names],
        },
        fields=["student_applicant", "assigned_to_user", "assigned_to_role"],
        limit_page_length=10000,
    )

    assignment_summary = {name: {"open_total": 0, "open_for_me": 0} for name in applicant_names}
    for row_assignment in assignment_rows:
        applicant_name = _to_text(row_assignment.get("student_applicant"))
        if not applicant_name or applicant_name not in assignment_summary:
            continue

        assignment_summary[applicant_name]["open_total"] += 1

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
        return _empty_payload(all_organizations, all_schools)

    columns = {col_id: {"id": col_id, "title": title, "items": []} for col_id, title in KANBAN_COLUMNS}
    blocker_counts = {key: 0 for key in BLOCKER_LABELS}
    counts = {
        "active_applications": 0,
        "blocked_applications": 0,
        "ready_for_decision": 0,
        "accepted_pending_promotion": 0,
        "my_open_assignments": 0,
    }

    logger = frappe.logger("admissions_cockpit", allow_site=True)

    for row in applicant_rows:
        applicant_name = _to_text(row.get("name"))
        if not applicant_name:
            continue

        assignee_stats = assignment_summary.get(applicant_name, {"open_total": 0, "open_for_me": 0})

        try:
            applicant_doc = frappe.get_doc("Student Applicant", applicant_name)
            snapshot = applicant_doc.get_readiness_snapshot() or {}
        except Exception:
            logger.exception("Admissions cockpit readiness failed for %s", applicant_name)
            snapshot = {
                "ready": False,
                "issues": [_("Readiness data unavailable")],
                "policies": {"ok": False, "missing": []},
                "documents": {"ok": False, "missing": [], "unapproved": []},
                "health": {"ok": False, "status": "missing"},
                "profile": {"ok": False, "missing": []},
            }

        ready = bool(snapshot.get("ready"))
        stage = _resolve_stage(_to_text(row.get("application_status")), ready)
        blockers = _build_blockers(
            snapshot=snapshot,
            application_status=_to_text(row.get("application_status")),
            open_assignments=assignee_stats.get("open_total", 0),
            applicant_name=applicant_name,
        )

        for blocker in blockers:
            kind = blocker.get("kind")
            if kind in blocker_counts:
                blocker_counts[kind] += 1

        has_blocker = any((row_blocker.get("kind") or "") != "pending_promotion" for row_blocker in blockers)
        if has_blocker:
            counts["blocked_applications"] += 1

        if stage == "awaiting_decision":
            counts["ready_for_decision"] += 1
        if stage == "accepted_pending_promotion":
            counts["accepted_pending_promotion"] += 1

        counts["active_applications"] += 1
        counts["my_open_assignments"] += assignee_stats.get("open_for_me", 0)

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
                "health_ok": bool((snapshot.get("health") or {}).get("ok")),
            },
            "top_blockers": [row_blocker.get("label") for row_blocker in blockers[:2] if row_blocker.get("label")],
            "blockers": blockers,
            "issues": [str(item) for item in (snapshot.get("issues") or [])],
            "open_url": f"/app/student-applicant/{applicant_name}",
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

    return {
        "config": {
            "organizations": all_organizations,
            "schools": all_schools,
            "columns": [{"id": col_id, "title": title} for col_id, title in KANBAN_COLUMNS],
        },
        "counts": counts,
        "blockers": blocker_tiles,
        "columns": [columns[col_id] for col_id, _ in KANBAN_COLUMNS],
        "generated_at": frappe.utils.now_datetime(),
    }
