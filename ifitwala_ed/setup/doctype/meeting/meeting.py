# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/meeting/meeting.py


from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, format_datetime, getdate, today, format_date


from ifitwala_ed.utilities.location_utils import find_room_conflicts
from ifitwala_ed.utilities.employee_booking import (
	assert_employee_free,
	upsert_employee_booking,
	delete_employee_bookings_for_source,
)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ifitwala_ed.setup.doctype.team.team import Team

from ifitwala_ed.stock.doctype.location_booking.location_booking import (
	build_source_key,
	build_slot_key_single,
	delete_location_bookings_for_source,
	upsert_location_booking,
)


def _combine_date_and_time(d, t) -> Optional[datetime]:
	"""
	Combine separate Date + Time fields into a single datetime.

	We deliberately go through frappe.utils.get_datetime which:
	- Uses the site's System Settings time zone (NOT the OS/server time),
	- Returns a timezone-aware datetime in that zone.

	This ensures from_datetime / to_datetime are always consistent with
	the Frappe site timezone.
	"""
	if not d or not t:
		return None

	# Example: "2025-11-15 14:30:00"
	return get_datetime(f"{d} {t}")

def get_academic_year_for_date(school: str, meeting_date) -> Optional[str]:
	"""
	Return the Academic Year name for a given school and date.

	Selection logic:
	- school == given school
	- archived == 0
	- year_start_date <= meeting_date <= year_end_date
	- pick the most recent (largest year_start_date) if multiple match
	"""
	if not (school and meeting_date):
		return None

	rows = frappe.get_all(
		"Academic Year",
		filters={
			"school": school,
			"archived": 0,
			"year_start_date": ("<=", meeting_date),
			"year_end_date": (">=", meeting_date),
		},
		fields=["name"],
		order_by="year_start_date desc",
		limit=1,
	)

	if not rows:
		return None

	return rows[0].name



