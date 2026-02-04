# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/team/team.py

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_months,
	cint,
	format_date,
	get_link_to_form,
	getdate,
	nowdate,
	time_diff_in_seconds,
)
from ifitwala_ed.utilities.school_tree import get_ancestor_schools

class Team(Document):

	def validate(self):
		self.ensure_minimum_members()
		self.check_parent_team_loop()
		self.ensure_unique_members()
		# other validations as needed

	def ensure_minimum_members(self):
		"""
		Require at least 2 members with a valid Employee link.
		"""
		members = [d for d in (self.members or []) if d.employee]
		if len(members) < 2:
			frappe.throw(_("A team must have at least 2 employees configured as members."))

	def check_parent_team_loop(self):
		if self.parent_team:
			parent = self.parent_team
			seen = set()
			while parent:
				if parent == self.name:
					frappe.throw(_("Circular parent_team reference detected."))
				if parent in seen:
					frappe.throw(_("Circular parent_team chain detected."))
				seen.add(parent)
				parent = frappe.db.get_value("Team", parent, "parent_team")

	def ensure_unique_members(self):
		seen = set()
		duplicates = []
		for d in self.members or []:
			member = d.employee or d.member
			if not member:
				continue
			if member in seen:
				duplicates.append(d.member_name or d.employee or d.member)
			else:
				seen.add(member)

		if duplicates:
			names = ", ".join(frappe.bold(name) for name in duplicates)
			frappe.throw(
				_("The following members are already part of this team: {0}. Remove duplicates before saving.").format(names)
			)


@frappe.whitelist()
def get_eligible_users(school=None, organization=None):
	"""Return enabled users with linked Employee records scoped by school/org."""
	conditions = ["u.enabled = 1", "ifnull(e.employment_status, 'Active') = 'Active'"]
	params = {}
	if school:
		conditions.append("e.school = %(school)s")
		params["school"] = school
	if organization:
		conditions.append("e.organization = %(organization)s")
		params["organization"] = organization

	where_clause = " AND ".join(conditions) if conditions else "1=1"
	sql = f"""
		SELECT
			u.name as value,
			coalesce(e.employee_full_name, u.full_name, u.name) as label,
			e.name as employee,
			e.employee_full_name as employee_name
		FROM `tabUser` u
		JOIN `tabEmployee` e ON e.user_id = u.name
		WHERE {where_clause}
		ORDER BY coalesce(e.employee_full_name, u.full_name, u.name)
	"""
	return frappe.db.sql(sql, params, as_dict=1)


MAX_MEETING_OCCURRENCES = 40
RECURRENCE_PRESETS = {
	"weekly": {"unit": "week", "interval": 1, "label": _("Weekly"), "series_unit": "Weekly"},
	"biweekly": {"unit": "week", "interval": 2, "label": _("Every 2 weeks"), "series_unit": "Weekly"},
	"three_weeks": {"unit": "week", "interval": 3, "label": _("Every 3 weeks"), "series_unit": "Weekly"},
	"monthly": {"unit": "month", "interval": 1, "label": _("Monthly"), "series_unit": "Monthly"},
}


@frappe.whitelist()
def get_schedulable_academic_years(team):
	"""Return academic years tied to the team's school whose end date hasn't passed."""
	team_row = frappe.db.get_value("Team", team, ["school"], as_dict=True)
	if not team_row:
		frappe.throw(_("Team {0} was not found.").format(frappe.bold(team)))

	candidate_schools = []
	if team_row.school:
		candidate_schools.append(team_row.school)
		for ancestor in get_ancestor_schools(team_row.school):
			if ancestor not in candidate_schools:
				candidate_schools.append(ancestor)

	def _fetch_for_school(school_name):
		filters = {"year_end_date": (">=", nowdate())}
		if school_name:
			filters["school"] = school_name
		return frappe.get_all(
			"Academic Year",
			filters=filters,
			fields=["name", "academic_year_name", "year_start_date", "year_end_date", "school"],
			order_by="year_start_date asc",
		)

	selected_school = None
	years = []
	for school_name in candidate_schools or [None]:
		years = _fetch_for_school(school_name)
		if years:
			selected_school = school_name
			break

	if not years:
		return []

	school_names = {row.school for row in years if row.school}
	if selected_school:
		school_names.add(selected_school)
	school_labels = {}
	if school_names:
		for row in frappe.get_all(
			"School", filters={"name": ["in", list(school_names)]}, fields=["name", "school_name"], as_list=False
		):
			school_labels[row["name"]] = row["school_name"]

	return [
		{
			"name": ay.name,
			"label": ay.academic_year_name or ay.name,
			"year_start_date": ay.year_start_date,
			"year_end_date": ay.year_end_date,
			"school": ay.school,
			"school_name": school_labels.get(ay.school),
			"source_school": selected_school or ay.school,
			"source_school_name": school_labels.get(selected_school) if selected_school else school_labels.get(ay.school),
		}
		for ay in years
	]


