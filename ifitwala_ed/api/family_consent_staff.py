from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from ifitwala_ed.api.policy_signature import (
    POLICY_SIGNATURE_ANALYTICS_ROLES,
    _ensure_organization_in_scope,
    _ensure_school_in_scope,
    _manager_scope_organizations,
    _school_options_for_scope,
)
from ifitwala_ed.governance.doctype.family_consent_request.family_consent_request import (
    AUDIENCE_MODE_ORDER,
    COMPLETION_CHANNEL_MODE_ORDER,
    REQUEST_STATUS_ORDER,
    REQUEST_STATUS_PUBLISHED,
    REQUEST_TYPE_ORDER,
)
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org

FAMILY_CONSENT_MANAGER_ROLES = frozenset(set(POLICY_SIGNATURE_ANALYTICS_ROLES) | {"Academic Staff"})
CURRENT_STATUS_COMPLETED = "completed"
CURRENT_STATUS_DECLINED = "declined"
CURRENT_STATUS_WITHDRAWN = "withdrawn"
CURRENT_STATUS_EXPIRED = "expired"
CURRENT_STATUS_OVERDUE = "overdue"
CURRENT_STATUS_PENDING = "pending"


def _require_roles(allowed_roles: set[str] | frozenset[str]) -> tuple[str, set[str]]:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & set(allowed_roles):
        return user, roles

    frappe.throw(_("You do not have permission for this Family Consent action."), frappe.PermissionError)
    return user, roles


def _scope_organizations(*, user: str, roles: set[str]) -> list[str]:
    if roles & set(POLICY_SIGNATURE_ANALYTICS_ROLES):
        return _manager_scope_organizations(user=user, roles=roles)

    base_org = (get_user_base_org(user) or "").strip()
    if not base_org:
        frappe.throw(_("No active Employee organization is linked to your account."), frappe.PermissionError)

    descendants = get_descendant_organizations(base_org) or [base_org]
    return sorted({(row or "").strip() for row in descendants if (row or "").strip()})


def _require_request_write(request_name: str):
    request_name = (request_name or "").strip()
    if not request_name:
        frappe.throw(_("Family Consent Request is required."))

    doc = frappe.get_doc("Family Consent Request", request_name)
    if not frappe.has_permission("Family Consent Request", doc=doc, ptype="write"):
        frappe.throw(_("You do not have permission to publish this Family Consent Request."), frappe.PermissionError)
    return doc


def _derive_current_target_status(
    *,
    request_row: dict[str, Any],
    latest_decision: dict[str, Any] | None,
    today,
) -> str:
    if latest_decision:
        status = (latest_decision.get("decision_status") or "").strip()
        if status in {"Approved", "Granted"}:
            return CURRENT_STATUS_COMPLETED
        if status in {"Declined", "Denied"}:
            return CURRENT_STATUS_DECLINED
        if status == "Withdrawn":
            return CURRENT_STATUS_WITHDRAWN

    effective_to = getdate(request_row.get("effective_to")) if request_row.get("effective_to") else None
    due_on = getdate(request_row.get("due_on")) if request_row.get("due_on") else None
    if effective_to and effective_to < today:
        return CURRENT_STATUS_EXPIRED
    if due_on and due_on < today:
        return CURRENT_STATUS_OVERDUE
    return CURRENT_STATUS_PENDING


@frappe.whitelist()
def get_family_consent_dashboard_context(
    organization: str | None = None,
) -> dict[str, Any]:
    user, roles = _require_roles(FAMILY_CONSENT_MANAGER_ROLES)
    scoped_organizations = _scope_organizations(user=user, roles=roles)

    organization = (organization or "").strip()
    if organization:
        _ensure_organization_in_scope(organization, scoped_organizations)

    organization_scope = (get_descendant_organizations(organization) if organization else scoped_organizations) or (
        [organization] if organization else []
    )

    return {
        "filters": {
            "organization": organization or None,
        },
        "options": {
            "organizations": sorted(scoped_organizations),
            "schools": _school_options_for_scope(organization_scope),
            "request_types": list(REQUEST_TYPE_ORDER),
            "statuses": list(REQUEST_STATUS_ORDER),
            "audience_modes": list(AUDIENCE_MODE_ORDER),
            "completion_channel_modes": list(COMPLETION_CHANNEL_MODE_ORDER),
        },
    }


