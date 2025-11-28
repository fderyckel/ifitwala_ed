# ifitwala_ed/api/student_attendance.py

import frappe
from frappe import _
from frappe.utils.caching import redis_cache
from frappe.utils.nestedset import get_descendants_of

from ifitwala_ed.api.student_groups import (
	TRIAGE_ROLES,
	_user_roles,
	_instructor_group_names,
)
from ifitwala_ed.utilities.school_tree import (
	get_descendant_schools,
	get_user_default_school,
)

PORTAL_GROUP_FIELDS = [
	"name",
	"student_group_name",
	"program",
	"school",
	"course",
	"cohort",
	"academic_year",
	"status",
]


@frappe.whitelist()
def fetch_portal_student_groups(school: str | None = None, program: str | None = None):
	"""
	Return active student groups visible to the logged-in staff member.
	* Academic Admin / Counselor / Instructor / Admin roles see all active groups.
	* Other instructors only see the groups they are assigned to through Student Group Instructor.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to view student groups."))

	filters: dict[str, object] = {"status": "Active"}

	school_scope = _expand_school_scope(school)
	if school_scope:
		filters["school"] = ["in", school_scope]

	program_scope = _expand_program_scope(program)
	if program_scope:
		filters["program"] = ["in", program_scope]

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


def _expand_school_scope(school: str | None) -> list[str] | None:
	"""
	Return an allowed list of schools for filtering:
	- Always restrict to the current user's default school + descendants.
	- If an explicit school is requested, only allow it when it sits inside that scope.
	"""
	default_school = get_user_default_school()
	allowed_scope = get_descendant_schools(default_school) if default_school else []

	# No explicit selection → use allowed scope (or None to keep old behaviour)
	if not school:
		return allowed_scope or None

	try:
		requested_scope = get_descendant_schools(school)
	except frappe.DoesNotExistError:
		requested_scope = [school]

	# If we know the allowed scope, clamp to it; otherwise return requested scope as-is
	if allowed_scope:
		intersection = [s for s in requested_scope if s in allowed_scope]
		return intersection or allowed_scope

	return requested_scope


def _expand_program_scope(program: str | None) -> list[str] | None:
	if not program:
		return None
	descendants = get_descendants_of("Program", program) or []
	return [program, *descendants]


# ---------------------------------------------------------------------------
# Filter metadata helpers
# ---------------------------------------------------------------------------

@frappe.whitelist()
def fetch_school_filter_context():
	"""
	Return the current user's default school and the schools they can filter by.
	Default list = default school + descendants; if no default, show all schools.
	"""
	default_school = get_user_default_school()
	school_names = []

	fields = ["name", "school_name"]
	if default_school:
		school_names = get_descendant_schools(default_school)

	if school_names:
		schools = frappe.get_all("School", fields=fields, filters={"name": ["in", school_names]}, order_by="lft asc")
	else:
		schools = frappe.get_all("School", fields=fields, order_by="lft asc")

	return {
		"default_school": default_school,
		"schools": schools,
	}


@frappe.whitelist()
def fetch_active_programs():
	"""Return all non-archived programs for the Program dropdown."""
	return frappe.get_all(
		"Program",
		fields=["name", "program_name", "parent_program", "lft", "rgt", "is_group"],
		filters={"archive": 0},
		order_by="lft asc",
	)


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
