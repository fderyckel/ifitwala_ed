# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/enrollment_analytics.py

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

import frappe
from frappe.utils import getdate, nowdate

from ifitwala_ed.api.student_log_dashboard import get_authorized_schools
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org
from ifitwala_ed.utilities.school_tree import get_descendant_schools


ALLOWED_ANALYTICS_ROLES = {
	"Academic Admin",
	"Grade Level Lead",
	"Counsellor",
	"Curriculum Coordinator",
	"Admissions Officer",
	"Admissions Manager",
	"System Manager",
	"Administrator",
}

INSTRUCTOR_ROLES = {"Instructor", "Academic Staff"}

CACHE_TTL_SECONDS = 600
DEFAULT_TOP_N = 8
MAX_YEARS = 5


def _parse_payload(payload: Any | None) -> dict:
	if isinstance(payload, str):
		try:
			payload = frappe.parse_json(payload) or {}
		except Exception:
			payload = {}
	payload = payload or {}
	if isinstance(payload, dict) and payload.get("filters"):
		payload = payload.get("filters") or {}
	return payload or {}


def _clean_link(value):
	if value is None:
		return None
	if isinstance(value, str):
		val = value.strip()
		return val or None
	return value


def _normalize_academic_years(value) -> list[str]:
	if not value:
		return []
	if isinstance(value, str):
		try:
			parsed = frappe.parse_json(value)
			if isinstance(parsed, list):
				return [str(v) for v in parsed if v]
		except Exception:
			parts = [v.strip() for v in value.split(",")]
			return [p for p in parts if p]
	if isinstance(value, (list, tuple)):
		return [str(v) for v in value if v]
	return []


def _normalize_filters(payload: dict) -> dict:
	compare_dimension = (payload.get("compare_dimension") or "school").strip().lower()
	if compare_dimension not in {"school", "program"}:
		compare_dimension = "school"

	chart_mode = (payload.get("chart_mode") or "snapshot").strip().lower()
	if chart_mode not in {"snapshot", "trend"}:
		chart_mode = "snapshot"

	return {
		"organization": _clean_link(payload.get("organization")),
		"school": _clean_link(payload.get("school")),
		"academic_years": _normalize_academic_years(payload.get("academic_years")),
		"compare_dimension": compare_dimension,
		"chart_mode": chart_mode,
		"as_of_date": payload.get("as_of_date") or nowdate(),
		"period_from": payload.get("period_from"),
		"period_to": payload.get("period_to"),
		"program": _clean_link(payload.get("program")),
		"cohort": _clean_link(payload.get("cohort")),
		"program_offering": _clean_link(payload.get("program_offering")),
		"top_n": int(payload.get("top_n") or DEFAULT_TOP_N),
	}


def _get_access_context(user: str | None = None) -> dict:
	user = user or frappe.session.user
	if not user or user == "Guest":
		frappe.throw("You need to sign in to access Enrollment Analytics.", frappe.PermissionError)

	roles = set(frappe.get_roles(user))
	if roles & ALLOWED_ANALYTICS_ROLES:
		return {"user": user, "mode": "full"}

	if roles & INSTRUCTOR_ROLES:
		has_students = frappe.db.sql(
			"""
			SELECT 1
			FROM `tabStudent Group Instructor` sgi
			JOIN `tabStudent Group Student` sgs ON sgi.parent = sgs.parent
			JOIN `tabStudent Group` sg ON sg.name = sgs.parent
			WHERE sgi.user_id = %(user)s
				AND COALESCE(sgs.active, 0) = 1
				AND IFNULL(sg.status, 'Active') = 'Active'
			LIMIT 1
			""",
			{"user": user},
		)
		if has_students:
			return {"user": user, "mode": "instructor"}

	frappe.throw("You do not have permission to access Enrollment Analytics.", frappe.PermissionError)
	return {"user": user, "mode": "full"}


