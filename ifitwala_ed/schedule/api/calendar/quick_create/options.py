# ifitwala_ed/schedule/api/calendar/quick_create/options.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.api.org_communication_quick_create import get_org_communication_quick_create_capability
from ifitwala_ed.schedule.api.calendar.core import _resolve_employee_for_user
from ifitwala_ed.schedule.api.calendar.quick_create.constants import (
    DEFAULT_DAY_END_TIME,
    DEFAULT_DAY_START_TIME,
    META_SELECT_OPTIONS_CACHE_TTL_SECONDS,
    QUICK_CREATE_OPTIONS_CACHE_TTL_SECONDS,
)
from ifitwala_ed.schedule.api.calendar.quick_create.dto import _safe_text, _split_select_options
from ifitwala_ed.schedule.api.calendar.quick_create.scope import _get_quick_create_scope
from ifitwala_ed.utilities.location_utils import get_visible_location_rows_for_school


def _school_options_for_scope(school_scope: list[str]) -> list[dict]:
    if not school_scope:
        return []
    rows = frappe.get_all(
        "School",
        filters={"name": ["in", school_scope]},
        fields=["name", "school_name"],
        order_by="school_name asc",
        limit=500,
    )
    return [{"value": row.name, "label": row.school_name or row.name} for row in rows]


def _team_option_rows(rows: list[dict]) -> list[dict]:
    options = []
    seen = set()
    for row in sorted(rows, key=lambda item: (item.get("team_name") or item.get("name") or "").lower()):
        team_name = row.get("name")
        if not team_name or team_name in seen:
            continue
        seen.add(team_name)
        options.append({"value": team_name, "label": row.get("team_name") or team_name})
    return options


def _team_options_for_scope(
    user: str,
    school_scope: list[str],
    is_admin_like: bool,
    organization_scope: list[str] | None = None,
) -> list[dict]:
    rows: list[dict] = []
    school_values = [school for school in (school_scope or []) if school]
    organization_values = [org for org in (organization_scope or []) if org]

    if school_values:
        rows.extend(
            frappe.get_all(
                "Team",
                filters={"school": ["in", school_values], "enabled": 1},
                fields=["name", "team_name", "school", "organization"],
                order_by="team_name asc",
                limit=500,
            )
        )

    if organization_values:
        organization_rows = frappe.get_all(
            "Team",
            filters={"organization": ["in", organization_values], "enabled": 1},
            fields=["name", "team_name", "school", "organization"],
            order_by="team_name asc",
            limit=500,
        )
        if school_values:
            school_set = set(school_values)
            rows.extend([row for row in organization_rows if not row.get("school") or row.get("school") in school_set])
        else:
            rows.extend(organization_rows)

    if school_values or organization_values:
        return _team_option_rows(rows)

    if is_admin_like:
        rows = frappe.get_all(
            "Team",
            filters={"enabled": 1},
            fields=["name", "team_name", "school", "organization"],
            order_by="team_name asc",
            limit=500,
        )
        return _team_option_rows(rows)

    employee_row = _resolve_employee_for_user(
        user,
        fields=["name"],
        employment_status_filter=["!=", "Inactive"],
    )
    employee_name = _safe_text((employee_row or {}).get("name"))
    team_or_filters: dict[str, str | list[str]] = {"member": user}
    if employee_name:
        team_or_filters["employee"] = employee_name

    team_names = frappe.get_all(
        "Team Member",
        filters={"parenttype": "Team"},
        or_filters=team_or_filters,
        pluck="parent",
        limit=500,
    )
    if not team_names:
        return []

    rows = frappe.get_all(
        "Team",
        filters={"name": ["in", sorted(set(team_names))]},
        fields=["name", "team_name", "school", "organization"],
        order_by="team_name asc",
        limit=500,
    )
    return _team_option_rows(rows)