@frappe.whitelist()
def schedule_recurring_meetings(
	team,
	academic_year,
	start_date,
	start_time,
	end_time,
	repeat_option,
	occurrences,
	meeting_title=None,
	location=None,
	virtual_meeting_link=None,
	meeting_category=None,
):
	"""Create a Meeting Series and schedule Meeting documents for the given Team."""
	team_doc = frappe.get_doc("Team", team)
	if not team_doc.has_permission("write"):
		frappe.throw(_("You do not have permission to schedule meetings for this team."), frappe.PermissionError)

	if not start_date or not start_time or not end_time:
		frappe.throw(_("Start Date, Start Time, and End Time are required."))

	if not repeat_option or repeat_option not in RECURRENCE_PRESETS:
		frappe.throw(_("Unsupported repeat option: {0}").format(frappe.bold(repeat_option)))

	occurrences = cint(occurrences)
	if occurrences <= 0:
		frappe.throw(_("Please request at least one occurrence."))
	occurrences = min(occurrences, MAX_MEETING_OCCURRENCES)

	ay_row = frappe.db.get_value(
		"Academic Year", academic_year, ["name", "year_start_date", "year_end_date"], as_dict=True
	)
	if not ay_row or not ay_row.year_start_date or not ay_row.year_end_date:
		frappe.throw(_("Academic Year {0} must have start and end dates.").format(frappe.bold(academic_year)))

	ay_start = getdate(ay_row.year_start_date)
	ay_end = getdate(ay_row.year_end_date)

	start_date_value = getdate(start_date)
	if start_date_value < ay_start or start_date_value > ay_end:
		frappe.throw(
			_("Start Date must fall within the Academic Year window ({0} → {1}).").format(
				format_date(ay_start), format_date(ay_end)
			)
		)

	if time_diff_in_seconds(end_time, start_time) <= 0:
		frappe.throw(_("End Time must be later than Start Time."))

	raw_members = frappe.get_all(
		"Team Member",
		filters={"parent": team_doc.name},
		fields=["employee", "member", "member_name", "role_in_team"],
		order_by="idx asc",
	)

	members = [row for row in raw_members if row.employee]
	if not members:
		frappe.throw(_("Add at least one employee to the team before scheduling meetings."))

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

	def resolve_employee_name(employee: str | None, fallback: str | None) -> str | None:
		if fallback:
			return fallback
		if not employee:
			return fallback
		if employee in name_cache:
			return name_cache[employee]
		emp_name = frappe.db.get_value("Employee", employee, "employee_name")
		name_cache[employee] = emp_name
		return emp_name

	preset = RECURRENCE_PRESETS[repeat_option]
	occurrence_dates = _generate_occurrence_dates(start_date_value, preset, occurrences, ay_end)
	if not occurrence_dates:
		frappe.throw(_("No meetings can be scheduled before the Academic Year ends."))

	base_title = meeting_title or team_doc.team_name or team_doc.name
	series_title = _("{0} [{1}]").format(base_title, ay_row.name)

	series_doc = frappe.get_doc(
		{
			"doctype": "Meeting Series",
			"series_title": series_title,
			"team": team_doc.name,
			"academic_year": ay_row.name,
			"meeting_title": base_title,
			"meeting_category": meeting_category,
			"start_date": start_date_value,
			"start_time": start_time,
			"end_time": end_time,
			"location": location,
			"virtual_meeting_link": virtual_meeting_link,
			"repeat_unit": preset["series_unit"],
			"repeat_interval": preset["interval"],
			"occurrences_requested": occurrences,
			"series_end_date": occurrence_dates[-1],
		}
	)
	series_doc.insert(ignore_permissions=True)

	created = []
	last_success_date = None
	failures = []
	for idx, meeting_date in enumerate(occurrence_dates, start=1):
		meeting = frappe.new_doc("Meeting")
		meeting.meeting_name = f"{base_title} | {format_date(meeting_date)}"
		meeting.team = team_doc.name
		meeting.date = meeting_date
		meeting.start_time = start_time
		meeting.end_time = end_time
		meeting.location = location
		meeting.virtual_meeting_link = virtual_meeting_link
		meeting.meeting_category = meeting_category
		meeting.status = "Scheduled"
		meeting.meeting_series = series_doc.name
		meeting.series_occurrence_no = idx

		for member in members:
			meeting.append(
				"participants",
				{
					"employee": member.employee,
					"participant": resolve_user(member.employee, member.member),
					"participant_name": resolve_employee_name(member.employee, member.member_name),
					"role_in_meeting": member.role_in_team or "Participant",
					"attendance_status": "Absent",
				},
			)

		try:
			meeting.insert(ignore_permissions=True)
			last_success_date = meeting.date
			created.append(
				{
					"name": meeting.name,
					"date": format_date(meeting.date),
					"start_time": meeting.start_time,
					"end_time": meeting.end_time,
				}
			)
		except Exception as err:
			frappe.log_error(
				frappe.get_traceback(),
				_("Failed to create meeting on {0}").format(format_date(meeting_date)),
			)
			failures.append({"date": format_date(meeting_date), "error": str(err)})

	series_doc.db_set(
		{
			"occurrences_created": len(created),
			"last_occurrence_date": last_success_date,
		}
	)

	if created:
		team_doc.add_comment(
			"Info",
			_("Scheduled {0} meeting(s) via {1}.").format(
				len(created), get_link_to_form("Meeting Series", series_doc.name)
			),
		)

	return {
		"series": series_doc.name,
		"series_title": series_doc.series_title,
		"created": created,
		"failed": failures,
		"requested": occurrences,
		"planned_dates": [format_date(d) for d in occurrence_dates],
	}


def _generate_occurrence_dates(start_date, preset, limit, ay_end):
	dates = []
	current = start_date
	for _ in range(limit):
		if current > ay_end:
			break
		dates.append(current)
		if preset["unit"] == "week":
			current = current + timedelta(days=7 * preset["interval"])
		else:
			current = getdate(add_months(current, preset["interval"]))
	return dates
