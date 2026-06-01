from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    _get_inquiry_assignment_organization_scope,
    _get_inquiry_assignment_school_scope,
)
from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import (
    CRM_MUTATION_ROLES,
    ensure_admissions_crm_permission,
)
from ifitwala_ed.admission.api.crm.guards import _require_conversation_write, _require_inquiry_write
from ifitwala_ed.admission.api.inbox.scope import _resolve_scope
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
)

DEFAULT_ASSIGNEE_LIMIT = 20
MAX_ASSIGNEE_LIMIT = 50


def _bounded_assignee_limit(value: int | str | None) -> int:
    limit = cint(value) or DEFAULT_ASSIGNEE_LIMIT
    return min(max(limit, 1), MAX_ASSIGNEE_LIMIT)


def _normalize_assignment_lane(lane: str | None) -> str | None:
    value = clean(lane)
    if not value:
        return None
    normalized = value.lower()
    if normalized == "admission":
        return "Admission"
    if normalized == "staff":
        return "Staff"
    frappe.throw(_("Invalid assignment lane: {lane}.").format(lane=value))
    return None


def _candidate_meta(row: dict) -> str | None:
    parts: list[str] = []
    school = clean(row.get("school"))
    organization = clean(row.get("organization"))
    user_id = clean(row.get("value"))
    label = clean(row.get("label"))

    if school:
        parts.append(school)
    elif organization:
        parts.append(organization)
    if user_id and user_id != label:
        parts.append(user_id)
    return " - ".join(parts) or None


def _candidate_dto(row: dict, *, force_lane: str | None = None) -> dict:
    lane = force_lane or clean(row.get("lane")) or "Staff"
    return {
        "value": clean(row.get("value")),
        "label": clean(row.get("label")) or clean(row.get("value")),
        "meta": _candidate_meta(row),
        "lane": lane,
    }


def _apply_query_condition(where: list[str], params: dict, query: str | None) -> None:
    text = clean(query)
    if len(text) < 2:
        return
    params["query"] = f"%{text}%"
    where.append(
        "("
        "u.name LIKE %(query)s "
        "OR u.email LIKE %(query)s "
        "OR u.full_name LIKE %(query)s "
        "OR e.employee_full_name LIKE %(query)s"
        ")"
    )


def _apply_inquiry_scope_conditions(
    where: list[str],
    params: dict,
    *,
    organization: str | None,
    school: str | None,
    fallback_org_scope: list[str] | None = None,
    fallback_school_scope: list[str] | None = None,
    scope_bypass: bool = False,
) -> None:
    organization_name = clean(organization)
    school_name = clean(school)

    org_scope = _get_inquiry_assignment_organization_scope(organization_name) if organization_name else []
    if organization_name and not org_scope:
        where.append("1=0")
        return

    school_scope = _get_inquiry_assignment_school_scope(school_name) if school_name else []
    if school_name and not school_scope:
        where.append("1=0")
        return

    if not org_scope and not school_scope and not scope_bypass:
        org_scope = fallback_org_scope or []
        school_scope = fallback_school_scope or []
        if not org_scope and not school_scope:
            where.append("1=0")
            return

    if org_scope:
        where.append("e.organization IN %(org_scope)s")
        params["org_scope"] = tuple(org_scope)

    if school_scope:
        if org_scope:
            where.append("(IFNULL(e.school, '') = '' OR e.school IN %(school_scope)s)")
        else:
            where.append("e.school IN %(school_scope)s")
        params["school_scope"] = tuple(school_scope)


def _apply_crm_scope_conditions(
    where: list[str],
    params: dict,
    *,
    organization: str | None,
    school: str | None,
    fallback_org_scope: list[str] | None = None,
    fallback_school_scope: list[str] | None = None,
    scope_bypass: bool = False,
) -> None:
    organization_name = clean(organization)
    school_name = clean(school)

    org_scope = []
    if organization_name:
        org_scope = [
            clean(value) for value in get_organization_ancestors_including_self(organization_name) if clean(value)
        ]
        if not org_scope:
            where.append("1=0")
            return

    school_scope = []
    if school_name:
        school_scope = [clean(value) for value in get_school_ancestors_including_self(school_name) if clean(value)]
        if not school_scope:
            where.append("1=0")
            return

    if not org_scope and not school_scope and not scope_bypass:
        org_scope = fallback_org_scope or []
        school_scope = fallback_school_scope or []
        if not org_scope and not school_scope:
            where.append("1=0")
            return

    if org_scope:
        where.append("e.organization IN %(crm_org_scope)s")
        params["crm_org_scope"] = tuple(org_scope)

    if school_scope:
        where.append("(IFNULL(e.school, '') = '' OR e.school IN %(crm_school_scope)s)")
        params["crm_school_scope"] = tuple(school_scope)


def _apply_lane_condition(where: list[str], params: dict, lane: str | None) -> None:
    if not lane:
        return

    params["admissions_roles"] = tuple(sorted(ADMISSIONS_ROLES))
    role_exists = "EXISTS (SELECT 1 FROM `tabHas Role` hr WHERE hr.parent = u.name AND hr.role IN %(admissions_roles)s)"
    if lane == "Admission":
        where.append(role_exists)
    elif lane == "Staff":
        where.append(f"NOT {role_exists}")


