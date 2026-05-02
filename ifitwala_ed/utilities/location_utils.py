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

from typing import Any, Dict, Iterable, List, Optional

import frappe
from frappe import _
from frappe.utils import cint, get_datetime
from frappe.utils.caching import redis_cache

from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools
from ifitwala_ed.utilities.tree_utils import get_descendants_inclusive

# ─────────────────────────────────────────────────────────────
# Core time & tree helpers
# ─────────────────────────────────────────────────────────────

LOCATION_SCOPE_CACHE_TTL = 60 * 60 * 12  # 12 hours
VISIBLE_LOCATION_SCOPE_CACHE_TTL = 60 * 5  # 5 minutes
SCHEDULABLE_LOCATION_CACHE_TTL = 60 * 5  # 5 minutes
VISIBLE_LOCATION_MAX_ROWS = 2000


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

    descendants = get_descendants_inclusive("Location", location, cache_ttl=LOCATION_SCOPE_CACHE_TTL) or [location]
    return [name for name in descendants if name != location]


def _get_location_scope_cached(location: str, include_children: bool) -> List[str]:
    """
    Cache-safe location scope expansion (root + descendants if requested).
    """
    if not location:
        return []

    cache_key = f"location_scope::{location}::include_children={1 if include_children else 0}"
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached is not None:
        return cached

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

    cache.set_value(cache_key, out, expires_in_sec=LOCATION_SCOPE_CACHE_TTL)
    return out


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

    return _get_location_scope_cached(location, include_children)


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


