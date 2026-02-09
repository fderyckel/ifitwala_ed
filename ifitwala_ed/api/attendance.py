# ifitwala_ed/api/attendance.py

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any, Callable

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from ifitwala_ed.api.student_groups import _instructor_group_names
from ifitwala_ed.schedule.schedule_utils import get_weekend_days_for_calendar
from ifitwala_ed.students.doctype.student_log.student_log import get_student_log_visibility_predicate
from ifitwala_ed.utilities.school_tree import _is_adminish, get_descendant_schools, get_user_default_school


MODE_OVERVIEW = "overview"
MODE_HEATMAP = "heatmap"
MODE_RISK = "risk"
MODE_CODE_USAGE = "code_usage"
MODE_MY_GROUPS = "my_groups"
ALLOWED_MODES = {MODE_OVERVIEW, MODE_HEATMAP, MODE_RISK, MODE_CODE_USAGE, MODE_MY_GROUPS}

HEATMAP_MODE_BLOCK = "block"
HEATMAP_MODE_DAY = "day"
ALLOWED_HEATMAP_MODES = {HEATMAP_MODE_BLOCK, HEATMAP_MODE_DAY}

ROLE_CLASS_INSTRUCTOR = "instructor"
ROLE_CLASS_COUNSELOR = "counselor"
ROLE_CLASS_ADMIN = "admin"

ADMIN_ROLES = {"Academic Admin", "Academic Assistant", "Administrator", "System Manager"}
COUNSELOR_ROLES = {"Counsellor", "Counselor", "Pastoral Lead", "Learning Support"}
INSTRUCTOR_ROLES = {"Instructor", "Academic Staff"}

LATE_SQL = "(LOWER(COALESCE(c.attendance_code_name, '')) LIKE '%%late%%' OR c.attendance_code = 'L')"
EXCUSED_SQL = "LOWER(COALESCE(c.attendance_code_name, '')) LIKE '%%excuse%%'"

DATE_PRESETS = {
	"today": 0,
	"last_week": 7,
	"last_2_weeks": 14,
	"last_month": 30,
	"last_3_months": 90,
}

MODE_TTL_SECONDS = {
	MODE_OVERVIEW: 900,
	MODE_HEATMAP: 900,
	MODE_RISK: 900,
	MODE_CODE_USAGE: 1800,
	MODE_MY_GROUPS: 600,
}


@frappe.whitelist()
def get(
	mode: str,
	school: str | None = None,
	academic_year: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	whole_day: int | None = None,
	thresholds: dict | str | None = None,
	term: str | None = None,
	date_preset: str | None = None,
	heatmap_mode: str | None = None,
	program: str | None = None,
	student_group: str | None = None,
	activity_only: int | None = None,
	include_context: int | None = None,
	context_student: str | None = None,
):
	"""Attendance analytics query engine.

	One endpoint, multiple modes. The backend always owns scope, hierarchy and permissions.
	"""
	mode_value = (mode or "").strip()
	if mode_value not in ALLOWED_MODES:
		frappe.throw(_("Invalid attendance mode: {0}").format(mode_value))

	thresholds_map = _normalize_thresholds(thresholds)
	heatmap_mode_value = _normalize_heatmap_mode(heatmap_mode)
	whole_day_value = 1 if cint(whole_day) else 0

	ctx = _resolve_request_context(
		academic_year=academic_year,
		date_preset=date_preset,
		end_date=end_date,
		program=program,
		school=school,
		start_date=start_date,
		student_group=student_group,
		term=term,
		whole_day=whole_day_value,
		activity_only=1 if cint(activity_only) else 0,
	)

	cache_ttl = MODE_TTL_SECONDS.get(mode_value, 900)
	if mode_value == MODE_HEATMAP and ctx["role_class"] == ROLE_CLASS_INSTRUCTOR:
		if ctx["date_from"] == getdate(nowdate()) and ctx["date_to"] == getdate(nowdate()):
			cache_ttl = 600

	payload = _fetch_cached_result(
		mode=mode_value,
		ctx=ctx,
		ttl_seconds=cache_ttl,
		extra={
			"thresholds": thresholds_map,
			"heatmap_mode": heatmap_mode_value,
			"program": program,
			"student_group": student_group,
			"activity_only": 1 if cint(activity_only) else 0,
			"whole_day": whole_day_value,
			"include_context": 1 if cint(include_context) else 0,
			"context_student": context_student,
		},
		compute=lambda: _dispatch_mode(
			mode=mode_value,
			ctx=ctx,
			thresholds=thresholds_map,
			heatmap_mode=heatmap_mode_value,
			include_context=1 if cint(include_context) else 0,
			context_student=context_student,
		),
	)

	return payload


def _dispatch_mode(
	mode: str,
	ctx: dict[str, Any],
	thresholds: dict[str, float],
	heatmap_mode: str,
	include_context: int,
	context_student: str | None,
) -> dict[str, Any]:
	if mode == MODE_OVERVIEW:
		return _get_overview_payload(ctx)

	if mode == MODE_HEATMAP:
		return _get_heatmap_payload(ctx, heatmap_mode=heatmap_mode)

	if mode == MODE_RISK:
		return _get_risk_payload(
			ctx,
			thresholds=thresholds,
			include_context=bool(include_context),
			context_student=context_student,
		)

	if mode == MODE_CODE_USAGE:
		return _get_code_usage_payload(ctx)

	if mode == MODE_MY_GROUPS:
		return _get_my_groups_payload(ctx, thresholds=thresholds)

	frappe.throw(_("Unsupported attendance mode."))
	return {}


