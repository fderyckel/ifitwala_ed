# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/morning_brief.py

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, getdate, now_datetime, strip_html, today

from ifitwala_ed.api.org_comm_utils import check_audience_match
from ifitwala_ed.api.org_communication_interactions import get_seen_org_communication_names
from ifitwala_ed.schedule.schedule_utils import get_weekend_days_for_calendar
from ifitwala_ed.school_settings.school_settings_utils import resolve_school_calendars_for_window
from ifitwala_ed.students.doctype.student_log.student_log import get_student_log_visibility_predicate
from ifitwala_ed.utilities.image_utils import (
    PROFILE_IMAGE_DERIVATIVE_SLOTS,
    apply_preferred_employee_images,
    apply_preferred_student_images,
)
from ifitwala_ed.utilities.school_tree import get_descendant_schools, get_user_default_school

CLINIC_SUMMARY_RANGE_BUSINESS_DAYS = "3D"
CLINIC_SUMMARY_RANGE_BUSINESS_WEEKS = "3W"
CLINIC_TREND_RANGES = {
    "3D": 14,
    "3W": 21,
    "1M": 30,
    "3M": 90,
    "6M": 180,
}


@frappe.whitelist()
def get_briefing_widgets():
    user = frappe.session.user
    roles = frappe.get_roles(user)

    widgets = {}

    site_now = now_datetime()
    widgets["today_label"] = site_now.strftime("%A, %d %B %Y")

    widgets["announcements"] = get_daily_bulletin(user, roles)

    if any(r in roles for r in ["Academic Staff", "Employee", "System Manager", "Instructor"]):
        widgets["staff_birthdays"] = get_staff_birthdays()

    if _can_view_clinic_metrics(user):
        widgets["clinic_volume"] = get_clinic_activity()

    if "Academic Admin" in roles or "System Manager" in roles:
        widgets["admissions_pulse"] = get_admissions_pulse()
        widgets["critical_incidents"] = get_critical_incidents_count()

    my_groups = []
    if "Instructor" in roles:
        my_groups = get_my_student_groups(user)
        if my_groups:
            widgets["grading_velocity"] = get_pending_grading_tasks(my_groups)
            widgets["my_student_birthdays"] = get_my_student_birthdays(my_groups)

    if "Academic Admin" in roles or "System Manager" in roles or "Pastoral Lead" in roles:
        widgets["student_logs"] = get_recent_student_logs(user)

    if "Academic Admin" in roles or "System Manager" in roles or "Academic Assistant" in roles:
        widgets["attendance_trend"] = get_attendance_trend(user)

    if "Instructor" in roles:
        if not my_groups:
            my_groups = get_my_student_groups(user)
        if my_groups:
            widgets["my_absent_students"] = get_my_absent_students(my_groups)

    return widgets


def get_daily_bulletin(user, roles):
    system_today = getdate(today())

    sql = """
		SELECT
			name,
			title,
			message,
			communication_type,
			priority,
			brief_end_date,
			brief_start_date,
			interaction_mode,
			allow_private_notes,
			allow_public_thread
		FROM `tabOrg Communication`
		WHERE status = 'Published'
		AND portal_surface IN ('Morning Brief', 'Everywhere')
		AND brief_start_date <= %s
		AND (brief_end_date >= %s OR brief_end_date IS NULL)
		AND EXISTS (
			SELECT 1
			FROM `tabOrg Communication Audience` aud
			WHERE aud.parent = `tabOrg Communication`.name
		)
		ORDER BY brief_start_date DESC, creation DESC
		LIMIT 50
	"""
    comms = frappe.db.sql(sql, (system_today, system_today), as_dict=True)

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["name", "school", "organization", "department"],
        as_dict=True,
    )

    visible_comms = []

    for c in comms:
        if check_audience_match(c.name, user, roles, employee):
            visible_comms.append(
                {
                    "name": c.name,
                    "title": c.title,
                    # FULL HTML – used by ContentDialog via v-html
                    "content": c.message or "",
                    "type": c.communication_type,
                    "priority": c.priority,
                    "brief_start_date": c.brief_start_date,
                    "interaction_mode": c.interaction_mode,
                    "allow_public_thread": c.allow_public_thread,
                    "allow_private_notes": c.allow_private_notes,
                }
            )

    seen_names = get_seen_org_communication_names(
        user=user,
        communication_names=[row["name"] for row in visible_comms],
    )
    for row in visible_comms:
        row["is_unread"] = row["name"] not in seen_names

    return visible_comms


