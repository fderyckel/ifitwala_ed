# ifitwala_ed/api/calendar_quick_create.py

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from hashlib import sha1
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint, format_datetime, get_datetime, get_time, getdate
from frappe.utils.caching import redis_cache

from ifitwala_ed.api.calendar_core import (
    _coerce_time,
    _course_meta_map,
    _resolve_employee_for_user,
    _system_tzinfo,
    _to_system_datetime,
)
from ifitwala_ed.api.org_communication_quick_create import (
    create_org_communication_quick,
    get_org_communication_quick_create_capability,
)
from ifitwala_ed.api.student_log_dashboard import get_authorized_schools
from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots
from ifitwala_ed.setup.doctype.org_communication.org_communication import (
    get_org_communication_allowed_portal_surfaces,
    resolve_org_communication_delivery_profile,
)
from ifitwala_ed.utilities.location_utils import find_room_conflicts, get_visible_location_rows_for_school
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools

QUICK_CREATE_IDEMPOTENCY_TTL_SECONDS = 900
META_SELECT_OPTIONS_CACHE_TTL_SECONDS = 3600
QUICK_CREATE_OPTIONS_CACHE_TTL_SECONDS = 300
ATTENDEE_SEARCH_CACHE_TTL_SECONDS = 60
SLOT_SUGGESTION_CACHE_TTL_SECONDS = 60
ROOM_SUGGESTION_CACHE_TTL_SECONDS = 60
MAX_ATTENDEE_SEARCH_RESULTS = 12
MAX_SLOT_SUGGESTIONS = 5
MAX_SLOT_FALLBACKS = 3
MAX_SLOT_ATTENDEES = 20
MAX_SLOT_SEARCH_DAYS = 14
SLOT_INCREMENT_MINUTES = 15
DEFAULT_DAY_START_TIME = "08:00:00"
DEFAULT_DAY_END_TIME = "17:00:00"


class StudentAvailabilityConflictError(frappe.ValidationError):
    pass


def _split_select_options(raw: str | None) -> list[str]:
    options = []
    seen = set()
    for line in (raw or "").splitlines():
        value = (line or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        options.append(value)
    return options


def _safe_text(value: object | None) -> str:
    return str(value or "").strip()


def _desk_route_slug(doctype: str) -> str:
    return frappe.scrub(doctype).replace("_", "-")


def _doc_url(doctype: str, name: str) -> str:
    slug = _desk_route_slug(doctype)
    return f"/desk/{slug}/{quote(_safe_text(name), safe='')}"


def _parse_user_list(value: object | None) -> list[str]:
    if value is None:
        return []

    raw = value
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                raw = frappe.parse_json(text)
            except Exception:
                raw = [part.strip() for part in text.split(",")]
        else:
            raw = [part.strip() for part in text.split(",")]

    users: list[str] = []
    seen = set()

    if not isinstance(raw, list):
        raw = [raw]

    for item in raw:
        if isinstance(item, dict):
            candidate = item.get("participant") or item.get("user") or item.get("value")
        else:
            candidate = item
        user_id = _safe_text(candidate)
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        users.append(user_id)

    return users


def _parse_attendee_list(value: object | None) -> list[dict]:
    if value is None:
        return []

    raw = value
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            raw = frappe.parse_json(text)
        except Exception:
            raw = [{"user": part.strip()} for part in text.split(",")]

    if not isinstance(raw, list):
        raw = [raw]

    attendees: list[dict] = []
    seen = set()
    for item in raw:
        if isinstance(item, dict):
            user_id = _safe_text(item.get("user") or item.get("participant") or item.get("value"))
            kind = _safe_text(item.get("kind")).lower()
            label = _safe_text(item.get("label"))
        else:
            user_id = _safe_text(item)
            kind = ""
            label = ""
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        attendees.append({"user": user_id, "kind": kind, "label": label})
    return attendees


def _normalize_attendee_kinds(value: object | None) -> list[str]:
    raw = value
    if raw is None:
        return ["employee", "student", "guardian"]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return ["employee", "student", "guardian"]
        if text.startswith("["):
            try:
                raw = frappe.parse_json(text)
            except Exception:
                raw = [part.strip() for part in text.split(",")]
        else:
            raw = [part.strip() for part in text.split(",")]
    if not isinstance(raw, list):
        raw = [raw]
    kinds: list[str] = []
    seen = set()
    for item in raw:
        kind = _safe_text(item).lower()
        if kind not in {"employee", "student", "guardian"} or kind in seen:
            continue
        seen.add(kind)
        kinds.append(kind)
    return kinds or ["employee", "student", "guardian"]


def _json_cache_key(prefix: str, payload: dict) -> str:
    digest = sha1(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _pick_publish_portal_surface(audiences: list[dict]) -> str:
    profile = resolve_org_communication_delivery_profile(audiences)
    allowed_surfaces = list(get_org_communication_allowed_portal_surfaces(profile))
    if "Portal Feed" in allowed_surfaces and profile == "portal_only":
        return "Portal Feed"
    if "Everywhere" in allowed_surfaces:
        return "Everywhere"
    if "Portal Feed" in allowed_surfaces:
        return "Portal Feed"
    if "Desk" in allowed_surfaces:
        return "Desk"
    if "Morning Brief" in allowed_surfaces:
        return "Morning Brief"
    return "Portal Feed"


def _build_published_org_communication_audiences(
    *,
    school: str,
    audience_type: str,
    audience_team: str | None,
    audience_student_group: str | None,
    include_guardians: int,
    include_students: int,
) -> list[dict]:
    include_guardians_flag = cint(include_guardians)
    include_students_flag = cint(include_students)

    if audience_type == "All Students, Guardians, and Employees":
        return [
            {
                "target_mode": "School Scope",
                "school": school,
                "team": None,
                "student_group": None,
                "include_descendants": 1,
                "to_staff": 1,
                "to_students": 1,
                "to_guardians": 1,
                "note": None,
            }
        ]

    if audience_type == "All Students":
        return [
            {
                "target_mode": "School Scope",
                "school": school,
                "team": None,
                "student_group": None,
                "include_descendants": 1,
                "to_staff": 0,
                "to_students": 1,
                "to_guardians": 1 if include_guardians_flag else 0,
                "note": None,
            }
        ]

    if audience_type == "All Guardians":
        return [
            {
                "target_mode": "School Scope",
                "school": school,
                "team": None,
                "student_group": None,
                "include_descendants": 1,
                "to_staff": 0,
                "to_students": 1 if include_students_flag else 0,
                "to_guardians": 1,
                "note": None,
            }
        ]

    if audience_type == "All Employees":
        return [
            {
                "target_mode": "School Scope",
                "school": school,
                "team": None,
                "student_group": None,
                "include_descendants": 1,
                "to_staff": 1,
                "to_students": 1 if include_students_flag else 0,
                "to_guardians": 0,
                "note": None,
            }
        ]

    if audience_type == "Students in Student Group":
        if not audience_student_group:
            frappe.throw(_("Student Group is required to publish this announcement."), frappe.ValidationError)
        return [
            {
                "target_mode": "Student Group",
                "school": None,
                "team": None,
                "student_group": audience_student_group,
                "include_descendants": 0,
                "to_staff": 0,
                "to_students": 1,
                "to_guardians": 1 if include_guardians_flag else 0,
                "note": None,
            }
        ]

    if audience_type == "Employees in Team":
        if include_students_flag:
            frappe.throw(
                _(
                    "Also publish announcement does not support 'Include Students' when audience type is 'Employees in Team'."
                ),
                frappe.ValidationError,
            )
        if not audience_team:
            frappe.throw(_("Team is required to publish this announcement."), frappe.ValidationError)
        return [
            {
                "target_mode": "Team",
                "school": None,
                "team": audience_team,
                "student_group": None,
                "include_descendants": 0,
                "to_staff": 1,
                "to_students": 0,
                "to_guardians": 0,
                "note": None,
            }
        ]

    if audience_type == "Custom Users":
        frappe.throw(
            _(
                "Also publish announcement is not available for 'Custom Users'. Create the event first, then publish a separate Org Communication if needed."
            ),
            frappe.ValidationError,
        )

    frappe.throw(
        _("Audience type {audience_type} is not supported for announcement publishing.").format(
            audience_type=audience_type
        ),
        frappe.ValidationError,
    )


def _publish_org_communication_for_school_event(
    *,
    request_id: str,
    event_name: str,
    subject: str,
    school: str,
    description: str | None,
    announcement_message: str | None,
    audience_type: str,
    audience_team: str | None,
    audience_student_group: str | None,
    include_guardians: int,
    include_students: int,
) -> dict:
    school_row = frappe.db.get_value("School", school, ["organization"], as_dict=True) or {}
    organization = _safe_text(school_row.get("organization"))
    if not organization:
        frappe.throw(
            _("School {school} is missing an organization, so the announcement cannot be published.").format(
                school=school
            ),
            frappe.ValidationError,
        )

    message_value = announcement_message if _safe_text(announcement_message) else description
    if not _safe_text(message_value):
        frappe.throw(
            _("Add an announcement message or event description before publishing the announcement."),
            frappe.ValidationError,
        )

    audiences = _build_published_org_communication_audiences(
        school=school,
        audience_type=audience_type,
        audience_team=audience_team,
        audience_student_group=audience_student_group,
        include_guardians=include_guardians,
        include_students=include_students,
    )

    response = create_org_communication_quick(
        title=subject,
        communication_type="Event Announcement",
        status="Published",
        priority="Normal",
        portal_surface=_pick_publish_portal_surface(audiences),
        organization=organization,
        school=school,
        message=message_value,
        internal_note=_("Published from School Event {event_name}.").format(event_name=event_name),
        interaction_mode="None",
        allow_private_notes=0,
        allow_public_thread=0,
        audiences=audiences,
        client_request_id=f"{request_id}:publish",
    )
    return {
        "name": response.get("name"),
        "title": response.get("title"),
        "status": response.get("status"),
    }


def _idempotency_key(doctype: str, user: str, client_request_id: str) -> str:
    return f"ifitwala_ed:event_quick_create:{doctype}:{user}:{client_request_id}"


def _run_idempotent_create(
    *,
    doctype: str,
    user: str,
    client_request_id: str,
    create_fn,
) -> dict:
    cache = frappe.cache()
    cache_key = _idempotency_key(doctype, user, client_request_id)

    existing = cache.get_value(cache_key)
    if existing:
        parsed = frappe.parse_json(existing)
        if isinstance(parsed, dict):
            return {**parsed, "status": "already_processed", "idempotent": True}

    lock_key = f"ifitwala_ed:lock:event_quick_create:{doctype}:{user}:{client_request_id}"
    with cache.lock(lock_key, timeout=15):
        existing = cache.get_value(cache_key)
        if existing:
            parsed = frappe.parse_json(existing)
            if isinstance(parsed, dict):
                return {**parsed, "status": "already_processed", "idempotent": True}

        result = create_fn()
        cache.set_value(cache_key, frappe.as_json(result), expires_in_sec=QUICK_CREATE_IDEMPOTENCY_TTL_SECONDS)
        return result


def _target_payload(*, doctype: str, name: str, label: str) -> dict:
    return {
        "target_doctype": doctype,
        "target_name": name,
        "target_url": _doc_url(doctype, name),
        "target_label": label,
    }


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


def _team_options_for_scope(user: str, school_scope: list[str], is_admin_like: bool) -> list[dict]:
    if school_scope:
        rows = frappe.get_all(
            "Team",
            filters={"school": ["in", school_scope], "enabled": 1},
            fields=["name", "team_name"],
            order_by="team_name asc",
            limit=500,
        )
        return [{"value": row.name, "label": row.team_name or row.name} for row in rows]

    if is_admin_like:
        rows = frappe.get_all(
            "Team",
            filters={"enabled": 1},
            fields=["name", "team_name"],
            order_by="team_name asc",
            limit=500,
        )
        return [{"value": row.name, "label": row.team_name or row.name} for row in rows]

    team_names = frappe.get_all(
        "Team Member",
        filters={"parenttype": "Team", "member": user},
        pluck="parent",
        limit=500,
    )
    if not team_names:
        return []

    rows = frappe.get_all(
        "Team",
        filters={"name": ["in", sorted(set(team_names))]},
        fields=["name", "team_name"],
        order_by="team_name asc",
        limit=500,
    )
    return [{"value": row.name, "label": row.team_name or row.name} for row in rows]


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
            _("You are not allowed to schedule meetings for school {0}.").format(school_value),
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
            _("You are not allowed to use location {0} for the selected host school.").format(location_value),
            frappe.PermissionError,
        )

    return location_value


def _ensure_allowed_location_type(user: str, school: str | None, location_type: str | None) -> str | None:
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
            _("You are not allowed to filter by location type {0} for the selected host school.").format(
                location_type_value
            ),
            frappe.PermissionError,
        )

    return location_type_value