def _employee_user_rows(
    *,
    where: list[str],
    params: dict,
    limit: int,
) -> list[dict]:
    params["limit"] = limit
    params.setdefault("admissions_roles", tuple(sorted(ADMISSIONS_ROLES)))
    where_clause = " AND ".join(where)
    return frappe.db.sql(
        f"""
        SELECT DISTINCT
            u.name AS value,
            COALESCE(NULLIF(e.employee_full_name, ''), NULLIF(u.full_name, ''), u.name) AS label,
            e.organization,
            e.school,
            CASE
                WHEN EXISTS (
                    SELECT 1 FROM `tabHas Role` lane_hr
                    WHERE lane_hr.parent = u.name
                      AND lane_hr.role IN %(admissions_roles)s
                )
                THEN 'Admission'
                ELSE 'Staff'
            END AS lane
        FROM `tabEmployee` e
        INNER JOIN `tabUser` u ON u.name = e.user_id
        WHERE {where_clause}
        ORDER BY label ASC, u.name ASC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def _search_inquiry_assignees(
    *,
    organization: str | None,
    school: str | None,
    fallback_org_scope: list[str] | None = None,
    fallback_school_scope: list[str] | None = None,
    scope_bypass: bool = False,
    assignment_lane: str | None,
    query: str | None,
    limit: int,
) -> list[dict]:
    lane = _normalize_assignment_lane(assignment_lane)
    where = [
        "u.enabled = 1",
        "IFNULL(e.employment_status, '') = 'Active'",
        "IFNULL(e.user_id, '') <> ''",
    ]
    params: dict = {}
    _apply_inquiry_scope_conditions(
        where,
        params,
        organization=organization,
        school=school,
        fallback_org_scope=fallback_org_scope,
        fallback_school_scope=fallback_school_scope,
        scope_bypass=scope_bypass,
    )
    _apply_lane_condition(where, params, lane)
    _apply_query_condition(where, params, query)

    return [_candidate_dto(row) for row in _employee_user_rows(where=where, params=params, limit=limit)]


def _search_conversation_assignees(
    *,
    organization: str | None,
    school: str | None,
    fallback_org_scope: list[str] | None = None,
    fallback_school_scope: list[str] | None = None,
    scope_bypass: bool = False,
    query: str | None,
    limit: int,
) -> list[dict]:
    where = [
        "u.enabled = 1",
        "IFNULL(e.employment_status, '') = 'Active'",
        "IFNULL(e.user_id, '') <> ''",
        ("EXISTS (SELECT 1 FROM `tabHas Role` crm_hr WHERE crm_hr.parent = u.name AND crm_hr.role IN %(crm_roles)s)"),
    ]
    params: dict = {"crm_roles": tuple(sorted(CRM_MUTATION_ROLES))}
    _apply_crm_scope_conditions(
        where,
        params,
        organization=organization,
        school=school,
        fallback_org_scope=fallback_org_scope,
        fallback_school_scope=fallback_school_scope,
        scope_bypass=scope_bypass,
    )
    _apply_query_condition(where, params, query)

    rows = _employee_user_rows(where=where, params=params, limit=limit)
    return [_candidate_dto(row, force_lane="Admission") for row in rows]


def _resolve_assignee_context(
    user: str,
    *,
    context_doctype: str | None,
    context_name: str | None,
    organization: str | None,
    school: str | None,
) -> tuple[str, str | None, str | None, list[str], list[str], bool]:
    doctype = clean(context_doctype)
    name = clean(context_name)

    if doctype == "Inquiry":
        doc = _require_inquiry_write(user, name)
        return "Inquiry", clean(doc.organization), clean(doc.school), [], [], False

    if doctype == "Admission Conversation":
        doc = _require_conversation_write(user, name)
        return "Admission Conversation", clean(doc.organization), clean(doc.school), [], [], False

    if doctype:
        frappe.throw(_("Unsupported admissions assignee context: {doctype}.").format(doctype=doctype))

    scope = _resolve_scope(user, organization=organization, school=school)
    return (
        "Inquiry",
        clean(scope.get("organization")),
        clean(scope.get("school")),
        list(scope.get("org_scope") or []),
        list(scope.get("school_scope") or []),
        bool(scope.get("bypass")),
    )


def search_admissions_inbox_assignees_impl(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    assignment_lane: str | None = None,
    query: str | None = None,
    limit: int | str | None = None,
) -> list[dict]:
    user = ensure_admissions_crm_permission()
    resolved_limit = _bounded_assignee_limit(limit)
    (
        target,
        resolved_organization,
        resolved_school,
        fallback_org_scope,
        fallback_school_scope,
        scope_bypass,
    ) = _resolve_assignee_context(
        user,
        context_doctype=context_doctype,
        context_name=context_name,
        organization=organization,
        school=school,
    )

    if target == "Admission Conversation":
        return _search_conversation_assignees(
            organization=resolved_organization,
            school=resolved_school,
            fallback_org_scope=fallback_org_scope,
            fallback_school_scope=fallback_school_scope,
            scope_bypass=scope_bypass,
            query=query,
            limit=resolved_limit,
        )

    return _search_inquiry_assignees(
        organization=resolved_organization,
        school=resolved_school,
        fallback_org_scope=fallback_org_scope,
        fallback_school_scope=fallback_school_scope,
        scope_bypass=scope_bypass,
        assignment_lane=assignment_lane,
        query=query,
        limit=resolved_limit,
    )
