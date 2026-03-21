# ifitwala_ed/api/calendar.py

"""
Calendar API compatibility facade.

Public API paths remain locked on this module (for example,
`ifitwala_ed.api.calendar.get_staff_calendar`) while implementations live in
split modules:
- calendar_core.py
- calendar_staff_feed.py
- calendar_details.py
- calendar_quick_create.py
- calendar_prefs.py
"""

import frappe

from ifitwala_ed.api.calendar_core import (
    CACHE_TTL_SECONDS,
    CAL_MIN_DURATION,
    DEFAULT_WINDOW_DAYS,
    LOOKBACK_DAYS,
    VALID_SOURCES,
    CalendarEvent,
    _attach_duration,
    _cache_key,
    _coerce_time,
    _combine,
    _course_meta_map,
    _localize_datetime,
    _meeting_window,
    _normalize_sources,
    _resolve_employee_for_user,
    _resolve_instructor_ids,
    _resolve_window,
    _student_group_memberships,
    _student_group_title_and_color,
    _system_tzinfo,
    _time_to_str,
    _to_system_datetime,
)
from ifitwala_ed.api.calendar_details import (
    _any_student_has_active_group_membership,
    _get_team_meta,
    _guardian_students_for_user,
    _meeting_access_allowed,
    _resolve_sg_booking_context,
    _resolve_sg_schedule_context,
    _resolve_student_for_user,
    _school_event_access_allowed,
    _student_has_active_group_membership,
    _user_has_student_group_access,
)
from ifitwala_ed.api.calendar_details import (
    get_meeting_details as _get_meeting_details,
)
from ifitwala_ed.api.calendar_details import (
    get_school_event_details as _get_school_event_details,
)
from ifitwala_ed.api.calendar_details import (
    get_student_group_event_details as _get_student_group_event_details,
)
from ifitwala_ed.api.calendar_prefs import (
    debug_staff_calendar_window as _debug_staff_calendar_window,
)
from ifitwala_ed.api.calendar_prefs import (
    get_portal_calendar_prefs as _get_portal_calendar_prefs,
)
from ifitwala_ed.api.calendar_quick_create import (
    ATTENDEE_SEARCH_CACHE_TTL_SECONDS,
    META_SELECT_OPTIONS_CACHE_TTL_SECONDS,
    QUICK_CREATE_IDEMPOTENCY_TTL_SECONDS,
    ROOM_SUGGESTION_CACHE_TTL_SECONDS,
    SLOT_SUGGESTION_CACHE_TTL_SECONDS,
    _cached_select_options,
    _desk_route_slug,
    _doc_url,
    _idempotency_key,
    _location_options_for_scope,
    _parse_user_list,
    _run_idempotent_create,
    _safe_text,
    _school_options_for_scope,
    _split_select_options,
    _student_group_options_for_scope,
    _target_payload,
    _team_options_for_scope,
)
from ifitwala_ed.api.calendar_quick_create import (
    create_meeting_quick as _create_meeting_quick,
)
from ifitwala_ed.api.calendar_quick_create import (
    create_school_event_quick as _create_school_event_quick,
)
from ifitwala_ed.api.calendar_quick_create import (
    get_event_quick_create_options as _get_event_quick_create_options,
)
from ifitwala_ed.api.calendar_quick_create import (
    get_meeting_team_attendees as _get_meeting_team_attendees,
)
from ifitwala_ed.api.calendar_quick_create import (
    search_meeting_attendees as _search_meeting_attendees,
)
from ifitwala_ed.api.calendar_quick_create import (
    suggest_meeting_rooms as _suggest_meeting_rooms,
)
from ifitwala_ed.api.calendar_quick_create import (
    suggest_meeting_slots as _suggest_meeting_slots,
)
from ifitwala_ed.api.calendar_staff_feed import (
    _collect_meeting_events,
    _collect_school_events,
    _collect_staff_holiday_events,
    _collect_student_group_events,
    _collect_student_group_events_from_bookings,
    _resolve_staff_calendar_for_employee,
)
from ifitwala_ed.api.calendar_staff_feed import (
    get_staff_calendar as _get_staff_calendar,
)


@frappe.whitelist()
def get_staff_calendar(
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    sources=None,
    force_refresh: bool = False,
):
    return _get_staff_calendar(
        from_datetime=from_datetime,
        to_datetime=to_datetime,
        sources=sources,
        force_refresh=force_refresh,
    )


@frappe.whitelist()
def get_meeting_details(meeting: str):
    return _get_meeting_details(meeting=meeting)


@frappe.whitelist()
def get_school_event_details(event: str):
    return _get_school_event_details(event=event)


@frappe.whitelist()
def get_student_group_event_details(
    event_id: str | None = None,
    eventId: str | None = None,
    id: str | None = None,
):
    return _get_student_group_event_details(event_id=event_id, eventId=eventId, id=id)


@frappe.whitelist()
def get_event_quick_create_options():
    return _get_event_quick_create_options()


