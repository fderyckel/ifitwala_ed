# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/location_conflicts.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, List, Optional, Tuple

import frappe
from frappe.utils import get_datetime

from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots

# ──────────────────────────────────────────────────────────────────────────────
# Data structure
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LocationSlot:
	"""A concrete occupied slot for a physical location."""
	location: str
	start: datetime
	end: datetime
	source_doctype: str
	source_name: str
	extra: dict | None = None   # e.g. {"rotation_day": 3, "block_number": 2}


# ──────────────────────────────────────────────────────────────────────────────
# Location tree helpers (Nested Set)
# ──────────────────────────────────────────────────────────────────────────────

def _get_location_lftrgt(name: str) -> Tuple[Optional[int], Optional[int]]:
	if not name:
		return (None, None)
	return (
		frappe.db.get_value("Location", name, ["lft", "rgt"], as_dict=False)
		or (None, None)
	)

def _ancestors_inclusive(name: str) -> set[str]:
	"""Return {location} ∪ all its ancestors."""
	lft, rgt = _get_location_lftrgt(name)
	if lft is None:
		return set()
	rows = frappe.db.sql(
		"""
		SELECT name
		FROM `tabLocation`
		WHERE lft <= %s AND rgt >= %s
		""",
		(lft, rgt),
		as_dict=True,
	)
	return {r["name"] for r in rows}

def _descendants_inclusive(name: str) -> set[str]:
	"""Return {location} ∪ all its descendants."""
	lft, rgt = _get_location_lftrgt(name)
	if lft is None:
		return set()
	rows = frappe.db.sql(
		"""
		SELECT name
		FROM `tabLocation`
		WHERE lft >= %s AND rgt <= %s
		""",
		(lft, rgt),
		as_dict=True,
	)
	return {r["name"] for r in rows}

def expand_location_branch(location: str) -> set[str]:
	"""
	For conflict purposes, a booking of <location> means:

	• The location itself is busy
	• All its descendants are busy
	• All its ancestors are busy

	So if "Floor 2" is booked → all rooms under Floor 2 are blocked,
	and if "Room 201" is booked → "Room 201" and "Floor 2" are blocked.
	"""
	if not location:
		return set()
	anc = _ancestors_inclusive(location)
	desc = _descendants_inclusive(location)
	if not anc and not desc:
		return {location}
	return anc.union(desc)


# ──────────────────────────────────────────────────────────────────────────────
# Student Group → LocationSlot adapter
# ──────────────────────────────────────────────────────────────────────────────

def _sgs_touching_branch(branch: set[str]) -> List[str]:
	"""Return Student Groups that have at least one schedule row in the branch."""
	if not branch:
		return []
	return frappe.db.get_all(
		"Student Group Schedule",
		filters={"location": ["in", list(branch)]},
		fields=["parent"],
		distinct=True,
		pluck="parent",
	)

def _sg_location_slots_for_range(
	branch: set[str],
	start_date: date,
	end_date: date,
	ignore_groups: Optional[set[str]] = None,
) -> Iterable[LocationSlot]:
	"""
	Expand Student Group schedules into concrete LocationSlot objects
	for the given date range, restricted to locations in <branch>.
	"""
	if not branch:
		return

	ignore_groups = ignore_groups or set()
	sg_names = _sgs_touching_branch(branch)

	for sg_name in sg_names:
		if sg_name in ignore_groups:
			continue

		# Reuse existing logic from schedule_utils
		for slot in iter_student_group_room_slots(sg_name, start_date, end_date):
			loc = slot.get("location")
			if not loc or loc not in branch:
				continue

			start = slot.get("start")
			end   = slot.get("end")
			if not (start and end):
				continue

			yield LocationSlot(
				location=loc,
				start=start,
				end=end,
				source_doctype="Student Group",
				source_name=sg_name,
				extra={
					"rotation_day": slot.get("rotation_day"),
					"block_number": slot.get("block_number"),
				},
			)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def _normalize_dt(value) -> datetime:
	"""
	Accepts datetime or string and converts to a system-timezone datetime.
	We assume all comparisons happen in the site timezone (System Settings),
	not raw server time.
	"""
	if isinstance(value, datetime):
		return value
	# Allow "YYYY-MM-DD HH:MM" or "YYYY-MM-DD"
	return get_datetime(value)

def _date_span(start: datetime, end: datetime) -> Tuple[date, date]:
	if end < start:
		raise ValueError("end < start in location free/busy check.")
	return (start.date(), end.date())

def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
	"""True if [a_start, a_end) and [b_start, b_end) overlap."""
	return not (a_end <= b_start or b_end <= a_start)


def find_location_conflicts(
	location: str,
	start,
	end,
	*,
	ignore_sources: Optional[List[Tuple[str, str]]] = None,
) -> List[LocationSlot]:
	"""
	Return all conflicting slots for <location> in [start, end).

	For now this only looks at:
		• Student Group timetables

	Later we will add:
		• Meetings
		• School Events
		• Room Booking / Parent-Teacher slots

	ignore_sources: list of (doctype, name) pairs to ignore. Useful when
	editing an existing Meeting / Student Group so it doesn't conflict with itself.
	"""
	start_dt = _normalize_dt(start)
	end_dt   = _normalize_dt(end)
	start_date, end_date = _date_span(start_dt, end_dt)

	branch = expand_location_branch(location)
	if not branch:
		return []

	ignore_sources = set(ignore_sources or [])

	conflicts: List[LocationSlot] = []

	# 1) Student Groups
	ignore_sg = {name for (dt, name) in ignore_sources if dt == "Student Group"}
	for slot in _sg_location_slots_for_range(branch, start_date, end_date, ignore_sg):
		if _overlaps(start_dt, end_dt, slot.start, slot.end):
			conflicts.append(slot)

	# TODO (next steps): add Meeting / School Event / Room Booking sources here.

	return conflicts


def is_location_free(
	location: str,
	start,
	end,
	*,
	ignore_sources: Optional[List[Tuple[str, str]]] = None,
) -> bool:
	"""
	Convenience wrapper:
		True  → no conflicts
		False → at least one conflict
	"""
	return not find_location_conflicts(location, start, end, ignore_sources=ignore_sources)
