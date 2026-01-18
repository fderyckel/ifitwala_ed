# ifitwala_ed/api/calendar.py

"""
APIs feeding the portal calendars (staff / student / guardian).

Current scope
-------------
- Staff portal calendar (HomeStaff.vue) that aggregates, for the logged-in user:
    • Student Group teaching slots
    • Meetings
    • School Events

- Student / guardian views that need:
    • merged calendar feeds
    • per-event drill-down (meeting details, class details, school event details)

Responsibilities (what this module DOES)
----------------------------------------
- Expose whitelisted API endpoints for Vue:
    • get_staff_calendar
    • get_meeting_details
    • get_school_event_details
    • get_student_group_event_details
    • get_portal_calendar_prefs
    • debug_staff_calendar_window

- Aggregate data from multiple sources into a unified event list:
    • normalise to site timezone (System Settings)
    • ensure consistent CalendarEvent payload shape for FullCalendar
    • enforce access rules (only events the current user is allowed to see)

- Provide small, calendar-specific helpers:
    • window resolution (from/to)
    • cache keys and TTLs
    • basic title/colour helpers for Student Groups and Courses

What this module does NOT do
----------------------------
- It does NOT own rotation/term logic or schedule resolution.
    • Rotation days and academic-year spans live in:
      ifitwala_ed.schedule.schedule_utils
      (e.g. get_effective_schedule_for_ay).

- It does NOT enforce Student Group business rules or validation.
    • Those live in:
      ifitwala_ed.schedule.student_group_scheduling
      ifitwala_ed.students.doctype.student_group.student_group

- It does NOT own attendance logic.
    • Attendance expansion / tools live in:
      ifitwala_ed.schedule.attendance_utils

Design intent
-------------
This file is a thin aggregation & presentation layer sitting on top of the
core scheduling / attendance utilities. Over time, schedule expansion and
conflict logic should be pushed down into schedule_utils / student_group_scheduling,
with this module reusing those helpers rather than re-implementing them.
"""


from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

import pytz

import frappe
from frappe import _
from frappe.utils import get_datetime, get_system_timezone, getdate, now_datetime, format_datetime

from ifitwala_ed.schedule.schedule_utils import (
	get_effective_schedule_for_ay,
	get_weekend_days_for_calendar,
)
from ifitwala_ed.utilities.school_tree import get_ancestor_schools

VALID_SOURCES = {"student_group", "meeting", "school_event", "staff_holiday"}

DEFAULT_WINDOW_DAYS = 30
LOOKBACK_DAYS = 3
CACHE_TTL_SECONDS = 600
CAL_MIN_DURATION = timedelta(minutes=45)


@dataclass(slots=True)
class CalendarEvent:
	id: str
	title: str
	start: datetime
	end: datetime
	source: str
	color: str
	all_day: bool = False
	meta: Optional[dict] = None

	def as_dict(self) -> dict:
		return {
			"id": self.id,
			"title": self.title,
			"start": self.start.isoformat(),
			"end": self.end.isoformat(),
			"allDay": self.all_day,
			"source": self.source,
			"color": self.color,
			"meta": self.meta or {},
		}


