# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/location_utils.py

"""
Location utilities.

This module defines the CANONICAL rules for location hierarchy handling.

If a location is considered booked:
- its children are considered booked ONLY if explicitly requested
- hierarchy expansion must always go through this module
"""

import frappe
from frappe.utils import get_datetime
from frappe.utils.caching import redis_cache
from typing import List, Dict, Any, Optional, Iterable


# ─────────────────────────────────────────────────────────────
# Core time & tree helpers
# ─────────────────────────────────────────────────────────────

def _overlaps(a_start, a_end, b_start, b_end) -> bool:
	"""
	Return True if [a_start, a_end) overlaps [b_start, b_end).

	We always treat intervals as half-open: [start, end)
	→ end == start is NOT a conflict.
	"""
	a_start = get_datetime(a_start)
	a_end = get_datetime(a_end)
	b_start = get_datetime(b_start)
	b_end = get_datetime(b_end)

	if a_start >= a_end or b_start >= b_end:
		# degenerate window(s) → no overlap
		return False

	return (a_start < b_end) and (b_start < a_end)


def _get_descendant_locations(location: str) -> List[str]:
	"""
	Return ALL descendant locations for a given Location, excluding the node itself.

	Assumes Location is a NestedSet DocType with lft/rgt.
	"""
	if not location:
		return []

	loc_doc = frappe.get_doc("Location", location)

	# children are strictly inside (lft, rgt)
	children = frappe.db.get_all(
		"Location",
		filters={
			"lft": [">", loc_doc.lft],
			"rgt": ["<", loc_doc.rgt],
		},
		pluck="name",
	)

	return children or []


# Canonical location hierarchy rule:
# - Parent booking blocks children
# - Child booking does NOT block parent
def get_location_scope(location: str, include_children: bool = True) -> List[str]:
	"""
	Return the list of locations that should be considered "blocked" when a given
	location is booked.

	Rules (per your decision):
	- If a parent location is booked, ALL its children are booked too.
	- If include_children=False, only that specific location is blocked.

	Examples:
	- get_location_scope("Library", True) → ["Library", <all rooms under Library>]
	- get_location_scope("Room 101", True) → ["Room 101", ...children if it has any]
	- get_location_scope("Room 101", False) → ["Room 101"]
	"""
	if not location:
		return []

	scope = [location]

	if include_children:
		scope.extend(_get_descendant_locations(location))

	# remove duplicates, keep order
	seen = set()
	out: List[str] = []
	for loc in scope:
		if loc and loc not in seen:
			seen.add(loc)
			out.append(loc)

	return out


def _get_location_flags(location: str) -> Optional[Dict[str, Any]]:
	if not location:
		return None

	fields = ["is_group"]
	if frappe.db.has_column("Location", "disabled"):
		fields.append("disabled")

	return frappe.db.get_value("Location", location, fields, as_dict=True)


@redis_cache(ttl=300)
def _is_bookable_room_cached(location: str) -> bool:
	if not location:
		return False

	row = _get_location_flags(location)
	if not row:
		return False

	try:
		if int(row.get("is_group") or 0) != 0:
			return False
	except Exception:
		return False

	if "disabled" in row:
		try:
			if int(row.get("disabled") or 0) != 0:
				return False
		except Exception:
			return False

	return True


def is_bookable_room(location: str) -> bool:
	"""
	Return True if this Location is intended to host people.

	v1 rule:
	- is_group = 0
	- disabled = 0 (if field exists)

	This helper is NOT yet enforced everywhere.
	"""
	return _is_bookable_room_cached(location)


# ─────────────────────────────────────────────────────────────
# Central conflict service (datetime-based bookings only)
# ─────────────────────────────────────────────────────────────

# Assumption / contract:
# Any doctype listed here:
#   • has a field "location" (Link to Location)
#   • has datetime fields named as below (from_field, to_field)
#   • uses docstatus < 2 for “active” / not-cancelled (when column exists)
LOCATION_SOURCES: List[Dict[str, Any]] = [
	{
		"doctype": "Employee Booking",
		"from_field": "from_datetime",
		"to_field": "to_datetime",
	},
	{
		"doctype": "Meeting",
		"from_field": "from_datetime",
		"to_field": "to_datetime",
		"status_field": "status",
		"status_exclude": ["Cancelled"],
	},
	{
		"doctype": "School Event",
		"from_field": "starts_on",
		"to_field": "ends_on",
	},
]