@frappe.whitelist()
def publish_family_consent_request(
    family_consent_request: str,
    send_initial_communication: int | str | bool | None = None,
) -> dict[str, Any]:
    user, roles = _require_roles(FAMILY_CONSENT_MANAGER_ROLES)
    doc = _require_request_write(family_consent_request)

    scoped_organizations = _scope_organizations(user=user, roles=roles)
    _ensure_organization_in_scope(doc.organization, scoped_organizations)
    _ensure_school_in_scope(school=doc.school, organization_scope=scoped_organizations)

    if doc.status == REQUEST_STATUS_PUBLISHED:
        return {
            "ok": True,
            "status": "already_published",
            "family_consent_request": doc.name,
            "request_key": doc.request_key,
            "target_count": len(doc.get("targets") or []),
            "communication_count": 0,
        }

    if doc.status != "Draft":
        frappe.throw(_("Only draft Family Consent Requests can be published."))
    if not doc.get("targets"):
        frappe.throw(_("Add at least one Target before publishing."))
    if not doc.get("fields"):
        frappe.throw(_("Add at least one Field before publishing."))

    doc.status = REQUEST_STATUS_PUBLISHED
    doc.save(ignore_permissions=True)

    # Communication dispatch is a later slice. Keep the field explicit in the API contract now.
    send_requested = bool(frappe.utils.cint(send_initial_communication))
    if send_requested:
        frappe.logger().info("Family Consent publish requested initial communication for %s", doc.name)

    return {
        "ok": True,
        "status": "published",
        "family_consent_request": doc.name,
        "request_key": doc.request_key,
        "target_count": len(doc.get("targets") or []),
        "communication_count": 0,
    }


