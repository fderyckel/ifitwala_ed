# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# Ifitwala Ed - Student Log + Follow-ups (Script Report)

import frappe
from frappe.utils import getdate, add_days, strip_html_tags

def execute(filters=None):
	filters = _normalize_filters(filters or {})
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data

def _normalize_filters(f):
	# Default: last 30 days (inclusive)
	if not f.get("from_date") or not f.get("to_date"):
		today = getdate()
		f.setdefault("to_date", today)
		f.setdefault("from_date", add_days(today, -30))

	# Coerce strings → dates
	f["from_date"] = getdate(f["from_date"])
	f["to_date"] = getdate(f["to_date"])

	# Limit statuses to the canonical set
	if f.get("follow_up_status") and f["follow_up_status"] not in {"Open", "In Progress", "Completed"}:
		f["follow_up_status"] = None

	# Optional booleans
	for k in ("requires_follow_up",):
		if k in f:
			try:
				f[k] = 1 if str(f[k]).lower() in {"1", "true", "yes"} else 0
			except Exception:
				f[k] = None

	# Current user for permission guard
	f["_user"] = frappe.session.user

	return f

def _get_columns():
	# Parent (Student Log) + Child (Follow-up) columns
	return [
		{"label": "Log ID", "fieldname": "log_id", "fieldtype": "Link", "options": "Student Log", "width": 140},
		{"label": "Log Date", "fieldname": "log_date", "fieldtype": "Date", "width": 100},
		{"label": "Time", "fieldname": "log_time", "fieldtype": "Data", "width": 90},
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 120},
		{"label": "Student Name", "fieldname": "student_name", "fieldtype": "Data", "width": 180},
		{"label": "Program", "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 140},
		{"label": "School", "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 140},
		{"label": "Academic Year", "fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "width": 120},
		{"label": "Log Type", "fieldname": "log_type", "fieldtype": "Link", "options": "Student Log Type", "width": 140},
		{"label": "Requires Follow-up", "fieldname": "requires_follow_up", "fieldtype": "Check", "width": 70},
		{"label": "Follow-up Status", "fieldname": "follow_up_status", "fieldtype": "Data", "width": 120},
		{"label": "Author", "fieldname": "author_name", "fieldtype": "Data", "width": 160},
		{"label": "Visibility", "fieldname": "visibility", "fieldtype": "Data", "width": 90},
		{"label": "Log Snippet", "fieldname": "log_snippet", "fieldtype": "Data", "width": 360},
		{"label": "Follow-ups", "fieldname": "follow_up_count", "fieldtype": "Int", "width": 90},
		{"label": "Last Follow-up On", "fieldname": "last_follow_up_on", "fieldtype": "Date", "width": 120},
		# Child
		{"label": "Follow-up ID", "fieldname": "follow_up_id", "fieldtype": "Link", "options": "Student Log Follow Up", "width": 160},
		{"label": "FU Date", "fieldname": "fu_date", "fieldtype": "Date", "width": 100},
		{"label": "FU Author", "fieldname": "fu_author", "fieldtype": "Data", "width": 160},
		{"label": "Follow-up Snippet", "fieldname": "follow_up_snippet", "fieldtype": "Data", "width": 360},
	]

def _get_data(f):
	params = {
		"from_date": f["from_date"],
		"to_date": f["to_date"],
		"student": f.get("student"),
		"program": f.get("program"),
		"school": f.get("school"),
		"academic_year": f.get("academic_year"),
		"log_type": f.get("log_type"),
		"follow_up_status": f.get("follow_up_status"),
		"requires_follow_up": f.get("requires_follow_up"),
		"author": f.get("author"),
		"fu_author": f.get("fu_author"),
		"user": f["_user"],
	}

	# Aggregation: count + last follow-up per log (no extra filters)
	agg_sql = """
		select
			student_log,
			count(*) as cnt,
			max(date) as last_on
		from `tabStudent Log Follow Up`
		group by student_log
	"""

	# Main query (select a computed latest_activity_on, then order by it DESC)
	sql = f"""
		select
			sl.name as log_id,
			sl.date as log_date,
			TIME_FORMAT(sl.time, '%%H:%%i') as log_time,
			sl.student,
			sl.student_name,
			sl.program,
			sl.school,
			sl.academic_year,
			sl.log_type,
			sl.requires_follow_up,
			sl.follow_up_status,
			sl.author_name,
			sl.visible_to_student,
			sl.visible_to_guardians,
			sl.log as log_html,

			coalesce(agg.cnt, 0) as follow_up_count,
			agg.last_on as last_follow_up_on,
			GREATEST(sl.date, coalesce(agg.last_on, sl.date)) as latest_activity_on,

			slfu.name as follow_up_id,
			slfu.date as fu_date,
			coalesce(slfu.follow_up_author, slfu.owner) as fu_author,
			slfu.follow_up as follow_up_html
		from `tabStudent Log` sl
		left join ({agg_sql}) agg on agg.student_log = sl.name
		left join `tabStudent Log Follow Up` slfu on slfu.student_log = sl.name
		where
			sl.docstatus = 1
			and sl.date between %(from_date)s and %(to_date)s
			{_opt("sl.student = %(student)s", params, "student")}
			{_opt("sl.program = %(program)s", params, "program")}
			{_opt("sl.school = %(school)s", params, "school")}
			{_opt("sl.academic_year = %(academic_year)s", params, "academic_year")}
			{_opt("sl.log_type = %(log_type)s", params, "log_type")}
			{_opt("sl.follow_up_status = %(follow_up_status)s", params, "follow_up_status")}
			{_opt("sl.requires_follow_up = %(requires_follow_up)s", params, "requires_follow_up")}
			{_opt("sl.owner = %(author)s", params, "author")}
			{_opt("coalesce(slfu.follow_up_author, slfu.owner) = %(fu_author)s", params, "fu_author")}
			and (
				%(user)s = sl.owner
				or %(user)s = sl.follow_up_person
				or exists (
					select 1
					from `tabHas Role` hr
					where hr.parenttype = 'User'
					and hr.parent = %(user)s
					and hr.role in ('Counselor','Academic Admin','System Manager')
				)
			)
		order by
			latest_activity_on desc,
			sl.name desc,
			slfu.date desc,
			slfu.name desc
	"""

	rows = frappe.db.sql(sql, params, as_dict=True)

	# Normalize to HH:MM defensively
	for r in rows:
			t = r.get("log_time")
			if t:
					r["log_time"] = str(t)[:5]

	# Group + indent: one group header per log, then child rows per follow-up (newest → oldest)
	seen = set()
	data = []
	for r in rows:
		if r["log_id"] not in seen:
			seen.add(r["log_id"])

			log_snip = _snippet(strip_html_tags(r.get("log_html") or ""), 220)
			visibility = _visibility_icons(r.get("visible_to_student"), r.get("visible_to_guardians"))

			data.append({
				# parent (group header)
				"is_group": 1,
				"indent": 0,
				"log_id": r["log_id"],
				"log_date": r["log_date"],
				"log_time": r.get("log_time"),
				"student": r.get("student"),
				"student_name": r.get("student_name"),
				"program": r.get("program"),
				"school": r.get("school"),
				"academic_year": r.get("academic_year"),
				"log_type": r.get("log_type"),
				"requires_follow_up": r.get("requires_follow_up"),
				"follow_up_status": r.get("follow_up_status"),
				"author_name": r.get("author_name"),
				"visibility": visibility,
				"log_snippet": log_snip,
				"follow_up_count": r.get("follow_up_count") or 0,
				"last_follow_up_on": r.get("last_follow_up_on"),
				# child columns blank at header level
				"follow_up_id": None,
				"fu_date": None,
				"fu_author": None,
				"follow_up_snippet": None,
			})

		# child rows (only when there is a follow-up)
		if r.get("follow_up_id"):
			fu_snip = _snippet(strip_html_tags(r.get("follow_up_html") or ""), 200)
			data.append({
				"indent": 1,
				# parent columns intentionally left empty for readability
				"log_id": "", "log_date": None, "log_time": None,
				"student": None, "student_name": None,
				"program": None, "school": None, "academic_year": None,
				"log_type": None, "requires_follow_up": None,
				"follow_up_status": None, "author_name": None,
				"visibility": "", "log_snippet": "", "follow_up_count": None,
				"last_follow_up_on": None,
				# child fields:
				"follow_up_id": r["follow_up_id"],
				"fu_date": r["fu_date"],
				"fu_author": r["fu_author"],
				"follow_up_snippet": fu_snip,
			})

	return data


def _opt(clause, params, key):
	# Return "and <clause>" only if params[key] has a non-null value
	return f"\n\t\t\tand {clause}" if params.get(key) not in (None, "", []) else ""

def _snippet(text: str, length: int) -> str:
	if not text:
		return ""
	text = " ".join(text.split())  # collapse whitespace
	return text if len(text) <= length else f"{text[:length].rstrip()}…"

def _visibility_icons(visible_to_student: int | None, visible_to_guardians: int | None) -> str:
	icons = []
	if int(visible_to_student or 0):
		icons.append("👤")
	if int(visible_to_guardians or 0):
		icons.append("👪")
	return "".join(icons)
