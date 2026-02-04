# Copyright (c) 2026
# For license information, please see license.txt

import frappe


def _chunked(seq, size=200):
	for i in range(0, len(seq), size):
		yield seq[i : i + size]


def _backfill_student_groups():
	if not frappe.db.table_exists("Student Group"):
		return

	from ifitwala_ed.schedule.student_group_employee_booking import (
		rebuild_employee_bookings_for_all_student_groups,
	)

	# Best-effort backfill for active groups; do not fail on missing locations.
	rebuild_employee_bookings_for_all_student_groups(
		only_active=True,
		skip_archived_ay=True,
		strict_location=False,
	)


def _backfill_meetings():
	if not frappe.db.table_exists("Meeting"):
		return

	names = frappe.get_all("Meeting", pluck="name")
	for batch in _chunked(names):
		for name in batch:
			try:
				doc = frappe.get_doc("Meeting", name)
				if hasattr(doc, "compute_datetime_window"):
					doc.compute_datetime_window()
				if hasattr(doc, "sync_location_booking"):
					doc.sync_location_booking()
			except Exception:
				frappe.logger().exception(
					f"Meeting Location Booking backfill failed for {name}"
				)
		frappe.db.commit()


def _backfill_school_events():
	if not frappe.db.table_exists("School Event"):
		return

	names = frappe.get_all("School Event", pluck="name")
	for batch in _chunked(names):
		for name in batch:
			try:
				doc = frappe.get_doc("School Event", name)
				if hasattr(doc, "sync_location_booking"):
					doc.sync_location_booking()
			except Exception:
				frappe.logger().exception(
					f"School Event Location Booking backfill failed for {name}"
				)
		frappe.db.commit()


def execute():
	if not frappe.db.table_exists("Location Booking"):
		return

	_backfill_student_groups()
	_backfill_meetings()
	_backfill_school_events()
	frappe.db.commit()
