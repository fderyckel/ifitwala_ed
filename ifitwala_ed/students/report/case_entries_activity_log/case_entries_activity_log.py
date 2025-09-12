# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/report/case_entries_activity_log/case_entries_activity_log.py

import re
from collections import defaultdict
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import getdate, formatdate, strip_html


ALLOWED = {"Counselor", "Academic Admin"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_guard_roles()

	# Dates (inclusive)
	date_from = getdate(filters.get("from_date")) if filters.get("from_date") else None
	date_to   = getdate(filters.get("to_date"))   if filters.get("to_date")   else None

	where, params = _build_where(filters, date_from, date_to)

	# ── Main query (note Employee join by user_id → employee_full_name) ──
	q = f"""
		SELECT
			rce.entry_datetime,
			DATE(rce.entry_datetime)           AS entry_date,
			rc.name                            AS referral_case,
			rc.referral                        AS referral,
			rc.student                         AS student,
			s.student_full_name                AS student_full_name,
			rc.school                          AS school,
			rc.program                         AS program,
			rc.academic_year                   AS academic_year,
			rc.case_manager                    AS case_manager,
			u.full_name                        AS user_full_name,
			e.employee_full_name               AS employee_full_name,
			rc.severity                        AS case_severity,
			rc.case_status                     AS case_status,
			rce.entry_type                     AS entry_type,
			rce.assignee                       AS assignee,
			rce.status                         AS entry_status,
			rce.summary                        AS summary_raw
		FROM `tabReferral Case` rc
		JOIN `tabReferral Case Entry` rce
		      ON rce.parent = rc.name
		LEFT JOIN `tabStudent` s
		      ON s.name = rc.student
		LEFT JOIN `tabUser` u
		      ON u.name = rc.case_manager
		LEFT JOIN `tabEmployee` e
		      ON e.user_id = rc.case_manager
		{('WHERE ' + ' AND '.join(where)) if where else ''}
		ORDER BY rce.entry_datetime DESC, rc.name ASC
	"""
	rows = frappe.db.sql(q, params, as_dict=True)

	# ── Presentational enrichments (no extra queries) ───────────────────
	for r in rows:
		# Pretty date (e.g., 9 September 2025)
		r["entry_date_pretty"] = formatdate(r["entry_date"], "d MMMM yyyy")

		# Linked student name
		full = r.get("student_full_name") or r.get("student") or ""
		sid  = r.get("student") or ""
		r["student_link"] = (
			f'<a href="/app/student/{frappe.utils.escape_html(sid)}" target="_blank" rel="noopener">'
			f'{frappe.utils.escape_html(full)}</a>'
		)

		# Case manager display: Employee > User.full_name > user id
		cm_emp = (r.get("employee_full_name") or "").strip()
		cm_usr = (r.get("user_full_name") or "").strip()
		r["case_manager_name"] = cm_emp or cm_usr or (r.get("case_manager") or "")

		# Nicer snippet
		snippet = strip_html(r.get("summary_raw") or "")
		snippet = re.sub(r"\s+", " ", snippet).strip()
		if len(snippet) > 220:
			snippet = snippet[:220].rsplit(" ", 1)[0] + "…"
		r["summary_snippet"] = (
			f'<div class="text-muted small" style="border-left:3px solid #e2e6ea;padding-left:.5rem;">'
			f'{frappe.utils.escape_html(snippet)}</div>'
		)

	columns = [
		{"label": _("Date"),            "fieldname": "entry_date_pretty", "fieldtype": "Data", "width": 150},
		{"label": _("Case"),            "fieldname": "referral_case",     "fieldtype": "Link", "options": "Referral Case", "width": 150},
		{"label": _("Referral"),        "fieldname": "referral",          "fieldtype": "Link", "options": "Student Referral", "width": 150},
		{"label": _("Student"),         "fieldname": "student_link",      "fieldtype": "HTML", "width": 220},
		{"label": _("School"),          "fieldname": "school",            "fieldtype": "Link", "options": "School", "width": 140},
		{"label": _("Program"),         "fieldname": "program",           "fieldtype": "Link", "options": "Program", "width": 140},
		{"label": _("Academic Year"),   "fieldname": "academic_year",     "fieldtype": "Link", "options": "Academic Year", "width": 140},
		{"label": _("Case Manager"),    "fieldname": "case_manager_name", "fieldtype": "Data", "width": 180},
		{"label": _("Case Severity"),   "fieldname": "case_severity",     "fieldtype": "Data", "width": 110},
		{"label": _("Case Status"),     "fieldname": "case_status",       "fieldtype": "Data", "width": 110},
		{"label": _("Entry Type"),      "fieldname": "entry_type",        "fieldtype": "Data", "width": 150},
		{"label": _("Assignee"),        "fieldname": "assignee",          "fieldtype": "Link", "options": "User", "width": 170},
		{"label": _("Entry Status"),    "fieldname": "entry_status",      "fieldtype": "Data", "width": 110},
		{"label": _("Summary"),         "fieldname": "summary_snippet",   "fieldtype": "HTML", "width": 420},
	]

	# ── Charts (default = weekly) ───────────────────────────────────────
	chart_week   = _chart_entries_over_time(rows, bucket="week")
	chart_month  = _chart_entries_over_time(rows, bucket="month")
	chart_school = _chart_simple_count(rows, key="school", title=_("Entries by School"))
	chart_prog   = _chart_simple_count(rows, key="program", title=_("Entries by Program"))
	chart_mgr    = _chart_simple_count(rows, key="case_manager_name", title=_("Entries per Case Manager"))

	# Supply one default chart; send others via message (the JS renders its own UI)
	message = {
		"chart_over_time_month": chart_month,
		"chart_by_school": chart_school,
		"chart_by_program": chart_prog,
		"chart_by_manager": chart_mgr,
	}
	return columns, rows, message, chart_week


# ---------------- helpers ----------------

def _guard_roles():
	user = frappe.session.user
	if user == "Administrator":
		return
	roles = set(frappe.get_roles(user))
	if not (roles & ALLOWED):
		frappe.throw(_("You are not permitted to run this report."))

def _build_where(f, date_from, date_to):
	where, params = [], {}
	if date_from:
		where.append("DATE(rce.entry_datetime) >= %(df)s"); params["df"] = date_from
	if date_to:
		where.append("DATE(rce.entry_datetime) <= %(dt)s"); params["dt"] = date_to
	if f.get("student"):       where.append("rc.student = %(student)s");     params["student"] = f.student
	if f.get("referral"):      where.append("rc.referral = %(referral)s");   params["referral"] = f.referral
	if f.get("school"):        where.append("rc.school = %(school)s");       params["school"] = f.school
	if f.get("program"):       where.append("rc.program = %(program)s");     params["program"] = f.program
	if f.get("academic_year"): where.append("rc.academic_year = %(ay)s");    params["ay"] = f.academic_year
	if f.get("case_manager"):  where.append("rc.case_manager = %(cm)s");     params["cm"] = f.case_manager
	if f.get("assignee"):      where.append("rce.assignee = %(assignee)s");  params["assignee"] = f.assignee
	if f.get("entry_type"):    where.append("rce.entry_type = %(et)s");      params["et"] = f.entry_type
	if f.get("entry_status"):  where.append("rce.status = %(es)s");          params["es"] = f.entry_status
	if f.get("case_severity"): where.append("rc.severity = %(sev)s");        params["sev"] = f.case_severity
	if f.get("case_status"):   where.append("rc.case_status = %(cs)s");      params["cs"] = f.case_status
	return where, params

def _chart_entries_over_time(rows, bucket="week"):
	"""Return a line chart; bucket = 'week'|'month'.
	Key the aggregation by real date objects → reliable sorting."""
	counts = defaultdict(int)

	def week_start(d: date) -> date:
		return d - timedelta(days=d.weekday())  # Monday

	for r in rows:
		d = r.get("entry_date")
		if not d:
			continue
		if bucket == "week":
			k = week_start(d)
		else:
			k = date(d.year, d.month, 1)
		counts[k] += 1

	if not counts:
		return None

	keys = sorted(counts.keys())
	if bucket == "week":
		labels = [formatdate(k, "d MMM yyyy") for k in keys]
	else:
		labels = [formatdate(k, "MMM yyyy") for k in keys]
	values = [counts[k] for k in keys]

	return {
		"data": {"labels": labels, "datasets": [{"name": _("Entries"), "values": values}]},
		"type": "line",
	}

def _chart_simple_count(rows, key, title):
	counts = defaultdict(int)
	for r in rows:
		val = (r.get(key) or "").strip() or _("(Missing)")
		counts[val] += 1
	if not counts:
		return None
	labels = sorted(counts.keys(), key=lambda s: s.lower())
	values = [counts[l] for l in labels]
	return {"data": {"labels": labels, "datasets": [{"name": title, "values": values}]}, "type": "bar"}