def _ensure_allowed_team(user: str, team: str | None) -> str | None:
    team_value = _safe_text(team) or None
    if not team_value:
        return None

    scope = _get_quick_create_scope(user)
    team_options = _team_options_for_scope(
        user,
        scope.get("school_scope") or [],
        bool(scope.get("is_admin_like")),
    )
    allowed = {row.get("value") for row in team_options if row.get("value")}
    if not bool(scope.get("is_admin_like")) and team_value not in allowed:
        frappe.throw(
            _("You are not allowed to use team {0} in quick create.").format(team_value),
            frappe.PermissionError,
        )
    return team_value


@redis_cache(ttl=600)
def _school_lineage(school: str) -> tuple[str, ...]:
    if not school:
        return tuple()
    return tuple(get_ancestor_schools(school) or [school])


def _coerce_minutes(value: object | None, *, default: int, minimum: int, maximum: int, label: str) -> int:
    try:
        minutes = int(value or default)
    except Exception:
        frappe.throw(_("{0} must be a whole number.").format(label))
    if minutes < minimum or minutes > maximum:
        frappe.throw(_("{0} must be between {1} and {2}.").format(label, minimum, maximum))
    return minutes


def _coerce_date_required(value: object | None, label: str) -> date:
    try:
        parsed = getdate(value)
    except Exception:
        parsed = None
    if not parsed:
        frappe.throw(_("{0} is required.").format(label))
    return parsed


def _coerce_time_required(value: object | None, label: str):
    parsed = _coerce_time(value)
    if not parsed:
        try:
            parsed = get_time(value)
        except Exception:
            parsed = None
    if not parsed:
        frappe.throw(_("{0} is required.").format(label))
    return parsed


def _coerce_flag(value: object | None) -> bool:
    if isinstance(value, bool):
        return value
    text = _safe_text(value).lower()
    if text in {"", "0", "false", "no"}:
        return False
    if text in {"1", "true", "yes"}:
        return True
    return bool(value)


def _combine_date_and_time_local(day: date, time_value) -> datetime:
    return get_datetime(f"{day.isoformat()} {time_value}")


def _format_slot_label(start_dt: datetime, end_dt: datetime) -> str:
    return f"{format_datetime(start_dt, 'EEE d MMM yyyy HH:mm')} - {format_datetime(end_dt, 'HH:mm')}"


def _current_user_label(user: str) -> str:
    return frappe.db.get_value("User", user, "full_name") or user


