# ifitwala_ed/api/student_attendance.py

import frappe
from frappe import _
from frappe.utils.caching import redis_cache
from frappe.utils.nestedset import get_descendants_of

from ifitwala_ed.api.student_groups import _user_roles, _instructor_group_names
from ifitwala_ed.utilities.school_tree import get_user_default_school,_is_adminish
from ifitwala_ed.schedule.schedule_utils import get_weekend_days_for_calendar


# Roles that can see all groups in their allowed school scope
PORTAL_FULL_ACCESS_ROLES = {
	"Administrator",
	"System Manager",
	"Academic Admin",
	"Academic Assistant",
}

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

	- Portal full-access roles (Admin, System Manager, Academic Admin, Academic Assistant)
	  see all active groups within their allowed school scope and can use filters.
	- Everyone else (instructors, academic staff, counselors, etc.) only sees
	  the groups they are assigned to via Student Group Instructor, still
	  clamped to their default school + descendants.
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

	# 1. School Scope Check
	# If the user is restricted to a school, they can only see groups in that school (or descendants)
	allowed_schools = _get_allowed_school_scope(user)
	if allowed_schools is not None:
		# If allowed_schools is a list, we filter by it.
		# If it's empty, it means they have no access to any school? Or maybe they are not linked to a school.
		# If they are not linked to a school, do we show all?
		# The requirement says: "The employee should only be able to see his/her own school... or once of its descendants."
		if not allowed_schools:
			# No linked school → no access unless they are “adminish”
			if not (roles & {"System Manager", "Administrator", "Academic Admin", "Academic Assistant"}):
				return []
		else:
			filters["school"] = ["in", allowed_schools]

	# 2. Instructor Group Check
	# If they are NOT in a full-access role, restrict to their own groups.
	if not (roles & PORTAL_FULL_ACCESS_ROLES):
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


def _get_allowed_school_scope(user: str) -> list[str] | None:
	"""
	Return the list of schools the user is allowed to access.
	- If Admin/System Manager: None (all schools).
	- If Employee with school: [school, *descendants].
	- If no school linked: [] (no access).
	"""
	if _is_adminish(user):
		return None

	default_school = get_user_default_school()
	if default_school:
		# Use db.get_value to avoid permission issues
		values = frappe.db.get_value("School", default_school, ["lft", "rgt"], as_dict=True)
		if values:
			return [
				s.name
				for s in frappe.get_all(
					"School",
					filters={"lft": (">=", values.lft), "rgt": ("<=", values.rgt)},
					fields=["name"]
				)
			]
	return []


def _expand_school_scope(school: str | None) -> list[str] | None:
	"""
	Return an allowed list of schools for filtering:
	- Always restrict to the current user's default school + descendants.
	- If an explicit school is requested, only allow it when it sits inside that scope.
	"""
	user = frappe.session.user
	allowed_scope = _get_allowed_school_scope(user)

	# If allowed_scope is None, it means all schools are allowed (Admin)
	if allowed_scope is None:
		if not school:
			return None
		# If specific school requested, return it + descendants
		try:
			# Use db.get_value to avoid permission issues
			values = frappe.db.get_value("School", school, ["lft", "rgt"], as_dict=True)
			if values:
				return [
					s.name
					for s in frappe.get_all(
						"School",
						filters={"lft": (">=", values.lft), "rgt": ("<=", values.rgt)},
						fields=["name"]
					)
				]
			return [school]
		except Exception:
			return [school]

	# If allowed_scope is a list (restricted)
	if not school:
		return allowed_scope

	# If specific school requested, check if it's in allowed_scope
	# And return intersection of requested descendants AND allowed scope
	try:
		# Use db.get_value to avoid permission issues
		values = frappe.db.get_value("School", school, ["lft", "rgt"], as_dict=True)
		requested_scope = []
		if values:
			requested_scope = [
				s.name
				for s in frappe.get_all(
					"School",
					filters={"lft": (">=", values.lft), "rgt": ("<=", values.rgt)},
					fields=["name"]
				)
			]
		else:
			requested_scope = [school]
	except Exception:
		requested_scope = [school]

	intersection = [s for s in requested_scope if s in allowed_scope]
	return intersection or []


def _expand_program_scope(program: str | None) -> list[str] | None:
	if not program:
		return None
	descendants = get_descendants_of("Program", program) or []
	return [program, *descendants]


# ---------------------------------------------------------------------------
# Filter metadata helpers
# ---------------------------------------------------------------------------

# ifitwala_ed/api/student_attendance.py

@frappe.whitelist()
def fetch_school_filter_context():
    """
    Return the current user's default school and the schools they can filter by.

    - If the user has a default school: return that school + all its descendants
      (same nested-set subtree).
    - If no default school: return all schools.
    """
    default_school = get_user_default_school()
    fields = ["name", "school_name"]

    schools = []

    if default_school:
        # Use nested set span of the default school to include it + all descendants
        values = frappe.db.get_value("School", default_school, ["lft", "rgt"], as_dict=True)
        if values:
            schools = frappe.get_all(
                "School",
                fields=fields,
                filters={"lft": (">=", values.lft), "rgt": ("<=", values.rgt)},
                order_by="lft asc",
            )

    # Fallback: no default or no subtree → show all schools (admin, misconfigured users)
    if not schools:
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


@frappe.whitelist()
@redis_cache(ttl=86400)
def get_weekend_days(student_group: str | None = None) -> list[int]:
	"""
	Return weekend weekday numbers (JS 0–6) for the group's calendar.

	This is a thin wrapper around schedule_utils.get_weekend_days_for_calendar,
	so all School Calendar weekend logic lives in one place.
	"""
	# No group specified → use global calendar defaults
	if not student_group:
		return get_weekend_days_for_calendar(None)

	# Resolve School Schedule → School Calendar
	schedule_name = frappe.db.get_value("Student Group", student_group, "school_schedule")
	if not schedule_name:
		return get_weekend_days_for_calendar(None)

	calendar_name = frappe.db.get_value("School Schedule", schedule_name, "school_calendar")
	return get_weekend_days_for_calendar(calendar_name)