@frappe.whitelist()
def get_staff_calendar(
	from_datetime: Optional[str] = None,
	to_datetime: Optional[str] = None,
	sources: Optional[Sequence[str]] = None,
	force_refresh: bool = False,
):
	"""Return a merged list of calendar entries for the logged-in employee."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to view your calendar."), frappe.PermissionError)

	employee = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": ["!=", "Inactive"]},
		["name", "employee_full_name"],
		as_dict=True,
	)
	if not employee:
		frappe.throw(_("Your user is not linked to an Employee record."), frappe.PermissionError)
	employee_id = employee["name"]

	tzinfo = _system_tzinfo()
	tzname = tzinfo.zone
	window_start, window_end = _resolve_window(from_datetime, to_datetime, tzinfo)
	source_list = _normalize_sources(sources)

	cache_key = _cache_key(employee_id, window_start, window_end, source_list)
	if not force_refresh:
		if cached := frappe.cache().get_value(cache_key):
			try:
				return frappe.parse_json(cached)
			except Exception:
				pass

	events: List[CalendarEvent] = []
	source_counts: MutableMapping[str, int] = defaultdict(int)

	if "student_group" in source_list:
		sg_events = _collect_student_group_events(
			user,
			window_start,
			window_end,
			tzinfo,
			employee_id=employee_id,
		)
		for evt in sg_events:
			events.append(evt)
			source_counts[evt.source] += 1

	if "staff_holiday" in source_list:
		holiday_events = _collect_staff_holiday_events(
			user,
			window_start,
			window_end,
			tzinfo,
			employee_id=employee_id,
		)
		for evt in holiday_events:
			events.append(evt)
			source_counts[evt.source] += 1

	if "meeting" in source_list:
		meeting_events = _collect_meeting_events(user, window_start, window_end, tzinfo)
		for evt in meeting_events:
			events.append(evt)
			source_counts[evt.source] += 1

	if "school_event" in source_list:
		se_events = _collect_school_events(user, window_start, window_end, tzinfo)
		for evt in se_events:
			events.append(evt)
			source_counts[evt.source] += 1

	events.sort(key=lambda ev: (ev.start, ev.end, ev.id))

	payload = {
		"timezone": tzname,
		"window": {
			"from": window_start.isoformat(),
			"to": window_end.isoformat(),
		},
		"generated_at": _localize_datetime(now_datetime(), tzinfo).isoformat(),
		"events": [evt.as_dict() for evt in events],
		"sources": source_list,
		"counts": dict(source_counts),
	}

	frappe.cache().set_value(cache_key, frappe.as_json(payload), expires_in_sec=CACHE_TTL_SECONDS)
	return payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _system_tzinfo() -> pytz.timezone:
	tzname = get_system_timezone() or "UTC"
	return pytz.timezone(tzname)


def _normalize_sources(raw) -> List[str]:
	if not raw:
		return sorted(VALID_SOURCES)
	if isinstance(raw, str):
		try:
			raw = frappe.parse_json(raw)
		except Exception:
			raw = [raw]
	if isinstance(raw, (set, tuple)):
		raw = list(raw)
	if not isinstance(raw, list):
		return sorted(VALID_SOURCES)
	out = [s for s in raw if isinstance(s, str) and s in VALID_SOURCES]
	return out or sorted(VALID_SOURCES)


def _cache_key(employee: str, start: datetime, end: datetime, sources: Sequence[str]) -> str:
	src_key = ",".join(sorted(sources))
	return f"ifw:staff-cal:{employee}:{start.date().isoformat()}:{end.date().isoformat()}:{src_key}"


def _resolve_window(
	start_raw: Optional[str],
	end_raw: Optional[str],
	tzinfo: pytz.timezone,
) -> Tuple[datetime, datetime]:
	now = _localize_datetime(now_datetime(), tzinfo)
	default_start = now - timedelta(days=LOOKBACK_DAYS)
	if start_raw:
		start_dt = _to_system_datetime(start_raw, tzinfo)
	else:
		start_dt = default_start

	if end_raw:
		end_dt = _to_system_datetime(end_raw, tzinfo)
	else:
		end_dt = start_dt + timedelta(days=DEFAULT_WINDOW_DAYS)

	if end_dt <= start_dt:
		end_dt = start_dt + timedelta(days=1)

	return start_dt, end_dt


def _to_system_datetime(value: str | datetime, tzinfo: pytz.timezone) -> datetime:
	"""
	Convert a stored datetime to the site timezone.
	- If the incoming datetime is naive, treat it as already in the site tz and localize it.
	- If it already has tzinfo, convert to the site tz.
	"""
	if not isinstance(value, datetime):
		dt = get_datetime(value)
	else:
		dt = value

	if dt.tzinfo is None:
		return tzinfo.localize(dt)
	return dt.astimezone(tzinfo)


def _localize_datetime(dt: datetime, tzinfo: pytz.timezone) -> datetime:
	if dt.tzinfo:
		return dt.astimezone(tzinfo)
	return tzinfo.localize(dt)


def _coerce_time(value) -> Optional[time]:
	if not value:
		return None
	if isinstance(value, time):
		return value
	if isinstance(value, datetime):
		return value.time()
	if isinstance(value, timedelta):
		total = int(value.total_seconds())
		hours = (total // 3600) % 24
		minutes = (total % 3600) // 60
		seconds = total % 60
		return time(hour=hours, minute=minutes, second=seconds)
	if isinstance(value, (bytes, bytearray)):
		value = value.decode()
	if isinstance(value, str):
		parts = value.split(":")
		try:
			hours = int(parts[0])
			minutes = int(parts[1]) if len(parts) > 1 else 0
			seconds = int(parts[2]) if len(parts) > 2 else 0
		except ValueError:
			return None
		return time(hour=hours, minute=minutes, second=seconds)
	return None


def _time_to_str(raw, fallback: str = "00:00:00") -> str:
	"""Normalize various time-like values to HH:MM:SS strings."""
	if raw is None:
		return fallback
	if isinstance(raw, time):
		return raw.strftime("%H:%M:%S")
	if isinstance(raw, datetime):
		return raw.time().strftime("%H:%M:%S")
	if isinstance(raw, timedelta):
		total = int(raw.total_seconds())
		h = (total // 3600) % 24
		m = (total % 3600) // 60
		s = total % 60
		return f"{h:02}:{m:02}:{s:02}"
	if isinstance(raw, (bytes, bytearray)):
		raw = raw.decode()
	if isinstance(raw, str):
		return raw.strip()[:8]
	return fallback


def _combine(date_obj: date, time_obj: Optional[time], tzinfo: pytz.timezone) -> datetime:
	from_time = time_obj or time(hour=8, minute=0)
	combined = datetime.combine(date_obj, from_time)
	return tzinfo.localize(combined)


def _attach_duration(start_dt: datetime, end_dt: Optional[datetime]) -> timedelta:
	if not end_dt or end_dt <= start_dt:
		return CAL_MIN_DURATION
	return end_dt - start_dt


def _course_meta_map(course_ids: Iterable[str]) -> Dict[str, frappe._dict]:
	unique_ids = sorted({cid for cid in course_ids if cid})
	if not unique_ids:
		return {}
	rows = frappe.get_all(
		"Course",
		filters={"name": ["in", unique_ids]},
		fields=["name", "course_name", "calendar_event_color"],
		ignore_permissions=True,
	)
	return {row.name: row for row in rows}


def _student_group_title_and_color(
	group_name: str,
	group_label: Optional[str],
	course_id: Optional[str],
	meta: Dict[str, frappe._dict],
) -> Tuple[str, str]:
	course = meta.get(course_id) if course_id else None
	title = (
		course.course_name
		if course and course.course_name
		else group_label
		or group_name
		or _("Class")
	)
	color = (course.calendar_event_color or "").strip() if course else ""
	return title, color or "#2563eb"


def _resolve_instructor_ids(user: str, employee_id: Optional[str]) -> set[str]:
	instructor_ids = set(
		frappe.get_all(
			"Instructor",
			filters={"linked_user_id": user},
			pluck="name",
			ignore_permissions=True,
		)
		or []
	)
	if employee_id:
		instructor_ids.update(
			frappe.get_all(
				"Instructor",
				filters={"employee": employee_id},
				pluck="name",
				ignore_permissions=True,
			)
			or []
		)
	return instructor_ids


def _student_group_memberships(
	user: str,
	employee_id: Optional[str],
	instructor_ids: set[str],
) -> Tuple[set[str], set[str]]:
	"""Return (group_names, instructor_ids) resolved via Student Group Instructor rows."""
	group_names: set[str] = set()

	def _consume(rows: Iterable[frappe._dict]):
		for row in rows or []:
			parent = getattr(row, "parent", None)
			if parent:
				group_names.add(parent)
			instr = getattr(row, "instructor", None)
			if instr:
				instructor_ids.add(instr)

	base_filters = {"parenttype": "Student Group"}
	fields = ["parent", "instructor"]

	if user and user != "Guest":
		_consume(
			frappe.get_all(
				"Student Group Instructor",
				filters={**base_filters, "user_id": user},
				fields=fields,
				ignore_permissions=True,
			)
		)

	if employee_id:
		_consume(
			frappe.get_all(
				"Student Group Instructor",
				filters={**base_filters, "employee": employee_id},
				fields=fields,
				ignore_permissions=True,
			)
		)

	if instructor_ids:
		_consume(
			frappe.get_all(
				"Student Group Instructor",
				filters={**base_filters, "instructor": ["in", list(instructor_ids)]},
				fields=fields,
				ignore_permissions=True,
			)
		)

	return group_names, instructor_ids


# ---------------------------------------------------------------------------
# Staff Calendar resolution
# ---------------------------------------------------------------------------

def _resolve_staff_calendar_for_employee(
	employee_id: str,
	start_date: date,
	end_date: date,
) -> Optional[dict]:
	"""
	Return the single best Staff Calendar match for this employee and window.

	Rule:
	- employee_group must match
	- calendar must overlap [start_date, end_date]
	- calendar school is chosen by nearest match in the employee school's ancestor chain
	  (employee school first, then parent, then grandparent...)

	This enables parent-school staff calendars to apply to descendant schools,
	while still allowing child calendars to override.
	"""
	if not employee_id:
		return None

	# employee_group is permlevel=1, so ignore_permissions is required here
	emp_rows = frappe.get_all(
		"Employee",
		filters={"name": employee_id},
		fields=["name", "school", "employee_group"],
		limit=1,
		ignore_permissions=True,
	)

	if not emp_rows:
		return None

	emp = emp_rows[0]
	employee_school = emp.get("school")
	employee_group = emp.get("employee_group")

	if not employee_school or not employee_group:
		return None

	# Build school chain (nearest-first): [employee_school] + ancestors
	from frappe.utils.nestedset import get_ancestors_of
	ancestors = get_ancestors_of("School", employee_school) or []
	school_chain = [employee_school] + ancestors

	# Fetch all overlapping calendars for any school in chain
	cals = frappe.get_all(
		"Staff Calendar",
		filters={
			"employee_group": employee_group,
			"school": ["in", school_chain],
			"from_date": ["<=", end_date],
			"to_date": [">=", start_date],
		},
		fields=["name", "school", "employee_group", "from_date", "to_date"],
		ignore_permissions=True,
	)

	if not cals:
		return None

	# Choose nearest school match
	rank = {school: i for i, school in enumerate(school_chain)}
	cals.sort(key=lambda r: rank.get(r.get("school"), 10**9))

	# Multiple matches should be prevented by Staff Calendar overlap validation.
	# Still log deterministically and continue.
	if len(cals) > 1:
		frappe.logger("ifitwala_ed.calendar").warning(
			"Multiple Staff Calendar matches; using nearest school match",
			{
				"employee": employee_id,
				"employee_school": employee_school,
				"employee_group": employee_group,
				"window_start": start_date.isoformat(),
				"window_end": end_date.isoformat(),
				"matches": [c.get("name") for c in cals[:10]],
			},
		)

	best = cals[0]
	return {
		"name": best.get("name"),
		"school": best.get("school"),
		"employee_group": best.get("employee_group"),
	}


# ---------------------------------------------------------------------------
# Student Group slots
# ---------------------------------------------------------------------------

def _collect_student_group_events(
	user: str,
	window_start: datetime,
	window_end: datetime,
	tzinfo: pytz.timezone,
	*,
	employee_id: Optional[str] = None,
) -> List[CalendarEvent]:
	employee_id = employee_id or frappe.db.get_value("Employee", {"user_id": user}, "name")
	return _collect_student_group_events_from_bookings(employee_id, window_start, window_end, tzinfo)


def _collect_student_group_events_from_bookings(
	employee_id: Optional[str],
	window_start: datetime,
	window_end: datetime,
	tzinfo: pytz.timezone,
) -> List[CalendarEvent]:
	if not employee_id or not frappe.db.table_exists("Employee Booking"):
		return []

	rows = frappe.db.sql(
		"""
		SELECT
			eb.name            AS booking_name,
			eb.from_datetime   AS from_datetime,
			eb.to_datetime     AS to_datetime,
			eb.source_name     AS student_group,
			sg.student_group_name,
			sg.course,
			sg.program,
			sg.program_offering,
			sg.school,
			sg.school_schedule,
			sg.academic_year,
			sg.status
		FROM `tabEmployee Booking` eb
		LEFT JOIN `tabStudent Group` sg ON sg.name = eb.source_name
		WHERE eb.employee = %(employee)s
			AND eb.source_doctype = 'Student Group'
			AND eb.docstatus < 2
			AND eb.from_datetime < %(window_end)s
			AND eb.to_datetime > %(window_start)s
			AND (sg.status IS NULL OR sg.status = 'Active')
		""",
		{"employee": employee_id, "window_start": window_start, "window_end": window_end},
		as_dict=True,
	)

	if not rows:
		return []

	course_meta = _course_meta_map(row.course for row in rows if row.course)
	events: List[CalendarEvent] = []

	for row in rows:
		sg_name = row.student_group or row.booking_name
		title, color = _student_group_title_and_color(
			sg_name,
			row.student_group_name,
			row.course,
			course_meta,
		)

		start_dt = _to_system_datetime(row.from_datetime, tzinfo)
		end_dt = _to_system_datetime(row.to_datetime, tzinfo) if row.to_datetime else None
		duration = _attach_duration(start_dt, end_dt)

		events.append(
			CalendarEvent(
				id=f"sg-booking::{row.booking_name}",
				title=title,
				start=start_dt,
				end=start_dt + duration,
				source="student_group",
				color=color,
				all_day=False,
				meta={
					"student_group": row.student_group,
					"course": row.course,
					"booking": row.booking_name,
				},
			)
		)

	return events


# ---------------------------------------------------------------------------
# Staff Holidays
# ---------------------------------------------------------------------------

def _collect_staff_holiday_events(
	user: str,
	window_start: datetime,
	window_end: datetime,
	tzinfo: pytz.timezone,
	employee_id: Optional[str] = None,
) -> List[CalendarEvent]:
	if not employee_id:
		return []

	start_date = getdate(window_start)
	end_date = getdate(window_end - timedelta(seconds=1))

	cal = _resolve_staff_calendar_for_employee(employee_id, start_date, end_date)
	if not cal:
		return []

	holiday_rows = frappe.get_all(
		"Staff Calendar Holidays",
		filters={
			"parent": cal["name"],
			"holiday_date": ["between", [start_date, end_date]],
		},
		fields=["holiday_date", "description", "color", "weekly_off"],
		order_by="holiday_date asc",
		ignore_permissions=True,
	)

	if not holiday_rows:
		return []

	default_color = "#64748B"
	events: List[CalendarEvent] = []

	for row in holiday_rows:
		hd = getdate(row.get("holiday_date"))
		if not hd:
			continue

		start_dt = _combine(hd, time(0, 0, 0), tzinfo)
		end_dt = _combine(hd + timedelta(days=1), time(0, 0, 0), tzinfo)

		title = (row.get("description") or "").strip() or _("Holiday")
		color = (row.get("color") or "").strip() or default_color

		events.append(
			CalendarEvent(
				id=f"staff_holiday::{cal['name']}::{hd.isoformat()}",
				title=title,
				start=start_dt,
				end=end_dt,
				source="staff_holiday",
				color=color,
				all_day=True,
				meta={
					"staff_calendar": cal["name"],
					"holiday_date": hd.isoformat(),
					"weekly_off": int(row.get("weekly_off") or 0),
					"employee_group": cal["employee_group"],
					"school": cal["school"],
				},
			)
		)

	return events


# ---------------------------------------------------------------------------
# Meetings
# ---------------------------------------------------------------------------

def _collect_meeting_events(
	user: str,
	window_start: datetime,
	window_end: datetime,
	tzinfo: pytz.timezone,
) -> List[CalendarEvent]:
	start_date = window_start.date()
	end_date = window_end.date()

	employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")

	params = {
		"user": user,
		"emp": employee_id or "",
		"start": window_start,
		"end": window_end,
	}

	rows = frappe.db.sql(
		"""
		SELECT
			m.name,
			m.meeting_name,
			m.date,
			m.start_time,
			m.end_time,
			m.from_datetime,
			m.to_datetime,
			m.location,
			m.team,
			m.virtual_meeting_link
		FROM `tabMeeting Participant` mp
		INNER JOIN `tabMeeting` m ON mp.parent = m.name
		WHERE mp.parenttype = 'Meeting'
			AND (
				mp.participant = %(user)s
				OR (%(emp)s != '' AND mp.employee = %(emp)s)
			)
			AND m.docstatus < 2
			AND (
				(m.from_datetime BETWEEN %(start)s AND %(end)s)
				OR (m.to_datetime BETWEEN %(start)s AND %(end)s)
				OR (m.from_datetime <= %(start)s AND m.to_datetime >= %(end)s)
				OR (m.date BETWEEN %(start)s AND %(end)s) -- fallback if datetimes are missing
			)
			AND (m.status IS NULL OR m.status != 'Cancelled')
		""",
		params,
		as_dict=True,
	)

	if not rows:
		return []

	team_colors: Dict[str, str] = {}
	teams = {row.team for row in rows if row.team}
	if teams:
		color_rows = frappe.get_all(
			"Team",
			filters={"name": ["in", list(teams)]},
			fields=["name", "meeting_color"],
			ignore_permissions=True,
		)
		team_colors = {row.name: (row.meeting_color or "").strip() for row in color_rows}

	events: List[CalendarEvent] = []
	for row in rows:
		# Centralised meeting window logic
		start_dt, end_dt = _meeting_window(row, tzinfo)
		if not start_dt:
			# If we can't resolve any reasonable start, skip this meeting
			continue

		# Team colour (if any) becomes the default event colour.
		team_color = (team_colors.get(row.team, "") or "").strip()
		event_color = team_color or "#7c3aed"

		events.append(
			CalendarEvent(
				id=f"meeting::{row.name}",
				title=row.meeting_name or _("Meeting"),
				start=start_dt,
				end=end_dt,
				source="meeting",
				color=event_color,
				all_day=False,
				meta={
					"location": row.location,
					"team": row.team,
					"team_color": team_color,
					"virtual_link": row.virtual_meeting_link,
				},
			)
		)

	return events


@frappe.whitelist()
def get_meeting_details(meeting: str):
	"""
	Return a rich payload for a single Meeting that can be rendered inside
	the portal modal. Access is granted if:
	- the user is explicitly listed as a participant,
	- or the user's Employee record is listed on a participant row,
	- or the user otherwise has read permission on the Meeting (desk role).
	"""
	if not meeting:
		frappe.throw(_("Missing meeting id"), frappe.ValidationError)

	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to view meetings."), frappe.PermissionError)

	try:
		doc = frappe.get_doc("Meeting", meeting)
	except frappe.DoesNotExistError:
		frappe.throw(_("Meeting {0} was not found.").format(meeting), frappe.DoesNotExistError)

	if doc.docstatus == 2 or doc.status == "Cancelled":
		frappe.throw(_("This meeting is no longer available."), frappe.PermissionError)

	participants = frappe.get_all(
		"Meeting Participant",
		filters={"parent": doc.name, "parenttype": "Meeting"},
		fields=[
			"participant",
			"participant_name",
			"employee",
			"role_in_meeting",
			"attendance_status",
		],
		order_by="idx asc",
	)

	employee_id = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": ["!=", "Inactive"]},
		"name",
	)

	if not _meeting_access_allowed(doc, participants, user, employee_id):
		frappe.throw(_("You are not a participant of this meeting."), frappe.PermissionError)

	tzinfo = _system_tzinfo()
	start_dt, end_dt = _meeting_window(doc, tzinfo)

	team_meta = _get_team_meta(doc.team) if doc.team else {}
	leader_roles = {"chair", "leader", "meeting leader"}
	leaders = [
		row for row in participants if (row.get("role_in_meeting") or "").strip().lower() in leader_roles
	]

	payload = {
		"name": doc.name,
		"title": doc.meeting_name or doc.name,
		"status": doc.status or "Scheduled",
		"date": doc.date,
		"start": start_dt.isoformat() if start_dt else None,
		"end": end_dt.isoformat() if end_dt else None,
		"start_label": format_datetime(start_dt) if start_dt else None,
		"end_label": format_datetime(end_dt) if end_dt else None,
		"location": doc.location,
		"virtual_link": doc.virtual_meeting_link,
		"meeting_category": doc.meeting_category,
		"agenda": doc.agenda or "",
		"minutes": doc.minutes or "",
		"timezone": tzinfo.zone,
		"participants": participants,
		"participant_count": len(participants),
		"leaders": leaders,
		"team": doc.team,
		"team_name": team_meta.get("team_name") or doc.team,
		"team_color": team_meta.get("meeting_color"),
		"school": doc.school,
		"academic_year": doc.academic_year,
	}

	return payload


@frappe.whitelist()
def get_school_event_details(event: str):
	"""
	Return detailed metadata for a School Event visible to the current portal user.
	Requires either explicit participant visibility, school visibility, or desk read permission.
	"""
	if not event:
		frappe.throw(_("Missing school event id"), frappe.ValidationError)

	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to view school events."), frappe.PermissionError)

	try:
		doc = frappe.get_doc("School Event", event)
	except frappe.DoesNotExistError:
		frappe.throw(_("School Event {0} was not found.").format(event), frappe.DoesNotExistError)

	if doc.docstatus == 2:
		frappe.throw(_("This school event is no longer available."), frappe.PermissionError)

	if not _school_event_access_allowed(doc, user):
		frappe.throw(_("You are not allowed to view this school event."), frappe.PermissionError)

	tzinfo = _system_tzinfo()
	start_dt = _to_system_datetime(doc.starts_on, tzinfo) if doc.starts_on else None
	end_dt = _to_system_datetime(doc.ends_on, tzinfo) if doc.ends_on else None
	if start_dt and end_dt and end_dt <= start_dt:
		end_dt = start_dt + CAL_MIN_DURATION

	color = (doc.color or "").strip() or "#059669"

	return {
		"name": doc.name,
		"subject": doc.subject or _("School Event"),
		"school": doc.school,
		"location": doc.location,
		"event_category": doc.event_category,
		"event_type": doc.event_type,
		"all_day": bool(doc.all_day),
		"color": color,
		"description": doc.description or "",
		"start": start_dt.isoformat() if start_dt else None,
		"end": end_dt.isoformat() if end_dt else None,
		"start_label": format_datetime(start_dt) if start_dt else None,
		"end_label": format_datetime(end_dt) if end_dt else None,
		"reference_type": doc.reference_type,
		"reference_name": doc.reference_name,
		"timezone": tzinfo.zone,
	}


@frappe.whitelist()
def get_student_group_event_details(
	event_id: Optional[str] = None,
	eventId: Optional[str] = None,
	id: Optional[str] = None,
):
	"""
	Resolve a class (Student Group) calendar entry into a richer payload for the portal modal.
	Supports Employee Booking ids (sg-booking::...). Schedule-based ids are
	available only in explicit debug/abstract viewers.
	"""
	resolved_event_id = (
		event_id
		or eventId
		or id
		or frappe.form_dict.get("event_id")
		or frappe.form_dict.get("eventId")
		or frappe.form_dict.get("id")
	)

	if not resolved_event_id:
		frappe.throw(_("Missing class event id."), frappe.ValidationError)

	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to view classes."), frappe.PermissionError)

	tzinfo = _system_tzinfo()

	debug_booking = bool(
		frappe.form_dict.get("debug_booking")
		or frappe.form_dict.get("debug")
	)
	debug_schedule = bool(
		frappe.form_dict.get("debug_schedule")
		or frappe.form_dict.get("debug")
	)

	if resolved_event_id.startswith("sg::"):
		if not debug_schedule:
			frappe.throw(
				_("Schedule-based class events are only available in debug/abstract viewers."),
				frappe.PermissionError,
			)
		context = _resolve_sg_schedule_context(resolved_event_id, tzinfo)
	elif resolved_event_id.startswith("sg-booking::"):
		context = _resolve_sg_booking_context(resolved_event_id, tzinfo, debug=debug_booking)
	else:
		frappe.throw(_("Unsupported class event format."), frappe.ValidationError)

	group_name = context.get("student_group")
	if not group_name:
		frappe.throw(_("Unable to resolve the student group for this event."), frappe.ValidationError)

	if not _user_has_student_group_access(user, group_name):
		frappe.throw(_("You are not allowed to view this class."), frappe.PermissionError)

	group_row = frappe.db.get_value(
		"Student Group",
		group_name,
		[
			"name",
			"student_group_name",
			"group_based_on",
			"program",
			"course",
			"cohort",
			"school",
		],
		as_dict=True
	)
	if not group_row:
		frappe.throw(_("Student Group {0} was not found.").format(group_name), frappe.DoesNotExistError)

	course_meta = _course_meta_map([group_row.course] if group_row.course else [])
	course_label = None
	if group_row.course:
		course_label = (course_meta.get(group_row.course) or {}).get("course_name") or group_row.course

	start_dt = context.get("start")
	end_dt = context.get("end")
	if start_dt and end_dt and end_dt <= start_dt:
		end_dt = start_dt + CAL_MIN_DURATION

	return {
		"id": resolved_event_id,
		"student_group": group_row.name,
		"title": group_row.student_group_name or group_row.name,
		"class_type": group_row.group_based_on,
		"program": group_row.program,
		"course": group_row.course,
		"course_name": course_label,
		"cohort": group_row.cohort,
		"school": group_row.school,
		"rotation_day": context.get("rotation_day"),
		"block_number": context.get("block_number"),
		"block_label": context.get("block_label"),
		"session_date": context.get("session_date"),
		"location": context.get("location"),
		"location_missing_reason": context.get("location_missing_reason"),
		"start": start_dt.isoformat() if start_dt else None,
		"end": end_dt.isoformat() if end_dt else None,
		"start_label": format_datetime(start_dt) if start_dt else None,
		"end_label": format_datetime(end_dt) if end_dt else None,
		"timezone": tzinfo.zone,
		"_debug": context.get("_debug") if debug_booking else None,
	}


# ---------------------------------------------------------------------------
# School Events
# ---------------------------------------------------------------------------

def _collect_school_events(
	user: str,
	window_start: datetime,
	window_end: datetime,
	tzinfo: pytz.timezone,
) -> List[CalendarEvent]:
	emp_row = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": ["!=", "Inactive"]},
		["name", "school"],
		as_dict=True
	)
	employee_school = (emp_row or {}).get("school") if emp_row else None
	allowed_schools = get_ancestor_schools(employee_school) if employee_school else []
	params = {
		"user": user,
		"start": window_start,
		"end": window_end,
	}
	visibility_clauses = ["sep.participant IS NOT NULL"]
	if allowed_schools:
		params["schools"] = allowed_schools
		visibility_clauses.append("se.school IN %(schools)s")
	visibility_sql = " OR ".join(visibility_clauses)

	rows = frappe.db.sql(
		f"""
		SELECT
			se.name,
			se.subject,
			se.starts_on,
			se.ends_on,
			se.all_day,
			se.location,
			se.color,
			se.school,
			sep.participant_name
		FROM `tabSchool Event` se
		LEFT JOIN `tabSchool Event Participant` sep
			ON sep.parent = se.name
			AND sep.parenttype = 'School Event'
			AND sep.participant = %(user)s
		WHERE se.docstatus < 2
			AND ({visibility_sql})
			AND (
				(se.starts_on BETWEEN %(start)s AND %(end)s)
				OR (se.ends_on BETWEEN %(start)s AND %(end)s)
				OR (se.starts_on <= %(start)s AND se.ends_on >= %(end)s)
			)
		""",
		params,
		as_dict=True,
	)

	if not rows:
		return []

	events: List[CalendarEvent] = []
	for row in rows:
		start_dt = _to_system_datetime(row.starts_on, tzinfo) if row.starts_on else window_start
		end_dt_raw = row.ends_on or row.starts_on
		end_dt = _to_system_datetime(end_dt_raw, tzinfo) if end_dt_raw else (start_dt + CAL_MIN_DURATION)
		if end_dt <= start_dt:
			end_dt = start_dt + CAL_MIN_DURATION
		color = (row.color or "").strip() or "#059669"
		events.append(
			CalendarEvent(
				id=f"school_event::{row.name}",
				title=row.subject or _("School Event"),
				start=start_dt,
				end=end_dt,
				source="school_event",
				color=color,
				all_day=bool(row.all_day),
				meta={
					"location": row.location,
					"participant_name": row.participant_name,
					"school": row.school,
				},
			)
		)

	return events

def _meeting_window(meeting: frappe.model.document.Document, tzinfo: pytz.timezone) -> Tuple[Optional[datetime], Optional[datetime]]:
	"""
	Resolve Meeting start/end datetimes with sensible fallbacks so the portal
	modal can always display a window.
	"""
	start_dt = None
	end_dt = None

	if meeting.from_datetime:
		start_dt = _to_system_datetime(meeting.from_datetime, tzinfo)
	elif meeting.date:
		start_dt = _combine(getdate(meeting.date), _coerce_time(meeting.start_time), tzinfo)

	if meeting.to_datetime:
		end_dt = _to_system_datetime(meeting.to_datetime, tzinfo)
	elif meeting.date:
		end_dt = _combine(getdate(meeting.date), _coerce_time(meeting.end_time), tzinfo)

	if start_dt and (not end_dt or end_dt <= start_dt):
		duration = _attach_duration(start_dt, end_dt)
		end_dt = start_dt + duration

	return start_dt, end_dt


def _get_team_meta(team: Optional[str]) -> Dict[str, str]:
	if not team:
		return {}
	row = frappe.db.get_value(
		"Team",
		team,
		["name", "team_name", "meeting_color"],
		as_dict=True
	)
	return row or {}


def _meeting_access_allowed(meeting, participants: List[Dict[str, str]], user: str, employee_id: Optional[str]) -> bool:
	if frappe.has_permission("Meeting", doc=meeting, ptype="read"):
		return True

	for row in participants:
		if row.get("participant") == user:
			return True
		if employee_id and row.get("employee") == employee_id:
			return True

	return False


def _resolve_sg_schedule_context(event_id: str, tzinfo: pytz.timezone) -> Dict[str, object]:
	"""Debug/abstract schedule resolver (not for production calendar reads)."""
	event_id = event_id.replace("sg/", "sg::", 1) if event_id.startswith("sg/") else event_id
	parts = event_id.split("::")
	if len(parts) < 5:
		frappe.throw(_("Invalid class event id."), frappe.ValidationError)

	group_name = parts[1]
	try:
		rotation_day = int(parts[2])
	except ValueError:
		rotation_day = None
	try:
		block_number = int(parts[3])
	except ValueError:
		block_number = None

	try:
		session_date = getdate(parts[4])
	except Exception:
		session_date = None

	slot = None
	if group_name and rotation_day is not None and block_number is not None:
		slots = frappe.get_all(
			"Student Group Schedule",
			filters={
				"parent": group_name,
				"rotation_day": rotation_day,
				"block_number": block_number,
			},
			fields=["location", "from_time", "to_time"],
			limit=1,
			ignore_permissions=True,
		)
		slot = slots[0] if slots else None

	from_time = _coerce_time(slot.from_time) if slot else None
	to_time = _coerce_time(slot.to_time) if slot else None

	start_dt = _combine(session_date, from_time, tzinfo) if session_date else None
	end_dt = _combine(session_date, to_time, tzinfo) if session_date and to_time else None

	return {
		"student_group": group_name,
		"rotation_day": rotation_day,
		"block_number": block_number,
		"block_label": _("Block {0}").format(block_number) if block_number is not None else None,
		"session_date": session_date.isoformat() if session_date else None,
		"location": slot.location if slot else None,
		"start": start_dt,
		"end": end_dt,
	}


def _resolve_sg_booking_context(
	event_id: str,
	tzinfo: pytz.timezone,
	*,
	debug: bool = False,
) -> Dict[str, object]:
	booking_name = event_id.split("::", 1)[1]
	row = frappe.db.get_value(
		"Employee Booking",
		booking_name,
		["source_doctype", "source_name", "from_datetime", "to_datetime", "location"],
		as_dict=True,
	)
	if not row or row.source_doctype != "Student Group":
		frappe.throw(
			_("Employee Booking {0} was not found for a class.").format(booking_name),
			frappe.DoesNotExistError,
		)

	start_dt = _to_system_datetime(row.from_datetime, tzinfo) if row.from_datetime else None
	end_dt = _to_system_datetime(row.to_datetime, tzinfo) if row.to_datetime else None

	location = row.get("location") or None
	location_missing_reason = None if location else "booking-missing-location"

	context = {
		"student_group": row.source_name,
		"rotation_day": None,
		"block_number": None,
		"block_label": None,
		"session_date": start_dt.date().isoformat() if start_dt else None,
		"location": location,
		"location_missing_reason": location_missing_reason,
		"start": start_dt,
		"end": end_dt,
	}

	if debug:
		context["_debug"] = {
			"booking_name": booking_name,
			"location_present": bool(location),
			"location_missing_reason": location_missing_reason,
		}

	return context


def _user_has_student_group_access(user: str, group_name: str) -> bool:
	if not user or user == "Guest":
		return False
	employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
	instructor_ids = _resolve_instructor_ids(user, employee_id)
	group_names, _ = _student_group_memberships(user, employee_id, instructor_ids)
	if group_name in group_names:
		return True
	try:
		doc = frappe.get_doc("Student Group", group_name)
	except frappe.DoesNotExistError:
		return False
	except Exception:
		return False
	# Allow if user has desk-level read permission on the group
	return frappe.has_permission("Student Group", doc=doc, ptype="read")


def _school_event_access_allowed(event_doc, user: str) -> bool:
	if frappe.has_permission("School Event", doc=event_doc, ptype="read"):
		return True

	is_participant = frappe.db.exists(
		"School Event Participant",
		{"parent": event_doc.name, "parenttype": "School Event", "participant": user},
	)
	if is_participant:
		return True

	emp_row = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": ["!=", "Inactive"]},
		["school"],
		as_dict=True,
	)
	employee_school = (emp_row or {}).get("school")
	if employee_school and event_doc.school:
		allowed_schools = get_ancestor_schools(employee_school) or []
		if event_doc.school in allowed_schools:
			return True

	return False


# ---------------------------------------------------------------------------
# Debug helpers
# ---------------------------------------------------------------------------

@frappe.whitelist()
def debug_staff_calendar_window(from_datetime: Optional[str] = None, to_datetime: Optional[str] = None):
	"""
	Lightweight debug endpoint: returns detected instructor ids, matched
	student groups, and a small sample of events for the current user.
	Useful for quick browser testing.
	"""
	user = frappe.session.user
	tzinfo = _system_tzinfo()
	start, end = _resolve_window(from_datetime, to_datetime, tzinfo)

	# instructor ids
	instr = set(
		frappe.get_all("Instructor", filters={"linked_user_id": user}, pluck="name", ignore_permissions=True)
		or []
	)
	emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if emp:
		instr.update(
			frappe.get_all("Instructor", filters={"employee": emp}, pluck="name", ignore_permissions=True) or []
		)

	# sg groups via SG Instructor
	sgi = set(
		frappe.get_all(
			"Student Group Instructor",
			filters={"parenttype": "Student Group", "instructor": ["in", list(instr) or [""]]},
			pluck="parent",
			ignore_permissions=True,
		)
		or []
	)

	# quick sample of student group events only (limit 10)
	sample = _collect_student_group_events(user, start, end, tzinfo)[:10]
	holiday_events = _collect_staff_holiday_events(
		user,
		start,
		end,
		tzinfo,
		employee_id=emp,
	)
	holiday_sample = holiday_events[:5]
	booking_samples = []
	if emp and frappe.db.table_exists("Employee Booking"):
		booking_rows = frappe.get_all(
			"Employee Booking",
			filters={
				"employee": emp,
				"source_doctype": "Student Group",
				"docstatus": ["<", 2],
				"from_datetime": ["<", end],
				"to_datetime": [">", start],
			},
			fields=["name", "source_name", "from_datetime", "to_datetime"],
			order_by="from_datetime desc",
			limit=5,
			ignore_permissions=True,
		)
		for row in booking_rows:
			context = _resolve_sg_booking_context(f"sg-booking::{row.name}", tzinfo, debug=True)
			booking_samples.append(
				{
					"booking": row.name,
					"student_group": row.source_name,
					"from": row.from_datetime,
					"to": row.to_datetime,
					"rotation_day": context.get("rotation_day"),
					"block_number": context.get("block_number"),
					"location": context.get("location"),
					"resolution": context.get("_debug"),
				}
			)

	return {
		"user": user,
		"system_tz": tzinfo.zone,
		"window": {"from": start.isoformat(), "to": end.isoformat()},
		"instructor_ids": sorted(instr),
		"sg_instructor_groups": sorted(sgi),
		"sample_events": [e.as_dict() for e in sample],
		"staff_holiday_count": len(holiday_events),
		"staff_holiday_sample": [e.as_dict() for e in holiday_sample],
		"booking_samples": booking_samples,
	}


@frappe.whitelist()
def get_portal_calendar_prefs(from_datetime: Optional[str] = None, to_datetime: Optional[str] = None):
	"""
	Return portal calendar preferences for the logged-in employee:
	- timezone (System Settings)
	- weekendDays (FullCalendar day indices to hide when weekends are off)
	- defaultSlotMin/Max (from School settings)
	"""
	user = frappe.session.user
	tzinfo = _system_tzinfo()

	# Resolve user's base school via Employee, else Instructor
	school = (
		frappe.db.get_value("Employee", {"user_id": user}, "school")
		or frappe.db.get_value("Instructor", {"linked_user_id": user}, "school")
	)

	# Academic Year window to scope the schedule/calendar
	try:
		from ifitwala_ed.schedule.schedule_utils import current_academic_year

		ay = current_academic_year()
	except Exception:
		ay = None

	# Find a School Schedule → School Calendar
	calendar_name = None
	if school and ay:
		sched = get_effective_schedule_for_ay(ay, school)
		if sched:
			try:
				sched_doc = frappe.get_cached_doc("School Schedule", sched)
				calendar_name = getattr(sched_doc, "school_calendar", None)
			except Exception:
				calendar_name = None

	# Fallback: School.current_school_calendar
	if not calendar_name and school:
		calendar_name = frappe.db.get_value("School", school, "current_school_calendar")

	weekend_fc_days: List[int] = get_weekend_days_for_calendar(calendar_name) if calendar_name else get_weekend_days_for_calendar(None)


	# Default slot window from School
	default_min = "07:00:00"
	default_max = "17:00:00"
	if school:
		row = frappe.db.get_value(
			"School",
			school,
			["portal_calendar_start_time", "portal_calendar_end_time"],
			as_dict=True,
		)
		if row:
			default_min = _time_to_str(row.get("portal_calendar_start_time"), default_min)
			default_max = _time_to_str(row.get("portal_calendar_end_time"), default_max)

	return {
		"timezone": tzinfo.zone,
		"weekendDays": weekend_fc_days,
		"defaultSlotMin": default_min,
		"defaultSlotMax": default_max,
	}