def _get_location_type_flag_map(location_types: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    names = sorted({name for name in (location_types or []) if name})
    if not names:
        return {}

    rows = frappe.get_all(
        "Location Type",
        filters={"name": ["in", names]},
        fields=["name", "location_type_name", "is_schedulable", "is_container"],
        limit=max(len(names), 1),
    )
    return {row.get("name"): row for row in rows if row.get("name")}


def _row_is_schedulable_space(row: Dict[str, Any], type_map: Dict[str, Dict[str, Any]]) -> bool:
    if not row:
        return False

    try:
        if cint(row.get("is_group") or 0):
            return False
    except Exception:
        return False

    location_type = row.get("location_type")
    type_row = type_map.get(location_type) if location_type else None
    if type_row:
        return cint(type_row.get("is_schedulable") or 0) == 1

    # Legacy fallback:
    # - explicit capacity 0 means "do not surface as a room" in rooming workflows
    # - blank capacity keeps pre-existing untyped rooms visible until data is cleaned up
    capacity = row.get("maximum_capacity")
    if capacity in (None, ""):
        return True

    try:
        return int(capacity) > 0
    except Exception:
        return False


@redis_cache(ttl=SCHEDULABLE_LOCATION_CACHE_TTL)
def is_schedulable_location(location: str) -> bool:
    if not location:
        return False

    fields = ["name", "is_group", "location_type", "maximum_capacity"]
    if frappe.db.has_column("Location", "disabled"):
        fields.append("disabled")

    row = frappe.db.get_value("Location", location, fields, as_dict=True)
    if not row:
        return False

    if "disabled" in row:
        try:
            if cint(row.get("disabled") or 0):
                return False
        except Exception:
            return False

    type_map = _get_location_type_flag_map([row.get("location_type")])
    return _row_is_schedulable_space(row, type_map)


def _dedupe_keep_order(names: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for name in names or []:
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


@redis_cache(ttl=VISIBLE_LOCATION_SCOPE_CACHE_TTL)
def get_visible_location_names_for_school(selected_school: str) -> List[str]:
    """
    Canonical location-visibility scope for school-scoped rooming surfaces.

    Visibility includes:
    - Locations whose own School is the selected school or any of its descendants
    - Descendants of group/container Locations in that same direct school scope
    - Descendants of ancestor-school Locations explicitly shared downward

    This preserves sibling isolation while allowing parent-school shared facilities
    such as a central auditorium or event hall.
    """
    if not selected_school:
        return []

    school_scope = get_descendant_schools(selected_school) or [selected_school]
    direct_rows = frappe.get_all(
        "Location",
        filters={"school": ["in", school_scope]},
        fields=["name", "is_group"],
        order_by="lft asc",
        limit=VISIBLE_LOCATION_MAX_ROWS,
    )

    names: List[str] = []
    for row in direct_rows:
        location_name = row.get("name")
        if not location_name:
            continue
        names.append(location_name)
        if cint(row.get("is_group") or 0):
            names.extend(get_location_scope(location_name, include_children=True))

    if frappe.db.has_column("Location", "shared_with_descendant_schools"):
        ancestor_scope = get_ancestor_schools(selected_school) or [selected_school]
        shared_rows = frappe.get_all(
            "Location",
            filters={
                "school": ["in", ancestor_scope],
                "shared_with_descendant_schools": 1,
            },
            fields=["name"],
            order_by="lft asc",
            limit=500,
        )
        for row in shared_rows:
            location_name = row.get("name")
            if not location_name:
                continue
            names.extend(get_location_scope(location_name, include_children=True))

    return _dedupe_keep_order(names)


def get_visible_location_rows_for_school(
    selected_school: str,
    *,
    include_groups: bool = False,
    only_schedulable: bool = False,
    within_location: Optional[str] = None,
    location_types: Optional[Iterable[str]] = None,
    capacity_needed: Optional[int] = None,
    fields: Optional[Iterable[str]] = None,
    limit: int = 500,
    order_by: str = "location_name asc",
) -> List[Dict[str, Any]]:
    """
    Return visible Location rows for a selected school using the canonical
    school-scope + ancestor-shared-location contract.

    This helper is the single source for:
    - room utilization candidates
    - room suggestion candidates
    - quick-create location options
    - location calendar selectors
    """
    if not selected_school:
        return []

    visible_names = get_visible_location_names_for_school(selected_school)
    if within_location:
        allowed_within = set(get_location_scope(within_location, include_children=True))
        visible_names = [name for name in visible_names if name in allowed_within]

    if not visible_names:
        return []

    requested_fields = list(
        fields
        or [
            "name",
            "location_name",
            "school",
            "parent_location",
            "location_type",
            "is_group",
            "maximum_capacity",
        ]
    )
    if (
        frappe.db.has_column("Location", "shared_with_descendant_schools")
        and "shared_with_descendant_schools" not in requested_fields
    ):
        requested_fields.append("shared_with_descendant_schools")

    row_limit = max(min(int(limit or 500), VISIBLE_LOCATION_MAX_ROWS), 1)
    rows = frappe.get_all(
        "Location",
        filters={"name": ["in", visible_names]},
        fields=requested_fields,
        order_by=order_by,
        limit=row_limit,
    )
    if not rows:
        return []

    location_type_map = _get_location_type_flag_map(row.get("location_type") for row in rows)
    type_filter = {name for name in (location_types or []) if name}

    out: List[Dict[str, Any]] = []
    for row in rows:
        if not include_groups and cint(row.get("is_group") or 0):
            continue

        if type_filter and row.get("location_type") not in type_filter:
            continue

        if only_schedulable and not _row_is_schedulable_space(row, location_type_map):
            continue

        if capacity_needed and capacity_needed > 0:
            try:
                if int(row.get("maximum_capacity") or 0) < int(capacity_needed):
                    continue
            except Exception:
                continue

        location_type = row.get("location_type")
        if location_type:
            row["location_type_name"] = (location_type_map.get(location_type) or {}).get(
                "location_type_name"
            ) or location_type
        else:
            row["location_type_name"] = None

        out.append(row)

    return out


# ─────────────────────────────────────────────────────────────
# Central conflict service (datetime-based bookings only)
# ─────────────────────────────────────────────────────────────


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
    conflicts.extend(
        _conflicts_from_location_booking(
            locations=scoped_locations,
            from_dt=from_dt,
            to_dt=to_dt,
            exclude=exclude,
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


def _conflicts_from_location_booking(
    *,
    locations: List[str],
    from_dt,
    to_dt,
    exclude: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Conflict finder for Location Booking (single source of truth).
    """
    if not frappe.db.table_exists("Location Booking"):
        return []

    filters = {
        "location": ["in", locations],
        "from_datetime": ["<", to_dt],
        "to_datetime": [">", from_dt],
    }
    if frappe.db.has_column("Location Booking", "docstatus"):
        filters["docstatus"] = ["<", 2]

    fields = [
        "name",
        "location",
        "from_datetime",
        "to_datetime",
        "source_doctype",
        "source_name",
        "occupancy_type",
        "slot_key",
    ]

    rows = frappe.db.get_all("Location Booking", filters=filters, fields=fields)

    out: List[Dict[str, Any]] = []
    for r in rows:
        start = r.get("from_datetime")
        end = r.get("to_datetime")
        if not start or not end:
            continue

        if not _overlaps(from_dt, to_dt, start, end):
            continue

        source_doctype = r.get("source_doctype") or "Location Booking"
        source_name = r.get("source_name") or r.name

        if exclude:
            if exclude.get("doctype") == "Location Booking" and exclude.get("name") == r.name:
                continue
            if exclude.get("source_doctype") == source_doctype and exclude.get("source_name") == source_name:
                continue
            if exclude.get("doctype") == source_doctype and exclude.get("name") == source_name:
                continue

        out.append(
            {
                "source_doctype": source_doctype,
                "source_name": source_name,
                "location": r.get("location"),
                "from": start,
                "to": end,
                "extra": {
                    "location_booking": r.get("name"),
                    "slot_key": r.get("slot_key"),
                    "occupancy_type": r.get("occupancy_type"),
                },
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


@frappe.whitelist()
def verify_room_conflicts_against_location_booking(
    location: str,
    start,
    end,
    include_children: int | bool = 1,
) -> Dict[str, Any]:
    """
    Verify that find_room_conflicts() matches Location Booking rows exactly.
    """
    frappe.only_for("System Manager")

    start_dt = get_datetime(start)
    end_dt = get_datetime(end)
    if not start_dt or not end_dt or end_dt <= start_dt:
        frappe.throw(_("Invalid datetime window for verification."))

    inc_children = bool(int(include_children)) if isinstance(include_children, (int, str)) else bool(include_children)

    conflicts = find_room_conflicts(
        location,
        start_dt,
        end_dt,
        include_children=inc_children,
    )

    conflict_slot_keys = {
        (row.get("extra") or {}).get("slot_key") for row in conflicts if (row.get("extra") or {}).get("slot_key")
    }

    locations = get_location_scope(location, include_children=inc_children)
    scoped_locations = [loc for loc in locations if is_bookable_room(loc)]

    if not scoped_locations:
        if conflict_slot_keys:
            frappe.throw(_("Conflicts returned for non-bookable or empty scope."))
        return {"ok": True, "count": 0, "slot_keys": []}

    if not frappe.db.table_exists("Location Booking"):
        frappe.throw(_("Location Booking table does not exist."))

    filters = {
        "location": ["in", scoped_locations],
        "from_datetime": ["<", end_dt],
        "to_datetime": [">", start_dt],
    }
    if frappe.db.has_column("Location Booking", "docstatus"):
        filters["docstatus"] = ["<", 2]

    rows = frappe.db.get_all("Location Booking", filters=filters, fields=["slot_key"])
    direct_slot_keys = {r.get("slot_key") for r in rows if r.get("slot_key")}

    if conflict_slot_keys != direct_slot_keys:
        missing = sorted(direct_slot_keys - conflict_slot_keys)
        extra = sorted(conflict_slot_keys - direct_slot_keys)
        frappe.throw(f"Conflict helper mismatch: missing={len(missing)} extra={len(extra)}.")

    return {"ok": True, "count": len(conflict_slot_keys), "slot_keys": sorted(conflict_slot_keys)}