def _resolve_request_context(
	*,
	academic_year: str | None,
	date_preset: str | None,
	end_date: str | None,
	program: str | None,
	school: str | None,
	start_date: str | None,
	student_group: str | None,
	term: str | None,
	whole_day: int,
	activity_only: int,
) -> dict[str, Any]:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to view attendance analytics."), frappe.PermissionError)

	roles = set(frappe.get_roles(user))
	role_class = _resolve_role_class(roles)

	school_scope = _resolve_school_scope(user=user, school=school)
	if not school_scope:
		return {
			"user": user,
			"roles": sorted(roles),
			"role_class": role_class,
			"school_scope": [],
			"group_scope": [],
			"student_scope": [],
			"date_from": getdate(nowdate()),
			"date_to": getdate(nowdate()),
			"valid_instruction_days": [],
			"previous_date_from": getdate(nowdate()),
			"previous_date_to": getdate(nowdate()),
			"previous_instruction_days": [],
			"window_source": "empty_scope",
			"program": _clean_optional(program),
			"student_group": _clean_optional(student_group),
			"whole_day": whole_day,
			"activity_only": activity_only,
		}

	group_scope, student_scope, group_rows = _resolve_role_scope(
		role_class=role_class,
		user=user,
		school_scope=school_scope,
	)

	program_value = _clean_optional(program)
	student_group_value = _clean_optional(student_group)
	if student_group_value and role_class != ROLE_CLASS_ADMIN and student_group_value not in set(group_scope):
		frappe.throw(_("You do not have access to this student group."), frappe.PermissionError)

	date_from, date_to, source = _resolve_time_window(
		academic_year=_clean_optional(academic_year),
		term=_clean_optional(term),
		start_date=_clean_optional(start_date),
		end_date=_clean_optional(end_date),
		date_preset=_clean_optional(date_preset),
		school_scope=school_scope,
	)

	valid_instruction_days = _resolve_instruction_days(
		school_scope=school_scope,
		date_from=date_from,
		date_to=date_to,
	)

	prev_from, prev_to = _resolve_previous_window(date_from, date_to)
	previous_instruction_days = _resolve_instruction_days(
		school_scope=school_scope,
		date_from=prev_from,
		date_to=prev_to,
	)

	return {
		"user": user,
		"roles": sorted(roles),
		"role_class": role_class,
		"school_scope": school_scope,
		"group_scope": group_scope,
		"group_rows": group_rows,
		"student_scope": student_scope,
		"date_from": date_from,
		"date_to": date_to,
		"valid_instruction_days": valid_instruction_days,
		"previous_date_from": prev_from,
		"previous_date_to": prev_to,
		"previous_instruction_days": previous_instruction_days,
		"window_source": source,
		"program": program_value,
		"student_group": student_group_value,
		"whole_day": whole_day,
		"activity_only": activity_only,
	}


def _resolve_role_class(roles: set[str]) -> str:
	if roles & ADMIN_ROLES:
		return ROLE_CLASS_ADMIN
	if roles & COUNSELOR_ROLES:
		return ROLE_CLASS_COUNSELOR
	if roles & INSTRUCTOR_ROLES:
		return ROLE_CLASS_INSTRUCTOR

	frappe.throw(
		_("You do not have permission to access Attendance Analytics."),
		frappe.PermissionError,
	)
	return ROLE_CLASS_INSTRUCTOR


def _resolve_school_scope(*, user: str, school: str | None) -> list[str]:
	requested_school = _clean_optional(school)

	if _is_adminish(user):
		if requested_school:
			return get_descendant_schools(requested_school) or [requested_school]
		default_school = get_user_default_school()
		if default_school:
			return get_descendant_schools(default_school) or [default_school]
		return frappe.get_all("School", pluck="name", order_by="lft asc")

	default_school = get_user_default_school()
	if not default_school:
		frappe.throw(
			_("No default school configured for your account."),
			frappe.PermissionError,
		)

	allowed_scope = get_descendant_schools(default_school) or [default_school]
	if not requested_school:
		return allowed_scope

	requested_scope = get_descendant_schools(requested_school) or [requested_school]
	allowed_set = set(allowed_scope)
	intersected = [school_name for school_name in requested_scope if school_name in allowed_set]
	if not intersected:
		frappe.throw(
			_("You do not have access to the selected school."),
			frappe.PermissionError,
		)
	return intersected


