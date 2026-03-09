# ifitwala_ed/api/calendar_quick_create.py

from __future__ import annotations

from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.api.calendar_core import _resolve_employee_for_user, _system_tzinfo, _to_system_datetime
from ifitwala_ed.utilities.school_tree import get_descendant_schools

QUICK_CREATE_IDEMPOTENCY_TTL_SECONDS = 900
META_SELECT_OPTIONS_CACHE_TTL_SECONDS = 3600


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
        limit_page_length=500,
    )
    return [{"value": row.name, "label": row.school_name or row.name} for row in rows]


def _team_options_for_scope(user: str, school_scope: list[str], is_admin_like: bool) -> list[dict]:
    if school_scope:
        rows = frappe.get_all(
            "Team",
            filters={"school": ["in", school_scope], "enabled": 1},
            fields=["name", "team_name"],
            order_by="team_name asc",
            limit_page_length=500,
        )
        return [{"value": row.name, "label": row.team_name or row.name} for row in rows]

    if is_admin_like:
        rows = frappe.get_all(
            "Team",
            filters={"enabled": 1},
            fields=["name", "team_name"],
            order_by="team_name asc",
            limit_page_length=500,
        )
        return [{"value": row.name, "label": row.team_name or row.name} for row in rows]

    team_names = frappe.get_all(
        "Team Member",
        filters={"parenttype": "Team", "member": user},
        pluck="parent",
        limit_page_length=500,
    )
    if not team_names:
        return []

    rows = frappe.get_all(
        "Team",
        filters={"name": ["in", sorted(set(team_names))]},
        fields=["name", "team_name"],
        order_by="team_name asc",
        limit_page_length=500,
    )
    return [{"value": row.name, "label": row.team_name or row.name} for row in rows]


def _student_group_options_for_scope(user: str, school_scope: list[str]) -> list[dict]:
    if school_scope:
        rows = frappe.get_all(
            "Student Group",
            filters={"school": ["in", school_scope], "status": "Active"},
            fields=["name", "student_group_name"],
            order_by="student_group_name asc",
            limit_page_length=500,
        )
        return [{"value": row.name, "label": row.student_group_name or row.name} for row in rows]

    group_names = frappe.get_all(
        "Student Group Instructor",
        filters={"parenttype": "Student Group", "user_id": user},
        pluck="parent",
        limit_page_length=500,
    )
    if not group_names:
        return []

    rows = frappe.get_all(
        "Student Group",
        filters={"name": ["in", sorted(set(group_names))]},
        fields=["name", "student_group_name"],
        order_by="student_group_name asc",
        limit_page_length=500,
    )
    return [{"value": row.name, "label": row.student_group_name or row.name} for row in rows]


def _location_options_for_scope(school_scope: list[str], is_admin_like: bool) -> list[dict]:
    if school_scope:
        filters = {"school": ["in", school_scope], "is_group": 0}
    elif is_admin_like:
        filters = {"is_group": 0}
    else:
        return []

    rows = frappe.get_all(
        "Location",
        filters=filters,
        fields=["name", "location_name"],
        order_by="location_name asc",
        limit_page_length=500,
    )
    return [{"value": row.name, "label": row.location_name or row.name} for row in rows]


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

    can_create_meeting = bool(frappe.has_permission("Meeting", ptype="create", user=user))
    can_create_school_event = bool(frappe.has_permission("School Event", ptype="create", user=user))

    if not can_create_meeting and not can_create_school_event:
        frappe.throw(_("You do not have permission to create Meetings or School Events."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    is_admin_like = user == "Administrator" or "System Manager" in roles

    employee_row = _resolve_employee_for_user(
        user,
        fields=["school"],
        employment_status_filter=["!=", "Inactive"],
    )
    base_school = _safe_text((employee_row or {}).get("school")) or _safe_text(
        frappe.defaults.get_user_default("school", user=user)
    )

    school_scope: list[str] = []
    if base_school:
        school_scope = get_descendant_schools(base_school) or [base_school]
    elif is_admin_like:
        school_scope = frappe.get_all(
            "School",
            filters={"is_group": 0},
            pluck="name",
            limit_page_length=500,
        )

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

    school_options = _school_options_for_scope(school_scope)

    default_school = None
    if base_school and any(opt.get("value") == base_school for opt in school_options):
        default_school = base_school
    elif school_options:
        default_school = school_options[0].get("value")

    return {
        "can_create_meeting": can_create_meeting,
        "can_create_school_event": can_create_school_event,
        "meeting_categories": meeting_category_options,
        "school_event_categories": school_event_category_options,
        "audience_types": audience_options,
        "schools": school_options,
        "teams": _team_options_for_scope(user, school_scope, is_admin_like),
        "student_groups": _student_group_options_for_scope(user, school_scope),
        "locations": _location_options_for_scope(school_scope, is_admin_like),
        "defaults": {
            "school": default_school,
        },
    }


def create_meeting_quick(
    *,
    meeting_name: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    team: str | None = None,
    location: str | None = None,
    meeting_category: str | None = None,
    virtual_meeting_link: str | None = None,
    agenda: str | None = None,
    visibility_scope: str | None = None,
    participants: object | None = None,
    client_request_id: str | None = None,
):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to create meetings."), frappe.PermissionError)

    if not frappe.has_permission("Meeting", ptype="create", user=user):
        frappe.throw(_("You do not have permission to create meetings."), frappe.PermissionError)

    title = _safe_text(meeting_name)
    meeting_date = _safe_text(date)
    start_value = _safe_text(start_time)
    end_value = _safe_text(end_time)
    team_value = _safe_text(team)
    request_id = _safe_text(client_request_id)

    if not request_id:
        frappe.throw(_("client_request_id is required."), frappe.ValidationError)
    if not title:
        frappe.throw(_("Meeting name is required."), frappe.ValidationError)
    if not meeting_date:
        frappe.throw(_("Meeting date is required."), frappe.ValidationError)
    if not start_value or not end_value:
        frappe.throw(_("Start time and end time are required."), frappe.ValidationError)

    participant_users = _parse_user_list(participants)

    def _create():
        payload = {
            "doctype": "Meeting",
            "meeting_name": title,
            "date": meeting_date,
            "start_time": start_value,
            "end_time": end_value,
            "status": "Scheduled",
        }

        if team_value:
            payload["team"] = team_value
        if _safe_text(location):
            payload["location"] = _safe_text(location)
        if _safe_text(meeting_category):
            payload["meeting_category"] = _safe_text(meeting_category)
        if _safe_text(virtual_meeting_link):
            payload["virtual_meeting_link"] = _safe_text(virtual_meeting_link)
        if _safe_text(agenda):
            payload["agenda"] = agenda
        if _safe_text(visibility_scope):
            payload["visibility_scope"] = _safe_text(visibility_scope)

        if participant_users:
            payload["participants"] = [{"participant": user_id} for user_id in participant_users]
        elif not team_value:
            payload["participants"] = [{"participant": user}]

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

    participants = _parse_user_list(custom_participants)
    if audience_value == "Custom Users" and not participants:
        participants = [user]

    def _create():
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
        if _safe_text(location):
            payload["location"] = _safe_text(location)
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