def _can_view_clinic_metrics(user: str) -> bool:
    if not frappe.db.exists("DocType", "Student Patient Visit"):
        return False
    return bool(frappe.has_permission("Student Patient Visit", ptype="read", user=user))


def _get_clinic_default_school() -> str | None:
    base_school = get_user_default_school()
    if base_school:
        return base_school

    user = frappe.session.user
    if not user or user == "Guest":
        return None

    fields = ["name", "school"]
    if frappe.db.has_column("Employee", "default_school"):
        fields.insert(1, "default_school")

    employee = frappe.db.get_value("Employee", {"user_id": user}, fields, as_dict=True)
    if not employee:
        return None

    return employee.get("default_school") or employee.get("school")


def _resolve_clinic_scope() -> dict:
    base_school = _get_clinic_default_school()
    if not base_school:
        return {
            "base_school": None,
            "school_scope": [],
            "scope_label": _("School assignment required"),
            "error": _("Assign a default school or Employee.school before opening clinic volume."),
        }

    school_scope = list(dict.fromkeys(get_descendant_schools(base_school) or [base_school]))
    school_label = frappe.db.get_value("School", base_school, "school_name") or base_school
    if len(school_scope) > 1:
        scope_label = _("{school_label} + {school_count} schools").format(
            school_label=school_label,
            school_count=len(school_scope) - 1,
        )
    else:
        scope_label = school_label

    return {
        "base_school": base_school,
        "school_scope": school_scope,
        "scope_label": scope_label,
        "error": None,
    }


def _load_clinic_calendar_context(school_scope: list[str], start_date, end_date) -> dict[str, list[dict]]:
    start_value = getdate(start_date)
    end_value = getdate(end_date)
    windows_by_school: dict[str, list[dict]] = defaultdict(list)
    calendar_names: set[str] = set()

    for school in school_scope:
        for row in resolve_school_calendars_for_window(school, start_value, end_value):
            calendar_name = row.get("name")
            if not calendar_name:
                continue

            calendar_names.add(calendar_name)
            windows_by_school[school].append(
                {
                    "calendar_name": calendar_name,
                    "start_date": getdate(row.get("year_start_date")),
                    "end_date": getdate(row.get("year_end_date")),
                }
            )

    holiday_by_calendar: dict[str, set] = defaultdict(set)
    if calendar_names:
        holiday_rows = frappe.get_all(
            "School Calendar Holidays",
            filters={
                "parent": ["in", list(calendar_names)],
                "holiday_date": ["between", [start_value, end_value]],
            },
            fields=["parent", "holiday_date"],
            order_by="holiday_date asc",
        )
        for row in holiday_rows:
            calendar_name = row.get("parent")
            holiday_date = row.get("holiday_date")
            if not calendar_name or not holiday_date:
                continue
            holiday_by_calendar[calendar_name].add(getdate(holiday_date))

    context: dict[str, list[dict]] = {}
    for school in school_scope:
        windows: list[dict] = []
        for row in windows_by_school.get(school, []):
            calendar_name = row["calendar_name"]
            windows.append(
                {
                    "start_date": row["start_date"],
                    "end_date": row["end_date"],
                    "weekend_days": set(get_weekend_days_for_calendar(calendar_name) or [6, 0]),
                    "holidays": holiday_by_calendar.get(calendar_name, set()),
                }
            )
        context[school] = windows

    return context


def _is_business_day_for_school(calendar_context: dict[str, list[dict]], school: str, day_value) -> bool:
    day_value = getdate(day_value)
    js_weekday = (day_value.weekday() + 1) % 7
    windows = calendar_context.get(school) or []

    if not windows:
        return js_weekday not in {6, 0}

    matched_window = False
    for window in windows:
        if day_value < window["start_date"] or day_value > window["end_date"]:
            continue

        matched_window = True
        if js_weekday in window["weekend_days"]:
            continue
        if day_value in window["holidays"]:
            continue
        return True

    if not matched_window:
        return js_weekday not in {6, 0}

    return False