def _search_employee_attendees(*, user: str, organization: str | None, query: str, limit: int) -> list[dict]:
    params = {
        "query": f"%{query}%",
        "limit": limit,
        "current_user": user,
    }

    org_sql = ""
    if organization:
        org_sql = "AND e.organization = %(organization)s"
        params["organization"] = organization

    rows = frappe.db.sql(
        f"""
        SELECT
            u.name AS user_id,
            COALESCE(NULLIF(u.full_name, ''), NULLIF(e.employee_full_name, ''), u.name) AS label,
            e.school AS school
        FROM `tabEmployee` e
        INNER JOIN `tabUser` u ON u.name = e.user_id
        WHERE
            e.user_id IS NOT NULL
            AND e.employment_status = 'Active'
            AND COALESCE(u.enabled, 1) = 1
            AND u.name != %(current_user)s
            {org_sql}
            AND (
                u.name LIKE %(query)s
                OR u.full_name LIKE %(query)s
                OR e.name LIKE %(query)s
                OR e.employee_full_name LIKE %(query)s
            )
        ORDER BY label ASC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )
    return [
        {
            "value": row.get("user_id"),
            "label": row.get("label") or row.get("user_id"),
            "meta": row.get("school") or _("Employee"),
            "kind": "employee",
            "availability_mode": "authoritative",
        }
        for row in rows
        if row.get("user_id")
    ]


def _search_student_attendees(*, school_scope: list[str], query: str, limit: int) -> list[dict]:
    if not school_scope:
        return []

    rows = frappe.db.sql(
        """
        SELECT
            u.name AS user_id,
            COALESCE(NULLIF(s.student_preferred_name, ''), NULLIF(s.student_full_name, ''), s.name) AS label,
            s.anchor_school AS school
        FROM `tabStudent` s
        INNER JOIN `tabUser` u ON u.name = s.student_email
        WHERE
            s.enabled = 1
            AND COALESCE(u.enabled, 1) = 1
            AND s.anchor_school IN %(schools)s
            AND (
                s.name LIKE %(query)s
                OR s.student_email LIKE %(query)s
                OR s.student_full_name LIKE %(query)s
                OR s.student_preferred_name LIKE %(query)s
            )
        ORDER BY label ASC
        LIMIT %(limit)s
        """,
        {
            "schools": tuple(school_scope),
            "query": f"%{query}%",
            "limit": limit,
        },
        as_dict=True,
    )
    return [
        {
            "value": row.get("user_id"),
            "label": row.get("label") or row.get("user_id"),
            "meta": row.get("school") or _("Student"),
            "kind": "student",
            "availability_mode": "school_schedule",
        }
        for row in rows
        if row.get("user_id")
    ]


def _search_guardian_attendees(*, school_scope: list[str], query: str, limit: int) -> list[dict]:
    if not school_scope:
        return []

    rows = frappe.db.sql(
        """
        SELECT DISTINCT
            u.name AS user_id,
            COALESCE(NULLIF(u.full_name, ''), NULLIF(g.guardian_full_name, ''), NULLIF(g.guardian_email, ''), u.name) AS label,
            s.student_full_name AS student_name
        FROM `tabGuardian` g
        INNER JOIN `tabUser` u ON u.name = g.user
        INNER JOIN `tabStudent Guardian` sg
            ON sg.guardian = g.name
            AND sg.parenttype = 'Student'
        INNER JOIN `tabStudent` s ON s.name = sg.parent
        WHERE
            g.user IS NOT NULL
            AND s.enabled = 1
            AND COALESCE(u.enabled, 1) = 1
            AND s.anchor_school IN %(schools)s
            AND (
                g.name LIKE %(query)s
                OR g.guardian_full_name LIKE %(query)s
                OR g.guardian_email LIKE %(query)s
                OR u.name LIKE %(query)s
                OR u.full_name LIKE %(query)s
                OR s.student_full_name LIKE %(query)s
            )
        ORDER BY label ASC
        LIMIT %(limit)s
        """,
        {
            "schools": tuple(school_scope),
            "query": f"%{query}%",
            "limit": limit,
        },
        as_dict=True,
    )
    return [
        {
            "value": row.get("user_id"),
            "label": row.get("label") or row.get("user_id"),
            "meta": row.get("student_name") or _("Guardian"),
            "kind": "guardian",
            "availability_mode": "school_meetings_only",
        }
        for row in rows
        if row.get("user_id")
    ]


def _resolve_attendee_contexts(attendees: list[dict], organizer_user: str) -> list[dict]:
    ordered_users: list[str] = []
    requested_kind: dict[str, str] = {}
    requested_label: dict[str, str] = {}

    for attendee in attendees:
        user_id = _safe_text(attendee.get("user"))
        if not user_id:
            continue
        if user_id not in ordered_users:
            ordered_users.append(user_id)
        kind = _safe_text(attendee.get("kind")).lower()
        if kind in {"employee", "student", "guardian"}:
            requested_kind[user_id] = kind
        if _safe_text(attendee.get("label")):
            requested_label[user_id] = _safe_text(attendee.get("label"))

    if organizer_user not in ordered_users:
        ordered_users.insert(0, organizer_user)

    employee_rows = frappe.get_all(
        "Employee",
        filters={"user_id": ["in", ordered_users], "employment_status": "Active"},
        fields=["name", "user_id", "employee_full_name", "school", "organization"],
        limit=max(len(ordered_users), 1),
    )
    employee_by_user = {row.user_id: row for row in employee_rows if row.user_id}

    student_rows = frappe.get_all(
        "Student",
        filters={"student_email": ["in", ordered_users], "enabled": 1},
        fields=["name", "student_email", "student_full_name", "student_preferred_name", "anchor_school"],
        limit=max(len(ordered_users), 1),
    )
    student_by_user = {row.student_email: row for row in student_rows if row.student_email}

    guardian_rows = frappe.get_all(
        "Guardian",
        filters={"user": ["in", ordered_users]},
        fields=["name", "user", "guardian_full_name"],
        limit=max(len(ordered_users), 1),
    )
    guardian_by_user = {row.user: row for row in guardian_rows if row.user}

    user_rows = frappe.get_all(
        "User",
        filters={"name": ["in", ordered_users]},
        fields=["name", "full_name"],
        limit=max(len(ordered_users), 1),
    )
    user_labels = {row.name: (row.full_name or row.name) for row in user_rows if row.name}

    student_groups_by_student: dict[str, set[str]] = defaultdict(set)
    student_names = [row.name for row in student_rows if row.name]
    if student_names:
        memberships = frappe.get_all(
            "Student Group Student",
            filters={"student": ["in", student_names], "active": 1},
            fields=["student", "parent"],
            limit=max(len(student_names) * 5, 20),
        )
        for row in memberships:
            if row.student and row.parent:
                student_groups_by_student[row.student].add(row.parent)

    guardian_school_map: dict[str, set[str]] = defaultdict(set)
    guardian_group_map: dict[str, set[str]] = defaultdict(set)
    guardian_names = [row.name for row in guardian_rows if row.name]
    if guardian_names:
        guardian_students = frappe.get_all(
            "Guardian Student",
            filters={"parent": ["in", guardian_names], "parenttype": "Guardian"},
            fields=["parent", "student"],
            limit=max(len(guardian_names) * 5, 20),
        )
        guardian_student_names = {row.student for row in guardian_students if row.student}
        if guardian_student_names:
            student_meta = frappe.get_all(
                "Student",
                filters={"name": ["in", list(guardian_student_names)], "enabled": 1},
                fields=["name", "anchor_school"],
                limit=max(len(guardian_student_names), 1),
            )
            student_school_map = {row.name: row.anchor_school for row in student_meta if row.name}

            guardian_memberships = frappe.get_all(
                "Student Group Student",
                filters={"student": ["in", list(guardian_student_names)], "active": 1},
                fields=["student", "parent"],
                limit=max(len(guardian_student_names) * 5, 20),
            )
            student_group_map: dict[str, set[str]] = defaultdict(set)
            for row in guardian_memberships:
                if row.student and row.parent:
                    student_group_map[row.student].add(row.parent)

            guardian_name_by_user = {row.user: row.name for row in guardian_rows if row.user and row.name}
            for row in guardian_students:
                guardian_name = row.parent
                student_name = row.student
                if not guardian_name or not student_name:
                    continue
                user_id = next(
                    (user for user, name in guardian_name_by_user.items() if name == guardian_name),
                    None,
                )
                if not user_id:
                    continue
                school = student_school_map.get(student_name)
                if school:
                    guardian_school_map[user_id].add(school)
                guardian_group_map[user_id].update(student_group_map.get(student_name) or set())

    contexts: list[dict] = []
    for user_id in ordered_users:
        employee_row = employee_by_user.get(user_id)
        student_row = student_by_user.get(user_id)
        guardian_row = guardian_by_user.get(user_id)
        requested = requested_kind.get(user_id)

        kind = requested or ""
        if not kind:
            if employee_row:
                kind = "employee"
            elif student_row:
                kind = "student"
            elif guardian_row:
                kind = "guardian"
            else:
                kind = "unknown"

        label = requested_label.get(user_id) or user_labels.get(user_id) or user_id
        if kind == "employee" and employee_row:
            label = employee_row.employee_full_name or label
        elif kind == "student" and student_row:
            label = student_row.student_preferred_name or student_row.student_full_name or label
        elif kind == "guardian" and guardian_row:
            label = guardian_row.guardian_full_name or label

        contexts.append(
            {
                "user": user_id,
                "kind": kind,
                "label": label,
                "employee": employee_row.name if employee_row else None,
                "student": student_row.name if student_row else None,
                "guardian": guardian_row.name if guardian_row else None,
                "school": (employee_row.school if employee_row else None)
                or (student_row.anchor_school if student_row else None),
                "student_groups": student_groups_by_student.get(student_row.name, set()) if student_row else set(),
                "guardian_schools": guardian_school_map.get(user_id, set()),
                "guardian_groups": guardian_group_map.get(user_id, set()),
                "availability_mode": (
                    "authoritative"
                    if kind == "employee"
                    else "school_schedule"
                    if kind == "student"
                    else "school_meetings_only"
                    if kind == "guardian"
                    else "unknown"
                ),
            }
        )

    return contexts


def _overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def _append_busy_window(
    busy_by_user: dict[str, list[tuple[datetime, datetime]]], user_id: str, start_dt, end_dt
) -> None:
    if not user_id or not start_dt or not end_dt:
        return
    start_value = get_datetime(start_dt)
    end_value = get_datetime(end_dt)
    if not start_value or not end_value or end_value <= start_value:
        return
    busy_by_user[user_id].append((start_value, end_value))


def _collect_employee_busy_windows(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> None:
    employee_to_user = {ctx["employee"]: ctx["user"] for ctx in contexts if ctx.get("employee")}
    if not employee_to_user or not frappe.db.table_exists("Employee Booking"):
        return

    rows = frappe.get_all(
        "Employee Booking",
        filters={
            "employee": ["in", list(employee_to_user.keys())],
            "from_datetime": ["<", window_end],
            "to_datetime": [">", window_start],
            "blocks_availability": 1,
        },
        fields=["employee", "from_datetime", "to_datetime"],
        limit=max(len(employee_to_user) * 20, 50),
    )
    for row in rows:
        user_id = employee_to_user.get(row.employee)
        if not user_id:
            continue
        _append_busy_window(busy_by_user, user_id, row.from_datetime, row.to_datetime)


def _collect_student_busy_windows(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> None:
    group_to_users: dict[str, set[str]] = defaultdict(set)
    for ctx in contexts:
        if ctx.get("kind") != "student":
            continue
        for group_name in ctx.get("student_groups") or set():
            group_to_users[group_name].add(ctx["user"])

    if not group_to_users:
        return

    start_date = window_start.date()
    end_date = window_end.date()
    for group_name, users in group_to_users.items():
        slots = iter_student_group_room_slots(group_name, start_date, end_date)
        for slot in slots:
            slot_start = get_datetime(slot.get("start"))
            slot_end = get_datetime(slot.get("end"))
            if not slot_start or not slot_end:
                continue
            if not _overlaps(slot_start, slot_end, window_start, window_end):
                continue
            for user_id in users:
                _append_busy_window(busy_by_user, user_id, slot_start, slot_end)


def _collect_meeting_busy_windows(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> None:
    users = [ctx["user"] for ctx in contexts if ctx.get("kind") != "employee"]
    if not users:
        return

    rows = frappe.db.sql(
        """
        SELECT
            mp.participant,
            m.from_datetime,
            m.to_datetime
        FROM `tabMeeting Participant` mp
        INNER JOIN `tabMeeting` m ON m.name = mp.parent
        WHERE
            mp.parenttype = 'Meeting'
            AND mp.participant IN %(users)s
            AND m.docstatus < 2
            AND COALESCE(m.status, 'Scheduled') != 'Cancelled'
            AND m.from_datetime < %(window_end)s
            AND m.to_datetime > %(window_start)s
        """,
        {
            "users": tuple(users),
            "window_start": window_start,
            "window_end": window_end,
        },
        as_dict=True,
    )
    for row in rows:
        _append_busy_window(busy_by_user, row.get("participant"), row.get("from_datetime"), row.get("to_datetime"))


def _collect_school_event_busy_windows(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> None:
    student_contexts = [ctx for ctx in contexts if ctx.get("kind") == "student"]
    guardian_contexts = [ctx for ctx in contexts if ctx.get("kind") == "guardian"]
    if not student_contexts and not guardian_contexts:
        return

    rows = frappe.db.sql(
        """
        SELECT
            name,
            school,
            starts_on,
            ends_on
        FROM `tabSchool Event`
        WHERE
            docstatus < 2
            AND starts_on < %(window_end)s
            AND ends_on > %(window_start)s
        """,
        {"window_start": window_start, "window_end": window_end},
        as_dict=True,
    )
    if not rows:
        return

    event_names = [row.get("name") for row in rows if row.get("name")]
    participants = frappe.get_all(
        "School Event Participant",
        filters={"parent": ["in", event_names]},
        fields=["parent", "participant"],
        limit=max(len(event_names) * 3, 20),
    )
    participant_map: dict[str, set[str]] = defaultdict(set)
    for row in participants:
        if row.parent and row.participant:
            participant_map[row.parent].add(row.participant)

    audience_rows = frappe.get_all(
        "School Event Audience",
        filters={"parent": ["in", event_names]},
        fields=["parent", "audience_type", "student_group", "include_guardians"],
        limit=max(len(event_names) * 3, 20),
    )
    audience_map: dict[str, list[dict]] = defaultdict(list)
    for row in audience_rows:
        if row.parent:
            audience_map[row.parent].append(row)

    student_lineage_map = {
        ctx["user"]: set(_school_lineage(ctx.get("school") or "")) for ctx in student_contexts if ctx.get("school")
    }
    guardian_lineage_map = {
        ctx["user"]: {
            lineage_school
            for school in (ctx.get("guardian_schools") or set())
            for lineage_school in _school_lineage(school)
        }
        for ctx in guardian_contexts
    }

    for row in rows:
        event_name = row.get("name")
        if not event_name:
            continue
        event_school = _safe_text(row.get("school"))
        start_dt = get_datetime(row.get("starts_on"))
        end_dt = get_datetime(row.get("ends_on"))
        if not start_dt or not end_dt or end_dt <= start_dt:
            continue

        explicit_users = participant_map.get(event_name) or set()
        for user_id in explicit_users:
            _append_busy_window(busy_by_user, user_id, start_dt, end_dt)

        for audience in audience_map.get(event_name) or []:
            audience_type = _safe_text(audience.get("audience_type"))
            student_group = _safe_text(audience.get("student_group"))
            include_guardians = cint(audience.get("include_guardians"))

            if audience_type in {"All Students", "All Students, Guardians, and Employees"}:
                for ctx in student_contexts:
                    lineage = student_lineage_map.get(ctx["user"]) or set()
                    if event_school and lineage and event_school not in lineage:
                        continue
                    _append_busy_window(busy_by_user, ctx["user"], start_dt, end_dt)

            if audience_type in {"All Guardians", "All Students, Guardians, and Employees"}:
                for ctx in guardian_contexts:
                    lineage = guardian_lineage_map.get(ctx["user"]) or set()
                    if event_school and lineage and event_school not in lineage:
                        continue
                    _append_busy_window(busy_by_user, ctx["user"], start_dt, end_dt)

            if audience_type == "Students in Student Group" and student_group:
                for ctx in student_contexts:
                    groups = ctx.get("student_groups") or set()
                    if student_group in groups:
                        _append_busy_window(busy_by_user, ctx["user"], start_dt, end_dt)
                if include_guardians:
                    for ctx in guardian_contexts:
                        groups = ctx.get("guardian_groups") or set()
                        if student_group in groups:
                            _append_busy_window(busy_by_user, ctx["user"], start_dt, end_dt)


def _dedupe_busy_windows(
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> dict[str, list[tuple[datetime, datetime]]]:
    deduped: dict[str, list[tuple[datetime, datetime]]] = {}
    for user_id, windows in busy_by_user.items():
        seen = set()
        normalized: list[tuple[datetime, datetime]] = []
        for start_dt, end_dt in sorted(windows, key=lambda item: (item[0], item[1])):
            key = (start_dt.isoformat(), end_dt.isoformat())
            if key in seen:
                continue
            seen.add(key)
            normalized.append((start_dt, end_dt))
        deduped[user_id] = normalized
    return deduped


def _format_conflict_reason(prefix: str, title: str, start_dt, end_dt) -> str:
    label = _safe_text(title) or prefix
    return _("{prefix}: {title} ({slot})").format(
        prefix=prefix,
        title=label,
        slot=_format_slot_label(get_datetime(start_dt), get_datetime(end_dt)),
    )


def _collect_student_schedule_conflict_labels(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, set[str]]:
    group_to_users: dict[str, set[str]] = defaultdict(set)
    for ctx in contexts:
        if ctx.get("kind") != "student":
            continue
        for group_name in ctx.get("student_groups") or set():
            group_to_users[group_name].add(ctx["user"])

    if not group_to_users:
        return {}

    group_rows = frappe.get_all(
        "Student Group",
        filters={"name": ["in", list(group_to_users.keys())]},
        fields=["name", "student_group_name", "course"],
        limit=max(len(group_to_users), 1),
    )
    group_meta = {row.name: row for row in group_rows if row.name}
    course_map = _course_meta_map(row.course for row in group_rows if row.course)

    reasons_by_user: dict[str, set[str]] = defaultdict(set)
    start_date = window_start.date()
    end_date = window_end.date()
    for group_name, users in group_to_users.items():
        meta = group_meta.get(group_name)
        course = course_map.get(meta.course) if meta and meta.course else None
        title = (course.course_name if course else None) or (meta.student_group_name if meta else None) or group_name
        for slot in iter_student_group_room_slots(group_name, start_date, end_date):
            slot_start = get_datetime(slot.get("start"))
            slot_end = get_datetime(slot.get("end"))
            if not slot_start or not slot_end or not _overlaps(slot_start, slot_end, window_start, window_end):
                continue
            reason = _format_conflict_reason(_("Class"), title, slot_start, slot_end)
            for user_id in users:
                reasons_by_user[user_id].add(reason)

    return reasons_by_user


def _collect_student_meeting_conflict_labels(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, set[str]]:
    users = [ctx["user"] for ctx in contexts if ctx.get("kind") == "student" and ctx.get("user")]
    if not users:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            mp.participant,
            m.meeting_name,
            m.from_datetime,
            m.to_datetime
        FROM `tabMeeting Participant` mp
        INNER JOIN `tabMeeting` m ON m.name = mp.parent
        WHERE
            mp.parenttype = 'Meeting'
            AND mp.participant IN %(users)s
            AND m.docstatus < 2
            AND COALESCE(m.status, 'Scheduled') != 'Cancelled'
            AND m.from_datetime < %(window_end)s
            AND m.to_datetime > %(window_start)s
        """,
        {
            "users": tuple(users),
            "window_start": window_start,
            "window_end": window_end,
        },
        as_dict=True,
    )
    if not rows:
        return {}

    reasons_by_user: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        participant = _safe_text(row.get("participant"))
        if not participant:
            continue
        reasons_by_user[participant].add(
            _format_conflict_reason(
                _("Meeting"),
                _safe_text(row.get("meeting_name")) or _("Meeting"),
                row.get("from_datetime"),
                row.get("to_datetime"),
            )
        )

    return reasons_by_user


