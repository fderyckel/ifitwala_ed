import frappe
from frappe import _

from ifitwala_ed.api.student_groups import (
	TRIAGE_ROLES,
	_user_roles,
	_instructor_group_names,
)

PORTAL_GROUP_FIELDS = [
	"name",
	"student_group_name",
	"program",
	"course",
	"cohort",
	"academic_year",
	"status",
]


@frappe.whitelist()
def fetch_portal_student_groups():
	"""
	Return active student groups visible to the logged-in staff member.
	* Academic Admin / Counselor / Instructor / Admin roles see all active groups.
	* Other instructors only see the groups they are assigned to through Student Group Instructor.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to view student groups."))

	filters: dict[str, object] = {"status": "Active"}
	roles = _user_roles(user)

	if roles & TRIAGE_ROLES:
		return _query_groups(filters)

	# Restrict to instructor-linked groups
	group_names = _instructor_group_names(user)
	if not group_names:
		return []

	filters["name"] = ["in", list(group_names)]
	return _query_groups(filters)


def _query_groups(filters: dict[str, object]):
	return frappe.get_all(
		"Student Group",
		fields=PORTAL_GROUP_FIELDS,
		filters=filters,
		order_by="student_group_name asc",
	)


import frappe
from frappe.utils.caching import redis_cache

# MySQL DAYOFWEEK(): Sun=1 ... Sat=7  → JS getDay(): Sun=0 ... Sat=6
MYSQL_TO_JS = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}
DAY_LABEL_TO_JS = {
	"Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3,
	"Thursday": 4, "Friday": 5, "Saturday": 6
}

@frappe.whitelist()
@redis_cache(ttl=86400)
def get_weekend_days(student_group: str) -> list[int]:
	"""Return weekend weekday numbers (JS 0–6) for the group's calendar.
	Tries Holidays.weekly_off=1 first; falls back to School Calendar.weekly_off.
	Default: [6, 0] (Sat, Sun)
	"""
	if not student_group:
		return [6, 0]

	# 1) Resolve School Schedule → School Calendar
	school_schedule = frappe.db.get_value("Student Group", student_group, "school_schedule")
	if not school_schedule:
		return [6, 0]

	calendar = frappe.db.get_value("School Schedule", school_schedule, "school_calendar")
	if not calendar:
		return [6, 0]

	# 2) Distinct weekday(s) from weekly offs recorded in Holidays child table
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT DAYOFWEEK(holiday_date) AS dow
		FROM `tabSchool Calendar Holidays`
		WHERE parent = %s AND weekly_off = 1
		""",
		(calendar,),
		as_dict=True,
	)
	js_days = sorted({MYSQL_TO_JS.get(r["dow"]) for r in rows if MYSQL_TO_JS.get(r["dow"]) is not None})

	# 3) Fallback: single-select 'weekly_off' on parent (in case holidays not generated yet)
	if not js_days:
		weekday_label = frappe.db.get_value("School Calendar", calendar, "weekly_off")
		if weekday_label:
			js = DAY_LABEL_TO_JS.get(weekday_label)
			if js is not None:
				js_days = [js]

	# 4) Final fallback: Sat–Sun
	if not js_days:
		js_days = [6, 0]

	return js_days
