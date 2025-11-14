# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/location_conflicts.py

from __future__ import annotations

import frappe
from dataclasses import dataclass
from datetime import datetime, date
from typing import Iterable, List, Optional, Tuple, Callable

from frappe.utils import get_datetime, getdate

from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots


# ──────────────────────────────────────────────────────────────────────────────
# Normalized structure
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LocationSlot:
	location: str
	start: datetime
	end: datetime
	source_doctype: str
	source_name: str
	extra: dict | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Location expansion (SIMPLIFIED — exact match only)
# ──────────────────────────────────────────────────────────────────────────────

def expand_location_branch(location: str) -> set[str]:
	"""
	Simplified model:
	Only the exact location is considered busy.
	Parent/child relationships are ignored.
	"""
	return {location} if location else set()


# ──────────────────────────────────────────────────────────────────────────────
# Normalization utilities
# ──────────────────────────────────────────────────────────────────────────────

def _normalize_dt(value) -> datetime:
	if isinstance(value, datetime):
		return value
	return get_datetime(value)

def _overlaps(a_start, a_end, b_start, b_end) -> bool:
	return not (a_end <= b_start or b_end <= a_start)

def _date_span(start_dt: datetime, end_dt: datetime) -> Tuple[date, date]:
	return (start_dt.date(), end_dt.date())


# ──────────────────────────────────────────────────────────────────────────────
# Adapters — each yields LocationSlot entries
# ──────────────────────────────────────────────────────────────────────────────

def slots_from_student_groups(
	branch: set[str],
	start_date: date,
	end_date: date,
	ignore: set[str],
) -> Iterable[LocationSlot]:
	"""
	Yield slots for Student Groups that use any location in `branch`
	between start_date and end_date (inclusive).
	"""
	sg_names = frappe.db.get_all(
		"Student Group Schedule",
		filters={"location": ["in", list(branch)]},
		pluck="parent",
		distinct=True,
	)

	for sg in sg_names:
		if sg in ignore:
			continue

		for s in iter_student_group_room_slots(sg, start_date, end_date):
			loc = s.get("location")
			if not loc or loc not in branch:
				continue

			yield LocationSlot(
				location=loc,
				start=s["start"],
				end=s["end"],
				source_doctype="Student Group",
				source_name=sg,
				extra={
					"rotation_day": s.get("rotation_day"),
					"block_number": s.get("block_number"),
				},
			)


def slots_from_meeting(docname: str) -> Iterable[LocationSlot]:
	doc = frappe.get_cached_doc("Meeting", docname)
	if not doc.location:
		return []

	if not (doc.date and doc.start_time and doc.end_time):
		return []

	start_dt = get_datetime(f"{doc.date} {doc.start_time}")
	end_dt = get_datetime(f"{doc.date} {doc.end_time}")

	if not start_dt or not end_dt:
		return []

	return [
		LocationSlot(
			location=doc.location,
			start=start_dt,
			end=end_dt,
			source_doctype="Meeting",
			source_name=docname,
		)
	]


def slots_from_school_event(docname: str) -> Iterable[LocationSlot]:
	doc = frappe.get_cached_doc("School Event", docname)
	if not doc.location or not doc.starts_on or not doc.ends_on:
		return []

	return [
		LocationSlot(
			location=doc.location,
			start=get_datetime(doc.starts_on),
			end=get_datetime(doc.ends_on),
			source_doctype="School Event",
			source_name=docname,
		)
	]


# Registry of sources (kept for future extension if needed)
SOURCE_ADAPTERS: dict[str, Callable] = {
	"Student Group": slots_from_student_groups,  # special signature
	"Meeting": slots_from_meeting,
	"School Event": slots_from_school_event,
}


# ──────────────────────────────────────────────────────────────────────────────
# Main conflict engine
# ──────────────────────────────────────────────────────────────────────────────

def find_location_conflicts(
	location: str,
	start,
	end,
	*,
	ignore_sources: Optional[Iterable[Tuple[str, str]]] = None,
) -> List[LocationSlot]:
	start_dt = _normalize_dt(start)
	end_dt = _normalize_dt(end)

	if end_dt <= start_dt:
		return []

	branch = expand_location_branch(location)  # now exact match only
	if not branch:
		return []

	ignore_sources = set(ignore_sources or [])
	conflicts: List[LocationSlot] = []

	start_date, end_date = _date_span(start_dt, end_dt)

	# 1) Student Groups
	ignore_sg = {name for (dt, name) in ignore_sources if dt == "Student Group"}
	for slot in slots_from_student_groups(branch, start_date, end_date, ignore_sg):
		if _overlaps(start_dt, end_dt, slot.start, slot.end):
			conflicts.append(slot)

	# 2) Meetings
	if "Meeting" not in {dt for (dt, _) in ignore_sources}:
		meetings = frappe.db.get_all(
			"Meeting",
			filters={"location": ["in", list(branch)]},
			pluck="name",
		)
		for m in meetings:
			if ("Meeting", m) in ignore_sources:
				continue
			for s in slots_from_meeting(m):
				if _overlaps(start_dt, end_dt, s.start, s.end):
					conflicts.append(s)

	# 3) School Events
	events = frappe.db.get_all(
		"School Event",
		filters={"location": ["in", list(branch)]},
		pluck="name",
	)
	for e in events:
		if ("School Event", e) in ignore_sources:
			continue
		for s in slots_from_school_event(e):
			if _overlaps(start_dt, end_dt, s.start, s.end):
				conflicts.append(s)

	return conflicts


def is_location_free(location: str, start, end, *, ignore_sources=None) -> bool:
	return not find_location_conflicts(location, start, end, ignore_sources=ignore_sources)