def _collect_student_school_event_conflict_labels(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, set[str]]:
    student_contexts = [ctx for ctx in contexts if ctx.get("kind") == "student"]
    if not student_contexts:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            name,
            subject,
            school,
            starts_on,
            ends_on
        FROM `tabSchool Event`
        WHERE
            docstatus < 2
            AND starts_on < %(window_end)s
            AND ends_on > %(window_start)s
        """,
        {"window_start": window_start, "window_end": window_end},
        as_dict=True,
    )
    if not rows:
        return {}

    event_names = [row.get("name") for row in rows if row.get("name")]
    participant_rows = frappe.get_all(
        "School Event Participant",
        filters={"parent": ["in", event_names]},
        fields=["parent", "participant"],
        limit=max(len(event_names) * 3, 20),
    )
    participant_map: dict[str, set[str]] = defaultdict(set)
    for row in participant_rows:
        if row.parent and row.participant:
            participant_map[row.parent].add(row.participant)

    audience_rows = frappe.get_all(
        "School Event Audience",
        filters={"parent": ["in", event_names]},
        fields=["parent", "audience_type", "student_group"],
        limit=max(len(event_names) * 3, 20),
    )
    audience_map: dict[str, list[dict]] = defaultdict(list)
    for row in audience_rows:
        if row.parent:
            audience_map[row.parent].append(row)

    student_lineage_map = {
        ctx["user"]: set(_school_lineage(ctx.get("school") or "")) for ctx in student_contexts if ctx.get("user")
    }
    reasons_by_user: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        event_name = _safe_text(row.get("name"))
        if not event_name:
            continue

        reason = _format_conflict_reason(
            _("School event"),
            _safe_text(row.get("subject")) or _("School Event"),
            row.get("starts_on"),
            row.get("ends_on"),
        )
        for user_id in participant_map.get(event_name) or set():
            reasons_by_user[user_id].add(reason)

        event_school = _safe_text(row.get("school"))
        for audience in audience_map.get(event_name) or []:
            audience_type = _safe_text(audience.get("audience_type"))
            student_group = _safe_text(audience.get("student_group"))

            if audience_type in {"All Students", "All Students, Guardians, and Employees"}:
                for ctx in student_contexts:
                    lineage = student_lineage_map.get(ctx["user"]) or set()
                    if event_school and lineage and event_school not in lineage:
                        continue
                    reasons_by_user[ctx["user"]].add(reason)
                continue

            if audience_type == "Students in Student Group" and student_group:
                for ctx in student_contexts:
                    if student_group in (ctx.get("student_groups") or set()):
                        reasons_by_user[ctx["user"]].add(reason)

    return reasons_by_user


def _summarize_conflict_reasons(reasons: set[str]) -> str:
    ordered = sorted(reason for reason in reasons if _safe_text(reason))
    if not ordered:
        return _("Another school commitment in the selected window.")
    if len(ordered) <= 3:
        return "; ".join(ordered)
    return _("{visible}; and {remaining} more.").format(
        visible="; ".join(ordered[:3]),
        remaining=len(ordered) - 3,
    )


def _assert_students_available_for_meeting(
    *,
    attendees: list[dict],
    organizer_user: str,
    window_start: datetime,
    window_end: datetime,
) -> None:
    if not attendees or not window_start or not window_end or window_end <= window_start:
        return

    contexts = [ctx for ctx in _resolve_attendee_contexts(attendees, organizer_user) if ctx.get("kind") == "student"]
    if not contexts:
        return

    busy_by_user: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    _collect_student_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_meeting_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_school_event_busy_windows(contexts, window_start, window_end, busy_by_user)
    busy_by_user = _dedupe_busy_windows(busy_by_user)
    reasons_by_user = defaultdict(set)
    for reason_map in (
        _collect_student_schedule_conflict_labels(contexts, window_start, window_end),
        _collect_student_meeting_conflict_labels(contexts, window_start, window_end),
        _collect_student_school_event_conflict_labels(contexts, window_start, window_end),
    ):
        for user_id, reasons in (reason_map or {}).items():
            reasons_by_user[user_id].update(reasons or set())

    blocked_lines: list[str] = []
    for ctx in contexts:
        user_id = _safe_text(ctx.get("user"))
        if not any(
            _overlaps(window_start, window_end, busy_start, busy_end)
            for busy_start, busy_end in (busy_by_user.get(user_id) or [])
        ):
            continue
        blocked_lines.append(
            _("{student}: {reasons}").format(
                student=_safe_text(ctx.get("label")) or user_id,
                reasons=_summarize_conflict_reasons(reasons_by_user.get(user_id) or set()),
            )
        )

    if not blocked_lines:
        return

    frappe.throw(
        "\n".join(
            [
                _("Student availability conflict for {slot}.").format(
                    slot=_format_slot_label(window_start, window_end),
                ),
                _("These students already have school commitments in that window:"),
                *blocked_lines,
                _("Choose another time or use Find common times first."),
            ]
        ),
        StudentAvailabilityConflictError,
    )


def _build_slot_payload(
    start_dt: datetime,
    end_dt: datetime,
    blocked_count: int,
    *,
    available_room_count: int | None = None,
    suggested_room: dict | None = None,
) -> dict:
    payload = {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "date": start_dt.date().isoformat(),
        "start_time": start_dt.strftime("%H:%M"),
        "end_time": end_dt.strftime("%H:%M"),
        "label": _format_slot_label(start_dt, end_dt),
        "blocked_count": blocked_count,
    }
    if available_room_count is not None:
        payload["available_room_count"] = available_room_count
        payload["suggested_room"] = suggested_room
    return payload


def _room_rows_for_school_scope(school: str, capacity_needed: int, *, location_type: str | None = None) -> list[dict]:
    return get_visible_location_rows_for_school(
        school,
        include_groups=False,
        only_schedulable=True,
        location_types=[location_type] if location_type else None,
        capacity_needed=capacity_needed if capacity_needed > 0 else None,
        fields=[
            "name",
            "location_name",
            "parent_location",
            "maximum_capacity",
            "location_type",
            "is_group",
        ],
        order_by="location_name asc",
        limit=300,
    )


def _rank_room_suggestions(room_rows: list[dict], *, capacity_needed: int) -> list[dict]:
    ranked: list[dict] = []
    for row in room_rows:
        room_name = row.get("name")
        if not room_name:
            continue
        max_capacity = cint(row.get("maximum_capacity")) if row.get("maximum_capacity") is not None else None
        capacity_delta = (
            max(max_capacity - capacity_needed, 0) if max_capacity is not None and capacity_needed > 0 else 9999
        )
        ranked.append(
            {
                "value": room_name,
                "label": row.get("location_name") or room_name,
                "building": row.get("parent_location"),
                "location_type": row.get("location_type"),
                "location_type_name": row.get("location_type_name"),
                "max_capacity": max_capacity,
                "_capacity_delta": capacity_delta,
            }
        )

    ranked.sort(
        key=lambda item: (
            item.get("_capacity_delta", 9999),
            item.get("max_capacity") is None,
            item.get("label") or "",
        )
    )

    return [
        {
            "value": row["value"],
            "label": row["label"],
            "building": row.get("building"),
            "location_type": row.get("location_type"),
            "location_type_name": row.get("location_type_name"),
            "max_capacity": row.get("max_capacity"),
        }
        for row in ranked
    ]


def _collect_room_busy_windows(
    room_suggestions: list[dict],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, list[tuple[datetime, datetime]]]:
    room_names = [row.get("value") for row in room_suggestions if row.get("value")]
    if not room_names:
        return {}

    busy_by_room: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    conflicts = find_room_conflicts(
        None,
        window_start,
        window_end,
        locations=room_names,
        include_children=False,
    )
    for row in conflicts:
        _append_busy_window(busy_by_room, row.get("location"), row.get("from"), row.get("to"))
    return _dedupe_busy_windows(busy_by_room)


def _available_room_suggestions_for_slot(
    slot_start: datetime,
    slot_end: datetime,
    ranked_rooms: list[dict],
    busy_by_room: dict[str, list[tuple[datetime, datetime]]],
) -> list[dict]:
    available: list[dict] = []
    for room in ranked_rooms:
        room_name = room.get("value")
        room_windows = busy_by_room.get(room_name) or []
        if any(_overlaps(slot_start, slot_end, busy_start, busy_end) for busy_start, busy_end in room_windows):
            continue
        available.append(room)
    return available


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
        "teams": _team_options_for_scope(user, scope.get("school_scope") or [], bool(scope.get("is_admin_like"))),
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


def search_meeting_attendees(
    *,
    query: str | None = None,
    attendee_kinds: object | None = None,
    limit: int | None = None,
):
    user = frappe.session.user
    _ensure_can_create_meeting(user)

    search_query = _safe_text(query)
    if len(search_query) < 2:
        return {"results": [], "notes": []}

    result_limit = _coerce_minutes(
        limit,
        default=MAX_ATTENDEE_SEARCH_RESULTS,
        minimum=1,
        maximum=MAX_ATTENDEE_SEARCH_RESULTS,
        label=_("Result limit"),
    )
    kinds = _normalize_attendee_kinds(attendee_kinds)
    scope = _get_quick_create_scope(user)

    cache_key = _json_cache_key(
        "ifitwala_ed:event_quick_create:attendee_search",
        {
            "user": user,
            "query": search_query.lower(),
            "kinds": kinds,
            "limit": result_limit,
        },
    )
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached:
        parsed = frappe.parse_json(cached)
        if isinstance(parsed, dict):
            return parsed

    results: list[dict] = []
    if "employee" in kinds:
        results.extend(
            _search_employee_attendees(
                user=user,
                organization=scope.get("organization"),
                query=search_query,
                limit=result_limit,
            )
        )
    if "student" in kinds:
        results.extend(
            _search_student_attendees(
                school_scope=scope.get("student_scope") or [],
                query=search_query,
                limit=result_limit,
            )
        )
    if "guardian" in kinds:
        results.extend(
            _search_guardian_attendees(
                school_scope=scope.get("student_scope") or [],
                query=search_query,
                limit=result_limit,
            )
        )

    deduped: list[dict] = []
    seen = set()
    for row in sorted(results, key=lambda item: ((item.get("label") or "").lower(), item.get("kind") or "")):
        key = (row.get("value"), row.get("kind"))
        if not row.get("value") or key in seen:
            continue
        seen.add(key)
        deduped.append(row)
        if len(deduped) >= result_limit:
            break

    payload = {"results": deduped, "notes": []}
    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=ATTENDEE_SEARCH_CACHE_TTL_SECONDS)
    return payload


def get_meeting_team_attendees(*, team: str | None = None):
    user = frappe.session.user
    _ensure_can_create_meeting(user)

    team_value = _ensure_allowed_team(user, team)
    if not team_value:
        frappe.throw(_("Team is required."))

    from ifitwala_ed.setup.doctype.meeting.meeting import get_team_participants

    rows = get_team_participants(team_value) or []
    results = []
    seen = set()
    for row in rows:
        user_id = _safe_text(row.get("user_id"))
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        results.append(
            {
                "value": user_id,
                "label": _safe_text(row.get("full_name")) or _current_user_label(user_id),
                "meta": team_value,
                "kind": "employee",
                "availability_mode": "authoritative",
            }
        )

    return {"team": team_value, "results": results}


def suggest_meeting_slots(
    *,
    attendees: object | None = None,
    duration_minutes: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    day_start_time: str | None = None,
    day_end_time: str | None = None,
    school: str | None = None,
    location_type: str | None = None,
    require_room: object | None = None,
):
    user = frappe.session.user
    _ensure_can_create_meeting(user)

    attendee_rows = _parse_attendee_list(attendees)
    attendee_count = len(attendee_rows)
    if attendee_count == 0:
        frappe.throw(_("Add at least one attendee before asking for common times."))
    if attendee_count > MAX_SLOT_ATTENDEES:
        frappe.throw(_("Quick scheduling supports up to {0} attendees at a time.").format(MAX_SLOT_ATTENDEES))

    duration = _coerce_minutes(
        duration_minutes,
        default=60,
        minimum=15,
        maximum=240,
        label=_("Duration"),
    )
    start_date = _coerce_date_required(date_from, _("Start date"))
    end_date = _coerce_date_required(date_to, _("End date"))
    if end_date < start_date:
        frappe.throw(_("End date must be on or after Start date."))
    if (end_date - start_date).days + 1 > MAX_SLOT_SEARCH_DAYS:
        frappe.throw(_("Search window cannot exceed {0} days.").format(MAX_SLOT_SEARCH_DAYS))

    day_start = _coerce_time_required(day_start_time or DEFAULT_DAY_START_TIME, _("Earliest start"))
    day_end = _coerce_time_required(day_end_time or DEFAULT_DAY_END_TIME, _("Latest end"))
    if _combine_date_and_time_local(start_date, day_end) <= _combine_date_and_time_local(start_date, day_start):
        frappe.throw(_("Latest end must be later than earliest start."))

    require_room_value = _coerce_flag(require_room)
    school_value = None
    location_type_value = None
    if require_room_value:
        school_value = _ensure_allowed_school(user, school)
        if not school_value:
            frappe.throw(_("Host school is required before room-aware common times can be ranked."))
        location_type_value = _ensure_allowed_location_type(user, school_value, location_type)

    cache_key = _json_cache_key(
        "ifitwala_ed:event_quick_create:slot_suggestions",
        {
            "user": user,
            "attendees": attendee_rows,
            "duration": duration,
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
            "day_start_time": str(day_start),
            "day_end_time": str(day_end),
            "school": school_value,
            "location_type": location_type_value,
            "require_room": require_room_value,
        },
    )
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached:
        parsed = frappe.parse_json(cached)
        if isinstance(parsed, dict):
            return parsed

    window_start = _combine_date_and_time_local(start_date, day_start)
    window_end = _combine_date_and_time_local(end_date, day_end)
    contexts = _resolve_attendee_contexts(attendee_rows, user)

    busy_by_user: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    _collect_employee_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_student_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_meeting_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_school_event_busy_windows(contexts, window_start, window_end, busy_by_user)
    busy_by_user = _dedupe_busy_windows(busy_by_user)

    ranked_room_candidates: list[dict] = []
    busy_by_room: dict[str, list[tuple[datetime, datetime]]] = {}
    room_capacity_target = attendee_count + 1
    if require_room_value and school_value:
        ranked_room_candidates = _rank_room_suggestions(
            _room_rows_for_school_scope(
                school_value,
                room_capacity_target,
                location_type=location_type_value,
            ),
            capacity_needed=room_capacity_target,
        )
        busy_by_room = _collect_room_busy_windows(ranked_room_candidates, window_start, window_end)

    duration_delta = timedelta(minutes=duration)
    exact_slots: list[dict] = []
    fallback_slots: list[dict] = []
    room_blocked_exact_slots = 0
    cursor_day = start_date
    while cursor_day <= end_date:
        cursor = _combine_date_and_time_local(cursor_day, day_start)
        day_end_dt = _combine_date_and_time_local(cursor_day, day_end)
        while cursor + duration_delta <= day_end_dt:
            slot_end = cursor + duration_delta
            blocked_count = 0
            for ctx in contexts:
                user_windows = busy_by_user.get(ctx["user"]) or []
                if any(_overlaps(cursor, slot_end, busy_start, busy_end) for busy_start, busy_end in user_windows):
                    blocked_count += 1
            available_rooms = []
            available_room_count = None
            suggested_room = None
            if require_room_value:
                available_rooms = _available_room_suggestions_for_slot(
                    cursor,
                    slot_end,
                    ranked_room_candidates,
                    busy_by_room,
                )
                available_room_count = len(available_rooms)
                suggested_room = available_rooms[0] if available_rooms else None

            payload = _build_slot_payload(
                cursor,
                slot_end,
                blocked_count,
                available_room_count=available_room_count,
                suggested_room=suggested_room,
            )
            if blocked_count == 0 and require_room_value and not available_rooms:
                room_blocked_exact_slots += 1
            elif blocked_count == 0 and len(exact_slots) < MAX_SLOT_SUGGESTIONS:
                exact_slots.append(payload)
            elif blocked_count > 0 and len(fallback_slots) < 50:
                fallback_slots.append(payload)
            cursor += timedelta(minutes=SLOT_INCREMENT_MINUTES)
        cursor_day += timedelta(days=1)

    fallback_slots.sort(key=lambda item: (item.get("blocked_count") or 0, item.get("start") or ""))
    fallback_slots = fallback_slots[:MAX_SLOT_FALLBACKS]

    notes: list[str] = []
    if any(ctx.get("kind") == "student" for ctx in contexts):
        notes.append(_("Student availability is checked against school timetable, meetings, and school events."))
    if any(ctx.get("kind") == "guardian" for ctx in contexts):
        notes.append(_("Guardian availability is limited to known school-side meetings and events."))
    if require_room_value:
        if ranked_room_candidates:
            notes.append(_("Exact matches already include at least one free room in the selected school scope."))
        else:
            notes.append(_("No rooms are configured for the selected school scope."))
        if location_type_value:
            notes.append(_("Room ranking is limited to location type {0}.").format(location_type_value))
        if room_blocked_exact_slots:
            notes.append(
                _(
                    "{0} attendee-free slot(s) were excluded because no room was free in the selected school scope."
                ).format(room_blocked_exact_slots)
            )

    payload = {
        "slots": exact_slots,
        "fallback_slots": fallback_slots,
        "notes": notes,
        "duration_minutes": duration,
        "attendees": [
            {
                "user": ctx["user"],
                "label": ctx["label"],
                "kind": ctx["kind"],
                "availability_mode": ctx["availability_mode"],
            }
            for ctx in contexts
        ],
    }
    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=SLOT_SUGGESTION_CACHE_TTL_SECONDS)
    return payload


def suggest_meeting_rooms(
    *,
    school: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    location_type: str | None = None,
    capacity_needed: int | None = None,
    limit: int | None = None,
):
    user = frappe.session.user
    _ensure_can_create_meeting(user)

    school_value = _ensure_allowed_school(user, school)
    if not school_value:
        frappe.throw(_("Host school is required before suggesting rooms."))
    location_type_value = _ensure_allowed_location_type(user, school_value, location_type)

    target_date = _coerce_date_required(date, _("Meeting date"))
    start_value = _coerce_time_required(start_time, _("Start time"))
    end_value = _coerce_time_required(end_time, _("End time"))
    start_dt = _combine_date_and_time_local(target_date, start_value)
    end_dt = _combine_date_and_time_local(target_date, end_value)
    if end_dt <= start_dt:
        frappe.throw(_("End time must be later than start time."))

    room_limit = _coerce_minutes(limit, default=8, minimum=1, maximum=20, label=_("Room limit"))
    cap_needed = (
        _coerce_minutes(capacity_needed, default=0, minimum=0, maximum=200, label=_("Capacity"))
        if capacity_needed not in (None, "")
        else 0
    )

    cache_key = _json_cache_key(
        "ifitwala_ed:event_quick_create:room_suggestions",
        {
            "user": user,
            "school": school_value,
            "date": target_date.isoformat(),
            "start": str(start_value),
            "end": str(end_value),
            "location_type": location_type_value,
            "capacity": cap_needed,
            "limit": room_limit,
        },
    )
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached:
        parsed = frappe.parse_json(cached)
        if isinstance(parsed, dict):
            return parsed

    rows = _room_rows_for_school_scope(
        school_value,
        cap_needed,
        location_type=location_type_value,
    )
    if not rows:
        payload = {
            "rooms": [],
            "notes": [_("No rooms are configured for the selected school scope.")],
        }
        cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=ROOM_SUGGESTION_CACHE_TTL_SECONDS)
        return payload

    conflicts = find_room_conflicts(
        None,
        start_dt,
        end_dt,
        locations=[row.name for row in rows if row.name],
        include_children=False,
    )
    busy_rooms = {row.get("location") for row in conflicts if row.get("location")}

    available_rooms = [
        room for room in _rank_room_suggestions(rows, capacity_needed=cap_needed) if room.get("value") not in busy_rooms
    ]

    payload = {
        "rooms": available_rooms[:room_limit],
        "notes": (
            [_("Room suggestions are limited to location type {0}.").format(location_type_value)]
            if location_type_value
            else []
        ),
    }
    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=ROOM_SUGGESTION_CACHE_TTL_SECONDS)
    return payload


def _build_participant_rows(user_ids: list[str]) -> list[dict]:
    if not user_ids:
        return []

    employee_rows = frappe.get_all(
        "Employee",
        filters={"user_id": ["in", user_ids], "employment_status": "Active"},
        fields=["name", "user_id", "employee_full_name"],
        limit=max(len(user_ids), 1),
    )
    employee_by_user = {row.user_id: row for row in employee_rows if row.user_id}

    user_rows = frappe.get_all(
        "User",
        filters={"name": ["in", user_ids]},
        fields=["name", "full_name"],
        limit=max(len(user_ids), 1),
    )
    user_label_map = {row.name: (row.full_name or row.name) for row in user_rows if row.name}

    rows = []
    for user_id in user_ids:
        employee_row = employee_by_user.get(user_id)
        payload = {
            "participant": user_id,
            "participant_name": (
                (employee_row.employee_full_name if employee_row else None) or user_label_map.get(user_id) or user_id
            ),
        }
        if employee_row:
            payload["employee"] = employee_row.name
        rows.append(payload)
    return rows


def _resolve_meeting_participants(*, organizer_user: str, team: str | None, explicit_users: list[str]) -> list[str]:
    users: list[str] = []
    seen = set()

    if team:
        from ifitwala_ed.setup.doctype.meeting.meeting import get_team_participants

        for row in get_team_participants(team) or []:
            user_id = _safe_text(row.get("user_id"))
            if not user_id or user_id in seen:
                continue
            seen.add(user_id)
            users.append(user_id)

    for user_id in explicit_users:
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        users.append(user_id)

    if organizer_user not in seen:
        users.append(organizer_user)

    return users


def create_meeting_quick(
    *,
    meeting_name: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    team: str | None = None,
    school: str | None = None,
    location: str | None = None,
    meeting_category: str | None = None,
    virtual_meeting_link: str | None = None,
    agenda: str | None = None,
    visibility_scope: str | None = None,
    participants: object | None = None,
    client_request_id: str | None = None,
):
    user = frappe.session.user
    _ensure_can_create_meeting(user)

    title = _safe_text(meeting_name)
    meeting_date = _safe_text(date)
    start_value = _safe_text(start_time)
    end_value = _safe_text(end_time)
    team_value = _ensure_allowed_team(user, team)
    school_value = _ensure_allowed_school(user, school)
    location_value = _ensure_allowed_location(user, school_value, location)
    request_id = _safe_text(client_request_id)

    if not request_id:
        frappe.throw(_("client_request_id is required."), frappe.ValidationError)
    if not title:
        frappe.throw(_("Meeting name is required."), frappe.ValidationError)
    if not meeting_date:
        frappe.throw(_("Meeting date is required."), frappe.ValidationError)
    if not start_value or not end_value:
        frappe.throw(_("Start time and end time are required."), frappe.ValidationError)

    attendee_rows = _parse_attendee_list(participants)
    proposed_date = _coerce_date_required(meeting_date, _("Meeting date"))
    proposed_start_time = _coerce_time_required(start_value, _("Start time"))
    proposed_end_time = _coerce_time_required(end_value, _("End time"))
    proposed_start = _combine_date_and_time_local(proposed_date, proposed_start_time)
    proposed_end = _combine_date_and_time_local(proposed_date, proposed_end_time)
    _assert_students_available_for_meeting(
        attendees=attendee_rows,
        organizer_user=user,
        window_start=proposed_start,
        window_end=proposed_end,
    )
    participant_users = [row["user"] for row in attendee_rows if row.get("user")]
    meeting_participants = _resolve_meeting_participants(
        organizer_user=user,
        team=team_value,
        explicit_users=participant_users,
    )
    visibility_value = _safe_text(visibility_scope) or ("Team & Participants" if team_value else "Participants Only")

    def _create():
        payload = {
            "doctype": "Meeting",
            "meeting_name": title,
            "date": meeting_date,
            "start_time": start_value,
            "end_time": end_value,
            "status": "Scheduled",
            "visibility_scope": visibility_value,
            "participants": _build_participant_rows(meeting_participants),
        }

        if team_value:
            payload["team"] = team_value
        elif school_value:
            # Ad-hoc meetings need a host school so AY + visibility metadata stay anchored.
            payload["school"] = school_value
        else:
            scope = _get_quick_create_scope(user)
            fallback_school = _safe_text(scope.get("base_school"))
            if fallback_school:
                payload["school"] = fallback_school

        if location_value:
            payload["location"] = location_value
        if _safe_text(meeting_category):
            payload["meeting_category"] = _safe_text(meeting_category)
        if _safe_text(virtual_meeting_link):
            payload["virtual_meeting_link"] = _safe_text(virtual_meeting_link)
        if _safe_text(agenda):
            payload["agenda"] = agenda

        doc = frappe.get_doc(payload)
        doc.insert()

        start_dt = (
            _to_system_datetime(doc.from_datetime, _system_tzinfo()) if getattr(doc, "from_datetime", None) else None
        )
        end_dt = _to_system_datetime(doc.to_datetime, _system_tzinfo()) if getattr(doc, "to_datetime", None) else None

        return {
            "ok": True,
            "status": "created",
            "idempotent": False,
            "doctype": "Meeting",
            "name": doc.name,
            "title": doc.meeting_name or doc.name,
            "start": start_dt.isoformat() if start_dt else None,
            "end": end_dt.isoformat() if end_dt else None,
            **_target_payload(
                doctype="Meeting",
                name=doc.name,
                label=doc.meeting_name or doc.name,
            ),
        }

    return _run_idempotent_create(
        doctype="Meeting",
        user=user,
        client_request_id=request_id,
        create_fn=_create,
    )


def create_school_event_quick(
    *,
    subject: str | None = None,
    school: str | None = None,
    starts_on: str | None = None,
    ends_on: str | None = None,
    audience_type: str | None = None,
    event_category: str | None = None,
    all_day: int | None = 0,
    location: str | None = None,
    description: str | None = None,
    audience_team: str | None = None,
    audience_student_group: str | None = None,
    include_guardians: int | None = 0,
    include_students: int | None = 0,
    reference_type: str | None = None,
    reference_name: str | None = None,
    custom_participants: object | None = None,
    publish_announcement: int | None = 0,
    announcement_message: str | None = None,
    client_request_id: str | None = None,
):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to create school events."), frappe.PermissionError)

    if not frappe.has_permission("School Event", ptype="create", user=user):
        frappe.throw(_("You do not have permission to create school events."), frappe.PermissionError)

    subject_value = _safe_text(subject)
    school_value = _safe_text(school)
    starts_value = _safe_text(starts_on)
    ends_value = _safe_text(ends_on)
    audience_value = _safe_text(audience_type)
    request_id = _safe_text(client_request_id)
    reference_type_value = _safe_text(reference_type)
    reference_name_value = _safe_text(reference_name)
    team_value = _safe_text(audience_team)
    student_group_value = _safe_text(audience_student_group)
    publish_announcement_flag = cint(publish_announcement)

    if publish_announcement_flag:
        publish_capability = get_org_communication_quick_create_capability(user=user)
        if not publish_capability.get("enabled"):
            frappe.throw(
                _safe_text(publish_capability.get("blocked_reason"))
                or _("You do not have permission to publish announcements from this workflow."),
                frappe.PermissionError,
            )

    if not request_id:
        frappe.throw(_("client_request_id is required."), frappe.ValidationError)
    if not subject_value:
        frappe.throw(_("Event subject is required."), frappe.ValidationError)
    if not school_value:
        frappe.throw(_("School is required."), frappe.ValidationError)
    if not starts_value or not ends_value:
        frappe.throw(_("Start and end datetime are required."), frappe.ValidationError)
    if not audience_value:
        frappe.throw(_("Audience type is required."), frappe.ValidationError)
    if reference_type_value and not reference_name_value:
        frappe.throw(_("Reference name is required when reference type is set."), frappe.ValidationError)
    if reference_name_value and not reference_type_value:
        frappe.throw(_("Reference type is required when reference name is set."), frappe.ValidationError)

    if audience_value == "Employees in Team" and not team_value:
        frappe.throw(_("Team is required for 'Employees in Team' audience."), frappe.ValidationError)
    if audience_value == "Students in Student Group" and not student_group_value:
        frappe.throw(_("Student Group is required for 'Students in Student Group' audience."), frappe.ValidationError)

    school_value = _ensure_allowed_school(user, school_value)
    location_value = _ensure_allowed_location(user, school_value, location)
    participants = _parse_user_list(custom_participants)
    if audience_value == "Custom Users" and not participants:
        participants = [user]

    def _create():
        published_communication = None
        audience_row = {
            "audience_type": audience_value,
            "include_guardians": cint(include_guardians),
            "include_students": cint(include_students),
        }
        if team_value:
            audience_row["team"] = team_value
        if student_group_value:
            audience_row["student_group"] = student_group_value

        payload = {
            "doctype": "School Event",
            "subject": subject_value,
            "school": school_value,
            "starts_on": starts_value,
            "ends_on": ends_value,
            "event_category": _safe_text(event_category) or "Other",
            "all_day": cint(all_day),
            "audience": [audience_row],
        }
        if location_value:
            payload["location"] = location_value
        if _safe_text(description):
            payload["description"] = description
        if reference_type_value:
            payload["reference_type"] = reference_type_value
        if reference_name_value:
            payload["reference_name"] = reference_name_value
        if participants:
            payload["participants"] = [{"participant": user_id} for user_id in participants]

        doc = frappe.get_doc(payload)
        doc.insert()
        if publish_announcement_flag:
            published_communication = _publish_org_communication_for_school_event(
                request_id=request_id,
                event_name=doc.name,
                subject=doc.subject or doc.name,
                school=school_value,
                description=description,
                announcement_message=announcement_message,
                audience_type=audience_value,
                audience_team=team_value or None,
                audience_student_group=student_group_value or None,
                include_guardians=cint(include_guardians),
                include_students=cint(include_students),
            )

        start_dt = _to_system_datetime(doc.starts_on, _system_tzinfo()) if getattr(doc, "starts_on", None) else None
        end_dt = _to_system_datetime(doc.ends_on, _system_tzinfo()) if getattr(doc, "ends_on", None) else None

        return {
            "ok": True,
            "status": "created",
            "idempotent": False,
            "doctype": "School Event",
            "name": doc.name,
            "title": doc.subject or doc.name,
            "start": start_dt.isoformat() if start_dt else None,
            "end": end_dt.isoformat() if end_dt else None,
            "published_communication": published_communication,
            **_target_payload(
                doctype="School Event",
                name=doc.name,
                label=doc.subject or doc.name,
            ),
        }

    return _run_idempotent_create(
        doctype="School Event",
        user=user,
        client_request_id=request_id,
        create_fn=_create,
    )
