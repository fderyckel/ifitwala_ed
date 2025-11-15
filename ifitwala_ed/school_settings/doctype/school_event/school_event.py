# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/school_event/school_event.py

import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.desk.reportview import get_filters_cond
from frappe.model.document import Document
from frappe.utils import (
	get_datetime,
	now_datetime,
	get_system_timezone,
)


# ============================================================================
#  SCHOOL EVENT DOCUMENT
# ============================================================================

class SchoolEvent(Document):

	def validate(self):
		self.validate_time()
		self.validate_audience_permissions()

	def on_update(self):
		self.validate_date()

	def validate_date(self):
		"""Non-'Other' categories must be in the future."""
		if (
			self.event_category != "Other"
			and get_datetime(self.starts_on) < get_datetime(now_datetime())
		):
			frappe.throw(
				_(
					f"The date {self.starts_on} of the event must be in the future. "
					"Please adjust the date."
				)
			)

	def validate_time(self):
		"""Start must be <= end."""
		if get_datetime(self.starts_on) > get_datetime(self.ends_on):
			frappe.throw(
				_(
					f"Start time {self.starts_on} must be earlier than end time {self.ends_on}. "
					"Please adjust the time."
				)
			)

	def validate_audience_permissions(self):
		"""
		Only privileged roles may use broad audience types:

		- Whole School Community
		- All Students
		- All Guardians
		- All Employees

		Allowed roles:
		- System Manager
		- Academic Admin
		- Organization IT

		All other users must use Student Group / Team / Program audiences.
		"""

		# Bypass for scripted inserts
		if getattr(self, "flags", None) and getattr(self.flags, "ignore_audience_permissions", False):
			return

		user = frappe.session.user

		# Administrator = allowed
		if user in ("Administrator", "Guest"):
			return

		if not getattr(self, "audience", None):
			return

		broad_types = {
			"Whole School Community",
			"All Students",
			"All Guardians",
			"All Employees",
		}

		priv_roles = {"System Manager", "Academic Admin", "Organization IT"}

		user_roles = set(frappe.get_roles(user))

		# Privileged roles may use anything
		if user_roles.intersection(priv_roles):
			return

		# Otherwise reject broad types
		for row in self.audience:
			if row.audience_type in broad_types:
				frappe.throw(
					_(
						f"You are not permitted to use the audience type '{row.audience_type}'. "
						"Choose a specific Student Group / Team, or ask an Academic Admin."
					),
					title=_("Not permitted"),
				)


# ============================================================================
#  PERMISSION QUERY (TEMPORARY, WILL BE REMOVED LATER)
# ============================================================================

def get_permission_query_conditions(user):
	"""
	Legacy PQC: Only enforces owner + explicit participant.
	Will be replaced once full audience logic is implemented.
	"""
	if not user:
		user = frappe.session.user

	participant = frappe.qb.DocType("School Event Participant")
	event = frappe.qb.DocType("School Event")

	result = (
		frappe.qb.from_(participant)
		.join(event)
		.on(participant.parent == event.name)
		.where(participant.participant == user)
		.select(event.name)
	).run()

	names = [r[0] for r in result]

	owner_cond = f"owner = {frappe.db.escape(user)}"

	if names:
		name_cond = ", ".join([frappe.db.escape(n) for n in names])
		return f"(name IN ({name_cond}) OR {owner_cond})"

	return owner_cond


# ============================================================================
#  ROW-LEVEL PERMISSIONS (TEMPORARY: WILL CHANGE WITH FULL AUDIENCE LOGIC)
# ============================================================================

def event_has_permission(doc, user):
	"""
	Backwards-compatible fallback.
	Will eventually be replaced by pure audience-based logic.

	Current:
	- New docs allowed
	- Public events allowed
	- Private: owner or explicit participant
	- Course events: instructor/student visibility (temporary)
	"""
	if doc.is_new():
		return True

	if doc.event_type == "Public":
		return True

	if doc.event_type == "Private" and (
		doc.owner == user or user in [d.participant for d in doc.participants]
	):
		return True

	# TEMPORARY: Course-based visibility
	if doc.event_category == "Course" and doc.reference_name:
		try:
			stg = frappe.get_doc("Student Group", doc.reference_name)
		except frappe.DoesNotExistError:
			return False

		instructors = [ins.user_id for ins in getattr(stg, "instructors", [])]
		students = [stu.user_id for stu in getattr(stg, "students", [])]

		if user in instructors or user in students:
			return True

	return False


# ============================================================================
#  AUDIENCE MATCHING (CURRENT: BROAD TYPES ONLY)
# ============================================================================

def _audience_row_matches_user(a_row, user_roles):
	"""
	First pass: broad types only.
	Later we extend to teams, student groups, programs, cohorts.
	"""

	a_type = a_row.get("audience_type")
	if not a_type:
		return False

	if a_type == "Whole School Community":
		return True

	if a_type == "All Students":
		return "Student" in user_roles

	if a_type == "All Guardians":
		return "Guardian" in user_roles

	if a_type == "All Employees":
		return bool({"Employee", "Academic Staff", "Instructor"}.intersection(user_roles))

	# Student Group / Team / Program / Cohort → handled in next steps
	return False


# ============================================================================
#  CENTRALIZED EVENT FETCH API
# ============================================================================

def get_school_events_for_user(start, end, user=None, filters=None):
	"""
	Main API used by Desk + Portal calendars.

	Event is visible to user if:
	- audience rule matches (broad types only so far), OR
	- permission fallback (owner, participant, course)
	"""

	if not user:
		user = frappe.session.user

	site_tz = get_system_timezone() or "UTC"

	# Normalize filters
	if isinstance(filters, str):
		filters = json.loads(filters)

	filter_cond = get_filters_cond("School Event", filters, [])

	start_local = f"CONVERT_TZ(`tabSchool Event`.starts_on, 'UTC', %(site_tz)s)"
	end_local = f"CONVERT_TZ(`tabSchool Event`.ends_on, 'UTC', %(site_tz)s)"

	# Main time-window query
	events = frappe.db.sql(
		f"""
		SELECT `tabSchool Event`.*
		FROM `tabSchool Event`
		LEFT JOIN `tabSchool Event Participant`
			ON `tabSchool Event`.name = `tabSchool Event Participant`.parent
		WHERE
			(
				({start_local} BETWEEN %(start)s AND %(end)s)
				OR ({end_local} BETWEEN %(start)s AND %(end)s)
			)
			{filter_cond}
		ORDER BY `tabSchool Event`.starts_on
		""",
		{"start": start, "end": end, "site_tz": site_tz},
		as_dict=True,
	)

	if not events:
		return []

	event_names = [e["name"] for e in events]

	# Pull audience rows in one batch
	audience_rows = frappe.get_all(
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

	by_event = defaultdict(list)
	for row in audience_rows:
		by_event[row.parent].append(row)

	user_roles = set(frappe.get_roles(user))
	allowed = []

	for ev in events:
		name = ev["name"]
		a_rows = by_event.get(name, [])

		# First check audience match
		if any(_audience_row_matches_user(r, user_roles) for r in a_rows):
			allowed.append(ev)
			continue

		# Then fallback to old permission logic
		if frappe.get_doc("School Event", name).has_permission(user=user):
			allowed.append(ev)

	return allowed


# ============================================================================
#  PUBLIC WRAPPER
# ============================================================================

@frappe.whitelist()
def get_school_events(start, end, user=None, filters=None):
	return get_school_events_for_user(start=start, end=end, user=user, filters=filters)
