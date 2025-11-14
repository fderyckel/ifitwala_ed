# ifitwala_ed/api/calendar.py

"""
APIs feeding the portal calendars (staff / student / guardian).

Current scope: staff calendar that aggregates Student Group schedules,
Meetings, Frappe Events, and School Events the logged-in employee participates in.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

import pytz

import frappe
from frappe import _
from frappe.utils import (
	get_datetime,
	get_system_timezone,
	getdate,
	now_datetime,
)

from ifitwala_ed.schedule.schedule_utils import (
    get_effective_schedule_for_ay,
    get_rotation_dates,
    get_school_for_student_group,
)

VALID_SOURCES = {
	"student_group",
	"meeting",
	"school_event",
	"frappe_event",
}

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

	tzinfo = _system_tzinfo()
	tzname = tzinfo.zone
	window_start, window_end = _resolve_window(from_datetime, to_datetime, tzinfo)
	source_list = _normalize_sources(sources)

	cache_key = _cache_key(employee["name"], window_start, window_end, source_list)
	if not force_refresh:
		if cached := frappe.cache().get_value(cache_key):
			try:
				return frappe.parse_json(cached)
			except Exception:
				pass

	events: List[CalendarEvent] = []
	source_counts: MutableMapping[str, int] = defaultdict(int)

	if "student_group" in source_list:
		sg_events = _collect_student_group_events(user, window_start, window_end, tzinfo)
		for evt in sg_events:
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

	if "frappe_event" in source_list:
		frappe_events = _collect_frappe_events(user, window_start, window_end, tzinfo)
		for evt in frappe_events:
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
	Convert a DB datetime (stored as UTC) to the system timezone.
	- If the incoming datetime is naive, assume it is UTC and convert.
	- If it already has tzinfo, just convert to the system tz.
	"""
	if not isinstance(value, datetime):
		dt = get_datetime(value)
	else:
		dt = value

	if dt.tzinfo is None:
		# Treat DB naive timestamps as UTC
		dt = pytz.UTC.localize(dt)
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


def _combine(date_obj: date, time_obj: Optional[time], tzinfo: pytz.timezone) -> datetime:
	from_time = time_obj or time(hour=8, minute=0)
	combined = datetime.combine(date_obj, from_time)
	return tzinfo.localize(combined)


def _attach_duration(start_dt: datetime, end_dt: Optional[datetime]) -> timedelta:
	if not end_dt or end_dt <= start_dt:
		return CAL_MIN_DURATION
	return end_dt - start_dt


# ---------------------------------------------------------------------------
# Student Group slots
# ---------------------------------------------------------------------------

