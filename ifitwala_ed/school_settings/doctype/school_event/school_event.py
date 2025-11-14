# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/school_event/school_event.py

import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.desk.reportview import get_filters_cond
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime, get_system_timezone
from six import string_types


class SchoolEvent(Document):
	def validate(self):
		self.validate_time()

	def on_update(self):
		self.validate_date()

	def validate_date(self):
		# For non-"Other" categories, event must be in the future
		if (
			self.event_category != "Other"
			and get_datetime(self.starts_on) < get_datetime(now_datetime())
		):
			frappe.throw(
				_("The date {0} of the event has to be in the future. Please adjust the date.").format(
					self.starts_on
				)
			)

	def validate_time(self):
		# Sanity check: start must be <= end
		if get_datetime(self.starts_on) > get_datetime(self.ends_on):
			frappe.throw(
				_(
					"The start time of your event {0} has to be earlier than its end {1}. "
					"Please adjust the time."
				).format(self.starts_on, self.ends_on)
			)


def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	participant = frappe.qb.DocType("School Event Participant")
	event = frappe.qb.DocType("School Event")

	# NOTE:
	# This is intentionally narrow: it only constrains by explicit participants
	# and owner. We will extend it later with audience-based logic.
	query = (
		frappe.qb.from_(participant)
		.join(event)
		.on(participant.parent == event.name)
		.where(participant.participant == user)
		.select(event.name)
	)

	names = [r[0] for r in query.run()]

	if names:
		name_condition = "name IN ({names})".format(
			names=", ".join([frappe.db.escape(n) for n in names])
		)
	else:
		name_condition = ""

	owner_condition = "owner = {user}".format(user=frappe.db.escape(user))

	if name_condition:
		combined_condition = f"({name_condition} OR {owner_condition})"
	else:
		combined_condition = owner_condition

	return combined_condition


def event_has_permission(doc, user):
	"""Row-level permission check used by Frappe.

	Current behaviour (unchanged here):
	- New docs are allowed.
	- Public events are visible to everyone.
	- Private events:
	  - visible to owner
	  - visible to explicit participants
	  - visible for Course events to student group instructors/students

	We will NOT put the new audience logic here yet to avoid per-row DB hits.
	Instead, audience-based visibility is handled in get_school_events_for_user().
	"""
	if doc.is_new():
		return True

	if doc.event_type == "Public":
		return True

	if doc.event_type == "Private" and (
		doc.owner == user or user in [d.participant for d in doc.participants]
	):
		return True

	if doc.event_category == "Course" and doc.reference_name:
		# Special case: course events visible to instructors/students
		try:
			stu_group = frappe.get_doc("Student Group", doc.reference_name)
		except frappe.DoesNotExistError:
			return False

		if user in [ins.user_id for ins in getattr(stu_group, "instructors", [])]:
			return True

		if user in [stu.user_id for stu in getattr(stu_group, "students", [])]:
			return True

	return False


# ─────────────────────────────────────────────────────────────
# Audience matching (first pass: role-based only)
# ─────────────────────────────────────────────────────────────


def _audience_row_matches_user(audience_row, user_roles):
	"""Return True if this single School Event Audience row matches the user.

	First-pass implementation:
	- Handles only the broad, role-based types:
	  * Whole School Community      → everyone (we rely on school filters elsewhere)
	  * All Students                → user has "Student" role
	  * All Guardians               → user has "Guardian" role
	  * All Employees               → user has one of Employee/Academic Staff/Instructor roles

	- Ignores Student Group / Team / Program / Cohort for now (returns False).
	- Doesn't yet enforce the "only Academic Admin can use broad audiences" rule;
	  that will be validated on save in a later step.

	This is intentionally conservative and easy to extend later.
	"""
	a_type = audience_row.get("audience_type")

	# No type → no match
	if not a_type:
		return False

	# For now, treat whole school community as "any authenticated user".
	if a_type == "Whole School Community":
		return True

	if a_type == "All Students":
		return "Student" in user_roles

	if a_type == "All Guardians":
		return "Guardian" in user_roles

	if a_type == "All Employees":
		employee_roles = {"Employee", "Academic Staff", "Instructor"}
		return bool(employee_roles.intersection(user_roles))

	# Cohort / Program / Program Offering / Students in Student Group / Employees in Team / Custom Users
	# will be wired in a later step once we hook into your membership model.
	return False


# ─────────────────────────────────────────────────────────────
# Centralized fetch API (Step 2/3 of refactor)
# ─────────────────────────────────────────────────────────────


def get_school_events_for_user(start, end, user=None, filters=None):
	"""Core API for fetching School Events for a given user.

	Current behaviour:
	- Time-window filter on starts_on/ends_on (converted from UTC to site timezone).
	- Optional filters from Report View helpers.
	- Row-level permission enforced via has_permission / event_has_permission.
	- NEW: basic audience-based visibility using School Event Audience for broad types.

	We deliberately never make events LESS visible than before:
	- An event is returned if:
	  * it matches an audience row for this user (broad types only for now), OR
	  * it passes the existing has_permission() check.
	"""
	if not user:
		user = frappe.session.user

	site_tz = get_system_timezone() or "UTC"

	if isinstance(filters, string_types):
		filters = json.loads(filters)

	filters_condition = get_filters_cond("School Event", filters, [])

	start_local = "CONVERT_TZ(`tabSchool Event`.starts_on, 'UTC', %(site_tz)s)"
	end_local = "CONVERT_TZ(`tabSchool Event`.ends_on, 'UTC', %(site_tz)s)"

	events = frappe.db.sql(
		f"""
		SELECT `tabSchool Event`.*
		FROM `tabSchool Event`
		LEFT JOIN `tabSchool Event Participant`
			ON `tabSchool Event`.name = `tabSchool Event Participant`.parent
		WHERE
			({start_local} BETWEEN %(start)s AND %(end)s)
			OR ({end_local} BETWEEN %(start)s AND %(end)s)
			{filters_condition}
		ORDER BY `tabSchool Event`.starts_on
		""",
		{"start": start, "end": end, "site_tz": site_tz},
		as_dict=True,
	)

	if not events:
		return []

	event_names = [e["name"] for e in events]

	# Pull all audience rows for these events in one shot, then index by parent.
	raw_audience = frappe.get_all(
		"School Event Audience",
		filters={"parent": ["in", event_names]},
		fields=[
			"parent",
			"audience_type",
			"student_group",
			"team",
			"cohort",
			"program",
			"program_offering",
			"include_guardians",
			"include_students",
		],
	)

	audience_by_event = defaultdict(list)
	for row in raw_audience:
		audience_by_event[row.parent].append(row)

	user_roles = set(frappe.get_roles(user))

	allowed_events = []

	for event in events:
		event_name = event["name"]
		audience_rows = audience_by_event.get(event_name, [])

		audience_match = False
		for a_row in audience_rows:
			if _audience_row_matches_user(a_row, user_roles):
				audience_match = True
				break

		if audience_match:
			# New path: user is in the event's broad audience → allow
			allowed_events.append(event)
			continue

		# Fallback to existing permission logic (owner, participants, course special-case)
		if frappe.get_doc("School Event", event_name).has_permission(user=user):
			allowed_events.append(event)

	return allowed_events


@frappe.whitelist()
def get_school_events(start, end, user=None, filters=None):
	"""Backward-compatible wrapper used by Desk/portal calendars.

	All new logic should live inside get_school_events_for_user().
	"""
	return get_school_events_for_user(start=start, end=end, user=user, filters=filters)
