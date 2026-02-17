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
from frappe.utils import get_datetime
from frappe.utils.caching import redis_cache

# ─────────────────────────────────────────────────────────────
# Core time & tree helpers
# ─────────────────────────────────────────────────────────────

LOCATION_SCOPE_CACHE_TTL = 60 * 60 * 12  # 12 hours


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
        frappe.throw("Invalid datetime window for verification.")

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
            frappe.throw("Conflicts returned for non-bookable or empty scope.")
        return {"ok": True, "count": 0, "slot_keys": []}

    if not frappe.db.table_exists("Location Booking"):
        frappe.throw("Location Booking table does not exist.")

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