def _is_scope_business_day(calendar_context: dict[str, list[dict]], school_scope: list[str], day_value) -> bool:
    if not school_scope:
        day_value = getdate(day_value)
        return (day_value.weekday() + 1) % 7 not in {6, 0}

    return any(_is_business_day_for_school(calendar_context, school, day_value) for school in school_scope)


def _query_clinic_visit_counts(school_scope: list[str], start_date, end_date) -> list[dict]:
    school_expr = "COALESCE(NULLIF(spv.school, ''), st.anchor_school)"
    school_condition = f"AND {school_expr} IN %(schools)s" if school_scope else ""
    return frappe.db.sql(
        f"""
        SELECT
            {school_expr} AS school,
            spv.date AS date,
            COUNT(*) AS count
        FROM `tabStudent Patient Visit` spv
        LEFT JOIN `tabStudent Patient` sp
            ON sp.name = spv.student_patient
        LEFT JOIN `tabStudent` st
            ON st.name = sp.student
        WHERE spv.docstatus = 1
          AND spv.date BETWEEN %(start_date)s AND %(end_date)s
          {school_condition}
        GROUP BY {school_expr}, spv.date
        ORDER BY spv.date ASC
        """,
        {
            "schools": tuple(school_scope),
            "start_date": getdate(start_date),
            "end_date": getdate(end_date),
        },
        as_dict=True,
    )


def _build_clinic_count_map(rows: list[dict]) -> dict[tuple[str, object], int]:
    count_map: dict[tuple[str, object], int] = {}
    for row in rows or []:
        school = row.get("school")
        visit_date = row.get("date")
        if not school or not visit_date:
            continue
        count_map[(school, getdate(visit_date))] = int(row.get("count") or 0)
    return count_map


def _collect_clinic_count_dates(
    count_map: dict[tuple[str, object], int],
    school_scope: list[str],
    start_date,
    end_date,
) -> list:
    allowed_schools = set(school_scope or [])
    start_value = getdate(start_date)
    end_value = getdate(end_date)
    dates = {
        day_value
        for (school, day_value), count in (count_map or {}).items()
        if count
        and school
        and day_value
        and (not allowed_schools or school in allowed_schools)
        and start_value <= getdate(day_value) <= end_value
    }
    return sorted(dates)


def _sum_clinic_counts_for_day(
    count_map: dict[tuple[str, object], int],
    calendar_context: dict[str, list[dict]],
    school_scope: list[str],
    day_value,
) -> int:
    day_value = getdate(day_value)
    total = 0
    for school in school_scope:
        if not _is_business_day_for_school(calendar_context, school, day_value):
            continue
        total += count_map.get((school, day_value), 0)
    return total


def _collect_recent_business_dates(
    calendar_context: dict[str, list[dict]],
    school_scope: list[str],
    end_date,
    limit: int,
) -> list:
    dates: list = []
    cursor = getdate(end_date)
    inspected_days = 0
    max_lookback = max(limit * 30, 90)

    while len(dates) < limit and inspected_days < max_lookback:
        if _is_scope_business_day(calendar_context, school_scope, cursor):
            dates.append(cursor)
        cursor = getdate(add_days(cursor, -1))
        inspected_days += 1

    return dates


def _format_week_range_label(start_date, end_date) -> str:
    start_label = formatdate(start_date, "dd MMM")
    end_label = formatdate(end_date, "dd MMM")
    return f"{start_label} - {end_label}"


def _build_clinic_business_day_summary(
    count_map: dict[tuple[str, object], int],
    calendar_context: dict[str, list[dict]],
    school_scope: list[str],
    end_date,
    limit: int = 3,
) -> list[dict]:
    points: list[dict] = []
    for day_value in _collect_recent_business_dates(calendar_context, school_scope, end_date, limit):
        points.append(
            {
                "label": formatdate(day_value, "dd-MMM"),
                "count": _sum_clinic_counts_for_day(count_map, calendar_context, school_scope, day_value),
            }
        )
    return points


def _build_clinic_business_week_summary(
    count_map: dict[tuple[str, object], int],
    calendar_context: dict[str, list[dict]],
    school_scope: list[str],
    end_date,
    limit: int = 3,
) -> list[dict]:
    end_value = getdate(end_date)
    current_week_start = getdate(add_days(end_value, -end_value.weekday()))
    points: list[dict] = []

    for offset in range(limit):
        week_start = getdate(add_days(current_week_start, -(offset * 7)))
        week_end = getdate(add_days(week_start, 6))
        if week_end > end_value:
            week_end = end_value

        cursor = week_start
        total = 0
        while cursor <= week_end:
            if _is_scope_business_day(calendar_context, school_scope, cursor):
                total += _sum_clinic_counts_for_day(count_map, calendar_context, school_scope, cursor)
            cursor = getdate(add_days(cursor, 1))

        points.append({"label": _format_week_range_label(week_start, week_end), "count": total})

    return points


