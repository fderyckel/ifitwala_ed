# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/meeting/meeting.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, format_datetime

from ifitwala_ed.utilities.location_conflicts import find_location_conflicts


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
		self.validate_minutes_when_completed()

	def after_insert(self):
		self.create_or_update_event()

	def on_update(self):
		self.create_or_update_event()

	# ───────────────────────────────────────────────────────────
	# Participants / team
	# ───────────────────────────────────────────────────────────

	def ensure_team_selected(self):
		if not self.team:
			frappe.throw(_("Please select a Team for the meeting."))

	def ensure_unique_participants(self):
		seen = set()
		for d in self.participants or []:
			if d.participant in seen:
				frappe.throw(_("Duplicate participant: {0}").format(d.participant))
			seen.add(d.participant)

	def ensure_participants_from_team(self):
		"""
		If participants table is empty, auto-populate with active team members.
		"""
		if self.get("participants"):
			return

		team_members = frappe.db.get_all(
			"Team Member",
			filters={"parent": self.team, "active": 1},
			fields=["member"],
		)
		for m in team_members:
			self.append("participants", {
				"participant": m.member,
				"role_in_meeting": "Participant",
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

	# ───────────────────────────────────────────────────────────
	# Event sync (Frappe Event)
	# ───────────────────────────────────────────────────────────

	def create_or_update_event(self):
		"""Create or update a Frappe Event record corresponding to this Meeting."""
		if not self.date or not self.start_time:
			return

		start_dt = _combine_date_and_time(self.date, self.start_time)
		if not start_dt:
			return

		end_dt = None
		if self.end_time:
			end_dt = _combine_date_and_time(self.date, self.end_time)

		title = f"{self.team or _('Unassigned Team')} – {self.meeting_name or _('Meeting')}"

		description = ""
		if self.agenda:
			description += f"<b>{_('Agenda')}:</b><br>{self.agenda}<br><br>"
		if self.virtual_meeting_link:
			description += f"<b>{_('Virtual Meeting Link')}:</b> {self.virtual_meeting_link}<br>"
		if self.location:
			description += f"<b>{_('Location')}:</b> {self.location}<br>"

		# Find or create linked Event
		existing = frappe.db.exists(
			"Event",
			{"reference_doctype": "Meeting", "reference_name": self.name},
		)
		if existing:
			event = frappe.get_doc("Event", existing)
		else:
			event = frappe.new_doc("Event")
			event.reference_doctype = "Meeting"
			event.reference_name = self.name

		event.subject = title
		event.starts_on = start_dt
		event.ends_on = end_dt or start_dt
		event.description = description
		event.status = "Open" if self.status == "Scheduled" else "Closed"
		event.color = self.get_team_color()
		event.event_type = "Public"

		# replace attendees
		event.attendees = []
		for p in self.participants or []:
			if p.participant:
				event.append("attendees", {"person": p.participant})

		event.flags.ignore_mandatory = True
		event.save(ignore_permissions=True)

	def get_team_color(self):
		if self.team:
			color = frappe.db.get_value("Team", self.team, "meeting_color")
			if color:
				return color
		return "#364FC7"
