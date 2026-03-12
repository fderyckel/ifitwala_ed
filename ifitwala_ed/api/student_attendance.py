# ifitwala_ed/api/student_attendance.py

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import getdate, nowdate
from frappe.utils.caching import redis_cache
from frappe.utils.nestedset import get_descendants_of

from ifitwala_ed.api.student_groups import _instructor_group_names, _user_roles
from ifitwala_ed.schedule.attendance_utils import (
    attendance_recorded_dates,
    fetch_blocks_for_day,
    fetch_existing_attendance,
    fetch_students,
    get_meeting_dates,
    list_attendance_codes,
    previous_status_map,
)
from ifitwala_ed.schedule.schedule_utils import get_weekend_days_for_calendar
from ifitwala_ed.utilities.school_tree import _is_adminish, get_school_lineage, get_user_default_school

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

ATTENDANCE_CONTEXT_TTL = 300


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
                    "School", filters={"lft": (">=", values.lft), "rgt": ("<=", values.rgt)}, fields=["name"]
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
                        "School", filters={"lft": (">=", values.lft), "rgt": ("<=", values.rgt)}, fields=["name"]
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
                    "School", filters={"lft": (">=", values.lft), "rgt": ("<=", values.rgt)}, fields=["name"]
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
def fetch_attendance_ledger_context(
    school: str | None = None,
    program: str | None = None,
    academic_year: str | None = None,
    term: str | None = None,
    student_group: str | None = None,
):
    requested = {
        "school": _clean_value(school),
        "program": _clean_value(program),
        "academic_year": _clean_value(academic_year),
        "term": _clean_value(term),
        "student_group": _clean_value(student_group),
    }

    def _build():
        school_context = fetch_school_filter_context()
        schools = school_context.get("schools") or []
        selected_school = _pick_named_value(
            requested["school"],
            schools,
            fallback=school_context.get("default_school"),
            allow_first=True,
        )
        programs = fetch_active_programs()
        selected_program = _pick_named_value(requested["program"], programs)

        groups = fetch_portal_student_groups(
            school=selected_school,
            program=selected_program,
        )
        academic_years = fetch_portal_academic_years(school=selected_school)
        if not academic_years:
            academic_years = _derive_academic_year_rows_from_groups(groups)

        selected_academic_year = _pick_named_value(
            requested["academic_year"],
            academic_years,
            fallback=academic_years[0]["name"] if academic_years else None,
            allow_first=True,
        )
        terms = fetch_portal_terms(
            academic_year=selected_academic_year,
            school=selected_school,
        )
        selected_term = _pick_named_value(requested["term"], terms)
        selected_group = _pick_named_value(requested["student_group"], groups)

        return {
            "schools": schools,
            "default_school": selected_school,
            "programs": programs,
            "default_program": selected_program,
            "academic_years": academic_years,
            "default_academic_year": selected_academic_year,
            "terms": terms,
            "default_term": selected_term,
            "student_groups": groups,
            "default_student_group": selected_group,
        }

    return _cached_context(
        "attendance_ledger_context",
        requested,
        _build,
    )


@frappe.whitelist()
def fetch_attendance_tool_bootstrap(
    school: str | None = None,
    program: str | None = None,
    student_group: str | None = None,
):
    requested = {
        "school": _clean_value(school),
        "program": _clean_value(program),
        "student_group": _clean_value(student_group),
    }

    def _build():
        school_context = fetch_school_filter_context()
        schools = school_context.get("schools") or []
        selected_school = _pick_named_value(
            requested["school"],
            schools,
            fallback=school_context.get("default_school"),
            allow_first=True,
        )
        programs = fetch_active_programs()
        selected_program = _pick_named_value(requested["program"], programs)
        groups = fetch_portal_student_groups(
            school=selected_school,
            program=selected_program,
        )
        attendance_codes = list_attendance_codes()
        selected_group = _pick_named_value(requested["student_group"], groups)
        if not selected_group and len(groups) == 1:
            selected_group = groups[0]["name"]

        return {
            "schools": schools,
            "default_school": selected_school,
            "programs": programs,
            "default_program": selected_program,
            "student_groups": groups,
            "default_student_group": selected_group,
            "attendance_codes": attendance_codes,
            "default_code": attendance_codes[0]["name"] if attendance_codes else None,
        }

    return _cached_context(
        "attendance_tool_bootstrap",
        requested,
        _build,
    )


@frappe.whitelist()
def fetch_attendance_tool_group_context(student_group: str):
    group_name = _clean_value(student_group)
    if not group_name:
        frappe.throw(_("Student Group is required."))

    weekend_days = get_weekend_days(group_name)
    meeting_dates = get_meeting_dates(group_name)
    recorded_dates = attendance_recorded_dates(group_name)

    return {
        "weekend_days": weekend_days or [6, 0],
        "meeting_dates": meeting_dates,
        "recorded_dates": recorded_dates,
        "default_selected_date": _pick_default_meeting_date(meeting_dates),
    }


@frappe.whitelist()
def fetch_attendance_tool_roster_context(student_group: str, attendance_date: str):
    group_name = _clean_value(student_group)
    selected_date = _clean_value(attendance_date)
    if not group_name:
        frappe.throw(_("Student Group is required."))
    if not selected_date:
        frappe.throw(_("Attendance Date is required."))

    return {
        "roster": fetch_students(group_name, start=0, page_length=500),
        "prev_map": previous_status_map(group_name, selected_date),
        "existing_map": fetch_existing_attendance(group_name, selected_date),
        "blocks": fetch_blocks_for_day(group_name, selected_date),
    }


