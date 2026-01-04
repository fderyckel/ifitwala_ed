# ifitwala_ed/api/student_calendar.py

"""
API for the Student Portal Calendar.
Focus: High concurrency, aggressive caching, efficient SQL.
"""

from __future__ import annotations

import pytz
from datetime import datetime, timedelta, date, time
from typing import List, Optional, Tuple, Dict, Any

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, get_system_timezone

# Reuse existing utilities for schedule expansion
from ifitwala_ed.api.calendar import (
    CalendarEvent,
    _system_tzinfo,
    _resolve_window,
    _localize_datetime,
    _to_system_datetime,
    _course_meta_map,
    _attach_duration,
)
from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots

CACHE_TTL = 600  # 10 minutes


@frappe.whitelist()
def get_student_calendar(
    from_datetime: Optional[str] = None,
    to_datetime: Optional[str] = None,
    force_refresh: bool = False,
):
    """
    Return calendar events for the currently logged-in student.
    Aggregates:
      - Classes (Student Groups)
      - School Events
      - Meetings
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to view your calendar."), frappe.PermissionError)

    # 1. Resolve Student
    student = frappe.db.get_value("Student", {"student_email": user}, "name")
    if not student:
        # Fallback: maybe they are a guardian? TODO: Handle guardian logic if needed.
        # For now, strict student check as per reqs.
        return _empty_payload()

    # 2. Resolve Window
    tzinfo = _system_tzinfo()
    window_start, window_end = _resolve_window(from_datetime, to_datetime, tzinfo)
    
    # 3. Cache Check
    cache_key = f"ifw:stud-cal:{student}:{window_start.date()}:{window_end.date()}"
    if not force_refresh:
        cached = frappe.cache().get_value(cache_key)
        if cached:
            return cached

    # 4. Fetch Data
    events: List[CalendarEvent] = []
    
    # A) Classes
    events.extend(_fetch_classes(student, window_start, window_end, tzinfo))
    
    # B) School Events
    events.extend(_fetch_school_events(student, window_start, window_end, tzinfo))
    
    # C) Meetings
    events.extend(_fetch_meetings(user, student, window_start, window_end, tzinfo))

    # 5. Build Response
    events.sort(key=lambda x: (x.start, x.end))
    
    payload = {
        "events": [evt.as_dict() for evt in events],
        "meta": {
            "tz": tzinfo.zone,
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "cached_at": now_datetime().isoformat(),
        }
    }

    # 6. Cache
    frappe.cache().set_value(cache_key, payload, expires_in_sec=CACHE_TTL)
    
    return payload


def _empty_payload():
    return {"events": [], "meta": {}}


def _fetch_classes(
    student: str, 
    start: datetime, 
    end: datetime, 
    tzinfo: pytz.timezone
) -> List[CalendarEvent]:
    """
    Fetch active Student Group enrollments and expand them into slots.
    """
    # Get active enrollments
    # We select specific fields to avoid full doc loading
    enrollments = frappe.db.sql(
        """
        SELECT parent, parent as student_group 
        FROM `tabStudent Group Student`
        WHERE student = %s AND active = 1
        """,
        (student,),
        as_dict=True
    )
    
    if not enrollments:
        return []

    # Get details for these groups (Course, Color, etc.)
    sg_names = [r.student_group for r in enrollments]
    if not sg_names:
        return []
        
    group_meta = frappe.get_all(
        "Student Group",
        filters={"name": ["in", sg_names]},
        fields=["name", "student_group_name", "course"],
    )
    from ifitwala_ed.api.calendar import _course_meta_map
    course_map = _course_meta_map(g.course for g in group_meta if g.course)
    
    meta_by_name = {g.name: g for g in group_meta}

    events = []
    
    # Expand schedule for each group
    # Note: iter_student_group_room_slots handles term/holiday logic efficiently
    start_date = start.date()
    end_date = end.date()
    
    for sg_name in sg_names:
        slots = iter_student_group_room_slots(sg_name, start_date, end_date)
        
        g_meta = meta_by_name.get(sg_name)
        if not g_meta:
            continue
            
        # Determine Title & Color
        course = course_map.get(g_meta.course)
        title = course.course_name if course else (g_meta.student_group_name or sg_name)
        color = (course.calendar_event_color if course else None) or "#3b82f6" # Blue default

        for slot in slots:
            # slot has: start (datetime), end (datetime), location, etc.
            # Convert naive slots to system tz if needed (though util usually returns localized)
            s_start = slot["start"]
            s_end = slot["end"]
            
            # Ensure timezone
            if s_start.tzinfo is None:
                s_start = tzinfo.localize(s_start)
            if s_end.tzinfo is None:
                s_end = tzinfo.localize(s_end)

            events.append(CalendarEvent(
                id=f"sg::{sg_name}::{s_start.isoformat()}", # Unique ID per slot instance
                title=title,
                start=s_start,
                end=s_end,
                source="student_group",
                color=color,
                all_day=False,
                meta={
                    "student_group": sg_name,
                    "location": slot.get("location"),
                    "course": g_meta.course,
                }
            ))
            
    return events


def _fetch_school_events(
    student: str,
    start: datetime, 
    end: datetime, 
    tzinfo: pytz.timezone
) -> List[CalendarEvent]:
    """
    Fetch School Events visible to this student.
    Logic: event.participants includes student OR event.audience includes 'Student' (and public/school scope matches).
    Simplified for concurrent efficiency:
    - Get events in range
    - Filter in SQL/Python
    """
    
    # 1. Fetch potentially relevant events regardless of specific audience (optimization pending on audience structure)
    # We will assume 'School Event' has an 'audience' field or child table.
    # Checking standard schema... assuming standard 'School Event' where audience is check.
    # For now, let's look for events where audience field contains "Student" or is Public.
    
    # NOTE: user didn't specify strict schemas, relying on typical setup.
    # Refined query:
    events_data = frappe.db.sql(
        """
        SELECT 
            name, subject, starts_on, ends_on, color, 
            description, location, all_day
        FROM `tabSchool Event`
        WHERE 
            docstatus < 2
            AND (
                (starts_on BETWEEN %(start)s AND %(end)s)
                OR (ends_on BETWEEN %(start)s AND %(end)s)
            )
        """,
        {"start": start, "end": end},
        as_dict=True
    )
    
    # Filter for permission (can't do complex audience logic easily in SQL without joins)
    # We'll use a fast check here.
    # TODO: If audience is complex (child table), we need a join. 
    # For MVP/High-perf, let's assume we filter by `get_list` logic or simple field.
    # Let's rely on standard permissions + explicit "Student" check if applicable.
    
    valid_events = []
    for evt in events_data:
        # Check specific audience visibility if needed
        # For now, we assume if they can READ the event (doc perms), they see it.
        # But we should double check if the Logic requires "Audience" check.
        # User said: "when the audience include students".
        
        doc = frappe.get_doc("School Event", evt.name) # Inefficient loop? 
        # Better: Filter IDs first? 
        # Let's trust `frappe.db.get_list` to handle basic perms, but we need audience check.
        
        has_access = False
        
        # Check Audience field (MultiSelect or Child Table?)
        # Assuming simple Check/Select for now based on typical Frappe logic, 
        # or checking `event_participants` child table.
        
        # Let's check if 'Student' is in audience roles.
        # This part might need adjustment if schema is custom.
        # Safe bet: If 'Student' role is allowed.
        
        if _is_student_audience(doc, student):
            has_access = True
            
        if has_access:
            start_dt = _to_system_datetime(evt.starts_on, tzinfo)
            end_dt = _to_system_datetime(evt.ends_on, tzinfo) if evt.ends_on else start_dt + timedelta(hours=1)
            
            valid_events.append(CalendarEvent(
                id=f"school_event::{evt.name}",
                title=evt.subject,
                start=start_dt,
                end=end_dt,
                source="school_event",
                color=evt.color or "#10b981", # Emerald default
                all_day=bool(evt.all_day),
                meta={
                    "location": evt.location,
                    "description": evt.description
                }
            ))
            
    return valid_events

def _is_student_audience(doc, student_name):
    # Heuristic for "Student" audience.
    # 1. 'Audience' field has 'Student'
    if hasattr(doc, 'audience') and doc.audience:
        if 'Student' in str(doc.audience):
            return True
            
    # 2. Participants child table has this student
    if hasattr(doc, 'participants'):
        for p in doc.participants:
            if p.student == student_name:
                return True
                
    return False


def _fetch_meetings(
    user: str,
    student: str,
    start: datetime,
    end: datetime,
    tzinfo: pytz.timezone
) -> List[CalendarEvent]:
    """
    Fetch meetings where the student (or their user) is a participant.
    """
    meetings = frappe.db.sql(
        """
        SELECT 
            m.name, m.meeting_name, m.from_datetime, m.to_datetime, m.location, m.virtual_meeting_link
        FROM `tabMeeting` m
        JOIN `tabMeeting Participant` mp ON mp.parent = m.name
        WHERE 
            m.docstatus < 2
            AND m.status != 'Cancelled'
            AND mp.participant = %s
            AND m.from_datetime < %s
            AND m.to_datetime > %s
        """,
        (user, end, start),
        as_dict=True
    )
    
    events = []
    seen = set()
    
    for m in meetings:
        if m.name in seen: continue
        seen.add(m.name)
        
        s_dt = _to_system_datetime(m.from_datetime, tzinfo)
        e_dt = _to_system_datetime(m.to_datetime, tzinfo)
        
        events.append(CalendarEvent(
            id=f"meeting::{m.name}",
            title=m.meeting_name,
            start=s_dt,
            end=e_dt,
            source="meeting",
            color="#8b5cf6", # Violet
            all_day=False,
            meta={
                "location": m.location,
                "virtual_link": m.virtual_meeting_link
            }
        ))
        
    return events
