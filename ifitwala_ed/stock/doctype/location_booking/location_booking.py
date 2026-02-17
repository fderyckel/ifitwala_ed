# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class LocationBooking(Document):
    pass


def build_source_key(source_doctype: str, source_name: str) -> str:
    return f"{source_doctype}::{source_name}"


def build_slot_key_single(source_key: str, location: str) -> str:
    """
    Stable key for single-instance domain sources:
    Meeting / School Event / Room Booking

    Edits (time changes) must UPDATE the same row, not create a new identity.
    """
    return f"{source_key}::{location}"


def build_slot_key_instance(source_key: str, location: str, from_dt, to_dt) -> str:
    """
    Stable key for multi-instance materialization (Teaching):
    1 row per instance, identity includes the time window.
    """
    fdt = get_datetime(from_dt).isoformat()
    tdt = get_datetime(to_dt).isoformat()
    return f"{source_key}::{location}::{fdt}::{tdt}"


def upsert_location_booking(
    *,
    location: str,
    from_datetime,
    to_datetime,
    occupancy_type: str,
    source_doctype: str,
    source_name: str,
    slot_key: str,
    school: str | None = None,
    academic_year: str | None = None,
) -> str:
    """
    Idempotent upsert keyed by slot_key.

    - Uses UNIQUE(slot_key) at DB level (patch).
    - Safe under concurrency:
      - Try insert
      - If duplicate, fetch by slot_key and update

    Returns the Location Booking document name.
    """
    if not location:
        frappe.throw("Location Booking: location is required.")
    if not source_doctype or not source_name:
        frappe.throw("Location Booking: source_doctype and source_name are required.")
    if not slot_key:
        frappe.throw("Location Booking: slot_key is required.")

    fdt = get_datetime(from_datetime)
    tdt = get_datetime(to_datetime)
    if not tdt or not fdt or tdt <= fdt:
        frappe.throw("Location Booking: to_datetime must be greater than from_datetime.")

    source_key = build_source_key(source_doctype, source_name)

    update = {
        "location": location,
        "from_datetime": fdt,
        "to_datetime": tdt,
        "occupancy_type": occupancy_type,
        "source_doctype": source_doctype,
        "source_name": source_name,
        "source_key": source_key,
        "slot_key": slot_key,
        "school": school,
        "academic_year": academic_year,
    }

    existing = frappe.db.get_value(
        "Location Booking",
        {"slot_key": slot_key},
        "name",
    )
    if existing:
        frappe.db.set_value(
            "Location Booking",
            existing,
            update,
            update_modified=True,
        )
        return existing

    # First attempt: insert
    doc = frappe.new_doc("Location Booking")
    doc.location = location
    doc.from_datetime = fdt
    doc.to_datetime = tdt
    doc.occupancy_type = occupancy_type
    doc.source_doctype = source_doctype
    doc.source_name = source_name
    doc.source_key = source_key
    doc.slot_key = slot_key
    doc.school = school
    doc.academic_year = academic_year

    try:
        doc.insert(ignore_permissions=True)
        return doc.name
    except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
        # Another worker inserted the same slot_key.
        existing = frappe.db.get_value(
            "Location Booking",
            {"slot_key": slot_key},
            "name",
        )
        if not existing:
            # Extremely unlikely: duplicate error but no row found.
            # Re-raise to avoid silent corruption.
            raise

        # Update the existing row.
        frappe.db.set_value(
            "Location Booking",
            existing,
            update,
            update_modified=True,
        )
        return existing


def delete_location_bookings_for_source(*, source_doctype: str, source_name: str) -> int:
    """
    Delete ALL Location Booking rows derived from a given domain source.

    Used on cancel/trash, and also for migration cleanups.
    Returns the number of rows deleted.
    """
    if not source_doctype or not source_name:
        return 0

    # Count first (for deterministic return).
    cnt = frappe.db.count(
        "Location Booking",
        {"source_doctype": source_doctype, "source_name": source_name},
    )
    if not cnt:
        return 0

    frappe.db.delete(
        "Location Booking",
        {"source_doctype": source_doctype, "source_name": source_name},
    )

    return int(cnt or 0)


def delete_location_bookings_for_source_in_window(
    *,
    source_doctype: str,
    source_name: str,
    start_dt,
    end_dt,
    keep_slot_keys: set[str] | None = None,
) -> int:
    """
    Delete Location Booking rows for a source within a bounded window.

    If keep_slot_keys is provided, delete only rows whose slot_key is NOT in that set.
    Returns the number of rows deleted.
    """
    if not source_doctype or not source_name:
        return 0

    fdt = get_datetime(start_dt)
    tdt = get_datetime(end_dt)
    if not fdt or not tdt or tdt <= fdt:
        return 0

    rows = frappe.db.get_all(
        "Location Booking",
        filters={
            "source_doctype": source_doctype,
            "source_name": source_name,
            "from_datetime": [">=", fdt],
            "to_datetime": ["<=", tdt],
        },
        fields=["name", "slot_key"],
    )

    if not rows:
        return 0

    to_delete = []
    keep_slot_keys = set(keep_slot_keys or [])
    for r in rows:
        if keep_slot_keys and r.get("slot_key") in keep_slot_keys:
            continue
        to_delete.append(r["name"])

    if not to_delete:
        return 0

    deleted = 0
    chunk = 200
    for i in range(0, len(to_delete), chunk):
        names = to_delete[i : i + chunk]
        frappe.db.sql(
            "delete from `tabLocation Booking` where name in %(names)s",
            {"names": tuple(names)},
        )
        deleted += len(names)

    return deleted