def _resolve_role_scope(
	*,
	role_class: str,
	user: str,
	school_scope: list[str],
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
	if role_class == ROLE_CLASS_ADMIN:
		return [], [], []

	group_candidates = sorted(_instructor_group_names(user))
	if not group_candidates:
		return [], [], []

	group_rows = frappe.get_all(
		"Student Group",
		filters={
			"name": ["in", group_candidates],
			"school": ["in", school_scope],
		},
		fields=["name", "student_group_name", "student_group_abbreviation", "group_based_on", "program", "attendance_scope"],
	)
	if not group_rows:
		return [], [], []

	group_scope = [row.name for row in group_rows if row.get("name")]
	if not group_scope:
		return [], [], []

	student_scope = frappe.get_all(
		"Student Group Student",
		filters={
			"parent": ["in", group_scope],
			"active": 1,
		},
		pluck="student",
	)

	return group_scope, list(dict.fromkeys(student_scope)), group_rows


def _resolve_time_window(
	*,
	academic_year: str | None,
	term: str | None,
	start_date: str | None,
	end_date: str | None,
	date_preset: str | None,
	school_scope: list[str],
) -> tuple[date, date, str]:
	if bool(start_date) != bool(end_date):
		frappe.throw(_("Provide both start_date and end_date."))

	if start_date and end_date:
		date_from = getdate(start_date)
		date_to = getdate(end_date)
		if date_to < date_from:
			frappe.throw(_("End date must be after start date."))
		return date_from, date_to, "explicit_range"

	if term:
		term_row = frappe.db.get_value(
			"Term",
			term,
			["term_start_date", "term_end_date"],
			as_dict=True,
		)
		if term_row and term_row.term_start_date and term_row.term_end_date:
			return getdate(term_row.term_start_date), getdate(term_row.term_end_date), "selected_term"

	active_term = _get_active_term_window(school_scope=school_scope, academic_year=academic_year)
	if active_term:
		return active_term[0], active_term[1], "active_term"

	if academic_year:
		ay_row = frappe.db.get_value(
			"Academic Year",
			academic_year,
			["year_start_date", "year_end_date"],
			as_dict=True,
		)
		if ay_row and ay_row.year_start_date and ay_row.year_end_date:
			return getdate(ay_row.year_start_date), getdate(ay_row.year_end_date), "academic_year"

	preset = date_preset if date_preset in DATE_PRESETS else "today"
	to_date = getdate(nowdate())
	from_date = to_date - timedelta(days=DATE_PRESETS[preset])
	return from_date, to_date, f"preset:{preset}"


def _get_active_term_window(
	*,
	school_scope: list[str],
	academic_year: str | None,
) -> tuple[date, date] | None:
	today_value = getdate(nowdate())
	params: dict[str, Any] = {"today": today_value}
	conditions = [
		"t.term_type = 'Academic'",
		"COALESCE(t.archived, 0) = 0",
		"t.term_start_date <= %(today)s",
		"t.term_end_date >= %(today)s",
	]

	if school_scope:
		conditions.append("(t.school IN %(schools)s OR COALESCE(t.school, '') = '')")
		params["schools"] = tuple(school_scope)

	if academic_year:
		conditions.append("t.academic_year = %(academic_year)s")
		params["academic_year"] = academic_year

	rows = frappe.db.sql(
		f"""
		SELECT t.term_start_date, t.term_end_date
		FROM `tabTerm` t
		WHERE {' AND '.join(conditions)}
		ORDER BY t.term_start_date DESC
		LIMIT 1
		""",
		params,
		as_dict=True,
	)
	if not rows:
		return None

	row = rows[0]
	if not row.get("term_start_date") or not row.get("term_end_date"):
		return None

	return getdate(row.term_start_date), getdate(row.term_end_date)


def _resolve_instruction_days(
	*,
	school_scope: list[str],
	date_from: date,
	date_to: date,
) -> list[str]:
	if date_to < date_from:
		return []

	all_dates: list[date] = []
	cursor = date_from
	while cursor <= date_to:
		all_dates.append(cursor)
		cursor += timedelta(days=1)

	if not school_scope:
		return [d.isoformat() for d in all_dates]

	calendar_rows = frappe.db.sql(
		"""
		SELECT DISTINCT ss.school_calendar
		FROM `tabSchool Schedule` ss
		WHERE ss.school IN %(schools)s
		  AND COALESCE(ss.school_calendar, '') != ''
		""",
		{"schools": tuple(school_scope)},
		as_dict=True,
	)
	calendar_names = [row.school_calendar for row in calendar_rows if row.get("school_calendar")]
	if not calendar_names:
		return [d.isoformat() for d in all_dates]

	weekend_days_by_calendar: dict[str, set[int]] = {}
	for calendar_name in calendar_names:
		weekend_days_by_calendar[calendar_name] = set(get_weekend_days_for_calendar(calendar_name) or [6, 0])

	holiday_rows = frappe.db.sql(
		"""
		SELECT h.parent AS calendar_name, h.holiday_date
		FROM `tabSchool Calendar Holidays` h
		WHERE h.parent IN %(calendars)s
		  AND h.holiday_date BETWEEN %(date_from)s AND %(date_to)s
		""",
		{
			"calendars": tuple(calendar_names),
			"date_from": date_from,
			"date_to": date_to,
		},
		as_dict=True,
	)
	holiday_by_calendar: dict[str, set[str]] = {}
	for row in holiday_rows:
		calendar_name = row.get("calendar_name")
		holiday_date = row.get("holiday_date")
		if not calendar_name or not holiday_date:
			continue
		holiday_by_calendar.setdefault(calendar_name, set()).add(getdate(holiday_date).isoformat())

	valid_dates: list[str] = []
	for day in all_dates:
		day_iso = day.isoformat()
		js_weekday = (day.weekday() + 1) % 7
		is_instructional_any = False
		for calendar_name in calendar_names:
			weekend_set = weekend_days_by_calendar.get(calendar_name, {6, 0})
			holiday_set = holiday_by_calendar.get(calendar_name, set())
			if js_weekday in weekend_set:
				continue
			if day_iso in holiday_set:
				continue
			is_instructional_any = True
			break
		if is_instructional_any:
			valid_dates.append(day_iso)

	return valid_dates


def _resolve_previous_window(date_from: date, date_to: date) -> tuple[date, date]:
	window_days = (date_to - date_from).days + 1
	prev_to = date_from - timedelta(days=1)
	prev_from = prev_to - timedelta(days=max(window_days - 1, 0))
	return prev_from, prev_to


def _build_attendance_where(
	*,
	ctx: dict[str, Any],
	alias: str,
	date_from: date,
	date_to: date,
	instruction_days: list[str],
	whole_day: int | None,
	include_group_filter: bool = False,
) -> tuple[str, dict[str, Any]]:
	conditions = [
		f"{alias}.attendance_date BETWEEN %(date_from)s AND %(date_to)s",
	]
	params: dict[str, Any] = {
		"date_from": date_from,
		"date_to": date_to,
	}

	school_scope = ctx.get("school_scope") or []
	if school_scope:
		conditions.append(f"{alias}.school IN %(school_scope)s")
		params["school_scope"] = tuple(school_scope)
	else:
		conditions.append("1=0")

	if instruction_days:
		conditions.append(f"{alias}.attendance_date IN %(instruction_days)s")
		params["instruction_days"] = tuple(instruction_days)
	else:
		conditions.append("1=0")

	if whole_day in {0, 1}:
		conditions.append(f"{alias}.whole_day = %(whole_day)s")
		params["whole_day"] = whole_day

	if ctx.get("program"):
		conditions.append(f"{alias}.program = %(program)s")
		params["program"] = ctx["program"]

	if ctx.get("student_group"):
		conditions.append(f"{alias}.student_group = %(student_group)s")
		params["student_group"] = ctx["student_group"]

	if ctx.get("activity_only"):
		conditions.append(
			f"EXISTS (SELECT 1 FROM `tabStudent Group` sgf WHERE sgf.name = {alias}.student_group AND sgf.group_based_on = 'Activity')"
		)

	if ctx["role_class"] != ROLE_CLASS_ADMIN:
		student_scope = ctx.get("student_scope") or []
		if student_scope:
			conditions.append(f"{alias}.student IN %(student_scope)s")
			params["student_scope"] = tuple(student_scope)
		else:
			conditions.append("1=0")

		if include_group_filter:
			group_scope = ctx.get("group_scope") or []
			if group_scope:
				conditions.append(f"{alias}.student_group IN %(group_scope)s")
				params["group_scope"] = tuple(group_scope)
			else:
				conditions.append("1=0")

	return " AND ".join(conditions), params


def _compute_period_kpis(
	*,
	ctx: dict[str, Any],
	date_from: date,
	date_to: date,
	instruction_days: list[str],
) -> dict[str, float]:
	where_clause, params = _build_attendance_where(
		ctx=ctx,
		alias="a",
		date_from=date_from,
		date_to=date_to,
		instruction_days=instruction_days,
		whole_day=ctx["whole_day"],
	)

	rows = frappe.db.sql(
		f"""
		SELECT
			COUNT(*) AS expected_sessions,
			SUM(CASE WHEN c.count_as_present = 1 THEN 1 ELSE 0 END) AS present_sessions,
			SUM(CASE WHEN {LATE_SQL} THEN 1 ELSE 0 END) AS late_sessions,
			SUM(CASE WHEN c.count_as_present = 0 AND NOT ({EXCUSED_SQL}) AND NOT ({LATE_SQL}) THEN 1 ELSE 0 END) AS unexplained_absent_sessions
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent Attendance Code` c ON c.name = a.attendance_code
		WHERE {where_clause}
		""",
		params,
		as_dict=True,
	)

	row = rows[0] if rows else {}
	expected_sessions = int(row.get("expected_sessions") or 0)
	present_sessions = int(row.get("present_sessions") or 0)
	late_sessions = int(row.get("late_sessions") or 0)
	unexplained = int(row.get("unexplained_absent_sessions") or 0)
	absent_sessions = max(expected_sessions - present_sessions, 0)
	attendance_rate = round((present_sessions / expected_sessions) * 100, 2) if expected_sessions else 0.0

	return {
		"expected_sessions": expected_sessions,
		"present_sessions": present_sessions,
		"absent_sessions": absent_sessions,
		"late_sessions": late_sessions,
		"unexplained_absent_sessions": unexplained,
		"attendance_rate": attendance_rate,
	}


def _get_overview_payload(ctx: dict[str, Any]) -> dict[str, Any]:
	current_kpis = _compute_period_kpis(
		ctx=ctx,
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
	)
	previous_kpis = _compute_period_kpis(
		ctx=ctx,
		date_from=ctx["previous_date_from"],
		date_to=ctx["previous_date_to"],
		instruction_days=ctx["previous_instruction_days"],
	)

	previous_rate = float(previous_kpis.get("attendance_rate") or 0.0)
	current_rate = float(current_kpis.get("attendance_rate") or 0.0)
	trend_delta = round(current_rate - previous_rate, 2)

	return {
		"meta": _response_meta(ctx),
		"kpis": current_kpis,
		"trend": {
			"previous_rate": previous_rate,
			"delta": trend_delta,
		},
	}


def _get_heatmap_payload(ctx: dict[str, Any], *, heatmap_mode: str) -> dict[str, Any]:
	whole_day = ctx["whole_day"]
	where_clause, params = _build_attendance_where(
		ctx=ctx,
		alias="a",
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
		whole_day=whole_day,
	)

	if heatmap_mode == HEATMAP_MODE_DAY or whole_day == 1:
		y_expr = "1"
	else:
		y_expr = "COALESCE(a.block_number, 0)"

	rows = frappe.db.sql(
		f"""
		SELECT
			a.attendance_date AS x,
			{y_expr} AS y,
			SUM(CASE WHEN c.count_as_present = 1 THEN 1 ELSE 0 END) AS present,
			COUNT(*) AS expected
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent Attendance Code` c ON c.name = a.attendance_code
		WHERE {where_clause}
		GROUP BY a.attendance_date, y
		ORDER BY a.attendance_date ASC, y ASC
		""",
		params,
		as_dict=True,
	)

	x_axis: list[str] = []
	y_axis_set: set[int] = set()
	cells: list[dict[str, Any]] = []
	for row in rows:
		x_value = getdate(row.x).isoformat() if row.get("x") else ""
		y_value = int(row.get("y") or 0)
		if x_value and x_value not in x_axis:
			x_axis.append(x_value)
		y_axis_set.add(y_value)
		cells.append(
			{
				"x": x_value,
				"y": y_value,
				"present": int(row.get("present") or 0),
				"expected": int(row.get("expected") or 0),
			}
		)

	return {
		"meta": _response_meta(ctx),
		"axis": {"x": x_axis, "y": sorted(y_axis_set) or [1]},
		"cells": cells,
	}


def _compute_student_metrics(
	*,
	ctx: dict[str, Any],
	date_from: date,
	date_to: date,
	instruction_days: list[str],
	include_group_filter: bool = False,
) -> dict[str, dict[str, Any]]:
	where_clause, params = _build_attendance_where(
		ctx=ctx,
		alias="a",
		date_from=date_from,
		date_to=date_to,
		instruction_days=instruction_days,
		whole_day=ctx["whole_day"],
		include_group_filter=include_group_filter,
	)

	rows = frappe.db.sql(
		f"""
		SELECT
			a.student,
			MAX(COALESCE(NULLIF(a.student_name, ''), s.student_full_name, a.student)) AS student_name,
			COUNT(*) AS expected_sessions,
			SUM(CASE WHEN c.count_as_present = 1 THEN 1 ELSE 0 END) AS present_sessions,
			SUM(CASE WHEN {LATE_SQL} THEN 1 ELSE 0 END) AS late_sessions,
			SUM(CASE WHEN c.count_as_present = 0 AND NOT ({EXCUSED_SQL}) AND NOT ({LATE_SQL}) THEN 1 ELSE 0 END) AS unexplained_absences
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent Attendance Code` c ON c.name = a.attendance_code
		LEFT JOIN `tabStudent` s ON s.name = a.student
		WHERE {where_clause}
		GROUP BY a.student
		""",
		params,
		as_dict=True,
	)

	metrics: dict[str, dict[str, Any]] = {}
	for row in rows:
		student = row.get("student")
		if not student:
			continue
		expected = int(row.get("expected_sessions") or 0)
		present = int(row.get("present_sessions") or 0)
		late = int(row.get("late_sessions") or 0)
		unexplained = int(row.get("unexplained_absences") or 0)
		absent = max(expected - present, 0)
		metrics[student] = {
			"student": student,
			"student_name": row.get("student_name") or student,
			"expected_sessions": expected,
			"present_sessions": present,
			"absent_sessions": absent,
			"late_sessions": late,
			"unexplained_absences": unexplained,
			"attendance_rate": round((present / expected) * 100, 2) if expected else 0,
		}

	return metrics


def _compute_block_1_pattern_counts(ctx: dict[str, Any]) -> dict[str, int]:
	if ctx["whole_day"] == 1:
		return {}

	where_clause, params = _build_attendance_where(
		ctx=ctx,
		alias="a",
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
		whole_day=0,
	)
	where_clause = f"{where_clause} AND COALESCE(a.block_number, 0) = 1"

	rows = frappe.db.sql(
		f"""
		SELECT
			a.student,
			SUM(CASE WHEN c.count_as_present = 0 THEN 1 ELSE 0 END) AS block_1_absences
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent Attendance Code` c ON c.name = a.attendance_code
		WHERE {where_clause}
		GROUP BY a.student
		""",
		params,
		as_dict=True,
	)

	return {
		row.student: int(row.get("block_1_absences") or 0)
		for row in rows
		if row.get("student")
	}


def _compute_mismatch_students(ctx: dict[str, Any]) -> list[dict[str, Any]]:
	where_clause, params = _build_attendance_where(
		ctx=ctx,
		alias="wd",
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
		whole_day=1,
	)

	rows = frappe.db.sql(
		f"""
		SELECT
			wd.student,
			MAX(COALESCE(NULLIF(wd.student_name, ''), s.student_full_name, wd.student)) AS student_name,
			COUNT(DISTINCT wd.attendance_date) AS mismatch_days
		FROM `tabStudent Attendance` wd
		INNER JOIN `tabStudent Attendance Code` c_wd ON c_wd.name = wd.attendance_code
		LEFT JOIN `tabStudent Attendance` bl
			ON bl.student = wd.student
			AND bl.attendance_date = wd.attendance_date
			AND bl.whole_day = 0
		LEFT JOIN `tabStudent Attendance Code` c_bl ON c_bl.name = bl.attendance_code
		LEFT JOIN `tabStudent` s ON s.name = wd.student
		WHERE {where_clause}
			AND c_wd.count_as_present = 1
		GROUP BY wd.student
		HAVING SUM(CASE WHEN c_bl.count_as_present = 0 THEN 1 ELSE 0 END) > 0
		ORDER BY mismatch_days DESC
		LIMIT 60
		""",
		params,
		as_dict=True,
	)

	return [
		{
			"student": row.get("student"),
			"student_name": row.get("student_name") or row.get("student"),
			"mismatch_days": int(row.get("mismatch_days") or 0),
		}
		for row in rows
		if row.get("student")
	]


def _normalize_thresholds(thresholds: dict | str | None) -> dict[str, float]:
	default_warning = 90.0
	default_critical = 80.0

	if isinstance(thresholds, str):
		try:
			thresholds = frappe.parse_json(thresholds)
		except Exception:
			thresholds = None

	if not isinstance(thresholds, dict):
		return {"warning": default_warning, "critical": default_critical}

	warning = _to_float(thresholds.get("warning"), default_warning)
	critical = _to_float(thresholds.get("critical"), default_critical)
	if warning < critical:
		warning, critical = critical, warning
	return {"warning": warning, "critical": critical}


def _normalize_heatmap_mode(value: str | None) -> str:
	candidate = (value or "").strip().lower() or HEATMAP_MODE_BLOCK
	if candidate not in ALLOWED_HEATMAP_MODES:
		return HEATMAP_MODE_BLOCK
	return candidate


def _to_float(value: Any, fallback: float) -> float:
	try:
		return float(value)
	except Exception:
		return fallback


def _get_risk_payload(
	ctx: dict[str, Any],
	*,
	thresholds: dict[str, float],
	include_context: bool,
	context_student: str | None,
) -> dict[str, Any]:
	current_metrics = _compute_student_metrics(
		ctx=ctx,
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
	)
	previous_metrics = _compute_student_metrics(
		ctx=ctx,
		date_from=ctx["previous_date_from"],
		date_to=ctx["previous_date_to"],
		instruction_days=ctx["previous_instruction_days"],
	)
	mismatch_students = _compute_mismatch_students(ctx)
	mismatch_by_student = {row["student"]: int(row["mismatch_days"] or 0) for row in mismatch_students}

	warning = thresholds["warning"]
	critical = thresholds["critical"]

	buckets = {"critical": 0, "warning": 0, "ok": 0}
	top_critical: list[dict[str, Any]] = []
	declining: list[dict[str, Any]] = []
	frequent_unexplained: list[dict[str, Any]] = []
	improving: list[dict[str, Any]] = []

	students = set(current_metrics.keys()) | set(previous_metrics.keys())
	for student in students:
		current = current_metrics.get(student) or {
			"student": student,
			"student_name": student,
			"expected_sessions": 0,
			"present_sessions": 0,
			"absent_sessions": 0,
			"late_sessions": 0,
			"unexplained_absences": 0,
			"attendance_rate": 0.0,
		}
		previous = previous_metrics.get(student) or {
			"expected_sessions": 0,
			"present_sessions": 0,
			"absent_sessions": 0,
			"late_sessions": 0,
			"unexplained_absences": 0,
			"attendance_rate": 0.0,
		}

		current_rate = float(current.get("attendance_rate") or 0.0)
		previous_rate = float(previous.get("attendance_rate") or 0.0)
		delta = round(current_rate - previous_rate, 2)
		unexplained = int(current.get("unexplained_absences") or 0)
		late_count = int(current.get("late_sessions") or 0)
		mismatch_days = mismatch_by_student.get(student, 0)

		if current.get("expected_sessions"):
			if current_rate < critical:
				buckets["critical"] += 1
				top_critical.append(
					{
						"student": student,
						"student_name": current.get("student_name") or student,
						"attendance_rate": current_rate,
						"absent_count": int(current.get("absent_sessions") or 0),
						"late_count": late_count,
						"unexplained_absences": unexplained,
						"mismatch_days": mismatch_days,
					}
				)
			elif current_rate < warning:
				buckets["warning"] += 1
			else:
				buckets["ok"] += 1

		if current.get("expected_sessions") and previous.get("expected_sessions"):
			if delta <= -5.0:
				declining.append(
					{
						"student": student,
						"student_name": current.get("student_name") or student,
						"current_rate": current_rate,
						"previous_rate": previous_rate,
						"delta": delta,
					}
				)

		if unexplained >= 2:
			frequent_unexplained.append(
				{
					"student": student,
					"student_name": current.get("student_name") or student,
					"unexplained_absences": unexplained,
					"attendance_rate": current_rate,
				}
			)

		was_risk = (
			previous_rate < warning
			or int(previous.get("unexplained_absences") or 0) >= 2
			or int(previous.get("late_sessions") or 0) >= 2
		)
		now_clean = current.get("expected_sessions") and current_rate >= warning and unexplained == 0
		if was_risk and now_clean:
			improving.append(
				{
					"student": student,
					"student_name": current.get("student_name") or student,
					"previous_rate": previous_rate,
					"current_rate": current_rate,
					"delta": delta,
				}
			)

	context = None
	if include_context and context_student:
		context = _get_context_sparkline(ctx, context_student)

	top_critical = sorted(top_critical, key=lambda row: row["attendance_rate"])[:50]
	declining = sorted(declining, key=lambda row: row["delta"])[:50]
	frequent_unexplained = sorted(frequent_unexplained, key=lambda row: row["unexplained_absences"], reverse=True)[:50]
	improving = sorted(improving, key=lambda row: row["delta"], reverse=True)[:50]
	compliance_by_scope = _compute_scope_compliance_rows(ctx)
	method_mix = _compute_method_mix_rows(ctx)

	return {
		"meta": _response_meta(ctx),
		"thresholds": thresholds,
		"buckets": buckets,
		"top_critical": top_critical,
		"declining_trend": declining,
		"frequent_unexplained": frequent_unexplained,
		"mismatch_students": mismatch_students,
		"improving_trends": improving,
		"compliance_by_scope": compliance_by_scope,
		"method_mix": method_mix,
		"context_sparkline": context,
	}


def _get_context_sparkline(ctx: dict[str, Any], student: str) -> dict[str, Any] | None:
	if not (ctx.get("school_scope") or []):
		return None

	if ctx["role_class"] != ROLE_CLASS_ADMIN:
		student_scope = set(ctx.get("student_scope") or [])
		if not student_scope or student not in student_scope:
			return None

	attendance_where, attendance_params = _build_attendance_where(
		ctx=ctx,
		alias="a",
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
		whole_day=ctx["whole_day"],
	)
	attendance_where = f"{attendance_where} AND a.student = %(context_student)s"
	attendance_params["context_student"] = student

	attendance_rows = frappe.db.sql(
		f"""
		SELECT
			a.attendance_date AS day,
			COUNT(*) AS expected,
			SUM(CASE WHEN c.count_as_present = 1 THEN 1 ELSE 0 END) AS present
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent Attendance Code` c ON c.name = a.attendance_code
		WHERE {attendance_where}
		GROUP BY a.attendance_date
		ORDER BY a.attendance_date ASC
		""",
		attendance_params,
		as_dict=True,
	)

	academic_rows = frappe.db.sql(
		"""
		SELECT
			DATE(COALESCE(t.published_on, t.completed_on, t.modified)) AS day,
			AVG(COALESCE(t.official_grade_value, t.official_score, 0)) AS average_value,
			COUNT(*) AS samples
		FROM `tabTask Outcome` t
		WHERE t.student = %(student)s
			AND t.school IN %(school_scope)s
			AND DATE(COALESCE(t.published_on, t.completed_on, t.modified)) BETWEEN %(date_from)s AND %(date_to)s
		GROUP BY DATE(COALESCE(t.published_on, t.completed_on, t.modified))
		ORDER BY day ASC
		""",
		{
			"student": student,
			"school_scope": tuple(ctx["school_scope"]),
			"date_from": ctx["date_from"],
			"date_to": ctx["date_to"],
		},
		as_dict=True,
	)

	log_visibility_sql, log_visibility_params = get_student_log_visibility_predicate(
		user=ctx.get("user"),
		table_alias="sl",
		allow_aggregate_only=True,
	)
	behaviour_rows: list[dict[str, Any]] = []
	if log_visibility_sql != "0=1":
		behaviour_rows = frappe.db.sql(
			f"""
			SELECT
				sl.date AS day,
				COUNT(*) AS total_logs,
				SUM(CASE WHEN sl.requires_follow_up = 1 THEN 1 ELSE 0 END) AS follow_up_logs
			FROM `tabStudent Log` sl
			WHERE sl.student = %(student)s
				AND sl.school IN %(school_scope)s
				AND sl.date BETWEEN %(date_from)s AND %(date_to)s
				AND ({log_visibility_sql})
			GROUP BY sl.date
			ORDER BY sl.date ASC
			""",
			{
				"student": student,
				"school_scope": tuple(ctx["school_scope"]),
				"date_from": ctx["date_from"],
				"date_to": ctx["date_to"],
				**(log_visibility_params or {}),
			},
			as_dict=True,
		)

	return {
		"student": student,
		"attendance": [
			{
				"day": getdate(row.day).isoformat() if row.get("day") else "",
				"expected": int(row.get("expected") or 0),
				"present": int(row.get("present") or 0),
			}
			for row in attendance_rows
		],
		"academic_standing": [
			{
				"day": getdate(row.day).isoformat() if row.get("day") else "",
				"average_value": round(float(row.get("average_value") or 0), 2),
				"samples": int(row.get("samples") or 0),
			}
			for row in academic_rows
		],
		"behaviour_incidents": [
			{
				"day": getdate(row.day).isoformat() if row.get("day") else "",
				"total_logs": int(row.get("total_logs") or 0),
				"follow_up_logs": int(row.get("follow_up_logs") or 0),
			}
			for row in behaviour_rows
		],
	}


def _compute_scope_compliance_rows(ctx: dict[str, Any]) -> list[dict[str, Any]]:
	where_clause, params = _build_attendance_where(
		ctx=ctx,
		alias="a",
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
		whole_day=ctx["whole_day"],
	)

	rows = frappe.db.sql(
		f"""
		SELECT
			a.school,
			MAX(sc.school_name) AS school_label,
			COALESCE(a.program, '') AS program,
			COUNT(*) AS expected_sessions,
			SUM(CASE WHEN c.count_as_present = 1 THEN 1 ELSE 0 END) AS present_sessions
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent Attendance Code` c ON c.name = a.attendance_code
		LEFT JOIN `tabSchool` sc ON sc.name = a.school
		WHERE {where_clause}
		GROUP BY a.school, COALESCE(a.program, '')
		ORDER BY school_label ASC, program ASC
		LIMIT 200
		""",
		params,
		as_dict=True,
	)

	return [
		{
			"school": row.get("school"),
			"school_label": row.get("school_label") or row.get("school") or "",
			"program": row.get("program") or "",
			"expected_sessions": int(row.get("expected_sessions") or 0),
			"present_sessions": int(row.get("present_sessions") or 0),
			"attendance_rate": round(
				(
					int(row.get("present_sessions") or 0)
					/ int(row.get("expected_sessions") or 1)
				)
				* 100,
				2,
			)
			if int(row.get("expected_sessions") or 0)
			else 0.0,
		}
		for row in rows
	]


def _compute_method_mix_rows(ctx: dict[str, Any]) -> list[dict[str, Any]]:
	where_clause, params = _build_attendance_where(
		ctx=ctx,
		alias="a",
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
		whole_day=ctx["whole_day"],
	)

	rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(NULLIF(a.attendance_method, ''), 'Manual') AS attendance_method,
			COUNT(*) AS count
		FROM `tabStudent Attendance` a
		WHERE {where_clause}
		GROUP BY COALESCE(NULLIF(a.attendance_method, ''), 'Manual')
		ORDER BY count DESC
		LIMIT 50
		""",
		params,
		as_dict=True,
	)

	total = sum(int(row.get("count") or 0) for row in rows)
	return [
		{
			"attendance_method": row.get("attendance_method") or "Manual",
			"count": int(row.get("count") or 0),
			"share": round((int(row.get("count") or 0) / total) * 100, 2) if total else 0.0,
		}
		for row in rows
	]


def _get_code_usage_payload(ctx: dict[str, Any]) -> dict[str, Any]:
	where_clause, params = _build_attendance_where(
		ctx=ctx,
		alias="a",
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
		whole_day=ctx["whole_day"],
	)

	usage_rows = frappe.db.sql(
		f"""
		SELECT
			c.name AS code_name,
			c.attendance_code,
			c.attendance_code_name,
			c.count_as_present,
			COUNT(*) AS count
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent Attendance Code` c ON c.name = a.attendance_code
		WHERE {where_clause}
		GROUP BY c.name, c.attendance_code, c.attendance_code_name, c.count_as_present
		ORDER BY count DESC
		LIMIT 200
		""",
		params,
		as_dict=True,
	)

	all_codes = frappe.get_all(
		"Student Attendance Code",
		fields=["name", "attendance_code", "attendance_code_name", "count_as_present"],
	)

	usage_map = {row.code_name: row for row in usage_rows if row.get("code_name")}
	total_count = sum(int(row.get("count") or 0) for row in usage_rows)
	codes_payload: list[dict[str, Any]] = []
	for code in all_codes:
		row = usage_map.get(code.name)
		count = int(row.get("count") or 0) if row else 0
		attendance_code_name = (code.get("attendance_code_name") or code.get("attendance_code") or "").lower()
		is_late = 1 if ("late" in attendance_code_name or code.get("attendance_code") == "L") else 0
		is_excused = 1 if "excuse" in attendance_code_name else 0
		share = round((count / total_count) * 100, 2) if total_count else 0.0
		codes_payload.append(
			{
				"attendance_code": code.get("attendance_code") or code.name,
				"attendance_code_name": code.get("attendance_code_name") or code.get("attendance_code") or code.name,
				"count": count,
				"count_as_present": int(code.get("count_as_present") or 0),
				"is_late": is_late,
				"is_excused": is_excused,
				"usage_share": share,
			}
		)

	codes_payload.sort(key=lambda row: row["count"], reverse=True)
	unused_codes = [row for row in codes_payload if row["count"] == 0]

	return {
		"meta": _response_meta(ctx),
		"codes": codes_payload,
		"summary": {
			"total_records": total_count,
			"unused_codes": len(unused_codes),
			"dominant_absence_code": _dominant_absence_code(codes_payload),
		},
	}


def _dominant_absence_code(codes_payload: list[dict[str, Any]]) -> str | None:
	absent_codes = [row for row in codes_payload if row.get("count_as_present") == 0 and row.get("count", 0) > 0]
	if not absent_codes:
		return None
	absent_codes.sort(key=lambda row: row.get("count", 0), reverse=True)
	return absent_codes[0].get("attendance_code")


def _get_my_groups_payload(ctx: dict[str, Any], *, thresholds: dict[str, float]) -> dict[str, Any]:
	group_scope = ctx.get("group_scope") or []
	if not group_scope:
		return {
			"meta": _response_meta(ctx),
			"groups": [],
			"emerging_patterns": [],
			"exceptions": [],
			"improving_trends": [],
		}

	where_clause, params = _build_attendance_where(
		ctx=ctx,
		alias="a",
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
		whole_day=ctx["whole_day"],
		include_group_filter=True,
	)

	group_rows = frappe.db.sql(
		f"""
		SELECT
			a.student_group,
			MAX(sg.student_group_abbreviation) AS student_group_abbreviation,
			MAX(sg.student_group_name) AS student_group_name,
			MAX(sg.group_based_on) AS group_based_on,
			COUNT(*) AS expected,
			SUM(CASE WHEN c.count_as_present = 1 THEN 1 ELSE 0 END) AS present,
			SUM(CASE WHEN c.count_as_present = 0 THEN 1 ELSE 0 END) AS absent,
			SUM(CASE WHEN {LATE_SQL} THEN 1 ELSE 0 END) AS late
		FROM `tabStudent Attendance` a
		INNER JOIN `tabStudent Attendance Code` c ON c.name = a.attendance_code
		LEFT JOIN `tabStudent Group` sg ON sg.name = a.student_group
		WHERE {where_clause}
		GROUP BY a.student_group
		ORDER BY student_group_name ASC
		LIMIT 200
		""",
		params,
		as_dict=True,
	)

	groups = [
		{
			"student_group": row.get("student_group"),
			"student_group_abbreviation": row.get("student_group_abbreviation") or row.get("student_group") or "",
			"student_group_name": row.get("student_group_name") or row.get("student_group") or "",
			"group_based_on": row.get("group_based_on"),
			"expected": int(row.get("expected") or 0),
			"present": int(row.get("present") or 0),
			"absent": int(row.get("absent") or 0),
			"late": int(row.get("late") or 0),
		}
		for row in group_rows
		if row.get("student_group")
	]

	current_metrics = _compute_student_metrics(
		ctx=ctx,
		date_from=ctx["date_from"],
		date_to=ctx["date_to"],
		instruction_days=ctx["valid_instruction_days"],
		include_group_filter=True,
	)
	previous_metrics = _compute_student_metrics(
		ctx=ctx,
		date_from=ctx["previous_date_from"],
		date_to=ctx["previous_date_to"],
		instruction_days=ctx["previous_instruction_days"],
		include_group_filter=True,
	)
	block_1_counts = _compute_block_1_pattern_counts(ctx)

	warning = thresholds["warning"]
	emerging_patterns: list[dict[str, Any]] = []
	improving_trends: list[dict[str, Any]] = []
	for student, current in current_metrics.items():
		absent = int(current.get("absent_sessions") or 0)
		late = int(current.get("late_sessions") or 0)
		block_1 = int(block_1_counts.get(student) or 0)
		if absent >= 2 or late >= 2 or block_1 >= 2:
			emerging_patterns.append(
				{
					"student": student,
					"student_name": current.get("student_name") or student,
					"absent_count": absent,
					"late_count": late,
					"pattern_absent_block_1": block_1,
					"attendance_rate": float(current.get("attendance_rate") or 0),
				}
			)

		previous = previous_metrics.get(student) or {}
		previous_rate = float(previous.get("attendance_rate") or 0)
		current_rate = float(current.get("attendance_rate") or 0)
		was_risk = (
			previous_rate < warning
			or int(previous.get("unexplained_absences") or 0) >= 2
			or int(previous.get("late_sessions") or 0) >= 2
		)
		now_clean = current_rate >= warning and int(current.get("unexplained_absences") or 0) == 0
		if was_risk and now_clean:
			improving_trends.append(
				{
					"student": student,
					"student_name": current.get("student_name") or student,
					"previous_rate": previous_rate,
					"current_rate": current_rate,
					"delta": round(current_rate - previous_rate, 2),
				}
			)

	emerging_patterns.sort(key=lambda row: (row["absent_count"], row["late_count"], row["pattern_absent_block_1"]), reverse=True)
	improving_trends.sort(key=lambda row: row["delta"], reverse=True)

	exceptions = _compute_teacher_exceptions(ctx)

	return {
		"meta": _response_meta(ctx),
		"groups": groups,
		"emerging_patterns": emerging_patterns[:120],
		"exceptions": exceptions,
		"improving_trends": improving_trends[:120],
	}


def _compute_teacher_exceptions(ctx: dict[str, Any]) -> list[dict[str, Any]]:
	group_scope = ctx.get("group_scope") or []
	if not group_scope:
		return []

	instruction_days = ctx.get("valid_instruction_days") or []
	exception_date = getdate(instruction_days[-1]) if instruction_days else ctx["date_to"]
	params: dict[str, Any] = {
		"group_scope": tuple(group_scope),
		"school_scope": tuple(ctx["school_scope"]),
		"exception_date": exception_date,
		"whole_day": ctx["whole_day"],
	}
	optional_conditions = []
	if ctx.get("program"):
		optional_conditions.append("AND sg.program = %(program)s")
		params["program"] = ctx["program"]
	if ctx.get("student_group"):
		optional_conditions.append("AND sg.name = %(student_group)s")
		params["student_group"] = ctx["student_group"]
	if ctx.get("activity_only"):
		optional_conditions.append("AND sg.group_based_on = 'Activity'")

	rows = frappe.db.sql(
		f"""
		SELECT
			sgs.parent AS student_group,
			MAX(sg.student_group_abbreviation) AS student_group_abbreviation,
			sgs.student,
			MAX(sgs.student_name) AS student_name,
			CASE
				WHEN agg.total_rows IS NULL THEN 'No record'
				WHEN agg.absent_rows > 0 AND agg.present_rows = 0 THEN 'Absent'
				WHEN agg.late_rows > 0 THEN 'Late'
				ELSE 'Present'
			END AS status
		FROM `tabStudent Group Student` sgs
		INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
		LEFT JOIN (
			SELECT
				a.student_group,
				a.student,
				COUNT(*) AS total_rows,
				SUM(CASE WHEN c.count_as_present = 1 THEN 1 ELSE 0 END) AS present_rows,
				SUM(CASE WHEN c.count_as_present = 0 THEN 1 ELSE 0 END) AS absent_rows,
				SUM(CASE WHEN {LATE_SQL} THEN 1 ELSE 0 END) AS late_rows
			FROM `tabStudent Attendance` a
			INNER JOIN `tabStudent Attendance Code` c ON c.name = a.attendance_code
			WHERE a.student_group IN %(group_scope)s
				AND a.school IN %(school_scope)s
				AND a.attendance_date = %(exception_date)s
				AND a.whole_day = %(whole_day)s
			GROUP BY a.student_group, a.student
		) agg ON agg.student_group = sgs.parent AND agg.student = sgs.student
		WHERE sgs.parent IN %(group_scope)s
			AND COALESCE(sgs.active, 0) = 1
			{' '.join(optional_conditions)}
		GROUP BY sgs.parent, sgs.student
		ORDER BY sg.student_group_name ASC, student_name ASC
		LIMIT 200
		""",
		params,
		as_dict=True,
	)

	exceptions: list[dict[str, Any]] = []
	for row in rows:
		status = row.get("status")
		if status == "Present":
			continue
		exceptions.append(
			{
				"student_group": row.get("student_group"),
				"student_group_abbreviation": row.get("student_group_abbreviation") or row.get("student_group") or "",
				"student": row.get("student"),
				"student_name": row.get("student_name") or row.get("student"),
				"status": status,
			}
		)

	return exceptions


def _response_meta(ctx: dict[str, Any]) -> dict[str, Any]:
	return {
		"role_class": ctx["role_class"],
		"school_scope": ctx["school_scope"],
		"date_from": ctx["date_from"].isoformat(),
		"date_to": ctx["date_to"].isoformat(),
		"window_source": ctx.get("window_source") or "",
		"whole_day": int(ctx.get("whole_day") or 0),
		"activity_only": int(ctx.get("activity_only") or 0),
	}


def _fetch_cached_result(
	*,
	mode: str,
	ctx: dict[str, Any],
	ttl_seconds: int,
	extra: dict[str, Any],
	compute: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
	cache_payload = {
		"mode": mode,
		"user": ctx.get("user"),
		"role_class": ctx.get("role_class"),
		"schools": sorted(ctx.get("school_scope") or []),
		"groups": sorted(ctx.get("group_scope") or []),
		"students_hash": _hash_list(ctx.get("student_scope") or []),
		"date_from": (ctx.get("date_from") or getdate(nowdate())).isoformat(),
		"date_to": (ctx.get("date_to") or getdate(nowdate())).isoformat(),
		"window_source": ctx.get("window_source"),
		"program": ctx.get("program"),
		"student_group": ctx.get("student_group"),
		"whole_day": ctx.get("whole_day"),
		"activity_only": ctx.get("activity_only"),
		"extra": extra,
	}
	cache_key = "ifitwala_ed:attendance:analytics:" + hashlib.sha1(
		json.dumps(cache_payload, sort_keys=True, default=str).encode("utf-8")
	).hexdigest()

	cached = frappe.cache().get_value(cache_key)
	if cached:
		if isinstance(cached, dict):
			return cached
		try:
			parsed = frappe.parse_json(cached)
			if isinstance(parsed, dict):
				return parsed
		except Exception:
			pass

	payload = compute()
	frappe.cache().set_value(cache_key, frappe.as_json(payload), expires_in_sec=ttl_seconds)
	return payload


def _hash_list(values: list[str]) -> str:
	if not values:
		return ""
	return hashlib.sha1(",".join(sorted(values)).encode("utf-8")).hexdigest()


def _clean_optional(value: str | None) -> str | None:
	if not value:
		return None
	cleaned = value.strip()
	return cleaned or None