def _resolve_scope(filters: dict, ctx: dict) -> dict:
	user = ctx["user"]

	authorized_schools = get_authorized_schools(user) or []
	base_school = authorized_schools[0] if authorized_schools else None

	base_org = get_user_base_org(user)
	if not base_org and base_school:
		base_org = frappe.db.get_value("School", base_school, "organization")

	org_scope = get_descendant_organizations(base_org) if base_org else []
	if base_org and base_org not in org_scope:
		org_scope = [base_org]

	selected_org = filters.get("organization") or base_org
	if selected_org and org_scope and selected_org not in org_scope:
		frappe.throw("You do not have access to this organization.", frappe.PermissionError)

	allowed_schools = authorized_schools
	if not allowed_schools and org_scope:
		allowed_schools = frappe.get_all(
			"School",
			filters={"organization": ["in", org_scope]},
			pluck="name",
		)

	selected_org_scope = (
		get_descendant_organizations(selected_org) if selected_org else []
	)
	if selected_org and selected_org not in selected_org_scope:
		selected_org_scope = [selected_org]

	if selected_org_scope:
		org_schools = frappe.get_all(
			"School",
			filters={"organization": ["in", selected_org_scope]},
			pluck="name",
		)
		if allowed_schools:
			allowed_schools = [s for s in allowed_schools if s in org_schools]
		else:
			allowed_schools = org_schools

	if selected_org_scope and not allowed_schools:
		selected_school = filters.get("school")
	else:
		selected_school = filters.get("school") or (allowed_schools[0] if allowed_schools else base_school)

	if selected_school and allowed_schools and selected_school not in allowed_schools:
		frappe.throw("You do not have access to this school.", frappe.PermissionError)

	school_scope = get_descendant_schools(selected_school) if selected_school else []
	if allowed_schools and school_scope:
		school_scope = [s for s in school_scope if s in allowed_schools]

	return {
		"organization": selected_org,
		"organization_scope": org_scope,
		"school": selected_school,
		"school_scope": school_scope,
		"authorized_schools": allowed_schools,
	}


def _load_academic_year_options(school_scope: list[str]) -> list[dict]:
	if not school_scope:
		return []

	rows = frappe.db.sql(
		"""
		SELECT DISTINCT
			pe.academic_year,
			pe.school,
			s.school_name,
			ay.academic_year_name,
			ay.year_start_date,
			ay.year_end_date
		FROM `tabProgram Enrollment` pe
		LEFT JOIN `tabSchool` s ON s.name = pe.school
		LEFT JOIN `tabAcademic Year` ay ON ay.name = pe.academic_year
		WHERE pe.school IN %(schools)s
		  AND pe.academic_year IS NOT NULL
		ORDER BY ay.year_start_date DESC, pe.academic_year DESC, pe.school ASC
		""",
		{"schools": tuple(school_scope)},
		as_dict=True,
	)

	if not rows:
		rows = frappe.get_all(
			"Academic Year",
			filters={"school": ["in", school_scope]},
			fields=[
				"name as academic_year",
				"academic_year_name",
				"year_start_date",
				"year_end_date",
				"school",
			],
			order_by="year_start_date desc",
		)

	options = []
	for row in rows or []:
		name = row.get("academic_year")
		if not name:
			continue
		options.append(
			{
				"name": name,
				"label": row.get("academic_year_name") or name,
				"year_start_date": row.get("year_start_date"),
				"year_end_date": row.get("year_end_date"),
				"school": row.get("school"),
				"school_label": row.get("school_name"),
			}
		)

	schools_missing = {opt.get("school") for opt in options if opt.get("school") and not opt.get("school_label")}
	if schools_missing:
		school_rows = frappe.get_all(
			"School",
			filters={"name": ["in", list(schools_missing)]},
			fields=["name", "school_name"],
		)
		school_labels = {row.name: row.school_name for row in school_rows}
		for opt in options:
			if opt.get("school") and not opt.get("school_label"):
				opt["school_label"] = school_labels.get(opt["school"])

	return options


def _default_academic_years(options: list[dict], count: int = 2) -> list[str]:
	names = [row["name"] for row in options if row.get("name")]
	if not names:
		return []
	return names[: min(count, len(names))]


def _normalize_academic_year_selection(filters: dict, options: list[dict]) -> list[str]:
	selected = [y for y in filters.get("academic_years") or [] if y]
	unique = []
	for y in selected:
		if y not in unique:
			unique.append(y)

	if len(unique) >= 2:
		return unique[:MAX_YEARS]

	target_school = filters.get("school")
	by_school: dict[str, list[dict]] = {}
	for row in options or []:
		school = row.get("school")
		if not school:
			continue
		by_school.setdefault(school, []).append(row)

	def _sorted_names(rows: list[dict]) -> list[str]:
		rows = sorted(
			rows,
			key=lambda r: r.get("year_start_date") or r.get("name") or "",
			reverse=True,
		)
		return [r["name"] for r in rows if r.get("name")]

	if target_school and by_school.get(target_school):
		names = _sorted_names(by_school[target_school])
		if len(names) >= 2:
			return names[:2]
		if names:
			return names[:1]

	for school, rows in by_school.items():
		names = _sorted_names(rows)
		if len(names) >= 2:
			return names[:2]
		if names:
			return names[:1]

	if unique:
		return unique[:MAX_YEARS]

	available = [row["name"] for row in options if row.get("name")]
	return available[:1]


