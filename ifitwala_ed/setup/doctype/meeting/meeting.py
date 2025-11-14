# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/meeting/meeting.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, format_datetime

from ifitwala_ed.utilities.location_conflicts import find_location_conflicts
from ifitwala_ed.utilities.employee_booking import (
	assert_employee_free,
	delete_employee_bookings_for_source,
	upsert_employee_booking,
)


def _combine_date_and_time(d, t):
	"""
	Combine separate Date + Time fields into a single datetime.

	Returns a Python datetime object or None if either part is missing.
	"""
	if not d or not t:
		return None

	return get_datetime(f"{d} {t}")


class Meeting(Document):

	def validate(self):
		self.ensure_team_selected()
		self.ensure_unique_participants()
		self.ensure_participants_from_team()
		self.ensure_at_least_one_participant()
		self.validate_time_logic()
		self.validate_location_free()
		self.validate_employee_conflicts()
		self.validate_minutes_when_completed()

	def after_insert(self):
		self.create_or_update_event()
		self.update_series_metrics()
		self.sync_employee_bookings()

	def on_update(self):
		self.create_or_update_event()
		self.update_series_metrics()
		self.sync_employee_bookings()

	def on_trash(self):
		self.update_series_metrics()
		delete_employee_bookings_for_source(self.doctype, self.name)

	# ───────────────────────────────────────────────────────────
	# Participants / team
	# ───────────────────────────────────────────────────────────

	def ensure_team_selected(self):
		if not self.team:
			frappe.throw(_("Please select a Team for the meeting."))

	def ensure_unique_participants(self):
		seen = set()
		for d in self.participants or []:
			key = (d.employee or d.participant or "").strip()
			if not key:
				continue
			if key in seen:
				label = d.participant_name or d.employee or d.participant
				frappe.throw(_("Duplicate participant: {0}").format(label))
			seen.add(key)

	def ensure_participants_from_team(self):
		"""
		If participants table is empty, auto-populate with team members.
		"""
		if self.get("participants"):
			return

		team_members = frappe.db.get_all(
			"Team Member",
			filters={"parent": self.team},
			fields=["employee", "member", "member_name", "role_in_team"],
		)
		if not team_members:
			return

		user_cache: dict[str, str | None] = {}
		name_cache: dict[str, str | None] = {}

		def resolve_user(employee: str | None, fallback: str | None) -> str | None:
			if fallback:
				return fallback
			if not employee:
				return None
			if employee in user_cache:
				return user_cache[employee]
			user_id = frappe.db.get_value("Employee", employee, "user_id")
			user_cache[employee] = user_id
			return user_id

		def resolve_name(employee: str | None, fallback: str | None) -> str | None:
			if fallback:
				return fallback
			if not employee:
				return fallback
			if employee in name_cache:
				return name_cache[employee]
			emp_name = frappe.db.get_value("Employee", employee, "employee_name")
			name_cache[employee] = emp_name
			return emp_name

		for m in team_members:
			if not m.employee:
				continue
			self.append("participants", {
				"employee": m.employee,
				"participant": resolve_user(m.employee, m.member),
				"participant_name": resolve_name(m.employee, m.member_name),
				"role_in_meeting": m.role_in_team or "Participant",
				"attendance_status": "Absent",
			})

	def ensure_at_least_one_participant(self):
		if not self.get("participants") or len(self.get("participants")) < 1:
			frappe.throw(_("Meeting must have at least one participant."))

	# ───────────────────────────────────────────────────────────
	# Time and location validation
	# ───────────────────────────────────────────────────────────

	def validate_time_logic(self):
		"""
		Basic sanity check on time fields.

		Currently assumes same-day meetings.
		"""
		if not self.date:
			# You can hard-enforce having a date later if you want.
			return

		if self.start_time and self.end_time and self.end_time <= self.start_time:
			frappe.throw(_("End Time must be later than Start Time."))

	def validate_location_free(self):
		"""
		Check that the meeting location is free using the shared conflict engine.
		"""
		if not (self.location and self.date and self.start_time and self.end_time):
			# incomplete info → skip conflict check
			return

		start_dt = _combine_date_and_time(self.date, self.start_time)
		end_dt = _combine_date_and_time(self.date, self.end_time)

		if not start_dt or not end_dt or end_dt <= start_dt:
			# Let validate_time_logic handle basic shape rules
			return

		conflicts = find_location_conflicts(
			location=self.location,
			start=start_dt,
			end=end_dt,
			ignore_sources=[("Meeting", self.name)] if self.name else None,
		)

		if not conflicts:
			return

		# Show first conflict in a clear message.
		c = conflicts[0]
		frappe.throw(
			_("Location {0} is already booked from {1} to {2} by {3} <b>{4}</b>.").format(
				c.location,
				format_datetime(c.start),
				format_datetime(c.end),
				c.source_doctype,
				c.source_name,
			)
		)

	def validate_minutes_when_completed(self):
		if self.status == "Completed" and not self.minutes:
			frappe.throw(_("Minutes must be entered if the meeting status is 'Completed'."))

	def validate_employee_conflicts(self):
		start_dt, end_dt = self._get_time_window()
		if not (start_dt and end_dt):
			return

		exclude = {"doctype": self.doctype, "name": self.name} if self.name else None
		for row in self.participants or []:
			if not row.employee:
				continue

			assert_employee_free(
				employee=row.employee,
				start=start_dt,
				end=end_dt,
				exclude=exclude,
			)

	# ───────────────────────────────────────────────────────────
	# Helpers
	# ───────────────────────────────────────────────────────────
	def get_team_color(self):
		if self.team:
			color = frappe.db.get_value("Team", self.team, "meeting_color")
			if color:
				return color
		return "#364FC7"

	def update_series_metrics(self):
		if not self.meeting_series:
			return

		total = frappe.db.count("Meeting", {"meeting_series": self.meeting_series})
		last = frappe.db.get_all(
			"Meeting",
			{"meeting_series": self.meeting_series},
			["date"],
			order_by="date desc",
			limit=1,
		)
		last_date = last[0].date if last else None

		values = {
			"occurrences_created": total,
			"last_occurrence_date": last_date,
			"series_end_date": last_date,
		}
		frappe.db.set_value("Meeting Series", self.meeting_series, values)

	def _get_time_window(self):
		if not (self.date and self.start_time and self.end_time):
			return None, None

		start_dt = _combine_date_and_time(self.date, self.start_time)
		end_dt = _combine_date_and_time(self.date, self.end_time)
		if not start_dt or not end_dt or end_dt <= start_dt:
			return None, None

		return start_dt, end_dt

	def _get_team_context(self):
		if not self.team:
			return {}
		if not hasattr(self, "_team_ctx"):
			self._team_ctx = frappe.db.get_value("Team", self.team, ["school"], as_dict=True) or {}
		return getattr(self, "_team_ctx", {})

	def sync_employee_bookings(self):
		"""
		Materialize each employee participant into Employee Booking.

		Called on insert/update. Automatically clears bookings on delete.
		"""
		if not self.name:
			return

		delete_employee_bookings_for_source(self.doctype, self.name)

		if (self.status or "").lower() == "cancelled":
			return

		start_dt, end_dt = self._get_time_window()
		if not (start_dt and end_dt):
			return

		team_ctx = self._get_team_context()
		school = team_ctx.get("school")

		for row in self.participants or []:
			if not row.employee:
				continue

			upsert_employee_booking(
				employee=row.employee,
				start=start_dt,
				end=end_dt,
				source_doctype=self.doctype,
				source_name=self.name,
				booking_type="Meeting",
				blocks_availability=1,
				school=school,
			)