def _collect_student_group_events(
	user: str,
	window_start: datetime,
	window_end: datetime,
	tzinfo: pytz.timezone,
) -> List[CalendarEvent]:
	start_date, end_date = window_start.date(), window_end.date()

	# Resolve instructor identities for this user
	instructor_ids = set(
		frappe.get_all(
			"Instructor",
			filters={"linked_user_id": user},
			pluck="name",
			ignore_permissions=True,
		)
		or []
	)

	if not instructor_ids:
		# Fallback: if user is an Employee, find Instructor linked via employee
		emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if emp:
			extra = frappe.get_all(
				"Instructor",
				filters={"employee": emp},
				pluck="name",
				ignore_permissions=True,
			)
			instructor_ids.update(extra or [])

	# If user has no instructor identity, we can't match class rows
	if not instructor_ids:
		return []

	# Fetch time slots for groups where the slot instructor matches this user
	slot_rows = frappe.get_all(
		"Student Group Schedule",
		filters={
			"parenttype": "Student Group",
			"instructor": ["in", list(instructor_ids)],
		},
		fields=[
			"parent",
			"rotation_day",
			"block_number",
			"location",
			"instructor",
			"from_time",
			"to_time",
		],
		ignore_permissions=True,
	)

	# Also include groups where the user is listed as SG Instructor but
	# the slot has no explicit instructor
	sgi_groups = set(
		frappe.get_all(
			"Student Group Instructor",
			filters={
				"parenttype": "Student Group",
				"instructor": ["in", list(instructor_ids)],
			},
			pluck="parent",
			ignore_permissions=True,
		)
		or []
	)
	# If the user was linked via user_id but no Instructor match, include those too
	sgi_groups.update(
		frappe.get_all(
			"Student Group Instructor",
			filters={"parenttype": "Student Group", "user_id": user},
			pluck="parent",
			ignore_permissions=True,
		)
		or []
	)

	if sgi_groups:
		blank_rows = frappe.get_all(
			"Student Group Schedule",
			filters={"parent": ["in", list(sgi_groups)]},
			fields=[
				"parent",
				"rotation_day",
				"block_number",
				"location",
				"instructor",
				"from_time",
				"to_time",
			],
			ignore_permissions=True,
		)
		for r in blank_rows:
			if not r.instructor and r.rotation_day:
				slot_rows.append(r)

	if not slot_rows:
		return []

	group_names = sorted({row.parent for row in slot_rows})

	group_docs = frappe.get_all(
		"Student Group",
		filters={"name": ["in", group_names], "status": "Active"},
		fields=[
			"name",
			"student_group_name",
			"course",
			"program",
			"program_offering",
			"school",
			"school_schedule",
			"academic_year",
		],
		ignore_permissions=True,
	)
	if not group_docs:
		return []

	course_ids = [g.course for g in group_docs if g.course]
	course_meta = {}
	if course_ids:
		course_rows = frappe.get_all(
			"Course",
			filters={"name": ["in", course_ids]},
			fields=["name", "course_name", "calendar_event_color"],
			ignore_permissions=True,
		)
		course_meta = {row.name: row for row in course_rows}

	# Group slots by SG for easier rendering
	slots_by_group: Dict[str, List[dict]] = defaultdict(list)
	for slot in slot_rows:
		if slot.rotation_day:
			slots_by_group[slot.parent].append(slot)

	rotation_cache: Dict[Tuple[str, str, int], Dict[int, List[date]]] = {}
	events: List[CalendarEvent] = []

	for group in group_docs:
		slots = slots_by_group.get(group.name)
		if not slots:
			continue

		school = group.school or get_school_for_student_group(group.name)
		if not school:
			continue

		schedule_name = group.school_schedule or get_effective_schedule_for_ay(group.academic_year, school)
		if not schedule_name:
			continue

		sched_doc = frappe.get_cached_doc("School Schedule", schedule_name)
		include_holidays = int(bool(sched_doc.include_holidays_in_rotation))
		cache_key = (schedule_name, group.academic_year, include_holidays)

		# Resolve effective AY (use schedule's AY if group lacks one)
		effective_ay = group.academic_year or getattr(sched_doc, "academic_year", None)
		if not effective_ay:
			continue

		if cache_key not in rotation_cache:
			rotation_dates = get_rotation_dates(
				schedule_name,
				effective_ay,
				include_holidays=bool(include_holidays),
			)
			day_map: Dict[int, List[date]] = defaultdict(list)
			for row in rotation_dates:
				rot_day = int(row["rotation_day"])
				day_val = getdate(row["date"])
				day_map[rot_day].append(day_val)
			rotation_cache[cache_key] = day_map

		rot_map = rotation_cache[cache_key]
		course = course_meta.get(group.course) if group.course else None
		title = course.course_name if course and course.course_name else group.student_group_name or group.name
		color = (course.calendar_event_color or "").strip() if course else ""
		color = color or "#2563eb"

		for slot in slots:
			dates = rot_map.get(int(slot.rotation_day)) or []
			from_time = _coerce_time(slot.from_time)
			to_time = _coerce_time(slot.to_time)
			for session_date in dates:
				if session_date < start_date or session_date > end_date:
					continue
				start_dt = _combine(session_date, from_time, tzinfo)
				duration = _attach_duration(
					start_dt,
					_combine(session_date, to_time, tzinfo) if to_time else None,
				)
				end_dt = start_dt + duration

				events.append(
					CalendarEvent(
						id=f"sg::{group.name}::{slot.rotation_day}::{slot.block_number}::{session_date.isoformat()}",
						title=title,
						start=start_dt,
						end=end_dt,
						source="student_group",
						color=color,
						all_day=False,
						meta={
							"student_group": group.name,
							"course": group.course,
							"rotation_day": slot.rotation_day,
							"block_number": slot.block_number,
							"location": slot.location,
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

	rows = frappe.db.sql(
		"""
		SELECT
			m.name,
			m.meeting_name,
			m.date,
			m.start_time,
			m.end_time,
			m.location,
			m.team,
			m.virtual_meeting_link
		FROM `tabMeeting Participant` mp
		INNER JOIN `tabMeeting` m ON mp.parent = m.name
		WHERE mp.parenttype = 'Meeting'
			AND mp.participants = %(user)s
			AND m.date BETWEEN %(start)s AND %(end)s
			AND (m.status IS NULL OR m.status != 'Cancelled')
		""",
		{"user": user, "start": start_date, "end": end_date},
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
		if not row.date:
			continue
		day = getdate(row.date)
		start_dt = _combine(day, _coerce_time(row.start_time), tzinfo)
		end_dt = None
		if row.end_time:
			end_dt = _combine(day, _coerce_time(row.end_time), tzinfo)
		duration = _attach_duration(start_dt, end_dt)
		color = team_colors.get(row.team, "#7c3aed")

		events.append(
			CalendarEvent(
				id=f"meeting::{row.name}",
				title=row.meeting_name or _("Meeting"),
				start=start_dt,
				end=start_dt + duration,
				source="meeting",
				color=color or "#7c3aed",
				meta={
					"location": row.location,
					"team": row.team,
					"virtual_link": row.virtual_meeting_link,
				},
			)
		)

	return events


# ---------------------------------------------------------------------------
# School Events
# ---------------------------------------------------------------------------

def _collect_school_events(
	user: str,
	window_start: datetime,
	window_end: datetime,
	tzinfo: pytz.timezone,
) -> List[CalendarEvent]:
	rows = frappe.db.sql(
		"""
		SELECT
			se.name,
			se.subject,
			se.starts_on,
			se.ends_on,
			se.all_day,
			se.location,
			se.color,
			sep.participant_name
		FROM `tabSchool Event Participant` sep
		INNER JOIN `tabSchool Event` se ON se.name = sep.parent
		WHERE sep.participant = %(user)s
			AND se.docstatus < 2
			AND (
				(se.starts_on BETWEEN %(start)s AND %(end)s)
				OR (se.ends_on BETWEEN %(start)s AND %(end)s)
				OR (se.starts_on <= %(start)s AND se.ends_on >= %(end)s)
			)
		""",
		{
			"user": user,
			"start": window_start,
			"end": window_end,
		},
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
				},
			)
		)

	return events


# ---------------------------------------------------------------------------
# Frappe Events
# ---------------------------------------------------------------------------

def _collect_frappe_events(
	user: str,
	window_start: datetime,
	window_end: datetime,
	tzinfo: pytz.timezone,
) -> List[CalendarEvent]:
	rows = frappe.db.sql(
		"""
		SELECT
			ev.name,
			ev.subject,
			ev.starts_on,
			ev.ends_on,
			ev.all_day,
			ev.event_category,
			ev.color
		FROM `tabEvent Participants` ep
		INNER JOIN `tabEvent` ev ON ev.name = ep.parent
		WHERE ep.parenttype = 'Event'
			AND ep.reference_doctype = 'User'
			AND ep.reference_docname = %(user)s
			AND ev.docstatus < 2
			AND (
				(ev.starts_on BETWEEN %(start)s AND %(end)s)
				OR (ev.ends_on BETWEEN %(start)s AND %(end)s)
				OR (ev.starts_on <= %(start)s AND ev.ends_on >= %(end)s)
			)
		""",
		{
			"user": user,
			"start": window_start,
			"end": window_end,
		},
		as_dict=True,
	)

	if not rows:
		return []

	events: List[CalendarEvent] = []
	for row in rows:
		start_dt = _to_system_datetime(row.starts_on, tzinfo) if row.starts_on else window_start
		end_dt = _to_system_datetime(row.ends_on, tzinfo) if row.ends_on else (start_dt + CAL_MIN_DURATION)
		if end_dt <= start_dt:
			end_dt = start_dt + CAL_MIN_DURATION
		color = (row.color or "").strip() or "#f59e0b"
		events.append(
			CalendarEvent(
				id=f"frappe_event::{row.name}",
				title=row.subject or _("Event"),
				start=start_dt,
				end=end_dt,
				source="frappe_event",
				color=color,
				all_day=bool(row.all_day),
				meta={"category": row.event_category},
			)
		)

	return events


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

	return {
		"user": user,
		"system_tz": tzinfo.zone,
		"window": {"from": start.isoformat(), "to": end.isoformat()},
		"instructor_ids": sorted(instr),
		"sg_instructor_groups": sorted(sgi),
		"sample_events": [e.as_dict() for e in sample],
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

	weekend_fc_days: List[int] = []
	if calendar_name:
		try:
			cal = frappe.get_cached_doc("School Calendar", calendar_name)
			# Collect weekdays for entries flagged as weekly_off
			days = set()
			for h in (cal.holidays or []):
				try:
					if int(getattr(h, "weekly_off", 0)) == 1 and getattr(h, "holiday_date", None):
						d = getdate(h.holiday_date)
						py_weekday = d.weekday()  # Monday=0..Sunday=6
						fc_day = (py_weekday + 1) % 7  # Sunday=0..Saturday=6
						days.add(fc_day)
				except Exception:
					continue
			weekend_fc_days = sorted(days)
		except Exception:
			weekend_fc_days = []

	if not weekend_fc_days:
		# Default to Sat/Sun
		weekend_fc_days = [0, 6]

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
			default_min = (row.get("portal_calendar_start_time") or default_min)[:8]
			default_max = (row.get("portal_calendar_end_time") or default_max)[:8]

	return {
		"timezone": tzinfo.zone,
		"weekendDays": weekend_fc_days,
		"defaultSlotMin": default_min,
		"defaultSlotMax": default_max,
	}