def find_room_conflicts(
	location: Optional[str],
	from_dt,
	to_dt,
	*,
	include_children: bool = True,
	exclude: Optional[Dict[str, str]] = None,
	locations: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
	"""
	Canonical checker: return ALL datetime-based conflicts for a room or room list.

	Args:
		location: base Location name (optional if locations provided)
		from_dt / to_dt: datetime or string; [from_dt, to_dt) interval
		include_children: if True, booking this location also blocks all descendants
		exclude: {"doctype": "...", "name": "..."} to ignore the current doc
		         when checking (e.g., editing an existing Meeting)
		locations: optional iterable of explicit Location names (already scoped)

	Returns:
		List of dicts:
		{
			"source_doctype": "Meeting",
			"source_name": "MEET-0001",
			"location": "Room 101",
			"from": <datetime>,
			"to": <datetime>,
		}
	"""
	from_dt = get_datetime(from_dt)
	to_dt = get_datetime(to_dt)

	if from_dt >= to_dt:
		return []

	if locations is None:
		if not location:
			return []
		locations = get_location_scope(location, include_children=include_children)
	else:
		locations = list(locations)

	if not locations:
		return []

	# Only real rooms participate in availability.
	scoped_locations = [loc for loc in locations if is_bookable_room(loc)]
	if not scoped_locations:
		return []

	conflicts: List[Dict[str, Any]] = []

	for src in LOCATION_SOURCES:
		conflicts.extend(
			_conflicts_from_source(
				doctype=src["doctype"],
				from_field=src["from_field"],
				to_field=src["to_field"],
				locations=scoped_locations,
				from_dt=from_dt,
				to_dt=to_dt,
				exclude=exclude,
				status_field=src.get("status_field"),
				status_exclude=src.get("status_exclude"),
			)
		)

	# Deduplicate across sources (e.g., Meeting + its Employee Booking)
	seen = set()
	out: List[Dict[str, Any]] = []
	for row in conflicts:
		key = (
			row.get("source_doctype"),
			row.get("source_name"),
			row.get("location"),
			row.get("from"),
			row.get("to"),
		)
		if key in seen:
			continue
		seen.add(key)
		out.append(row)

	return out


def _conflicts_from_source(
	*,
	doctype: str,
	from_field: str,
	to_field: str,
	locations: List[str],
	from_dt,
	to_dt,
	exclude: Optional[Dict[str, str]] = None,
	status_field: Optional[str] = None,
	status_exclude: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
	"""
	Generic conflict finder for a single doctype that has:
	  • location (Link)
	  • from_field / to_field (Datetime)

	Uses a coarse SQL filter then a precise _overlaps() check.
	"""
	if not frappe.db.table_exists(doctype):
		# Allow progressive rollout; no hard failure if doc is not present yet.
		return []

	# Coarse filter in SQL (interval overlap)
	filters = {
		"location": ["in", locations],
		from_field: ["<", to_dt],
		to_field: [">", from_dt],
	}
	if frappe.db.has_column(doctype, "docstatus"):
		filters["docstatus"] = ["<", 2]
	if status_field and status_exclude and frappe.db.has_column(doctype, status_field):
		if len(status_exclude) == 1:
			filters[status_field] = ["!=", status_exclude[0]]
		else:
			filters[status_field] = ["not in", list(status_exclude)]

	fields = ["name", "location", from_field, to_field]
	if doctype == "Employee Booking":
		fields.extend(["source_doctype", "source_name"])

	rows = frappe.db.get_all(doctype, filters=filters, fields=fields)

	out: List[Dict[str, Any]] = []

	for r in rows:
		if exclude and exclude.get("doctype") == doctype and exclude.get("name") == r.name:
			continue

		start = r.get(from_field)
		end = r.get(to_field)

		if not start or not end:
			continue

		if not _overlaps(from_dt, to_dt, start, end):
			continue

		if doctype == "Employee Booking":
			source_doctype = r.get("source_doctype") or doctype
			source_name = r.get("source_name") or r.name
			if exclude:
				if (
					exclude.get("source_doctype") == source_doctype
					and exclude.get("source_name") == source_name
				):
					continue
				if exclude.get("doctype") == source_doctype and exclude.get("name") == source_name:
					continue
			out.append(
				{
					"source_doctype": source_doctype,
					"source_name": source_name,
					"location": r.location,
					"from": start,
					"to": end,
					"extra": {"booking_name": r.name},
				}
			)
		else:
			out.append(
				{
					"source_doctype": doctype,
					"source_name": r.name,
					"location": r.location,
					"from": start,
					"to": end,
				}
			)

	return out


# Backwards-compatible alias; prefer find_room_conflicts.
def find_location_conflicts(
	location: Optional[str],
	from_dt,
	to_dt,
	*,
	include_children: bool = True,
	exclude: Optional[Dict[str, str]] = None,
	locations: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
	return find_room_conflicts(
		location,
		from_dt,
		to_dt,
		include_children=include_children,
		exclude=exclude,
		locations=locations,
	)
