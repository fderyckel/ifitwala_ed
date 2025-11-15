# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/meeting/meeting.py

# ifitwala_ed/setup/doctype/meeting/meeting.py

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

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
	if not d or not t:
		return None
	return get_datetime(f"{d} {t}")


class Meeting(Document):

	def validate(self):
		# 1) Normalize participants from Team if needed
		self.load_team_participants_if_empty()

		# 2) Participant integrity
		self.ensure_unique_participants()
		self.ensure_at_least_one_participant()

		# 3) Time normalization & logic
		self.compute_datetime_window()
		self.validate_time_logic()

		# 4) Enrich context (school/AY) if fields exist
		self.set_school_and_academic_year()

		# 5) Conflicts: room + employee
		self.validate_location_free()
		self.validate_employee_conflicts()

		# 6) Content rules
		self.validate_minutes_when_completed()

	def after_insert(self):
		self.sync_employee_bookings()

	def on_update(self):
		self.sync_employee_bookings()

	def on_cancel(self):
		delete_employee_bookings_for_source(self.doctype, self.name)

	def on_trash(self):
		delete_employee_bookings_for_source(self.doctype, self.name)

	# ─────────────────────────────────────────────────────────────
	# Participant helpers
	# ─────────────────────────────────────────────────────────────

	def load_team_participants_if_empty(self) -> None:
		"""
		If a team is selected AND no participants are already added,
		auto-populate participants based on Team.members (Team Member child).
		"""
		if not self.team:
			return

		if self.participants:
			# User already customized participants → do not override.
			return

		from .meeting import get_team_participants  # same module, safe import

		data = get_team_participants(self.team) or []

		for row in data:
			user_id = row.get("user_id")
			if not user_id:
				continue

			child = self.append("participants", {})
			child.participant = user_id
			if row.get("full_name"):
				child.participant_name = row["full_name"]
			# Only if Meeting Participant has an employee field
			if hasattr(child, "employee") and row.get("employee"):
				child.employee = row["employee"]

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
		if not self.participants:
			frappe.throw(
				_("Please add at least one participant to this meeting."),
				title=_("No Participants"),
			)

	# ─────────────────────────────────────────────────────────────
	# Time & context helpers
	# ─────────────────────────────────────────────────────────────

	def compute_datetime_window(self) -> None:
		start_dt = _combine_date_and_time(self.date, self.start_time)
		end_dt = _combine_date_and_time(self.date, self.end_time)

		self.from_datetime = start_dt
		self.to_datetime = end_dt

	def validate_time_logic(self) -> None:
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

	def set_school_and_academic_year(self) -> None:
		"""
		Lightweight helper:
		- If Meeting has a 'school' field and it's empty, pull from Team.school.
		- Academic Year left for future logic.
		Guarded with hasattr so we don't assume fields exist.
		"""
		if hasattr(self, "school") and not self.school and self.team:
			school = frappe.db.get_value("Team", self.team, "school")
			if school:
				self.school = school

		# Example hook for future:
		# if hasattr(self, "academic_year") and not self.academic_year and getattr(self, "school", None):
		#     self.academic_year = get_default_ay_for_school(self.school)

	# ─────────────────────────────────────────────────────────────
	# Conflict checks
	# ─────────────────────────────────────────────────────────────

	def validate_location_free(self) -> None:
		"""
		Ensure the selected location is not double-booked.
		Uses the location_conflicts.find_location_conflicts engine.
		"""
		if not self.location:
			return

		if not (self.from_datetime and self.to_datetime):
			return

		ignore = [(self.doctype, self.name)]

		conflicts = find_location_conflicts(
			location=self.location,
			start=self.from_datetime,
			end=self.to_datetime,
			ignore_sources=ignore,
		)

		if not conflicts:
			return

		lines: List[str] = []
		for c in conflicts:
			lines.append(
				_("{doctype} {name} from {start} to {end}").format(
					doctype=c.source_doctype,
					name=c.source_name,
					start=format_datetime(c.start),
					end=format_datetime(c.end),
				)
			)

		msg = "<br>".join(lines)
		frappe.throw(
			_("Location {0} is already booked:<br>{1}").format(self.location, msg),
			title=_("Location Conflict"),
		)

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

	def validate_employee_conflicts(self) -> None:
		"""
		Check double-booking for all employees resolved from participants.
		Uses Employee Booking as the single truth layer.
		"""
		if not (self.from_datetime and self.to_datetime):
			return

		employee_map = self._get_participant_employee_map()
		if not employee_map:
			return

		# Support both ignore_conflict and ignore_conflicts, just in case
		allow_double_booking = bool(
			getattr(self, "ignore_conflict", getattr(self, "ignore_conflicts", 0))
		)

		for row in self.participants or []:
			if not row.participant:
				continue

			employee = employee_map.get(row.participant)
			if not employee:
				continue

			# keep Meeting Participant.employee in sync if field exists
			if hasattr(row, "employee") and not row.employee:
				row.employee = employee

			assert_employee_free(
				employee=employee,
				start=self.from_datetime,
				end=self.to_datetime,
				exclude={"doctype": self.doctype, "name": self.name},
				allow_double_booking=allow_double_booking,
			)

	def validate_minutes_when_completed(self) -> None:
		if self.status == "Completed" and not self.minutes:
			frappe.throw(
				_("Please record meeting minutes before setting the status to Completed."),
				title=_("Minutes Required"),
			)

	# ─────────────────────────────────────────────────────────────
	# Booking projection
	# ─────────────────────────────────────────────────────────────

	def sync_employee_bookings(self) -> None:
		"""
		Project this Meeting into Employee Booking for each participant.

		Strategy:
		- Delete existing bookings for this Meeting.
		- Recreate for current participants and current time window.
		"""
		delete_employee_bookings_for_source(self.doctype, self.name)

		if not (self.from_datetime and self.to_datetime):
			return

		employee_map = self._get_participant_employee_map()
		if not employee_map:
			return

		school = getattr(self, "school", None) if hasattr(self, "school") else None
		academic_year = (
			getattr(self, "academic_year", None) if hasattr(self, "academic_year") else None
		)

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


@frappe.whitelist()
def get_team_participants(team: str) -> list[dict]:
	"""
	Return team members for a given Team as candidate meeting participants.

	Model:
	    Team
	        └─ Team Member (child table "members")
	            - employee     (Link Employee)
	            - member       (Link User)
	            - member_name  (Data)

	We return:
	    {
	        "user_id": "...",    # from Team Member.member
	        "full_name": "...",  # from member_name or User.full_name
	        "employee": "EMP-..." # from Team Member.employee
	    }
	"""
	if not team:
		return []

	rows = frappe.get_all(
		"Team Member",
		filters={
			"parent": team,
			"parenttype": "Team",
			"parentfield": "members",
		},
		fields=["employee", "member", "member_name"],
	)

	out: list[dict] = []
	seen_users: set[str] = set()

	for r in rows:
		user_id = r.get("member")
		if not user_id:
			continue

		if user_id in seen_users:
			continue

		full_name = (
			r.get("member_name")
			or frappe.db.get_value("User", user_id, "full_name")
			or user_id
		)

		out.append(
			{
				"user_id": user_id,
				"full_name": full_name,
				"employee": r.get("employee"),
			}
		)
		seen_users.add(user_id)

	return out