def _resolve_period(filters: dict, options: list[dict]) -> tuple[str, str]:
	if filters.get("period_from") and filters.get("period_to"):
		return str(filters["period_from"]), str(filters["period_to"])

	selected = set(filters.get("academic_years") or [])
	years = [row for row in options if row.get("name") in selected]

	starts = [row.get("year_start_date") for row in years if row.get("year_start_date")]
	ends = [row.get("year_end_date") for row in years if row.get("year_end_date")]

	period_from = min(starts) if starts else None
	period_to = max(ends) if ends else None

	if filters.get("as_of_date") and period_to:
		try:
			as_of = getdate(filters["as_of_date"])
			if as_of and getdate(period_to) > as_of:
				period_to = as_of
		except Exception:
			pass

	if not period_to:
		period_to = getdate(filters.get("as_of_date") or nowdate())
	if not period_from:
		period_from = period_to

	if isinstance(period_from, date):
		period_from = period_from.isoformat()
	if isinstance(period_to, date):
		period_to = period_to.isoformat()

	return str(period_from), str(period_to)


def _base_query_parts(filters: dict, ctx: dict, *, include_as_of: bool = False, archived: int | None = None):
	conditions = []
	params: dict[str, Any] = {}
	joins = []

	if ctx.get("mode") == "instructor":
		joins.append(
			"""
			JOIN `tabStudent Group Student` sgs ON sgs.student = pe.student
			JOIN `tabStudent Group Instructor` sgi ON sgi.parent = sgs.parent
			JOIN `tabStudent Group` sg ON sg.name = sgs.parent
			"""
		)
		conditions.append("sgi.user_id = %(user)s")
		conditions.append("COALESCE(sgs.active, 0) = 1")
		conditions.append("IFNULL(sg.status, 'Active') = 'Active'")
		params["user"] = ctx["user"]

	if ctx.get("school_scope") is not None:
		if ctx["school_scope"]:
			conditions.append("pe.school IN %(schools)s")
			params["schools"] = tuple(ctx["school_scope"])
		else:
			conditions.append("1=0")

	if filters.get("academic_years"):
		conditions.append("pe.academic_year IN %(years)s")
		params["years"] = tuple(filters["academic_years"])

	if filters.get("program"):
		conditions.append("pe.program = %(program)s")
		params["program"] = filters["program"]

	if filters.get("cohort"):
		conditions.append("pe.cohort = %(cohort)s")
		params["cohort"] = filters["cohort"]

	if filters.get("program_offering"):
		conditions.append("pe.program_offering = %(program_offering)s")
		params["program_offering"] = filters["program_offering"]

	if include_as_of and filters.get("as_of_date"):
		conditions.append("pe.enrollment_date <= %(as_of_date)s")
		params["as_of_date"] = filters["as_of_date"]

	if archived is not None:
		conditions.append("pe.archived = %(archived)s")
		params["archived"] = int(archived)

	where_clause = " AND ".join(conditions) if conditions else "1=1"
	return " ".join(joins), where_clause, params


