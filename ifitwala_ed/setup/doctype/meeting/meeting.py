# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/meeting/meeting.py

"""
Meeting

- Canonical source for staff meetings (agenda, minutes, action items).
- Time window: date + start_time / end_time → from_datetime / to_datetime.
- Conflict checks:
    - Location (room) conflicts via location_conflicts.find_location_conflicts
    - Employee conflicts via employee_booking.assert_employee_free
- Booking projection:
    - Writes to Employee Booking so that Student Group + Meeting
      share a single "this employee is busy" layer.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, format_datetime

from ifitwala_ed.utilities.location_conflicts import find_location_conflicts
from ifitwala_ed.utilities.employee_booking import (
	assert_employee_free,
	upsert_employee_booking,
	delete_employee_bookings_for_source,
)


def _combine_date_and_time(d, t) -> Optional[datetime]:
	"""
	Combine separate Date + Time fields into a single datetime.

	Returns a Python datetime object or None if either part is missing.
	"""
	if not d or not t:
		return None

	return get_datetime(f"{d} {t}")


class Meeting(Document):

	def validate(self):
		# Basic structural checks
		self.ensure_team_selected()
		self.ensure_unique_participants()
		self.ensure_at_least_one_participant()

		# Compute canonical datetime window from date + time fields
		self.compute_datetime_window()
		self.validate_time_logic()

		# Optional: derive school/AY from team (or leave for later)
		self.set_school_and_academic_year()

		# Conflict checks
		self.validate_location_free()
		self.validate_employee_conflicts()

		# Content-related validation
		self.validate_minutes_when_completed()

	def after_insert(self):
		# Project this meeting into Employee Booking for each participant.
		self.sync_employee_bookings()

	def on_update(self):
		# Keep Employee Booking rows in sync when time or participants change.
		self.sync_employee_bookings()

	def on_cancel(self):
		# Cancelled meetings free up employee time.
		delete_employee_bookings_for_source(self.doctype, self.name)

	def on_trash(self):
		# Deleted meeting should not leave orphan Employee Booking rows.
		delete_employee_bookings_for_source(self.doctype, self.name)

	# ─────────────────────────────────────────────────────────────
	# Field helpers
	# ─────────────────────────────────────────────────────────────

	def compute_datetime_window(self) -> None:
		"""
		Populate read-only Datetime fields from date + time.

		Requires Datetime fields:
		    - from_datetime
		    - to_datetime
		on the Meeting DocType.
		"""
		start_dt = _combine_date_and_time(self.date, self.start_time)
		end_dt = _combine_date_and_time(self.date, self.end_time)

		self.from_datetime = start_dt
		self.to_datetime = end_dt

	def set_school_and_academic_year(self) -> None:
		"""
		Lightweight helper to set school / academic_year.

		Current strategy:
		- If team is set and Meeting.school is empty, pull school from Team.
		- academic_year left as-is for now (can be wired to School defaults later).
		"""
		if getattr(self, "school", None):
			return

		if self.team:
			school = frappe.db.get_value("Team", self.team, "school")
			if school:
				self.school = school

		# TODO (future): infer academic_year from School / Org defaults
		# if not getattr(self, "academic_year", None) and getattr(self, "school", None):
		#     self.academic_year = get_default_academic_year_for_school(self.school)

	# ─────────────────────────────────────────────────────────────
	# Validation helpers
	# ─────────────────────────────────────────────────────────────

	def ensure_team_selected(self) -> None:
		"""
		Guard to ensure a Meeting is attached to some team context.

		Loosen this if you want truly ad-hoc meetings without a Team.
		"""
		if not self.team:
			frappe.throw(
				_("Please select a Team for this meeting."),
				title=_("Team Required"),
			)

	def ensure_unique_participants(self) -> None:
		"""
		Ensure that no User appears twice in the participants table.
		"""
		seen = set()
		dupes = set()

		for row in self.participants or []:
			if not row.participant:
				continue
			if row.participant in seen:
				dupes.add(row.participant)
			seen.add(row.participant)

		if dupes:
			user_list = ", ".join(sorted(dupes))
			frappe.throw(
				_("The following participants are listed more than once: {0}").format(user_list),
				title=_("Duplicate Participants"),
			)

	def ensure_at_least_one_participant(self) -> None:
		"""
		Meeting without participants is usually a modelling error.
		"""
		if not self.participants:
			frappe.throw(
				_("Please add at least one participant to this meeting."),
				title=_("No Participants"),
			)

	def validate_time_logic(self) -> None:
		"""
		Ensure date/time fields make sense and yield a valid window.
		"""
		if not self.date:
			frappe.throw(_("Please set a Date for the meeting."), title=_("Missing Date"))

		if not self.start_time or not self.end_time:
			frappe.throw(
				_("Please set both Start Time and End Time for the meeting."),
				title=_("Missing Time"),
			)

		if not self.from_datetime or not self.to_datetime:
			frappe.throw(
				_("Could not compute meeting start/end datetime. Please check Date and Time."),
				title=_("Invalid Date/Time"),
			)

		if self.to_datetime <= self.from_datetime:
			frappe.throw(
				_("End Time must be after Start Time."),
				title=_("Invalid Time Range"),
			)

	def validate_location_free(self) -> None:
		"""
		Check that the selected location (room) is not double-booked.
		"""
		if not self.location:
			return

		if not self.from_datetime or not self.to_datetime:
			# Time not ready; let time validation handle this.
			return

		conflicts = find_location_conflicts(
			location=self.location,
			start=self.from_datetime,
			end=self.to_datetime,
			exclude={"doctype": self.doctype, "name": self.name},
		)

		if not conflicts:
			return

		lines: List[str] = []
		for slot in conflicts:
			lines.append(
				_("{doctype} {name} from {start} to {end}").format(
					doctype=slot.source_doctype,
					name=slot.source_name,
					start=format_datetime(slot.start),
					end=format_datetime(slot.end),
				)
			)

		msg = "<br>".join(lines)
		frappe.throw(
			_(
				"Location {0} is already booked in this time window:<br>{1}"
			).format(self.location, msg),
			title=_("Location Conflict"),
		)

	def validate_employee_conflicts(self) -> None:
		"""
		Check double-booking for all employees derived from participants.

		Uses Employee Booking as the single truth layer.

		Requires:
		- Employee.user_id == Meeting Participant.participant
		"""
		if not self.from_datetime or not self.to_datetime:
			# Time logic will already throw; no point checking conflicts here.
			return

		employee_map = self._get_participant_employee_map()
		if not employee_map:
			# No employees resolved; nothing to check.
			return

		allow_double_booking = bool(getattr(self, "ignore_conflicts", 0))

		for row in self.participants or []:
			if not row.participant:
				continue

			employee = employee_map.get(row.participant)
			if not employee:
				continue

			# If the child table has an `employee` field, keep it in sync for UI/debugging.
			if hasattr(row, "employee"):
				row.employee = employee

			assert_employee_free(
				employee=employee,
				start=self.from_datetime,
				end=self.to_datetime,
				exclude={"doctype": self.doctype, "name": self.name},
				allow_double_booking=allow_double_booking,
			)

	def validate_minutes_when_completed(self) -> None:
		"""
		Enforce that 'Completed' meetings have some minutes recorded.
		Loosen if needed.
		"""
		if self.status == "Completed" and not self.minutes:
			frappe.throw(
				_("Please record meeting minutes before setting the status to Completed."),
				title=_("Minutes Required"),
			)

	# ─────────────────────────────────────────────────────────────
	# Employee booking projection
	# ─────────────────────────────────────────────────────────────

	def _get_participant_employee_map(self) -> Dict[str, str]:
		"""
		Resolve participants (User) → Employee in a single batched query.

		Returns:
		    dict: { user_id: employee_name }
		"""
		user_ids = {row.participant for row in (self.participants or []) if row.participant}
		if not user_ids:
			return {}

		rows = frappe.get_all(
			"Employee",
			filters={"status": "Active", "user_id": ("in", list(user_ids))},
			fields=["name", "user_id"],
		)

		return {r.user_id: r.name for r in rows}

	def sync_employee_bookings(self) -> None:
		"""
		Ensure Employee Booking rows accurately reflect this meeting.

		Strategy:
		- Wipe existing bookings for this Meeting.
		- Recreate bookings for current participants and current time window.
		"""
		# Always clear existing bookings for this meeting first (simple and safe).
		delete_employee_bookings_for_source(self.doctype, self.name)

		# If there is no valid time window, nothing to book.
		if not self.from_datetime or not self.to_datetime:
			return

		employee_map = self._get_participant_employee_map()
		if not employee_map:
			return

		school = getattr(self, "school", None)
		academic_year = getattr(self, "academic_year", None)

		for row in self.participants or []:
			if not row.participant:
				continue

			employee = employee_map.get(row.participant)
			if not employee:
				continue

			upsert_employee_booking(
				employee=employee,
				start=self.from_datetime,
				end=self.to_datetime,
				source_doctype=self.doctype,
				source_name=self.name,
				booking_type="Meeting",
				blocks_availability=1,
				school=school,
				academic_year=academic_year,
			)

	# ─────────────────────────────────────────────────────────────
	# (Optional) Team membership guard
	# ─────────────────────────────────────────────────────────────

	def ensure_participants_from_team(self) -> None:
		"""
		Placeholder for a stricter rule:

		- Optionally enforce that all participants belong to the selected Team.

		For now this is not called from validate(), but you can enable it later:

		    self.ensure_participants_from_team()

		once Team membership modelling is finalised.
		"""
		pass