@frappe.whitelist()
def get_family_consent_dashboard(
    organization: str | None = None,
    school: str | None = None,
    request_type: str | None = None,
    status: str | None = None,
    audience_mode: str | None = None,
    completion_channel_mode: str | None = None,
) -> dict[str, Any]:
    user, roles = _require_roles(FAMILY_CONSENT_MANAGER_ROLES)
    scoped_organizations = _scope_organizations(user=user, roles=roles)

    organization = (organization or "").strip()
    school = (school or "").strip()
    request_type = (request_type or "").strip()
    status = (status or "").strip()
    audience_mode = (audience_mode or "").strip()
    completion_channel_mode = (completion_channel_mode or "").strip()

    if organization:
        _ensure_organization_in_scope(organization, scoped_organizations)
    school_scope_organizations = (
        get_descendant_organizations(organization) if organization else scoped_organizations
    ) or ([organization] if organization else [])
    if school:
        _ensure_school_in_scope(school=school, organization_scope=school_scope_organizations)

    request_filters: dict[str, Any] = {
        "organization": ["in", tuple(scoped_organizations)],
    }
    if organization:
        request_filters["organization"] = organization
    if school:
        request_filters["school"] = school
    if request_type:
        request_filters["request_type"] = request_type
    if status:
        request_filters["status"] = status
    if audience_mode:
        request_filters["audience_mode"] = audience_mode
    if completion_channel_mode:
        request_filters["completion_channel_mode"] = completion_channel_mode

    request_rows = frappe.get_all(
        "Family Consent Request",
        filters=request_filters,
        fields=[
            "name",
            "request_key",
            "request_title",
            "request_type",
            "audience_mode",
            "signer_rule",
            "completion_channel_mode",
            "status",
            "organization",
            "school",
            "due_on",
            "effective_to",
        ],
        order_by="modified desc",
        limit=200,
    )

    request_names = [row.get("name") for row in request_rows if row.get("name")]
    if not request_names:
        return {
            "meta": {"generated_at": now_datetime().isoformat()},
            "filters": {
                "organization": organization or None,
                "school": school or None,
                "request_type": request_type or None,
                "status": status or None,
                "audience_mode": audience_mode or None,
                "completion_channel_mode": completion_channel_mode or None,
            },
            "counts": {
                "requests": 0,
                "pending": 0,
                "completed": 0,
                "declined": 0,
                "withdrawn": 0,
                "expired": 0,
                "overdue": 0,
            },
            "rows": [],
        }

    target_rows = frappe.get_all(
        "Family Consent Target",
        filters={
            "parent": ["in", tuple(request_names)],
            "parenttype": "Family Consent Request",
            "parentfield": "targets",
        },
        fields=["parent", "student"],
        order_by="parent asc, idx asc",
        limit=0,
    )
    targets_by_request: dict[str, list[str]] = defaultdict(list)
    for row in target_rows:
        parent = (row.get("parent") or "").strip()
        student = (row.get("student") or "").strip()
        if parent and student:
            targets_by_request[parent].append(student)

    decision_rows = frappe.get_all(
        "Family Consent Decision",
        filters={"family_consent_request": ["in", tuple(request_names)]},
        fields=[
            "name",
            "family_consent_request",
            "student",
            "decision_status",
            "decision_at",
            "decision_by",
        ],
        order_by="decision_at asc, creation asc",
        limit=0,
    )
    latest_decisions: dict[tuple[str, str], dict[str, Any]] = {}
    for row in decision_rows:
        key = (
            (row.get("family_consent_request") or "").strip(),
            (row.get("student") or "").strip(),
        )
        if not all(key):
            continue
        latest_decisions[key] = row

    today = getdate()
    overall_counts = {
        "requests": len(request_rows),
        "pending": 0,
        "completed": 0,
        "declined": 0,
        "withdrawn": 0,
        "expired": 0,
        "overdue": 0,
    }
    dashboard_rows = []

    for row in request_rows:
        request_name = (row.get("name") or "").strip()
        students = targets_by_request.get(request_name, [])
        row_counts = {
            "pending_count": 0,
            "completed_count": 0,
            "declined_count": 0,
            "withdrawn_count": 0,
            "expired_count": 0,
            "overdue_count": 0,
        }
        for student_name in students:
            current_status = _derive_current_target_status(
                request_row=row,
                latest_decision=latest_decisions.get((request_name, student_name)),
                today=today,
            )
            if current_status == CURRENT_STATUS_COMPLETED:
                row_counts["completed_count"] += 1
                overall_counts["completed"] += 1
            elif current_status == CURRENT_STATUS_DECLINED:
                row_counts["declined_count"] += 1
                overall_counts["declined"] += 1
            elif current_status == CURRENT_STATUS_WITHDRAWN:
                row_counts["withdrawn_count"] += 1
                overall_counts["withdrawn"] += 1
            elif current_status == CURRENT_STATUS_EXPIRED:
                row_counts["expired_count"] += 1
                overall_counts["expired"] += 1
            elif current_status == CURRENT_STATUS_OVERDUE:
                row_counts["overdue_count"] += 1
                overall_counts["overdue"] += 1
            else:
                row_counts["pending_count"] += 1
                overall_counts["pending"] += 1

        dashboard_rows.append(
            {
                "family_consent_request": request_name,
                "request_key": row.get("request_key") or "",
                "request_title": row.get("request_title") or "",
                "request_type": row.get("request_type") or "",
                "audience_mode": row.get("audience_mode") or "",
                "signer_rule": row.get("signer_rule") or "",
                "completion_channel_mode": row.get("completion_channel_mode") or "",
                "status": row.get("status") or "",
                "organization": row.get("organization") or "",
                "school": row.get("school") or "",
                "due_on": str(row.get("due_on") or ""),
                "target_count": len(students),
                **row_counts,
            }
        )

    return {
        "meta": {"generated_at": now_datetime().isoformat()},
        "filters": {
            "organization": organization or None,
            "school": school or None,
            "request_type": request_type or None,
            "status": status or None,
            "audience_mode": audience_mode or None,
            "completion_channel_mode": completion_channel_mode or None,
        },
        "counts": overall_counts,
        "rows": dashboard_rows,
    }
