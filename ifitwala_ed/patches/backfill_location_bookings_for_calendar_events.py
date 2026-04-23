# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Location Booking"):
        return

    for doctype in ("Meeting", "School Event"):
        _backfill_location_bookings_for_doctype(doctype)


def _backfill_location_bookings_for_doctype(doctype: str) -> None:
    if not frappe.db.table_exists(doctype):
        return

    filters = {"location": ["is", "set"]}
    if doctype == "Meeting":
        filters["status"] = ["!=", "Cancelled"]

    doc_names = frappe.get_all(
        doctype,
        filters=filters,
        pluck="name",
        limit=100000,
    )

    for doc_name in doc_names:
        name = str(doc_name or "").strip()
        if not name:
            continue

        try:
            doc = frappe.get_doc(doctype, name)
            sync_location_booking = getattr(doc, "sync_location_booking", None)
            if callable(sync_location_booking):
                sync_location_booking()
        except Exception:
            frappe.log_error(
                frappe.as_json(
                    {
                        "error": "calendar_event_location_booking_backfill_failed",
                        "doctype": doctype,
                        "name": name,
                    },
                    indent=2,
                ),
                "Calendar Event Location Booking Backfill Failed",
            )