def _student_group_options_for_scope(user: str, school_scope: list[str]) -> list[dict]:
    if school_scope:
        rows = frappe.get_all(
            "Student Group",
            filters={"school": ["in", school_scope], "status": "Active"},
            fields=["name", "student_group_name"],
            order_by="student_group_name asc",
            limit=500,
        )
        return [{"value": row.name, "label": row.student_group_name or row.name} for row in rows]

    group_names = frappe.get_all(
        "Student Group Instructor",
        filters={"parenttype": "Student Group", "user_id": user},
        pluck="parent",
        limit=500,
    )
    if not group_names:
        return []

    rows = frappe.get_all(
        "Student Group",
        filters={"name": ["in", sorted(set(group_names))]},
        fields=["name", "student_group_name"],
        order_by="student_group_name asc",
        limit=500,
    )
    return [{"value": row.name, "label": row.student_group_name or row.name} for row in rows]


def _location_options_for_scope(selected_school: str | None, is_admin_like: bool) -> list[dict]:
    if selected_school:
        rows = get_visible_location_rows_for_school(
            selected_school,
            include_groups=False,
            only_schedulable=True,
            fields=[
                "name",
                "location_name",
                "parent_location",
                "location_type",
                "maximum_capacity",
                "is_group",
            ],
            order_by="location_name asc",
            limit=800,
        )
        return [
            {
                "value": row.get("name"),
                "label": row.get("location_name") or row.get("name"),
                "parent_location": row.get("parent_location"),
                "location_type": row.get("location_type"),
                "location_type_name": row.get("location_type_name"),
                "max_capacity": cint(row.get("maximum_capacity"))
                if row.get("maximum_capacity") not in (None, "")
                else None,
            }
            for row in rows
        ]

    if not is_admin_like:
        return []

    rows = frappe.get_all(
        "Location",
        filters={"is_group": 0},
        fields=["name", "location_name", "parent_location"],
        order_by="location_name asc",
        limit=500,
    )
    return [
        {
            "value": row.name,
            "label": row.location_name or row.name,
            "parent_location": row.parent_location,
        }
        for row in rows
    ]


def _location_options_map_for_schools(school_values: list[str], is_admin_like: bool) -> dict[str, list[dict]]:
    payload: dict[str, list[dict]] = {}
    for school_value in school_values or []:
        school_name = _safe_text(school_value)
        if not school_name:
            continue
        payload[school_name] = _location_options_for_scope(school_name, is_admin_like)
    return payload


def _location_type_options_for_scope(selected_school: str | None, is_admin_like: bool) -> list[dict]:
    if selected_school:
        rows = get_visible_location_rows_for_school(
            selected_school,
            include_groups=False,
            only_schedulable=True,
            fields=["name", "location_type", "maximum_capacity", "is_group"],
            order_by="location_name asc",
            limit=800,
        )
        options = []
        seen = set()
        for row in rows:
            location_type = _safe_text(row.get("location_type"))
            location_type_label = _safe_text(row.get("location_type_name"))
            if not location_type or location_type in seen:
                continue
            seen.add(location_type)
            options.append({"value": location_type, "label": location_type_label or location_type})
        options.sort(key=lambda item: (item.get("label") or "").lower())
        return options

    if not is_admin_like:
        return []

    rows = frappe.get_all(
        "Location Type",
        filters={"is_schedulable": 1},
        fields=["name", "location_type_name"],
        order_by="location_type_name asc",
        limit=200,
    )
    return [{"value": row.name, "label": row.location_type_name or row.name} for row in rows]


def _location_type_options_map_for_schools(school_values: list[str], is_admin_like: bool) -> dict[str, list[dict]]:
    payload: dict[str, list[dict]] = {}
    for school_value in school_values or []:
        school_name = _safe_text(school_value)
        if not school_name:
            continue
        payload[school_name] = _location_type_options_for_scope(school_name, is_admin_like)
    return payload


def _cached_select_options(doctype: str, fieldname: str) -> list[str]:
    """
    Shared metadata cache for select options.
    Safe to cache because this is DocType metadata (non user-specific).
    """
    cache_key = f"ifitwala_ed:meta_select_options:{doctype}:{fieldname}"
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached:
        parsed = cached if isinstance(cached, list) else frappe.parse_json(cached)
        if isinstance(parsed, list):
            return [str(v) for v in parsed if str(v).strip()]

    meta = frappe.get_meta(doctype)
    field = meta.get_field(fieldname)
    options = _split_select_options(getattr(field, "options", None))
    cache.set_value(cache_key, frappe.as_json(options), expires_in_sec=META_SELECT_OPTIONS_CACHE_TTL_SECONDS)
    return options