@frappe.whitelist()
def fetch_portal_academic_years(school: str | None = None):
    """Return Academic Years visible in scope, with nearest-ancestor calendar fallback."""
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to view academic years."))

    filters: dict[str, object] = {}
    school_scope = _expand_school_scope(school)
    if school_scope is not None and not school_scope:
        return []

    if school_scope:
        filters["school"] = ["in", school_scope]

    rows = frappe.get_all(
        "Academic Year",
        fields=["name", "year_start_date", "year_end_date", "school"],
        filters=filters,
        order_by="year_start_date desc, name desc",
    )
    if rows or school_scope is None:
        return rows

    anchor_school = _resolve_lineage_anchor_school(school, school_scope)
    if not anchor_school:
        return rows

    for ancestor_school in get_school_lineage(anchor_school):
        ancestor_rows = frappe.get_all(
            "Academic Year",
            fields=["name", "year_start_date", "year_end_date", "school"],
            filters={"school": ancestor_school},
            order_by="year_start_date desc, name desc",
        )
        if ancestor_rows:
            return ancestor_rows

    return rows


@frappe.whitelist()
def fetch_portal_terms(academic_year: str | None = None, school: str | None = None):
    """Return Terms visible in scope, with nearest-ancestor calendar fallback."""
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to view terms."))

    school_scope = _expand_school_scope(school)
    if school_scope is not None and not school_scope:
        return []

    academic_year_value = (academic_year or "").strip()
    rows = _query_terms(
        academic_year=academic_year_value,
        school_scope=school_scope,
        include_global=True,
    )
    if rows or school_scope is None:
        return rows

    anchor_school = _resolve_lineage_anchor_school(school, school_scope)
    if not anchor_school:
        return rows

    for ancestor_school in get_school_lineage(anchor_school):
        ancestor_rows = _query_terms(
            academic_year=academic_year_value,
            school_scope=[ancestor_school],
            include_global=False,
        )
        if ancestor_rows:
            return ancestor_rows

    return rows


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


def _resolve_lineage_anchor_school(
    school: str | None,
    school_scope: list[str] | None,
) -> str | None:
    """
    Resolve which school to use for ancestor fallback.
    - explicit school when it is permitted
    - otherwise the user default school when it is in scope
    - otherwise a single scoped school
    """
    school_value = (school or "").strip() or None
    if school_value:
        if school_scope is None or school_value in school_scope:
            return school_value
        return None

    default_school = get_user_default_school()
    if default_school and (school_scope is None or default_school in school_scope):
        return default_school

    if school_scope and len(school_scope) == 1:
        return school_scope[0]

    return None


def _query_terms(
    *,
    academic_year: str | None,
    school_scope: list[str] | None,
    include_global: bool,
) -> list[dict]:
    params: dict[str, object] = {}
    conditions = ["COALESCE(t.archived, 0) = 0"]

    if academic_year:
        conditions.append("t.academic_year = %(academic_year)s")
        params["academic_year"] = academic_year

    if school_scope:
        if include_global:
            conditions.append("(t.school IN %(school_scope)s OR COALESCE(t.school, '') = '')")
        else:
            conditions.append("t.school IN %(school_scope)s")
        params["school_scope"] = tuple(school_scope)
    elif school_scope == []:
        return []

    return frappe.db.sql(
        f"""
		SELECT
			t.name,
			t.academic_year,
			t.school,
			t.term_start_date,
			t.term_end_date
		FROM `tabTerm` t
		WHERE {" AND ".join(conditions)}
		ORDER BY t.term_start_date DESC, t.name DESC
		""",
        params,
        as_dict=True,
    )


def _cached_context(prefix: str, requested: dict[str, str | None], builder):
    cache_key = _build_cache_key(prefix, requested)
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached is not None:
        return cached

    payload = builder()
    cache.set_value(cache_key, payload, expires_in_sec=ATTENDANCE_CONTEXT_TTL)
    return payload


def _build_cache_key(prefix: str, requested: dict[str, str | None]) -> str:
    raw = json.dumps(
        {
            "user": frappe.session.user,
            "requested": requested,
            "default_school": get_user_default_school(),
        },
        sort_keys=True,
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"ifw:{prefix}:{digest}"


def _clean_value(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def _pick_named_value(
    requested: str | None,
    rows: list[dict],
    *,
    fallback: str | None = None,
    allow_first: bool = False,
) -> str | None:
    names = {row.get("name") for row in rows if row.get("name")}
    if requested and requested in names:
        return requested
    if fallback and fallback in names:
        return fallback
    if allow_first and rows:
        return rows[0]["name"]
    return None


def _derive_academic_year_rows_from_groups(groups: list[dict]) -> list[dict]:
    names = sorted(
        {
            row.get("academic_year")
            for row in groups
            if isinstance(row.get("academic_year"), str) and row.get("academic_year", "").strip()
        },
        reverse=True,
    )
    return [{"name": value} for value in names]


def _pick_default_meeting_date(meeting_dates: list[str]) -> str | None:
    if not meeting_dates:
        return None

    today = getdate(nowdate())
    parsed_dates = sorted(
        {value: getdate(value) for value in meeting_dates if isinstance(value, str) and value.strip()}.items(),
        key=lambda item: item[1],
    )
    if not parsed_dates:
        return None

    past_or_today = [iso for iso, parsed in parsed_dates if parsed <= today]
    if past_or_today:
        return past_or_today[-1]
    return parsed_dates[0][0]