def _resolve_clinic_scope_academic_year_start(school_scope: list[str], end_date):
    if not school_scope:
        return None

    end_value = getdate(end_date)
    rows = frappe.get_all(
        "Academic Year",
        filters={
            "school": ["in", school_scope],
            "archived": 0,
            "year_start_date": ["<=", end_value],
            "year_end_date": [">=", end_value],
        },
        fields=["year_start_date", "year_end_date"],
        order_by="year_start_date asc",
        limit=50,
    )

    matching_starts = []
    for row in rows:
        year_start = row.get("year_start_date")
        year_end = row.get("year_end_date")
        if not year_start or not year_end:
            continue
        year_start_value = getdate(year_start)
        year_end_value = getdate(year_end)
        if year_start_value <= end_value <= year_end_value:
            matching_starts.append(year_start_value)

    if matching_starts:
        return min(matching_starts)

    return None


def _resolve_clinic_trend_start_date(time_range: str, end_date, school_scope: list[str] | None = None):
    end_value = getdate(end_date)
    if time_range == "YTD":
        academic_year_start = _resolve_clinic_scope_academic_year_start(school_scope or [], end_value)
        if academic_year_start:
            return academic_year_start
        return getdate(f"{end_value.year}-01-01")

    if time_range == CLINIC_SUMMARY_RANGE_BUSINESS_WEEKS:
        current_week_start = getdate(add_days(end_value, -end_value.weekday()))
        return getdate(add_days(current_week_start, -14))

    lookback_days = CLINIC_TREND_RANGES.get(time_range, CLINIC_TREND_RANGES["1M"])
    return getdate(add_days(end_value, -lookback_days))


def get_clinic_activity():
    """Business-day clinic volume summary for the Morning Brief card."""
    scope = _resolve_clinic_scope()
    if scope["error"]:
        return {
            "default_view": CLINIC_SUMMARY_RANGE_BUSINESS_DAYS,
            "school": scope["scope_label"],
            "views": {
                CLINIC_SUMMARY_RANGE_BUSINESS_DAYS: [],
                CLINIC_SUMMARY_RANGE_BUSINESS_WEEKS: [],
            },
            "error": scope["error"],
        }

    end_date = getdate(today())
    summary_scan_start = getdate(add_days(end_date, -90))
    calendar_context = _load_clinic_calendar_context(scope["school_scope"], summary_scan_start, end_date)
    recent_business_days = _collect_recent_business_dates(calendar_context, scope["school_scope"], end_date, 3)
    week_window_start = getdate(add_days(getdate(add_days(end_date, -end_date.weekday())), -14))
    query_start = min([*recent_business_days, week_window_start], default=week_window_start)
    count_map = _build_clinic_count_map(_query_clinic_visit_counts(scope["school_scope"], query_start, end_date))

    return {
        "default_view": CLINIC_SUMMARY_RANGE_BUSINESS_DAYS,
        "school": scope["scope_label"],
        "views": {
            CLINIC_SUMMARY_RANGE_BUSINESS_DAYS: _build_clinic_business_day_summary(
                count_map, calendar_context, scope["school_scope"], end_date
            ),
            CLINIC_SUMMARY_RANGE_BUSINESS_WEEKS: _build_clinic_business_week_summary(
                count_map, calendar_context, scope["school_scope"], end_date
            ),
        },
        "error": None,
    }


def get_admissions_pulse():
    """Weekly new applications count."""
    start_date = add_days(today(), -7)
    results = frappe.db.sql(
        """
		SELECT COUNT(name) as count, application_status
		FROM `tabStudent Applicant`
		WHERE creation >= %s
		GROUP BY application_status
	""",
        (start_date,),
        as_dict=True,
    )

    total = sum([r["count"] for r in results])
    return {"total_new_weekly": total, "breakdown": results}