def get_event_quick_create_options():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to create events."), frappe.PermissionError)

    cache = frappe.cache()
    cache_key = f"ifitwala_ed:event_quick_create:options:{user}"
    cached = cache.get_value(cache_key)
    if cached:
        parsed = frappe.parse_json(cached)
        if isinstance(parsed, dict):
            return parsed

    can_create_meeting = bool(frappe.has_permission("Meeting", ptype="create", user=user))
    can_create_school_event = bool(frappe.has_permission("School Event", ptype="create", user=user))

    if not can_create_meeting and not can_create_school_event:
        frappe.throw(_("You do not have permission to create Meetings or School Events."), frappe.PermissionError)

    scope = _get_quick_create_scope(user)
    roles = set(scope.get("roles") or [])

    meeting_category_options = _cached_select_options("Meeting", "meeting_category")
    school_event_category_options = _cached_select_options("School Event", "event_category")
    audience_options = _cached_select_options("School Event Audience", "audience_type")

    from ifitwala_ed.school_settings.doctype.school_event.school_event import (
        ADMIN_AUDIENCE_ROLES,
        BROAD_AUDIENCE_TYPES,
    )

    can_use_broad_audience = user == "Administrator" or bool(roles.intersection(set(ADMIN_AUDIENCE_ROLES)))
    if not can_use_broad_audience:
        audience_options = [value for value in audience_options if value not in BROAD_AUDIENCE_TYPES]

    school_options = _school_options_for_scope(scope.get("school_scope") or [])

    default_school = None
    base_school = scope.get("base_school")
    if base_school and any(opt.get("value") == base_school for opt in school_options):
        default_school = base_school
    elif school_options:
        default_school = school_options[0].get("value")

    school_values = [row.get("value") for row in school_options if row.get("value")]
    is_admin_like = bool(scope.get("is_admin_like"))
    locations_by_school = _location_options_map_for_schools(school_values, is_admin_like)
    location_types_by_school = _location_type_options_map_for_schools(school_values, is_admin_like)
    default_locations = (
        locations_by_school.get(default_school or "", [])
        if default_school
        else _location_options_for_scope(None, is_admin_like)
    )
    default_location_types = (
        location_types_by_school.get(default_school or "", [])
        if default_school
        else _location_type_options_for_scope(None, is_admin_like)
    )
    publish_capability = get_org_communication_quick_create_capability(user=user)

    payload = {
        "can_create_meeting": can_create_meeting,
        "can_create_school_event": can_create_school_event,
        "meeting_categories": meeting_category_options,
        "school_event_categories": school_event_category_options,
        "audience_types": audience_options,
        "schools": school_options,
        "teams": _team_options_for_scope(
            user,
            scope.get("school_scope") or [],
            bool(scope.get("is_admin_like")),
            scope.get("organization_scope") or [],
        ),
        "student_groups": _student_group_options_for_scope(user, scope.get("school_scope") or []),
        "locations": default_locations,
        "locations_by_school": locations_by_school,
        "location_types": default_location_types,
        "location_types_by_school": location_types_by_school,
        "attendee_kinds": [
            {"value": "employee", "label": "Employees"},
            {"value": "student", "label": "Students"},
            {"value": "guardian", "label": "Guardians"},
        ],
        "announcement_publish": {
            "enabled": bool(publish_capability.get("enabled")),
            "blocked_reason": _safe_text(publish_capability.get("blocked_reason")) or None,
        },
        "defaults": {
            "school": default_school,
            "day_start_time": DEFAULT_DAY_START_TIME,
            "day_end_time": DEFAULT_DAY_END_TIME,
            "duration_minutes": 60,
        },
    }
    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=QUICK_CREATE_OPTIONS_CACHE_TTL_SECONDS)
    return payload