def _stacked_snapshot(filters: dict, ctx: dict) -> dict:
	compare_dimension = filters.get("compare_dimension") or "school"
	if compare_dimension not in {"school", "program"}:
		compare_dimension = "school"

	join_clause, where_clause, params = _base_query_parts(
		filters, ctx, include_as_of=True, archived=0
	)

	if compare_dimension == "program":
		label_join = "LEFT JOIN `tabProgram` p ON p.name = pe.program"
		bucket_col = "pe.program"
		label_col = "COALESCE(p.program_name, pe.program)"
	else:
		label_join = "LEFT JOIN `tabSchool` s ON s.name = pe.school"
		bucket_col = "pe.school"
		label_col = "COALESCE(s.school_name, pe.school)"

	rows = frappe.db.sql(
		f"""
		SELECT
			pe.academic_year AS category,
			{bucket_col} AS bucket,
			{label_col} AS bucket_label,
			COUNT(*) AS value
		FROM `tabProgram Enrollment` pe
		{join_clause}
		{label_join}
		WHERE {where_clause}
		GROUP BY pe.academic_year, bucket, bucket_label
		""",
		params,
		as_dict=True,
	)

	series_totals: dict[str, int] = {}
	series_labels: dict[str, str] = {}
	value_map: dict[tuple[str, str], int] = {}

	for row in rows or []:
		bucket = row.get("bucket")
		if not bucket:
			continue
		category = row.get("category") or ""
		value = int(row.get("value") or 0)
		value_map[(category, bucket)] = value
		series_totals[bucket] = series_totals.get(bucket, 0) + value
		series_labels[bucket] = row.get("bucket_label") or bucket

	series_keys = [k for k, _ in sorted(series_totals.items(), key=lambda kv: kv[1], reverse=True)]
	series = [{"key": k, "label": series_labels.get(k, k)} for k in series_keys]

	categories = filters.get("academic_years") or []
	series_rows = []

	for category in categories:
		values: dict[str, int] = {}
		slice_keys: dict[str, str] = {}
		for s in series_keys:
			values[s] = value_map.get((category, s), 0)
			slice_keys[s] = json.dumps(
				{
					"type": "stack",
					"dimension": compare_dimension,
					"key": s,
					"bucket": category,
				},
				separators=(",", ":"),
			)
		series_rows.append(
			{
				"category": category,
				"values": values,
				"sliceKeys": slice_keys,
			}
		)

	return {"series": series, "rows": series_rows}


def _topn_items(filters: dict, ctx: dict, *, dimension: str, total_active: int) -> list[dict]:
	join_clause, where_clause, params = _base_query_parts(
		filters, ctx, include_as_of=True, archived=0
	)
	limit = max(1, min(int(filters.get("top_n") or DEFAULT_TOP_N), 25))
	params["limit"] = limit

	if dimension == "program":
		label_join = "LEFT JOIN `tabProgram` p ON p.name = pe.program"
		label_col = "COALESCE(p.program_name, pe.program)"
		bucket_col = "pe.program"
	else:
		label_join = ""
		label_col = "pe.cohort"
		bucket_col = "pe.cohort"

	rows = frappe.db.sql(
		f"""
		SELECT
			{bucket_col} AS bucket,
			{label_col} AS label,
			COUNT(*) AS value
		FROM `tabProgram Enrollment` pe
		{join_clause}
		{label_join}
		WHERE {where_clause}
		  AND {bucket_col} IS NOT NULL
		  AND {bucket_col} != ''
		GROUP BY bucket, label
		ORDER BY value DESC
		LIMIT %(limit)s
		""",
		params,
		as_dict=True,
	)

	items = []
	for row in rows or []:
		bucket = row.get("bucket")
		if not bucket:
			continue
		count = int(row.get("value") or 0)
		pct = round((count / total_active) * 100, 1) if total_active else 0
		items.append(
			{
				"label": row.get("label") or bucket,
				"count": count,
				"pct": pct,
				"sliceKey": json.dumps(
					{
						"type": "topn",
						"dimension": dimension,
						"key": bucket,
					},
					separators=(",", ":"),
				),
			}
		)
	return items


def _cache_key(user: str, filters: dict) -> str:
	payload = {
		"user": user,
		"filters": filters,
	}
	raw = json.dumps(payload, sort_keys=True, default=str)
	digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
	return f"ifitwala_ed:enrollment_dashboard:{digest}"


def _load_filter_options(ctx: dict) -> dict:
	org_scope = ctx.get("organization_scope") or []
	school_scope = ctx.get("authorized_schools") or []

	org_rows = []
	if org_scope:
		org_rows = frappe.get_all(
			"Organization",
			filters={"name": ["in", org_scope]},
			fields=["name", "organization_name", "abbr"],
			order_by="lft",
		)

	school_rows = []
	if school_scope:
		school_rows = frappe.get_all(
			"School",
			filters={"name": ["in", school_scope]},
			fields=["name", "school_name", "abbr", "organization"],
			order_by="lft",
		)

	return {
		"organizations": org_rows,
		"schools": school_rows,
		"academic_years": _load_academic_year_options(ctx.get("school_scope") or []),
	}