def get_critical_incidents_count():
    """Count of Open logs marked as 'Requires Follow Up'."""
    user = frappe.session.user
    visibility_sql, visibility_params = get_student_log_visibility_predicate(
        user=user,
        table_alias="sl",
        allow_aggregate_only=True,
    )
    if visibility_sql == "0=1":
        return 0

    row = frappe.db.sql(
        f"""
        SELECT COUNT(*) AS count
        FROM `tabStudent Log` sl
        WHERE sl.docstatus = 1
          AND sl.requires_follow_up = 1
          AND sl.follow_up_status = 'Open'
          AND ({visibility_sql})
        """,
        visibility_params,
        as_dict=True,
    )
    return int((row[0].get("count") if row else 0) or 0)


def get_my_student_groups(user: str) -> list[str]:
    """Return Student Group names where this user is an instructor.

    Priority:
    1) Employee.user_id → Student Group Instructor.instructor (Link to Employee)
    2) If no match and SGI has `user_id` column → match on that.
    """
    if not user or user == "Guest":
        return []

    groups: list[str] = []

    # 1) Primary path: Employee → instructor
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee:
        groups = frappe.db.get_all(
            "Student Group Instructor",
            filters={"instructor": employee},
            pluck="parent",
        )

    if groups:
        # Deduplicate while preserving order
        return list(dict.fromkeys(groups))

    # 2) Fallback path: direct User link on child table (if present)
    # This protects you if you later move to a User-based link
    if frappe.db.has_column("Student Group Instructor", "user_id"):
        groups = frappe.db.get_all(
            "Student Group Instructor",
            filters={"user_id": user},
            pluck="parent",
        )
        if groups:
            return list(dict.fromkeys(groups))

    return []


def get_pending_grading_tasks(group_names):
    """Count overdue grading deliveries for the instructor's groups."""
    if not group_names:
        return 0

    # Match the old "past due as of today" behavior without relying on DB timezone.
    site_cutoff = f"{today()} 00:00:00"

    return (
        frappe.db.sql(
            """
            SELECT COUNT(DISTINCT td.name)
            FROM `tabTask Delivery` td
            INNER JOIN `tabTask` t
                ON t.name = td.task
            LEFT JOIN `tabTask Outcome` tou
                ON tou.task_delivery = td.name
            WHERE td.student_group IN %(group_names)s
              AND td.require_grading = 1
              AND td.docstatus = 1
              AND td.due_date IS NOT NULL
              AND td.due_date < %(site_cutoff)s
              AND COALESCE(t.is_archived, 0) = 0
              AND (
                tou.name IS NULL
                OR COALESCE(tou.is_complete, 0) = 0
                OR COALESCE(tou.grading_status, '') NOT IN ('Finalized', 'Released', 'Moderated')
              )
            """,
            {
                "group_names": tuple(group_names),
                "site_cutoff": site_cutoff,
            },
        )[0][0]
        or 0
    )


# ==============================================================================
# SECTION 3: STUDENT LOGS FEED
# ==============================================================================


def get_recent_student_logs(user):
    from_date = add_days(today(), -1)
    visibility_sql, visibility_params = get_student_log_visibility_predicate(
        user=user,
        table_alias="sl",
        allow_aggregate_only=False,
    )
    if visibility_sql == "0=1":
        return []

    logs = frappe.db.sql(
        f"""
        SELECT
            sl.name,
            sl.student,
            sl.student_name,
            sl.student_image,
            sl.log_type,
            sl.date,
            sl.requires_follow_up,
            sl.follow_up_status,
            sl.log
        FROM `tabStudent Log` sl
        WHERE sl.docstatus = 1
          AND sl.date >= %(from_date)s
          AND sl.log_type != 'Medical'
          AND ({visibility_sql})
        ORDER BY sl.date DESC, sl.time DESC
        LIMIT 50
        """,
        {
            **(visibility_params or {}),
            "from_date": from_date,
        },
        as_dict=True,
    )

    apply_preferred_student_images(logs, student_field="student", image_field="student_image")

    formatted_logs = []
    for log in logs:
        raw_text = strip_html(log.log or "")
        snippet = (raw_text[:120] + "...") if len(raw_text) > 120 else raw_text

        status_color = "gray"
        if log.requires_follow_up:
            if log.follow_up_status == "Open":
                status_color = "red"
            elif log.follow_up_status == "Completed":
                status_color = "green"

        formatted_logs.append(
            {
                "name": log.name,
                "student_name": log.student_name,
                "student_image": log.student_image,
                "log_type": log.log_type,
                "date_display": formatdate(log.date, "dd-MMM"),
                "snippet": snippet,
                "full_content": log.log,
                "status_color": status_color,
            }
        )

    return formatted_logs


