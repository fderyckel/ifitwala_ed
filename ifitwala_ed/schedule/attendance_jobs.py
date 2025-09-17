# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/attendance_jobs.py

import frappe
from frappe.utils import now_datetime, nowdate, get_datetime, add_to_date, time_diff_in_seconds
from typing import Dict, Set, List, Tuple
from ifitwala_ed.schedule.schedule_utils import current_academic_year, build_rotation_map
from ifitwala_ed.schedule.attendance_utils import get_meeting_dates, LIMIT_DEFAULT, SG_SCHEDULE_DT


def _groups_with_schedule_in_ay(ay: str) -> List[dict]:
	"""
	Return SGs in the active AY that have a school_calendar and at least one schedule row.
	Fields kept minimal to reduce transfer.
	"""
	return frappe.db.sql(
		"""
		SELECT sg.name, sg.school_calendar
		FROM `tabStudent Group` sg
		WHERE sg.academic_year = %(ay)s
		  AND sg.school_calendar IS NOT NULL
		  AND EXISTS (
				SELECT 1 FROM `tabStudent Group Schedule` sgs WHERE sgs.parent = sg.name
		  )
		""",
		{"ay": ay},
		as_dict=True,
	)

def _rotation_days_by_group(names: List[str]) -> Dict[str, Set[int]]:
	"""Map each SG → {rotation_day,...} from Student Group Schedule rows."""
	if not names:
		return {}
	rows = frappe.db.get_all(
		SG_SCHEDULE_DT,
		filters={"parent": ["in", names]},
		fields=["parent", "rotation_day"]
	)
	out: Dict[str, Set[int]] = {}
	for r in rows:
		if r.rotation_day:
			out.setdefault(r.parent, set()).add(int(r.rotation_day))
	return out

def _today_rotation_for_calendars(calendars: Set[str], today_iso: str) -> Dict[str, int | None]:
	"""
	Use build_rotation_map(calendar) ONCE per calendar (already Redis-cached).
	Return calendar_name → today's rotation_day (or None if holiday/no slot).
	"""
	out: Dict[str, int | None] = {}
	for cal in calendars:
		rotmap = build_rotation_map(cal)  # {day:int -> [date,...]} (cached for a day)
		# invert once for today's lookup
		date_to_rot: Dict[str, int] = {}
		for rd, dates in rotmap.items():
			for d in dates:
				date_to_rot[d.isoformat()] = rd
		out[cal] = date_to_rot.get(today_iso)
	return out

def prewarm_meeting_dates(limit: int | None = None) -> dict:
	"""
	Pre-warm cache entries for Student Groups that actually meet today.
	Run this shortly before the attendance window.
	"""
	today_iso = nowdate()
	ay = current_academic_year()

	groups = _groups_with_schedule_in_ay(ay)
	if not groups:
		return {"warmed": 0, "candidates": 0}

	# compute today's rotation per calendar (reused across many SGs)
	cal_set = {g["school_calendar"] for g in groups}
	today_rot_by_cal = _today_rotation_for_calendars(cal_set, today_iso)

	# only groups whose calendar has a rotation today
	names = [g["name"] for g in groups if today_rot_by_cal.get(g["school_calendar"])]
	if not names:
		return {"warmed": 0, "candidates": 0}

	# keep groups that actually have a row on that rotation day
	rd_by_group = _rotation_days_by_group(names)
	candidates = [
		g["name"] for g in groups
		if (r := today_rot_by_cal.get(g["school_calendar"])) and r in rd_by_group.get(g["name"], set())
	]

	warmed = 0
	target_limit = int(limit or LIMIT_DEFAULT)
	for sg_name in candidates:
		try:
			# warm EXACTLY the same key the UI uses (include limit)
			get_meeting_dates(sg_name, limit=target_limit)
			warmed += 1
		except Exception:
			# best-effort; don't fail the job
			pass

	return {"warmed": warmed, "candidates": len(candidates)}


def _seconds_until(hour: int, minute: int = 0) -> int:
	# compute seconds until HH:MM using frappe utils
	now = now_datetime()
	end = get_datetime(f"{now.date().isoformat()} {hour:02d}:{minute:02d}:00")
	if end <= now:
		end = add_to_date(end, days=1, as_datetime=True)
	return int(time_diff_in_seconds(end, now))

def _already_warmed_today() -> bool:
	site = getattr(frappe.local, "site", "default")
	key = f"{site}::att_prewarm_done::{nowdate()}"
	return bool(frappe.cache().get_value(key))

def _mark_warmed_until(hour: int, minute: int = 0) -> None:
	site = getattr(frappe.local, "site", "default")
	key = f"{site}::att_prewarm_done::{nowdate()}"
	frappe.cache().set_value(key, "1", expires_in_sec=_seconds_until(hour, minute))

def prewarm_meeting_dates_hourly_guard():
	"""
	Run only once per day between 07:00–09:00 (server time).
	"""
	now = now_datetime().time()
	if not (7 <= now.hour < 9):
		return {"skipped": "outside window"}

	if _already_warmed_today():
		return {"skipped": "already warmed today"}

	# set flag first; warm is idempotent anyway
	_mark_warmed_until(9, 0)
	from ifitwala_ed.schedule.attendance_jobs import prewarm_meeting_dates, LIMIT_DEFAULT
	return prewarm_meeting_dates(LIMIT_DEFAULT)
