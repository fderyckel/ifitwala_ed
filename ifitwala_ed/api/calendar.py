# ifitwala_ed/api/calendar.py

"""
Calendar API public RPC boundary.

Public Frappe method paths remain locked on this module (for example,
`ifitwala_ed.api.calendar.get_staff_calendar`) while implementations live in
owner modules:
- calendar_staff_feed.py
- calendar_details.py
- calendar_quick_create.py
- calendar_prefs.py

Internal Python code should import helpers from those owner modules directly
instead of importing through this boundary module.
"""

import frappe

from ifitwala_ed.api import (
    calendar_details,
    calendar_export,
    calendar_prefs,
    calendar_quick_create,
    calendar_staff_feed,
)


@frappe.whitelist()
def get_staff_calendar(
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    sources=None,
    force_refresh: bool = False,
):
    return calendar_staff_feed.get_staff_calendar(
        from_datetime=from_datetime,
        to_datetime=to_datetime,
        sources=sources,
        force_refresh=force_refresh,
    )


@frappe.whitelist()
def get_meeting_details(meeting: str):
    return calendar_details.get_meeting_details(meeting=meeting)


@frappe.whitelist()
def get_school_event_details(event: str):
    return calendar_details.get_school_event_details(event=event)


@frappe.whitelist()
def get_student_group_event_details(
    event_id: str | None = None,
    eventId: str | None = None,
    id: str | None = None,
):
    return calendar_details.get_student_group_event_details(event_id=event_id, eventId=eventId, id=id)


@frappe.whitelist()
def get_event_quick_create_options():
    return calendar_quick_create.get_event_quick_create_options()


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
    return calendar_quick_create.create_meeting_quick(
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
    return calendar_quick_create.search_meeting_attendees(
        query=query,
        attendee_kinds=attendee_kinds,
        limit=limit,
    )


@frappe.whitelist()
def get_meeting_team_attendees(*, team: str | None = None):
    return calendar_quick_create.get_meeting_team_attendees(team=team)


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
    location_type: str | None = None,
    require_room: object | None = None,
):
    return calendar_quick_create.suggest_meeting_slots(
        attendees=attendees,
        duration_minutes=duration_minutes,
        date_from=date_from,
        date_to=date_to,
        day_start_time=day_start_time,
        day_end_time=day_end_time,
        school=school,
        location_type=location_type,
        require_room=require_room,
    )


@frappe.whitelist()
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
    return calendar_quick_create.suggest_meeting_rooms(
        school=school,
        date=date,
        start_time=start_time,
        end_time=end_time,
        location_type=location_type,
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
    publish_announcement: int | None = 0,
    announcement_message: str | None = None,
    client_request_id: str | None = None,
):
    return calendar_quick_create.create_school_event_quick(
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
        publish_announcement=publish_announcement,
        announcement_message=announcement_message,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def get_portal_calendar_prefs(from_datetime: str | None = None, to_datetime: str | None = None):
    return calendar_prefs.get_portal_calendar_prefs(from_datetime=from_datetime, to_datetime=to_datetime)


@frappe.whitelist()
def export_staff_timetable_pdf(
    preset: str | None = None,
    include_weekends: object | None = None,
):
    return calendar_export.export_staff_timetable_pdf(
        preset=preset,
        include_weekends=include_weekends,
    )


__all__ = [
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
    "get_portal_calendar_prefs",
    "export_staff_timetable_pdf",
]