def get_staff_birthdays():
    """
    Active employees with birthdays within the current +/-4 day briefing window.
    Handles year wrap-around (e.g. Dec 31 -> Jan 2).
    """
    start_md = formatdate(add_days(today(), -4), "MM-dd")
    end_md = formatdate(add_days(today(), 4), "MM-dd")

    condition = "DATE_FORMAT(employee_date_of_birth, '%%m-%%d') BETWEEN %s AND %s"
    if start_md > end_md:
        condition = (
            "(DATE_FORMAT(employee_date_of_birth, '%%m-%%d') >= %s "
            "OR DATE_FORMAT(employee_date_of_birth, '%%m-%%d') <= %s)"
        )

    sql = f"""
        SELECT
            name as employee,
            employee_full_name as name,
            employee_image as image,
            employee_date_of_birth as date_of_birth
        FROM
            `tabEmployee`
        WHERE
            employment_status = 'Active'
            AND employee_date_of_birth IS NOT NULL
            AND {condition}
        ORDER BY
            DATE_FORMAT(employee_date_of_birth, '%%%%m-%%%%d') ASC
    """
    rows = frappe.db.sql(sql, (start_md, end_md), as_dict=True)
    return apply_preferred_employee_images(
        rows,
        employee_field="employee",
        image_field="image",
        slots=PROFILE_IMAGE_DERIVATIVE_SLOTS,
        fallback_to_original=False,
        request_missing_derivatives=True,
    )


def get_my_student_birthdays(group_names):
    """
    Active students in my groups with birthdays ±4 days.
    """
    if not group_names:
        return []

    start_md = formatdate(add_days(today(), -4), "MM-dd")
    end_md = formatdate(add_days(today(), 4), "MM-dd")

    # Handle year wrap (Dec→Jan)
    condition = "DATE_FORMAT(s.student_date_of_birth, '%%m-%%d') BETWEEN %(start_md)s AND %(end_md)s"
    if start_md > end_md:
        condition = (
            "(DATE_FORMAT(s.student_date_of_birth, '%%m-%%d') >= %(start_md)s "
            "OR DATE_FORMAT(s.student_date_of_birth, '%%m-%%d') <= %(end_md)s)"
        )

    sql = f"""
		SELECT DISTINCT
			s.name AS student,
			s.student_first_name AS first_name,
			s.student_last_name AS last_name,
			s.student_image AS image,
			s.student_date_of_birth AS date_of_birth
		FROM `tabStudent Group Student` sgs
		INNER JOIN `tabStudent` s ON sgs.student = s.name
		WHERE sgs.parent IN %(group_names)s
			AND sgs.active = 1
			AND s.student_date_of_birth IS NOT NULL
			AND {condition}
		ORDER BY DATE_FORMAT(s.student_date_of_birth, '%%%%m-%%%%d') ASC
	"""

    rows = frappe.db.sql(
        sql,
        {
            "group_names": tuple(group_names),
            "start_md": start_md,
            "end_md": end_md,
        },
        as_dict=True,
    )
    return apply_preferred_student_images(rows, student_field="student", image_field="image")


def get_attendance_trend(user):
    """
    Returns daily absence count for the last 30 days for the user's school.
    """
    employee = frappe.db.get_value("Employee", {"user_id": user}, ["school"], as_dict=True)
    if not employee or not employee.school:
        return []

    # Get last 30 days
    end_date = today()
    start_date = add_days(end_date, -30)

    sql = """
		SELECT
			sa.attendance_date as date,
			COUNT(*) as count
		FROM `tabStudent Attendance` sa
		INNER JOIN `tabStudent Attendance Code` sac ON sa.attendance_code = sac.name
		WHERE sa.school = %s
		AND sa.attendance_date BETWEEN %s AND %s
		AND sa.docstatus = 1
		AND sac.count_as_present = 0
		GROUP BY sa.attendance_date
		ORDER BY sa.attendance_date ASC
	"""

    results = frappe.db.sql(sql, (employee.school, start_date, end_date), as_dict=True)

    # Fill in missing dates with 0
    data_map = {getdate(r.date): r.count for r in results}

    final_data = []
    current_date = getdate(start_date)
    target_date = getdate(end_date)

    while current_date <= target_date:
        d_str = formatdate(current_date, "yyyy-mm-dd")
        count = data_map.get(current_date, 0)
        final_data.append({"date": d_str, "count": count})
        current_date = add_days(current_date, 1)

    return final_data