@frappe.whitelist()
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
    return _create_meeting_quick(
        meeting_name=meeting_name,
        date=date,
        start_time=start_time,
        end_time=end_time,
        team=team,
        school=school,
        location=location,
        meeting_category=meeting_category,
        virtual_meeting_link=virtual_meeting_link,
        agenda=agenda,
        visibility_scope=visibility_scope,
        participants=participants,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def search_meeting_attendees(
    *,
    query: str | None = None,
    attendee_kinds=None,
    limit: int | None = None,
):
    return _search_meeting_attendees(
        query=query,
        attendee_kinds=attendee_kinds,
        limit=limit,
    )


@frappe.whitelist()
def get_meeting_team_attendees(*, team: str | None = None):
    return _get_meeting_team_attendees(team=team)


@frappe.whitelist()
def suggest_meeting_slots(
    *,
    attendees=None,
    duration_minutes: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    day_start_time: str | None = None,
    day_end_time: str | None = None,
    school: str | None = None,
    require_room: object | None = None,
):
    return _suggest_meeting_slots(
        attendees=attendees,
        duration_minutes=duration_minutes,
        date_from=date_from,
        date_to=date_to,
        day_start_time=day_start_time,
        day_end_time=day_end_time,
        school=school,
        require_room=require_room,
    )


@frappe.whitelist()
def suggest_meeting_rooms(
    *,
    school: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    capacity_needed: int | None = None,
    limit: int | None = None,
):
    return _suggest_meeting_rooms(
        school=school,
        date=date,
        start_time=start_time,
        end_time=end_time,
        capacity_needed=capacity_needed,
        limit=limit,
    )


@frappe.whitelist()
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
    return _create_school_event_quick(
        subject=subject,
        school=school,
        starts_on=starts_on,
        ends_on=ends_on,
        audience_type=audience_type,
        event_category=event_category,
        all_day=all_day,
        location=location,
        description=description,
        audience_team=audience_team,
        audience_student_group=audience_student_group,
        include_guardians=include_guardians,
        include_students=include_students,
        reference_type=reference_type,
        reference_name=reference_name,
        custom_participants=custom_participants,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def debug_staff_calendar_window(from_datetime: str | None = None, to_datetime: str | None = None):
    return _debug_staff_calendar_window(from_datetime=from_datetime, to_datetime=to_datetime)


@frappe.whitelist()
def get_portal_calendar_prefs(from_datetime: str | None = None, to_datetime: str | None = None):
    return _get_portal_calendar_prefs(from_datetime=from_datetime, to_datetime=to_datetime)


__all__ = [
    "VALID_SOURCES",
    "DEFAULT_WINDOW_DAYS",
    "LOOKBACK_DAYS",
    "CACHE_TTL_SECONDS",
    "CAL_MIN_DURATION",
    "QUICK_CREATE_IDEMPOTENCY_TTL_SECONDS",
    "META_SELECT_OPTIONS_CACHE_TTL_SECONDS",
    "ATTENDEE_SEARCH_CACHE_TTL_SECONDS",
    "SLOT_SUGGESTION_CACHE_TTL_SECONDS",
    "ROOM_SUGGESTION_CACHE_TTL_SECONDS",
    "CalendarEvent",
    "get_staff_calendar",
    "get_meeting_details",
    "get_school_event_details",
    "get_student_group_event_details",
    "get_event_quick_create_options",
    "search_meeting_attendees",
    "get_meeting_team_attendees",
    "suggest_meeting_slots",
    "suggest_meeting_rooms",
    "create_meeting_quick",
    "create_school_event_quick",
    "debug_staff_calendar_window",
    "get_portal_calendar_prefs",
    "_resolve_employee_for_user",
    "_system_tzinfo",
    "_normalize_sources",
    "_cache_key",
    "_resolve_window",
    "_to_system_datetime",
    "_localize_datetime",
    "_coerce_time",
    "_time_to_str",
    "_combine",
    "_attach_duration",
    "_course_meta_map",
    "_student_group_title_and_color",
    "_resolve_instructor_ids",
    "_student_group_memberships",
    "_resolve_staff_calendar_for_employee",
    "_collect_student_group_events",
    "_collect_student_group_events_from_bookings",
    "_collect_staff_holiday_events",
    "_collect_meeting_events",
    "_collect_school_events",
    "_meeting_window",
    "_get_team_meta",
    "_meeting_access_allowed",
    "_resolve_sg_schedule_context",
    "_resolve_sg_booking_context",
    "_user_has_student_group_access",
    "_resolve_student_for_user",
    "_guardian_students_for_user",
    "_student_has_active_group_membership",
    "_any_student_has_active_group_membership",
    "_school_event_access_allowed",
    "_split_select_options",
    "_safe_text",
    "_desk_route_slug",
    "_doc_url",
    "_parse_user_list",
    "_idempotency_key",
    "_run_idempotent_create",
    "_target_payload",
    "_school_options_for_scope",
    "_team_options_for_scope",
    "_student_group_options_for_scope",
    "_location_options_for_scope",
    "_cached_select_options",
]
