# ifitwala_ed/schedule/api/calendar/quick_create/scope.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.api.student_log_dashboard import get_authorized_schools
from ifitwala_ed.schedule.api.calendar.core import _resolve_employee_for_user
from ifitwala_ed.schedule.api.calendar.quick_create.constants import (
    QUICK_CREATE_OPTIONS_CACHE_TTL_SECONDS,
    VIRTUAL_ORGANIZATION_ROOT,
)
from ifitwala_ed.schedule.api.calendar.quick_create.dto import _safe_text
from ifitwala_ed.utilities.employee_utils import get_ancestor_organizations, get_descendant_organizations
from ifitwala_ed.utilities.location_utils import get_visible_location_rows_for_school
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools


def _employee_collaboration_organization_scope(organization: str | None) -> list[str]:
    organization_value = _safe_text(organization)
    if not organization_value:
        return []

    ancestors = [
        org
        for org in (get_ancestor_organizations(organization_value) or [organization_value])
        if org and org != VIRTUAL_ORGANIZATION_ROOT
    ]
    collaboration_root = ancestors[-1] if ancestors else organization_value
    return get_descendant_organizations(collaboration_root) or [collaboration_root]


def _get_quick_create_scope(user: str) -> dict:
    cache = frappe.cache()
    cache_key = f"ifitwala_ed:event_quick_create:scope:{user}"
    cached = cache.get_value(cache_key)
    if cached:
        parsed = frappe.parse_json(cached)
        if isinstance(parsed, dict):
            return parsed

    roles = set(frappe.get_roles(user))
    is_admin_like = user == "Administrator" or "System Manager" in roles

    employee_row = _resolve_employee_for_user(
        user,
        fields=["school", "organization"],
        employment_status_filter=["!=", "Inactive"],
    )
    base_school = _safe_text((employee_row or {}).get("school")) or _safe_text(
        frappe.defaults.get_user_default("school", user=user)
    )
    organization = _safe_text((employee_row or {}).get("organization"))
    organization_scope = get_descendant_organizations(organization) if organization else []
    employee_collaboration_organization_scope = _employee_collaboration_organization_scope(organization)

    school_scope: list[str] = []
    if base_school:
        school_scope = get_descendant_schools(base_school) or [base_school]
    elif is_admin_like:
        school_scope = frappe.get_all(
            "School",
            filters={"is_group": 0},
            pluck="name",
            limit=500,
        )

    student_scope = get_authorized_schools(user) or school_scope

    payload = {
        "roles": sorted(roles),
        "is_admin_like": bool(is_admin_like),
        "base_school": base_school or None,
        "organization": organization or None,
        "organization_scope": organization_scope,
        "employee_collaboration_organization_scope": employee_collaboration_organization_scope,
        "school_scope": school_scope,
        "student_scope": student_scope,
    }
    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=QUICK_CREATE_OPTIONS_CACHE_TTL_SECONDS)
    return payload


def _ensure_can_create_meeting(user: str) -> None:
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to create meetings."), frappe.PermissionError)
    if not frappe.has_permission("Meeting", ptype="create", user=user):
        frappe.throw(_("You do not have permission to create meetings."), frappe.PermissionError)


def _ensure_allowed_school(user: str, school: str | None) -> str | None:
    school_value = _safe_text(school) or None
    if not school_value:
        return None

    scope = _get_quick_create_scope(user)
    allowed = set(scope.get("school_scope") or [])
    if not bool(scope.get("is_admin_like")) and school_value not in allowed:
        frappe.throw(
            _("You are not allowed to schedule meetings for school {school}.").format(school=school_value),
            frappe.PermissionError,
        )
    return school_value


def _ensure_allowed_location(user: str, school: str | None, location: str | None) -> str | None:
    location_value = _safe_text(location) or None
    if not location_value:
        return None

    school_value = _safe_text(school) or None
    scope = _get_quick_create_scope(user)
    candidate_schools = [school_value] if school_value else []
    if not candidate_schools and scope.get("base_school"):
        candidate_schools = [_safe_text(scope.get("base_school"))]

    allowed_locations: set[str] = set()
    for school_name in candidate_schools:
        rows = get_visible_location_rows_for_school(
            school_name,
            include_groups=False,
            only_schedulable=True,
            fields=["name", "location_name", "location_type", "maximum_capacity", "is_group"],
            order_by="location_name asc",
            limit=800,
        )
        allowed_locations.update(row.get("name") for row in rows if row.get("name"))

    if not candidate_schools and bool(scope.get("is_admin_like")):
        admin_rows = frappe.get_all(
            "Location",
            filters={"is_group": 0},
            fields=["name"],
            limit=800,
        )
        allowed_locations.update(row.name for row in admin_rows if row.name)

    if location_value not in allowed_locations:
        frappe.throw(
            _("You are not allowed to use location {location} for the selected host school.").format(
                location=location_value
            ),
            frappe.PermissionError,
        )

    return location_value


def _ensure_allowed_location_type(user: str, school: str | None, location_type: str | None) -> str | None:
    from ifitwala_ed.schedule.api.calendar.quick_create.options import _location_type_options_for_scope

    location_type_value = _safe_text(location_type) or None
    if not location_type_value:
        return None

    school_value = _safe_text(school) or None
    scope = _get_quick_create_scope(user)
    selected_school = school_value or _safe_text(scope.get("base_school")) or None
    type_options = _location_type_options_for_scope(selected_school, bool(scope.get("is_admin_like")))
    allowed = {row.get("value") for row in type_options if row.get("value")}

    if location_type_value not in allowed:
        frappe.throw(
            _("You are not allowed to filter by location type {location_type} for the selected host school.").format(
                location_type=location_type_value
            ),
            frappe.PermissionError,
        )

    return location_type_value


def _ensure_allowed_team(user: str, team: str | None) -> str | None:
    from ifitwala_ed.schedule.api.calendar.quick_create.options import _team_options_for_scope

    team_value = _safe_text(team) or None
    if not team_value:
        return None

    scope = _get_quick_create_scope(user)
    team_options = _team_options_for_scope(
        user,
        scope.get("school_scope") or [],
        bool(scope.get("is_admin_like")),
        scope.get("organization_scope") or [],
    )
    allowed = {row.get("value") for row in team_options if row.get("value")}
    if not bool(scope.get("is_admin_like")) and team_value not in allowed:
        frappe.throw(
            _("You are not allowed to use team {team} in quick create.").format(team=team_value),
            frappe.PermissionError,
        )
    return team_value


def _school_lineage(school: str) -> tuple[str, ...]:
    if not school:
        return tuple()
    return tuple(get_ancestor_schools(school) or [school])
