# ifitwala_ed/admission/api/inquiry/scope.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.admission_utils import get_admissions_file_staff_scope
from ifitwala_ed.admission.api.inquiry.dates import _resolve_window
from ifitwala_ed.utilities.employee_utils import get_schools_for_organization_scope
from ifitwala_ed.utilities.school_tree import get_descendant_schools

SUBMITTED_LOCAL_EXPR = "i.submitted_at"


def _clean_values(values) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = (value or "").strip()
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return cleaned


def _get_descendant_organizations(root_org: str):
    if not root_org:
        return []
    org_bounds = frappe.db.get_value("Organization", root_org, ["lft", "rgt"], as_dict=True)
    if not org_bounds:
        return []
    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabOrganization`
        WHERE lft >= %(lft)s AND rgt <= %(rgt)s
        ORDER BY lft ASC, name ASC
        """,
        {"lft": org_bounds.lft, "rgt": org_bounds.rgt},
        as_list=True,
    )
    return [r[0] for r in rows]


def _apply_user_scope_conditions(user: str, conds: list, params: dict, alias: str = "i") -> None:
    """Apply the staff user's institutional Inquiry visibility scope before aggregation."""
    scope = get_admissions_file_staff_scope(user)
    if not scope.get("allowed"):
        conds.append("1=0")
        return

    if scope.get("bypass"):
        return

    roles = set(frappe.get_roles(user))
    org_scope = _clean_values(scope.get("org_scope") or [])
    school_scope = _clean_values(scope.get("school_scope") or [])

    visibility_clauses = [f"{alias}.assigned_to = %(visible_user)s"]
    params["visible_user"] = user

    if school_scope:
        visibility_clauses.append(f"{alias}.school IN %(user_school_scope)s")
        params["user_school_scope"] = tuple(school_scope)
    elif org_scope:
        visibility_clauses.append(f"{alias}.organization IN %(user_org_scope)s")
        params["user_org_scope"] = tuple(org_scope)

        org_schools = _clean_values(get_schools_for_organization_scope(org_scope))
        if org_schools:
            visibility_clauses.append(f"{alias}.school IN %(user_org_school_scope)s")
            params["user_org_school_scope"] = tuple(org_schools)

    if "Admission Manager" in roles and org_scope:
        visibility_clauses.append(f"((IFNULL({alias}.organization, '') = '') AND (IFNULL({alias}.school, '') = ''))")

    conds.append("(" + " OR ".join(visibility_clauses) + ")")


def _apply_org_school_conditions(filters: dict, conds: list, params: dict):
    org_filter = filters.get("organization")
    if org_filter:
        orgs = _get_descendant_organizations(org_filter)
        if orgs:
            conds.append("i.organization IN %(organizations)s")
            params["organizations"] = tuple(orgs)
        else:
            conds.append("1=0")

    school_filter = filters.get("school")
    if school_filter:
        schools = get_descendant_schools(school_filter)
        if schools:
            conds.append("i.school IN %(schools)s")
            params["schools"] = tuple(schools)
        else:
            conds.append("1=0")


def _apply_common_conditions(filters: dict, site_tz: str, user: str | None = None):
    conds = []
    params = {}
    fd, td = _resolve_window(filters)
    conds.append(f"{SUBMITTED_LOCAL_EXPR} >= %(from)s AND {SUBMITTED_LOCAL_EXPR} <= %(to)s")
    params.update(
        {
            "from": f"{fd} 00:00:00",
            "to": f"{td} 23:59:59",
            "site_tz": site_tz,
        }
    )

    if user:
        _apply_user_scope_conditions(user, conds, params)

    _apply_org_school_conditions(filters, conds, params)

    if filters.get("type_of_inquiry"):
        conds.append("i.type_of_inquiry = %(type)s")
        params["type"] = filters["type_of_inquiry"]

    if filters.get("source"):
        conds.append("i.source = %(source)s")
        params["source"] = filters["source"]

    if filters.get("assigned_to"):
        conds.append("i.assigned_to = %(assignee)s")
        params["assignee"] = filters["assigned_to"]

    if filters.get("sla_status"):
        conds.append("i.sla_status = %(sla)s")
        params["sla"] = filters["sla_status"]

    lane = (filters.get("assignment_lane") or "").strip()
    if lane:
        if lane not in ("Admission", "Staff"):
            frappe.throw("Invalid assignment_lane filter.")
        conds.append("COALESCE(i.assignment_lane, 'Admission') = %(assignment_lane)s")
        params["assignment_lane"] = lane

    return " AND ".join(conds), params


def _rest_conditions(filters: dict, user: str | None = None):
    conds, params = [], {}
    if user:
        _apply_user_scope_conditions(user, conds, params)
    _apply_org_school_conditions(filters, conds, params)
    if filters.get("type_of_inquiry"):
        conds.append("i.type_of_inquiry = %(type)s")
        params["type"] = filters["type_of_inquiry"]
    if filters.get("source"):
        conds.append("i.source = %(source)s")
        params["source"] = filters["source"]
    if filters.get("assigned_to"):
        conds.append("i.assigned_to = %(assignee)s")
        params["assignee"] = filters["assigned_to"]
    if filters.get("sla_status"):
        conds.append("i.sla_status = %(sla)s")
        params["sla"] = filters["sla_status"]
    lane = (filters.get("assignment_lane") or "").strip()
    if lane:
        if lane not in ("Admission", "Staff"):
            frappe.throw("Invalid assignment_lane filter.")
        conds.append("COALESCE(i.assignment_lane, 'Admission') = %(assignment_lane)s")
        params["assignment_lane"] = lane
    return " AND ".join(conds) or "1=1", params
