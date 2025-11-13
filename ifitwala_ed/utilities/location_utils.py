# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/location_utils.py

import frappe
from frappe.utils import get_datetime
from typing import List, Dict, Any, Optional


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


# ─────────────────────────────────────────────────────────────
# Central conflict service (datetime-based bookings only)
# ─────────────────────────────────────────────────────────────

# Assumption / contract:
# Any doctype listed here:
#   • has a field "location" (Link to Location)
#   • has datetime fields named as below (from_field, to_field)
#   • uses docstatus < 2 for “active” / not-cancelled
#
# You can change the doctype names to your actual ones if needed.
LOCATION_SOURCES: List[Dict[str, str]] = [
	# Future Room Booking doc
	{
		"doctype": "Room Booking",
		"from_field": "from_datetime",
		"to_field": "to_datetime",
	},

	# Your meeting doc – adjust doctype/fieldnames if different
	{
		"doctype": "Meeting",
		"from_field": "from_datetime",
		"to_field": "to_datetime",
	},

	# School Events – again, adjust to your schema
	{
		"doctype": "School Event",
		"from_field": "from_datetime",
		"to_field": "to_datetime",
	},
]


def find_location_conflicts(
	location: str,
	from_dt,
	to_dt,
	*,
	include_children: bool = True,
	exclude: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
	"""
	Central checker: return ALL datetime-based conflicts for a location.

	Args:
		location: base Location name
		from_dt / to_dt: datetime or string; [from_dt, to_dt) interval
		include_children: if True, booking this location also blocks all descendants
		exclude: {"doctype": "...", "name": "..."} to ignore the current doc
		         when checking (e.g., editing an existing Meeting)

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

	if not location or from_dt >= to_dt:
		return []

	locations = get_location_scope(location, include_children=include_children)
	if not locations:
		return []

	conflicts: List[Dict[str, Any]] = []

	for src in LOCATION_SOURCES:
		conflicts.extend(
			_conflicts_from_source(
				doctype=src["doctype"],
				from_field=src["from_field"],
				to_field=src["to_field"],
				locations=locations,
				from_dt=from_dt,
				to_dt=to_dt,
				exclude=exclude,
			)
		)

	return conflicts


def _conflicts_from_source(
	*,
	doctype: str,
	from_field: str,
	to_field: str,
	locations: List[str],
	from_dt,
	to_dt,
	exclude: Optional[Dict[str, str]] = None,
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
		"docstatus": ["<", 2],
		from_field: ["<", to_dt],
		to_field: [">", from_dt],
	}

	rows = frappe.db.get_all(
		doctype,
		filters=filters,
		fields=["name", "location", from_field, to_field],
	)

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