@frappe.whitelist()
def get_enrollment_dashboard(payload=None):
	ctx = _get_access_context()
	raw = _parse_payload(payload)
	filters = _normalize_filters(raw)

	scope = _resolve_scope(filters, ctx)
	filters["organization"] = scope.get("organization")
	filters["school"] = scope.get("school")
	ctx = {**ctx, **scope}

	filter_options = _load_filter_options(ctx)
	filters["academic_years"] = _normalize_academic_year_selection(filters, filter_options["academic_years"])

	period_from, period_to = _resolve_period(filters, filter_options["academic_years"])
	filters["period_from"] = period_from
	filters["period_to"] = period_to

	cache_key = _cache_key(ctx["user"], filters)
	cache = frappe.cache()
	cached = cache.get_value(cache_key)
	if cached:
		return cached

	join_clause, where_clause, params = _base_query_parts(
		filters, ctx, include_as_of=(filters.get("chart_mode") == "snapshot")
	)
	params["period_from"] = period_from
	params["period_to"] = period_to

	kpi_row = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN pe.archived = 0 THEN 1 ELSE 0 END) AS active,
			SUM(CASE WHEN pe.archived = 1 THEN 1 ELSE 0 END) AS archived,
			SUM(
				CASE WHEN pe.enrollment_date >= %(period_from)s
				 AND pe.enrollment_date <= %(period_to)s THEN 1 ELSE 0 END
			) AS new_in_period
		FROM `tabProgram Enrollment` pe
		{join_clause}
		WHERE {where_clause}
		""",
		params,
		as_dict=True,
	)
	kpi_row = (kpi_row or [{}])[0]

	drops_row = frappe.db.sql(
		f"""
		SELECT COUNT(*) AS drops_in_period
		FROM `tabProgram Enrollment Course` pec
		JOIN `tabProgram Enrollment` pe ON pe.name = pec.parent
		{join_clause}
		WHERE {where_clause}
		  AND pec.parenttype = 'Program Enrollment'
		  AND pec.status = 'Dropped'
		  AND pec.dropped_date >= %(period_from)s
		  AND pec.dropped_date <= %(period_to)s
		""",
		params,
		as_dict=True,
	)
	drops_in_period = int((drops_row or [{}])[0].get("drops_in_period") or 0)

	active = int(kpi_row.get("active") or 0)
	new_in_period = int(kpi_row.get("new_in_period") or 0)
	archived = int(kpi_row.get("archived") or 0)
	net_change = new_in_period - drops_in_period

	stacked_chart = _stacked_snapshot(filters, ctx)

	topn = {
		"cohorts": _topn_items(filters, ctx, dimension="cohort", total_active=active),
		"programs": _topn_items(filters, ctx, dimension="program", total_active=active),
	}

	payload_out = {
		"kpis": {
			"active": active,
			"new_in_period": new_in_period,
			"drops_in_period": drops_in_period,
			"net_change": net_change,
			"archived": archived,
		},
		"stacked_chart": stacked_chart,
		"topn": topn,
		"meta": {
			"generated_at": nowdate(),
			"filters_echo": {
				**filters,
				"school_scope": ctx.get("school_scope") or [],
			},
			"options": filter_options,
			"defaults": {
				"organization": filters.get("organization"),
				"school": filters.get("school"),
				"academic_years": filters.get("academic_years"),
				"compare_dimension": filters.get("compare_dimension"),
				"chart_mode": filters.get("chart_mode"),
				"as_of_date": filters.get("as_of_date"),
				"period_from": period_from,
				"period_to": period_to,
				"top_n": filters.get("top_n"),
			},
			"trend_enabled": False,
		},
	}

	cache.set_value(cache_key, payload_out, expires_in_sec=CACHE_TTL_SECONDS)
	return payload_out


def _slice_filters(
	filters: dict,
	ctx: dict,
	slice_data: dict,
	*,
	include_as_of: bool = False,
	archived: int | None = None,
):
	join_clause, where_clause, params = _base_query_parts(
		filters, ctx, include_as_of=include_as_of, archived=archived
	)

	dimension = slice_data.get("dimension")
	key = slice_data.get("key")
	bucket = slice_data.get("bucket")

	if slice_data.get("type") == "stack":
		if dimension == "school":
			where_clause += " AND pe.school = %(slice_key)s"
		elif dimension == "program":
			where_clause += " AND pe.program = %(slice_key)s"
		if bucket:
			where_clause += " AND pe.academic_year = %(slice_bucket)s"
		params["slice_key"] = key
		params["slice_bucket"] = bucket

	if slice_data.get("type") == "topn":
		if dimension == "cohort":
			where_clause += " AND pe.cohort = %(slice_key)s"
		elif dimension == "program":
			where_clause += " AND pe.program = %(slice_key)s"
		params["slice_key"] = key

	return join_clause, where_clause, params


def _drilldown_rows(
	filters: dict,
	ctx: dict,
	where_clause: str,
	params: dict,
	start: int,
	page_length: int,
	*,
	distinct: bool = False,
	joins: str = "",
):
	distinct_clause = "DISTINCT" if distinct else ""
	rows = frappe.db.sql(
		f"""
		SELECT {distinct_clause}
			pe.name AS id,
			pe.student_name,
			pe.cohort,
			pe.program,
			COALESCE(p.program_name, pe.program) AS program_label,
			pe.school,
			COALESCE(s.school_name, pe.school) AS school_label,
			pe.enrollment_date
		FROM `tabProgram Enrollment` pe
		LEFT JOIN `tabSchool` s ON s.name = pe.school
		LEFT JOIN `tabProgram` p ON p.name = pe.program
		{joins}
		WHERE {where_clause}
		ORDER BY pe.enrollment_date DESC, pe.name DESC
		LIMIT %(start)s, %(page_length)s
		""",
		{**params, "start": start, "page_length": page_length},
		as_dict=True,
	)

	count_expr = "COUNT(DISTINCT pe.name)" if distinct else "COUNT(*)"
	total_count = frappe.db.sql(
		f"""
		SELECT {count_expr}
		FROM `tabProgram Enrollment` pe
		{joins}
		WHERE {where_clause}
		""",
		params,
	)[0][0]

	return rows or [], int(total_count or 0)


@frappe.whitelist()
def get_enrollment_drilldown(payload=None):
	ctx = _get_access_context()
	raw = _parse_payload(payload)
	filters = _normalize_filters(raw)

	scope = _resolve_scope(filters, ctx)
	filters["organization"] = scope.get("organization")
	filters["school"] = scope.get("school")
	ctx = {**ctx, **scope}

	slice_data = raw.get("slice") or {}
	if isinstance(slice_data, str):
		try:
			slice_data = frappe.parse_json(slice_data) or {}
		except Exception:
			slice_data = {}

	start = int(raw.get("start") or 0)
	page_length = int(raw.get("page_length") or 50)

	period_from, period_to = _resolve_period(filters, _load_academic_year_options(ctx.get("school_scope") or []))
	filters["period_from"] = period_from
	filters["period_to"] = period_to

	if slice_data.get("type") == "kpi":
		key = slice_data.get("key")
		if key == "archived":
			join_clause, where_clause, params = _base_query_parts(filters, ctx, archived=1)
			return_rows, total = _drilldown_rows(
				filters, ctx, where_clause, params, start, page_length
			)
			return {"rows": return_rows, "total_count": total}

		if key == "new":
			join_clause, where_clause, params = _base_query_parts(filters, ctx)
			where_clause += " AND pe.enrollment_date >= %(period_from)s AND pe.enrollment_date <= %(period_to)s"
			params["period_from"] = period_from
			params["period_to"] = period_to
			return_rows, total = _drilldown_rows(
				filters, ctx, where_clause, params, start, page_length
			)
			return {"rows": return_rows, "total_count": total}

		if key == "drops":
			join_clause, where_clause, params = _base_query_parts(filters, ctx)
			where_clause += " AND pec.status = 'Dropped' AND pec.dropped_date >= %(period_from)s AND pec.dropped_date <= %(period_to)s"
			params["period_from"] = period_from
			params["period_to"] = period_to
			joins = (
				join_clause
				+ " JOIN `tabProgram Enrollment Course` pec ON pec.parent = pe.name AND pec.parenttype = 'Program Enrollment'"
			)
			return_rows, total = _drilldown_rows(
				filters, ctx, where_clause, params, start, page_length, distinct=True, joins=joins
			)
			return {"rows": return_rows, "total_count": total}

		if key == "net_change":
			slice_data["key"] = "new"
			slice_data["type"] = "kpi"
			return get_enrollment_drilldown(
				{
					**raw,
					"slice": slice_data,
				}
			)

		# Default KPI = active
		join_clause, where_clause, params = _base_query_parts(
			filters, ctx, include_as_of=(filters.get("chart_mode") == "snapshot"), archived=0
		)
		return_rows, total = _drilldown_rows(filters, ctx, where_clause, params, start, page_length)
		return {"rows": return_rows, "total_count": total}

	join_clause, where_clause, params = _slice_filters(
		filters,
		ctx,
		slice_data,
		include_as_of=(filters.get("chart_mode") == "snapshot"),
		archived=0,
	)
	return_rows, total = _drilldown_rows(
		filters,
		ctx,
		where_clause,
		params,
		start,
		page_length,
		joins=join_clause,
	)
	return {"rows": return_rows, "total_count": total}
