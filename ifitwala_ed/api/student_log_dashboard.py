# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_log_dashboard.py

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe.utils import get_datetime, getdate, strip_html
from frappe.utils.nestedset import get_descendants_of

from ifitwala_ed.students.doctype.student_log.student_log import (
    get_student_log_visibility_predicate,
)

ALLOWED_ANALYTICS_ROLES = {
    "Academic Admin",
    "Pastoral Lead",
    "Counselor",
    "Learning Support",
    "Curriculum Coordinator",
    "Accreditation Visitor",
    "System Manager",
    "Administrator",
}

FOLLOW_UP_DOCTYPE = "Student Log Follow Up"
FILTER_META_CACHE_TTL_SECONDS = 60 * 5


def _ensure_student_log_analytics_access(user: str | None = None) -> str:
    """Permit access only to the Student Log analytics roles."""
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw("You need to sign in to access Student Log Analytics.", frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & ALLOWED_ANALYTICS_ROLES:
        return user

    frappe.throw("You do not have permission to access Student Log Analytics.", frappe.PermissionError)
    return user


def _normalize_date_filter(value):
    """Accepts None, string, date, datetime and returns a YYYY-MM-DD string or None."""
    if not value:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v or None
    # Fallback for date/datetime objects etc.
    try:
        return getdate(value).isoformat()
    except Exception:
        # Last resort: string representation (still safe for SQL parameter)
        return str(value)


def _resolve_date_window(filters):
    """
    Return (date_from, date_to) as strings 'YYYY-MM-DD' applying these rules:

    - If no Academic Year: use from_date/to_date as provided (open-ended ok).
    - If Academic Year set:
            • If no from/to provided -> AY range.
            • If provided range(s) fully within AY -> keep provided (narrower).
            • If provided range(s) fall outside AY or are missing -> AY takes precedence.
    """
    fd = _normalize_date_filter(filters.get("from_date"))
    td = _normalize_date_filter(filters.get("to_date"))

    ay = (filters.get("academic_year") or "").strip()
    ay_start, ay_end = (None, None)
    if ay:
        ay_start, ay_end = frappe.db.get_value("Academic Year", ay, ["year_start_date", "year_end_date"]) or (
            None,
            None,
        )

    # No AY → pass through (already normalized)
    if not (ay_start and ay_end):
        return fd, td

    # Normalize AY dates to strings as well
    ay_start_s = getdate(ay_start).isoformat()
    ay_end_s = getdate(ay_end).isoformat()

    # AY present; precedence logic
    if not fd and not td:
        return ay_start_s, ay_end_s

    if fd and td and (fd >= ay_start_s and td <= ay_end_s):
        return fd, td

    if fd and not td and (ay_start_s <= fd <= ay_end_s):
        return fd, ay_end_s

    if td and not fd and (ay_start_s <= td <= ay_end_s):
        return ay_start_s, td

    # Not matching → AY wins
    return ay_start_s, ay_end_s


def _apply_common_filters(filters, visibility_clause, visibility_params, school_scope=None):
    """
    Build WHERE conditions/params shared by queries, including date window.
    """
    conditions = []
    params = dict(visibility_params or {})

    if visibility_clause:
        conditions.append(visibility_clause)

    # School filter (include descendants)
    if school_scope:
        conditions.append("sl.school IN %(field_school)s")
        params["field_school"] = school_scope

    # Direct columns in Student Log (alias sl)
    direct_map = {
        "academic_year": "sl.academic_year",
        "program": "sl.program",
        "author": "sl.author_name",
    }
    for key, col in direct_map.items():
        if filters.get(key):
            ph = f"field_{key}"
            conditions.append(f"{col} = %({ph})s")
            params[ph] = filters[key]

    # Date window (From/To with AY precedence)
    date_from, date_to = _resolve_date_window(filters)
    if date_from:
        conditions.append("sl.date >= %(date_from)s")
        params["date_from"] = date_from
    if date_to:
        conditions.append("sl.date <= %(date_to)s")
        params["to_date"] = date_to
        params["date_to"] = date_to  # keep original param name used in SQL

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params


def _resolve_school_scope(filters):
    school = (filters or {}).get("school")
    if not school:
        return None

    descendants = get_descendants_of("School", school, ignore_permissions=True) or []
    return tuple([school, *descendants])


def _filter_meta_cache_key(user: str) -> str:
    site = getattr(getattr(frappe, "local", None), "site", None) or "site"
    return f"ifitwala_ed:student_log_dashboard:filter_meta:v1:{site}:{user}"


def _format_response_time_label(total_minutes: int | None) -> str | None:
    if total_minutes is None:
        return None

    total_minutes = max(int(total_minutes), 0)
    days, rem_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(rem_minutes, 60)

    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return f"{minutes} min"


def _get_response_latency(log_created_at, follow_up_created_at):
    if not log_created_at or not follow_up_created_at:
        return None, None

    try:
        log_dt = get_datetime(log_created_at)
        follow_up_dt = get_datetime(follow_up_created_at)
    except Exception:
        return None, None

    if not log_dt or not follow_up_dt:
        return None, None

    total_minutes = max(int((follow_up_dt - log_dt).total_seconds() // 60), 0)
    return total_minutes, _format_response_time_label(total_minutes)


def _attach_follow_up_summaries(log_rows):
    if not log_rows:
        return log_rows

    log_names = [row.get("name") for row in log_rows if row.get("name")]
    if not log_names:
        return log_rows

    log_context = {
        row["name"]: {
            "next_step": row.get("next_step"),
            "created_at": row.get("created_at"),
        }
        for row in log_rows
        if row.get("name")
    }

    follow_up_rows = frappe.db.sql(
        f"""
        SELECT
            fu.name,
            fu.student_log,
            fu.date,
            fu.follow_up_author,
            fu.follow_up,
            fu.creation AS responded_at
        FROM `tab{FOLLOW_UP_DOCTYPE}` fu
        WHERE fu.docstatus = 1
          AND fu.student_log IN %(log_names)s
        ORDER BY fu.student_log ASC, fu.creation DESC, fu.name DESC
        """,
        {"log_names": tuple(log_names)},
        as_dict=True,
    )

    follow_ups_by_log = defaultdict(list)
    for follow_up_row in follow_up_rows:
        log_name = follow_up_row.get("student_log")
        if not log_name or log_name not in log_context:
            continue

        response_minutes, response_label = _get_response_latency(
            log_context[log_name].get("created_at"),
            follow_up_row.get("responded_at"),
        )
        comment_text = strip_html(follow_up_row.get("follow_up") or "").strip()
        follow_ups_by_log[log_name].append(
            {
                "name": follow_up_row.get("name"),
                "doctype": FOLLOW_UP_DOCTYPE,
                "next_step": log_context[log_name].get("next_step"),
                "date": str(follow_up_row.get("date")) if follow_up_row.get("date") else None,
                "responded_at": str(follow_up_row.get("responded_at")) if follow_up_row.get("responded_at") else None,
                "responded_in_minutes": response_minutes,
                "responded_in_label": response_label,
                "follow_up_author": follow_up_row.get("follow_up_author"),
                "comment_text": comment_text,
            }
        )

    for row in log_rows:
        follow_ups = follow_ups_by_log.get(row.get("name"), [])
        row["follow_ups"] = follow_ups
        row["follow_up_count"] = len(follow_ups)

    return log_rows


@frappe.whitelist()
def get_dashboard_data(filters=None):
    user = _ensure_student_log_analytics_access()
    try:
        # Make it robust whether filters arrives as JSON string or dict
        if isinstance(filters, str):
            filters = frappe.parse_json(filters) or {}
        else:
            filters = filters or {}

        school_scope = _resolve_school_scope(filters)
        visibility_clause, visibility_params = get_student_log_visibility_predicate(
            user=user, table_alias="sl", allow_aggregate_only=True
        )
        detail_clause, detail_params = get_student_log_visibility_predicate(
            user=user, table_alias="sl", allow_aggregate_only=False
        )

        where_clause, params = _apply_common_filters(
            filters, visibility_clause, visibility_params, school_scope=school_scope
        )

        # Consolidate 6 aggregate queries into single UNION query to reduce DB round-trips
        # per AGENTS.md §5: "Reduce DB round-trips aggressively"
        union_sql = f"""
            SELECT 'log_type' AS metric, sl.log_type AS label, COUNT(*) AS value
            FROM `tabStudent Log` sl WHERE {where_clause}
            GROUP BY sl.log_type

            UNION ALL

            SELECT 'cohort' AS metric, pe.cohort AS label, COUNT(sl.name) AS value
            FROM `tabStudent Log` sl
            LEFT JOIN `tabProgram Enrollment` pe
              ON pe.student = sl.student
             AND pe.academic_year = sl.academic_year
            WHERE {where_clause}
            GROUP BY pe.cohort

            UNION ALL

            SELECT 'program' AS metric, sl.program AS label, COUNT(sl.name) AS value
            FROM `tabStudent Log` sl WHERE {where_clause}
            GROUP BY sl.program

            UNION ALL

            SELECT 'author' AS metric, sl.author_name AS label, COUNT(*) AS value
            FROM `tabStudent Log` sl WHERE {where_clause}
            GROUP BY sl.author_name

            UNION ALL

            SELECT 'next_step' AS metric, sl.next_step AS label, COUNT(*) AS value
            FROM `tabStudent Log` sl WHERE {where_clause}
            GROUP BY sl.next_step

            UNION ALL

            SELECT 'date' AS metric, DATE_FORMAT(sl.date,'%%Y-%%m-%%d') AS label, COUNT(*) AS value
            FROM `tabStudent Log` sl WHERE {where_clause}
            GROUP BY DATE_FORMAT(sl.date,'%%Y-%%m-%%d')

            UNION ALL

            SELECT 'open_follow_ups' AS metric, 'open_follow_ups' AS label, COUNT(*) AS value
            FROM `tabStudent Log` sl
            WHERE {where_clause} AND sl.follow_up_status = 'Open'
        """
        union_results = frappe.db.sql(union_sql, params, as_dict=True)

        # Pivot results by metric
        buckets = defaultdict(list)
        for row in union_results:
            buckets[row["metric"]].append({"label": row["label"], "value": row["value"]})

        # Apply sorting: DESC by value (except date which is ASC by label)
        for key in buckets:
            if key == "date":
                buckets[key].sort(key=lambda x: x["label"])
            else:
                buckets[key].sort(key=lambda x: x["value"], reverse=True)

        log_type_count = buckets.get("log_type", [])
        logs_by_cohort = buckets.get("cohort", [])
        logs_by_program = buckets.get("program", [])
        logs_by_author = buckets.get("author", [])
        next_step_types = buckets.get("next_step", [])
        incidents_over_time = buckets.get("date", [])
        open_follow_ups = next(
            (row["value"] for row in buckets.get("open_follow_ups", []) if row.get("value") is not None),
            0,
        )

        # ── Student Logs (detail for a specific student) ─────────────
        student_logs = []
        if filters.get("student"):
            conds = [detail_clause, "sl.student = %(field_student)s"]
            p = {**detail_params, "field_student": filters["student"]}

            if school_scope:
                conds.append("sl.school IN %(field_school)s")
                p["field_school"] = school_scope

            where_detail = " AND ".join([c for c in conds if c]) if conds else "1=1"

            student_logs = frappe.db.sql(
                f"""
                SELECT
                    sl.name,
                    sl.date,
                    sl.log_type,
                    sl.log         AS content,
                    sl.author_name AS author,
                    sl.requires_follow_up,
                    sl.next_step,
                    sl.creation    AS created_at
                FROM `tabStudent Log` sl
                WHERE {where_detail}
                ORDER BY sl.date DESC
                """,
                p,
                as_dict=True,
            )

        student_logs = _attach_follow_up_summaries(student_logs)

        return {
            "logTypeCount": log_type_count,
            "logsByCohort": logs_by_cohort,
            "logsByProgram": logs_by_program,
            "logsByAuthor": logs_by_author,
            "nextStepTypes": next_step_types,
            "incidentsOverTime": incidents_over_time,
            "openFollowUps": open_follow_ups,
            "studentLogs": student_logs,
        }

    except Exception as e:
        frappe.log_error(str(e), "Student Log Dashboard Data Error")
        return {"error": str(e)}


@frappe.whitelist()
def get_distinct_students(filters=None, search_text: str = ""):
    user = _ensure_student_log_analytics_access()
    try:
        if isinstance(filters, str):
            filters = frappe.parse_json(filters) or {}
        else:
            filters = filters or {}

        txt = (search_text or "").strip()

        visibility_clause, visibility_params = get_student_log_visibility_predicate(
            user=user, table_alias="sl", allow_aggregate_only=False
        )
        school_scope = _resolve_school_scope(filters)
        where_clause, params = _apply_common_filters(
            filters, visibility_clause, visibility_params, school_scope=school_scope
        )
        if txt:
            where_clause = f"{where_clause} AND (sl.student LIKE %(txt)s OR s.student_full_name LIKE %(txt)s)"
            params["txt"] = f"%{txt}%"

        return frappe.db.sql(
            f"""
            SELECT DISTINCT sl.student, s.student_full_name AS student_full_name
            FROM `tabStudent Log` sl
            INNER JOIN `tabStudent` s ON sl.student = s.name
            WHERE {where_clause}
            ORDER BY s.student_full_name
            LIMIT 100
            """,
            params,
            as_dict=True,
        )

    except Exception as e:
        frappe.log_error(message=str(e), title="Student Lookup Error")
        return {"error": str(e)}


@frappe.whitelist()
def get_recent_logs(filters=None, start: int = 0, page_length: int = 25):
    user = _ensure_student_log_analytics_access()
    if isinstance(filters, str):
        filters = frappe.parse_json(filters) or {}
    else:
        filters = filters or {}

    visibility_clause, visibility_params = get_student_log_visibility_predicate(
        user=user, table_alias="sl", allow_aggregate_only=False
    )
    school_scope = _resolve_school_scope(filters)
    where_clause, params = _apply_common_filters(
        filters, visibility_clause, visibility_params, school_scope=school_scope
    )

    logs = frappe.db.sql(
        f"""
        SELECT
            sl.name,
            sl.date,
            sl.student          AS student,
            s.student_full_name AS student_full_name,
            sl.program,
            sl.log_type,
            sl.log              AS content,
            sl.author_name      AS author,
            sl.requires_follow_up,
            sl.next_step,
            sl.creation         AS created_at
        FROM `tabStudent Log` sl
        LEFT JOIN `tabStudent` s ON s.name = sl.student
        WHERE {where_clause}
        ORDER BY sl.date DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {**params, "start": start, "page_len": page_length},
        as_dict=True,
    )
    return _attach_follow_up_summaries(logs)


def get_authorized_schools(user):
    """Return user's school + all descendants using NestedSet helpers."""
    default_school = frappe.defaults.get_user_default("school", user)
    if not default_school:
        default_school = frappe.db.get_value("Employee", {"user_id": user}, "school")
    if not default_school:
        return []

    descendants = get_descendants_of("School", default_school, ignore_permissions=True) or []
    return [default_school, *descendants]


@frappe.whitelist()
def get_filter_meta():
    """Return schools, academic years, programs and authors the user can filter on.

    - Schools, Academic Years, Programs, and Authors are derived from the
      visible Student Log set (no leakage outside permission scope).
    """
    user = _ensure_student_log_analytics_access()
    cache = frappe.cache()
    cache_key = _filter_meta_cache_key(user)
    cached = cache.get_value(cache_key)
    if cached:
        return cached

    visibility_clause, visibility_params = get_student_log_visibility_predicate(
        user=user, table_alias="sl", allow_aggregate_only=True
    )
    where_clause = visibility_clause or "1=1"
    params = dict(visibility_params or {})

    schools = frappe.db.sql(
        f"""
        SELECT DISTINCT
            sc.name,
            sc.school_name AS label
        FROM `tabStudent Log` sl
        JOIN `tabSchool` sc ON sc.name = sl.school
        WHERE {where_clause}
        ORDER BY sc.school_name
        """,
        params,
        as_dict=True,
    )

    default_school = frappe.defaults.get_user_default("school", user)
    if not default_school:
        default_school = frappe.db.get_value("Employee", {"user_id": user}, "school")
    if default_school and default_school not in {s.get("name") for s in schools or []}:
        default_school = None

    academic_years = frappe.db.sql(
        f"""
        SELECT DISTINCT
            ay.name,
            ay.academic_year_name AS label,
            ay.year_start_date,
            ay.year_end_date,
            ay.school
        FROM `tabStudent Log` sl
        JOIN `tabAcademic Year` ay ON ay.name = sl.academic_year
        WHERE {where_clause}
        ORDER BY ay.year_start_date DESC
        """,
        params,
        as_dict=True,
    )

    programs = frappe.db.sql(
        f"""
        SELECT DISTINCT
            p.name,
            p.program_name AS label
        FROM `tabStudent Log` sl
        JOIN `tabProgram` p ON p.name = sl.program
        WHERE {where_clause}
        ORDER BY p.program_name
        """,
        params,
        as_dict=True,
    )

    authors = frappe.db.sql(
        f"""
        SELECT DISTINCT
            e.employee_full_name AS label,
            e.user_id            AS user_id
        FROM `tabStudent Log` sl
        JOIN `tabEmployee` e ON e.user_id = sl.owner
        WHERE {where_clause}
          AND e.employment_status = 'Active'
        ORDER BY e.employee_full_name
        """,
        params,
        as_dict=True,
    )

    response = {
        "schools": schools,
        "default_school": default_school,
        "academic_years": academic_years,
        "programs": programs,
        "authors": authors,
    }
    cache.set_value(cache_key, response, expires_in_sec=FILTER_META_CACHE_TTL_SECONDS)
    return response