def get_my_absent_students(group_names):
    """
    Returns list of students in my groups who are absent TODAY.
    """
    if not group_names:
        return []

    site_today = today()

    sql = """
		SELECT
			sa.student_name,
			sa.attendance_code,
			sa.student_group,
			sa.remark,
			s.student_image,
			sac.color as status_color
		FROM `tabStudent Attendance` sa
		INNER JOIN `tabStudent` s ON sa.student = s.name
		INNER JOIN `tabStudent Attendance Code` sac ON sa.attendance_code = sac.name
		WHERE sa.attendance_date = %(site_today)s
		AND sa.student_group IN %(group_names)s
		AND sa.docstatus = 1
		AND sac.count_as_present = 0
	"""

    return frappe.db.sql(
        sql,
        {
            "site_today": site_today,
            "group_names": tuple(group_names),
        },
        as_dict=True,
    )


@frappe.whitelist()
def get_critical_incidents_details():
    """
    Returns detailed list of Open logs marked as 'Requires Follow Up'.
    """
    user = frappe.session.user
    visibility_sql, visibility_params = get_student_log_visibility_predicate(
        user=user,
        table_alias="sl",
        allow_aggregate_only=False,
    )
    if visibility_sql == "0=1":
        return []

    logs = frappe.db.sql(
        f"""
        SELECT
            sl.name,
            sl.student_name,
            sl.student_image,
            sl.log_type,
            sl.date,
            sl.log
        FROM `tabStudent Log` sl
        WHERE sl.docstatus = 1
          AND sl.requires_follow_up = 1
          AND sl.follow_up_status = 'Open'
          AND ({visibility_sql})
        ORDER BY sl.date DESC, sl.creation DESC
        """,
        visibility_params,
        as_dict=True,
    )

    for log in logs:
        log.date_display = formatdate(log.date, "dd-MMM")
        raw_text = strip_html(log.log or "")
        log.snippet = (raw_text[:100] + "...") if len(raw_text) > 100 else raw_text

    return logs


@frappe.whitelist()
def get_clinic_visits_trend(time_range="1M"):
    """
    Returns business-day visit counts for the specified range.
    time_range: '3D', '3W', '1M', '3M', '6M', 'YTD'
    """
    user = frappe.session.user
    if not _can_view_clinic_metrics(user):
        frappe.throw(_("You do not have access to clinic volume."), frappe.PermissionError)

    scope = _resolve_clinic_scope()
    if scope["error"]:
        frappe.throw(scope["error"], frappe.PermissionError)

    end_date = getdate(today())
    start_date = _resolve_clinic_trend_start_date(time_range, end_date, scope["school_scope"])
    calendar_context = _load_clinic_calendar_context(scope["school_scope"], start_date, end_date)
    count_map = _build_clinic_count_map(_query_clinic_visit_counts(scope["school_scope"], start_date, end_date))
    final_data = []

    if time_range == CLINIC_SUMMARY_RANGE_BUSINESS_DAYS:
        trend_dates = list(
            reversed(_collect_recent_business_dates(calendar_context, scope["school_scope"], end_date, 3))
        )
    else:
        trend_dates = []
        curr = getdate(start_date)
        end = getdate(end_date)
        while curr <= end:
            if _is_scope_business_day(calendar_context, scope["school_scope"], curr):
                trend_dates.append(curr)
            curr = add_days(curr, 1)
        if not trend_dates:
            trend_dates = _collect_clinic_count_dates(count_map, scope["school_scope"], start_date, end_date)

    for day_value in trend_dates:
        final_data.append(
            {
                "date": formatdate(day_value, "yyyy-mm-dd"),
                "count": _sum_clinic_counts_for_day(count_map, calendar_context, scope["school_scope"], day_value),
            }
        )

    return {
        "data": final_data,
        "school": scope["scope_label"],
        "range": time_range,
    }
