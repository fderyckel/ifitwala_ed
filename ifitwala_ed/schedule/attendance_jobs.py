# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/attendance_jobs.py

import frappe
from frappe.utils import now_datetime, nowdate, get_datetime, add_to_date, time_diff_in_seconds
from typing import Dict, Set, List
from ifitwala_ed.schedule.schedule_utils import current_academic_year, get_rotation_dates
from ifitwala_ed.schedule.attendance_utils import get_meeting_dates, LIMIT_DEFAULT, SG_SCHEDULE_DT



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

def _groups_with_schedule_in_ay(ay: str) -> List[dict]:
	return frappe.db.sql(
		"""
		SELECT sg.name, sg.school_schedule, sg.academic_year
		FROM `tabStudent Group` sg
		WHERE sg.academic_year = %(ay)s
		  AND sg.school_schedule IS NOT NULL
		  AND EXISTS (
				SELECT 1 FROM `tabStudent Group Schedule` sgs WHERE sgs.parent = sg.name
		  )
		""",
		{"ay": ay},
		as_dict=True,
	)

def _today_rotation_by_sched_ay(groups: List[dict], today_iso: str) -> Dict[tuple, int | None]:
	"""
	Map each (school_schedule, academic_year) → today's rotation_day (or None).
	Uses get_rotation_dates() so schedule-specific offsets are honored.
	"""
	pairs = {(g["school_schedule"], g["academic_year"]) for g in groups}
	out: Dict[tuple, int | None] = {}
	for sched, ay in pairs:
		rot_dates = get_rotation_dates(sched, ay, include_holidays=False)
		rot_map = {rd["date"].isoformat(): int(rd["rotation_day"]) for rd in rot_dates}
		out[(sched, ay)] = rot_map.get(today_iso)
	return out

def prewarm_meeting_dates(limit: int | None = None) -> dict:
	today_iso = nowdate()
	ay = current_academic_year()

	groups = _groups_with_schedule_in_ay(ay)
	if not groups:
		return {"warmed": 0, "candidates": 0}

	# schedule-aware rotation for today
	rot_by_pair = _today_rotation_by_sched_ay(groups, today_iso)

	# only groups whose schedule has a rotation today
	names = [
		g["name"]
		for g in groups
		if rot_by_pair.get((g["school_schedule"], g["academic_year"]))
	]
	if not names:
		return {"warmed": 0, "candidates": 0}

	rd_by_group = _rotation_days_by_group(names)
	candidates = [
		g["name"] for g in groups
		if (r := rot_by_pair.get((g["school_schedule"], g["academic_year"])))
		and r in rd_by_group.get(g["name"], set())
	]

	warmed = 0
	target_limit = int(limit or LIMIT_DEFAULT)
	for sg_name in candidates:
		try:
			get_meeting_dates(sg_name, limit=target_limit)  # warms exact key
			warmed += 1
		except Exception:
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

	_mark_warmed_until(9, 0)  # set flag first
	return prewarm_meeting_dates(LIMIT_DEFAULT)