class Meeting(Document):

	def validate(self):
		# 1) Normalize participants from Team if needed
		self.load_team_participants_if_empty()
		self.default_attendance_pending()

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
		self.validate_attendance_statuses()

	def after_insert(self):
		self.sync_employee_bookings()
		self.sync_location_booking()

	def on_update(self):
		self.sync_employee_bookings()
		self.sync_location_booking()

	def on_cancel(self):
		delete_employee_bookings_for_source(self.doctype, self.name)
		delete_location_bookings_for_source(source_doctype=self.doctype, source_name=self.name)

	def on_trash(self):
		delete_employee_bookings_for_source(self.doctype, self.name)
		delete_location_bookings_for_source(source_doctype=self.doctype, source_name=self.name)

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

	def default_attendance_pending(self) -> None:
		# Draft / Scheduled / Cancelled / Postponed → blanks should be Pending
		if self.status == "Completed":
			return

		for row in self.participants or []:
			if not (row.attendance_status or "").strip():
				row.attendance_status = "Pending"


	# ─────────────────────────────────────────────────────────────
	# Time & context helpers
	# ─────────────────────────────────────────────────────────────

	def compute_datetime_window(self) -> None:
		"""
		Populate from_datetime / to_datetime from date + time.

		Uses _combine_date_and_time → frappe.utils.get_datetime, which is
		anchored to the Frappe site timezone (System Settings), not raw
		server OS time.
		"""
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
		- If Meeting has 'school' and it's empty, infer from Team.school.
		- If Meeting has 'academic_year' and it's empty, pick a non-archived
		  Academic Year for that school whose year_end_date is today or later.

		Priority:
		    1) School.current_academic_year, if valid (not archived, not past).
		    2) First matching Academic Year for that school with:
		       archived = 0 and year_end_date >= today, ordered by year_start_date.
		"""

		# 1) Infer school from Team if possible
		if hasattr(self, "school") and not self.school and getattr(self, "team", None):
			school = frappe.db.get_value("Team", self.team, "school")
			if school:
				self.school = school

		# 2) Handle Academic Year only if field exists and is empty
		if not hasattr(self, "academic_year"):
			return

		if getattr(self, "academic_year", None):
			# Already set; we don't override here
			return

		school = getattr(self, "school", None) if hasattr(self, "school") else None
		if not school:
			return

		today_date = getdate(today())

		def _is_valid_ay(name: str | None) -> bool:
			if not name:
				return False
			row = frappe.db.get_value(
				"Academic Year",
				name,
				["archived", "year_end_date"],
				as_dict=True,
			)
			if not row:
				return False
			# Must not be archived
			if row.archived:
				return False
			# If year_end_date is set, it must be today or in the future
			if row.year_end_date and getdate(row.year_end_date) < today_date:
				return False
			return True

		# 2a) Try School.current_academic_year first
		ay_name = frappe.db.get_value("School", school, "current_academic_year")
		if _is_valid_ay(ay_name):
			self.academic_year = ay_name
			return

		# 2b) Fallback: earliest non-archived AY for this school whose year_end_date >= today
		candidates = frappe.get_all(
			"Academic Year",
			filters={
				"school": school,
				"archived": 0,
				"year_end_date": (">=", today_date),
			},
			fields=["name"],
			order_by="year_start_date asc",
			limit=1,
		)
		if candidates:
			self.academic_year = candidates[0].name


	# ─────────────────────────────────────────────────────────────
	# Conflict checks
	# ─────────────────────────────────────────────────────────────

	def validate_location_free(self) -> None:
		"""
		Ensure the selected location is not double-booked.
		Uses the canonical room conflict helper.
		"""
		if not self.location:
			return

		if not (self.from_datetime and self.to_datetime):
			return

		conflicts = find_room_conflicts(
			self.location,
			self.from_datetime,
			self.to_datetime,
			exclude={"doctype": self.doctype, "name": self.name},
		)

		if not conflicts:
			return

		lines: List[str] = []
		for c in conflicts:
			lines.append(
				_("{doctype} {name} from {start} to {end}").format(
					doctype=c.get("source_doctype"),
					name=c.get("source_name"),
					start=format_datetime(c.get("from")),
					end=format_datetime(c.get("to")),
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
			filters={"employment_status": "Active", "user_id": ("in", list(user_ids))},
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

	def validate_attendance_statuses(self) -> None:
		"""
		Attendance semantics:

		- Before the meeting, participants should be in a neutral state
		  (e.g. 'Pending'), not pre-marked Absent.
		- When status = 'Completed', every participant must have a final
		  attendance_status (Present / Absent / Late / Excused), i.e.
		  no 'Pending' or blank.

		DocType side:
		- Meeting Participant.attendance_status should include at least:
		  'Pending', 'Present', 'Absent', 'Late', 'Excused'.
		- Default should be 'Pending'.
		"""
		if self.status != "Completed":
			return

		unresolved: List[str] = []

		for row in self.participants or []:
			status = (row.attendance_status or "").strip()
			if not status or status == "Pending":
				label = row.participant_name or row.participant or _("(unknown)")
				unresolved.append(label)

		if unresolved:
			name_list = ", ".join(unresolved)
			frappe.throw(
				_(
					"Please set attendance for all participants before marking the meeting as Completed. "
					"Missing for: {0}"
				).format(name_list),
				title=_("Attendance Not Recorded"),
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

	def sync_location_booking(self) -> None:
		"""
		Project this Meeting into Location Booking (single stable slot).
		"""
		if not (self.location and self.from_datetime and self.to_datetime):
			delete_location_bookings_for_source(source_doctype=self.doctype, source_name=self.name)
			return

		school = getattr(self, "school", None) if hasattr(self, "school") else None
		academic_year = (
			getattr(self, "academic_year", None) if hasattr(self, "academic_year") else None
		)

		source_key = build_source_key(self.doctype, self.name)
		slot_key = build_slot_key_single(source_key, self.location)

		upsert_location_booking(
			location=self.location,
			from_datetime=self.from_datetime,
			to_datetime=self.to_datetime,
			occupancy_type="Meeting",
			source_doctype=self.doctype,
			source_name=self.name,
			slot_key=slot_key,
			school=school,
			academic_year=academic_year,
		)

		# Clean up any stale rows from prior locations.
		frappe.db.delete(
			"Location Booking",
			{
				"source_doctype": self.doctype,
				"source_name": self.name,
				"slot_key": ["!=", slot_key],
			},
		)

	# ─────────────────────────────────────────────────────────────
	# Visibility / privacy layer
	# ─────────────────────────────────────────────────────────────

	def has_permission(self, ptype: str = "read") -> bool:
		"""
		Apply visibility_scope on top of role-based perms.

		Addition:
			- Academic Admin: can read/print any Meeting where Meeting.school is
				their Employee.school OR a descendant of their Employee.school.
		"""
		user = frappe.session.user
		roles = set(frappe.get_roles(user) or [])

		# Full bypass for admin / sys mgr
		if user == "Administrator" or "System Manager" in roles:
			return True

		# Always respect standard role-based permissions first.
		# (So Academic Admin must also have a DocType permission row for read/print.)
		if not super().has_permission(ptype):
			return False

		# For non-read operations, keep base perms only (no special bypass)
		if ptype not in ("read", "print"):
			return True

		# Academic Admin school-scope bypass (read/print)
		if "Academic Admin" in roles:
			meeting_school = getattr(self, "school", None)
			if meeting_school:
				emp_school = frappe.db.get_value(
					"Employee",
					{"user_id": user, "employment_status": "Active"},
					"school",
				)

				if emp_school:
					# Self or descendants
					from ifitwala_ed.utilities.school_tree import get_descendant_schools

					allowed = set(get_descendant_schools(user_school=emp_school) or [])
					if meeting_school in allowed:
						return True

		# Fall back to visibility_scope rules for everyone else
		return self._user_can_see(user)



	def _user_can_see(self, user: str) -> bool:
		scope = (self.visibility_scope or "").strip() or "Team & Participants"

		# Participation and team membership always grant access
		if self._user_is_participant(user):
			return True
		if self._user_on_team(user):
			return True

		if scope == "Participants Only":
			return False

		if scope == "Team & Participants":
			return False  # we already checked those cases

		if scope == "School Staff":
			if self._user_same_school(user):
				return True
			# fallback: no access
			return False

		if scope == "Public/Internal":
			# No extra restriction beyond base role-based perms
			return True

		# Unknown / future scope values → safest is deny
		return False

	def _user_is_participant(self, user: str) -> bool:
		return any(
			row.participant == user
			for row in (self.participants or [])
			if row.participant
		)

	def _user_on_team(self, user: str) -> bool:
		if not getattr(self, "team", None):
			return False

		return bool(
			frappe.db.exists(
				"Team Member",
				{
					"parent": self.team,
					"parenttype": "Team",
					"parentfield": "members",
					"member": user,
				},
			)
		)

	def _user_same_school(self, user: str) -> bool:
		"""
		School match: Meeting.school == Employee.school for this user.
		If either side is missing, returns False.
		"""
		meeting_school = getattr(self, "school", None)
		if not meeting_school:
			return False

		emp = frappe.db.get_value(
			"Employee",
			{"user_id": user, "employment_status": "Active"},
			["name", "school"],
			as_dict=True,
		)
		if not emp:
			return False

		return emp.school == meeting_school


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


@frappe.whitelist()
def create_next_meeting(source_meeting: str, new_date: str, new_time: str | None = None) -> str:
	"""
	Create a follow-up Meeting based on an existing one.

	Behaviours:

	- Participants:
	    The Meeting Participant child table is treated as the source of truth.
	    We copy EVERY participant row (User + Employee + name), regardless of
	    whether a Team is set. This covers:
	        * pure ad-hoc meetings (no Team, only participants),
	        * pure team meetings,
	        * team + extra invitees.

	- Team:
	    If src.team is set, we copy it as metadata, but we NEVER re-derive
	    participants from Team here. That is only done by
	    load_team_participants_if_empty() when the participants table is empty.

	- Time:
	    We preserve the original duration. If you shift start_time, the end_time
	    is moved by the same delta.

	- Status:
	    New meeting is created in status = "Scheduled".
	"""
	if not source_meeting:
		frappe.throw(_("Source meeting is required."))

	src = frappe.get_doc("Meeting", source_meeting)

	if not new_date:
		frappe.throw(_("New date is required."))

	# Fallback: if no new_time given, keep original start_time
	if not new_time:
		new_time = src.start_time

	# Compute original duration (if valid)
	src_start_dt = _combine_date_and_time(src.date, src.start_time)
	src_end_dt = _combine_date_and_time(src.date, src.end_time)
	duration = None
	if src_start_dt and src_end_dt and src_end_dt > src_start_dt:
		duration = src_end_dt - src_start_dt

	new = frappe.new_doc("Meeting")

	# Basic details
	new.meeting_name = f"{(src.meeting_name or src.name)} - next"
	new.meeting_code = ""
	new.team = src.team  # optional metadata; participants stay the source of truth
	new.date = new_date
	new.start_time = new_time
	new.location = src.location
	new.virtual_meeting_link = src.virtual_meeting_link
	new.meeting_category = src.meeting_category
	new.agenda = src.agenda
	new.status = "Scheduled"

	# Compute end_time from duration if possible; otherwise copy original
	if duration:
		new_start_dt = _combine_date_and_time(new_date, new_time)
		if new_start_dt:
			new_end_dt = new_start_dt + duration
			new.end_time = new_end_dt.time()
		else:
			new.end_time = src.end_time
	else:
		new.end_time = src.end_time

	# Context fields if present
	if hasattr(src, "school"):
		new.school = src.school
	if hasattr(src, "academic_year"):
		new.academic_year = src.academic_year

	# ── Participants: child table as source of truth ──
	for row in src.participants or []:
		if not row.participant:
			continue

		child = new.append("participants", {})
		child.participant = row.participant
		child.participant_name = getattr(row, "participant_name", None)

		# Keep Employee linkage if available
		if hasattr(row, "employee") and row.employee:
			child.employee = row.employee

		# Everyone starts as Participant + Pending
		if hasattr(child, "role_in_meeting"):
			child.role_in_meeting = "Participant"
		if hasattr(child, "attendance_status"):
			child.attendance_status = "Pending"

	# Insert will run validate(), but at this point:
	# - date, start_time, end_time are consistent
	# - participants is non-empty (unless src had none)
	new.insert()
	return new.name


@frappe.whitelist()
def get_team_meeting_book(
	team: str,
	academic_year: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> str:
	"""
	Return a long, printable HTML page with all meetings for a Team
	over a selected window.

	Usage: called from Team form, injected into a new browser tab via JS.

	Permission model:
	  - User must have read access to the Team.
	  - Each Meeting is further filtered via Meeting.has_permission("read").
	"""
	if not team:
		frappe.throw(_("Team is required."))

	user = frappe.session.user

	# 1) Team guard: if you can't see the Team, you can't see its meeting book
	team_doc = frappe.get_doc("Team", team)
	if not team_doc.has_permission("read"):
		frappe.throw(
			_("You do not have permission to view this team."),
			frappe.PermissionError,
		)

	# 2) Normalise filters
	date_filters = {}
	if academic_year:
		date_filters["academic_year"] = academic_year
	else:
		# Optional explicit date range
		if from_date:
			date_filters.setdefault("date", {})
			date_filters["date"] = (">=", getdate(from_date))
		if to_date:
			if "date" in date_filters:
				# Between
				date_filters["date"] = (
					"between",
					[getdate(from_date), getdate(to_date)],
				) if from_date else ("<=", getdate(to_date))
			else:
				date_filters["date"] = ("<=", getdate(to_date))

	# 3) Base Meeting filters
	meeting_filters: dict[str, object] = {
		"team": team,
		"status": ("!=", "Cancelled"),
	}
	meeting_filters.update(date_filters)

	# 4) Fetch candidates (let Frappe perms filter first)
	fields = [
		"name",
		"meeting_name",
		"meeting_code",
		"date",
		"start_time",
		"end_time",
		"status",
		"meeting_category",
		"location",
		"virtual_meeting_link",
		"agenda",
		"minutes",
	]
	candidates = frappe.get_all(
		"Meeting",
		filters=meeting_filters,
		fields=fields,
		order_by="date asc, start_time asc, name asc",
	)

	if not candidates:
		return _render_empty_meeting_book(team_doc, academic_year, from_date, to_date, user)

	# 5) Enforce Meeting.has_permission for each candidate
	allowed_names: set[str] = set()
	for row in candidates:
		doc = frappe.get_doc("Meeting", row.name)
		if doc.has_permission("read"):
			allowed_names.add(row.name)

	if not allowed_names:
		# Team visible, but no meetings visible under Meeting visibility rules
		return _render_empty_meeting_book(team_doc, academic_year, from_date, to_date, user)

	meetings: list[dict] = []
	for row in candidates:
		if row.name not in allowed_names:
			continue

		# Pre-format labels to keep template lightweight
		date_label = format_date(row.date) if row.date else ""
		start_label = ""
		end_label = ""
		if row.start_time:
			start_label = str(row.start_time)[:5]
		if row.end_time:
			end_label = str(row.end_time)[:5]
		time_range = ""
		if start_label and end_label:
			time_range = f"{start_label}–{end_label}"
		elif start_label:
			time_range = start_label

		meetings.append(
			{
				"name": row.name,
				"title": row.meeting_name or row.name,
				"code": row.meeting_code,
				"date": row.date,
				"date_label": date_label,
				"time_range": time_range,
				"status": row.status,
				"category": row.meeting_category,
				"location": row.location,
				"virtual_meeting_link": row.virtual_meeting_link,
				"agenda": row.agenda,
				"minutes": row.minutes,
			}
		)

	if not meetings:
		return _render_empty_meeting_book(team_doc, academic_year, from_date, to_date, user)

	meeting_names = [m["name"] for m in meetings]

	# 6) Batch-load participants and action items
	participants_by_meeting: dict[str, list[dict]] = {name: [] for name in meeting_names}
	action_items_by_meeting: dict[str, list[dict]] = {name: [] for name in meeting_names}

	participants = frappe.get_all(
		"Meeting Participant",
		filters={"parent": ("in", meeting_names)},
		fields=["parent", "participant", "participant_name", "role_in_meeting", "attendance_status"],
		order_by="parent asc, idx asc",
	)
	for row in participants:
		participants_by_meeting[row.parent].append(
			{
				"name": row.participant_name or row.participant,
				"role": row.role_in_meeting,
				"attendance": row.attendance_status,
			}
		)

	action_items = frappe.get_all(
			"Meeting Action Item",
			filters={"parent": ("in", meeting_names)},
			fields=["parent", "action_item_description", "assigned_to", "due_date", "status"],
			order_by="parent asc, idx asc",
	)

	# Collect all assignees so we can resolve User.full_name in one batch
	assignees = {row.assigned_to for row in action_items if row.assigned_to}
	user_fullnames: dict[str, str] = {}
	if assignees:
			user_rows = frappe.get_all(
					"User",
					filters={"name": ("in", list(assignees))},
					fields=["name", "full_name"],
			)
			user_fullnames = {u.name: (u.full_name or u.name) for u in user_rows}


	for row in action_items:
			display_owner = user_fullnames.get(row.assigned_to) if row.assigned_to else ""
			action_items_by_meeting[row.parent].append(
					{
							"description": row.action_item_description or "",
							"owner": display_owner or row.assigned_to or "",
							"due_date": format_date(row.due_date) if row.due_date else "",
							"status": row.status,
					}
			)


	# 7) Academic Year doc (if provided) just for header label
	ay_doc = None
	if academic_year:
		try:
			ay_doc = frappe.get_doc("Academic Year", academic_year)
		except frappe.DoesNotExistError:
			ay_doc = None

	context = {
		"team": team_doc,
		"academic_year": ay_doc,
		"from_date": getdate(from_date) if from_date else None,
		"to_date": getdate(to_date) if to_date else None,
		"meetings": meetings,
		"participants_by_meeting": participants_by_meeting,
		"action_items_by_meeting": action_items_by_meeting,
		"generated_by": user,
		"generated_on": format_date(getdate(today())),
	}

	html = frappe.render_template(
		"ifitwala_ed/templates/print/team_meeting_book.html",
		context,
	)
	return html


def _render_empty_meeting_book(
	team_doc: "Team",
	academic_year: str | None,
	from_date: str | None,
	to_date: str | None,
	user: str,
) -> str:
	"""Shared renderer when no visible meetings are found."""
	ay_doc = None
	if academic_year:
		try:
			ay_doc = frappe.get_doc("Academic Year", academic_year)
		except frappe.DoesNotExistError:
			ay_doc = None

	context = {
		"team": team_doc,
		"academic_year": ay_doc,
		"from_date": getdate(from_date) if from_date else None,
		"to_date": getdate(to_date) if to_date else None,
		"meetings": [],
		"participants_by_meeting": {},
		"action_items_by_meeting": {},
		"generated_by": user,
		"generated_on": format_date(getdate(today())),
	}

	return frappe.render_template(
		"ifitwala_ed/templates/print/team_meeting_book.html",
		context,
	)
