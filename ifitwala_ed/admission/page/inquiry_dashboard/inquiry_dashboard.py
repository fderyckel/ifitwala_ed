# Copyright (c) 2025, Francois de Ryckel and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import getdate, add_days, nowdate

def _ay_bounds(academic_year: str):
	if not academic_year:
		return None, None
	start, end = frappe.db.get_value(
		"Academic Year",
		academic_year,
		["year_start_date", "year_end_date"]
	)
	return start, end

def _resolve_window(filters: dict):
	# precedence: explicit dates > academic_year > last 90 days
	fd = filters.get("from_date")
	td = filters.get("to_date")
	ay = filters.get("academic_year")
	if ay and not (fd and td):
		ay_start, ay_end = _ay_bounds(ay)
		fd = fd or ay_start
		td = td or ay_end
	if not fd or not td:
		td = td or nowdate()
		fd = fd or add_days(td, -90)
	return getdate(fd), getdate(td)

def _apply_common_conditions(filters: dict):
	conds = []
	params = {}
	fd, td = _resolve_window(filters)
	conds.append("i.submitted_at >= %(from)s AND i.submitted_at < %(to)s")
	params.update({"from": f"{fd} 00:00:00", "to": f"{td} 23:59:59"})

	if filters.get("type_of_inquiry"):
		conds.append("i.type_of_inquiry = %(type)s")
		params["type"] = filters["type_of_inquiry"]

	if filters.get("assigned_to"):
		conds.append("i.assigned_to = %(assignee)s")
		params["assignee"] = filters["assigned_to"]

	if filters.get("sla_status"):
		conds.append("i.sla_status = %(sla)s")
		params["sla"] = filters["sla_status"]

	return " AND ".join(conds), params

def _rest_conditions(filters: dict):
	conds, params = [], {}
	if filters.get("type_of_inquiry"):
		conds.append("i.type_of_inquiry = %(type)s")
		params["type"] = filters["type_of_inquiry"]
	if filters.get("assigned_to"):
		conds.append("i.assigned_to = %(assignee)s")
		params["assignee"] = filters["assigned_to"]
	if filters.get("sla_status"):
		conds.append("i.sla_status = %(sla)s")
		params["sla"] = filters["sla_status"]
	return " AND ".join(conds) or "1=1", params


@frappe.whitelist()
def get_dashboard_data(filters=None):
	"""
	Returns summary + datasets for charts & cards.
	All queries parameterized (safe) and scoped by date window/filters.
	"""
	filters = frappe.parse_json(filters) or {}

	where, params = _apply_common_conditions(filters)
	rest_where, rest_params = _rest_conditions(filters)	

	# --- Admission Settings: upcoming horizon (days) ---
	upcoming_horizon_days = frappe.db.get_single_value("Admission Settings", "followup_sla_days") or 7
	try:
		upcoming_horizon_days = int(upcoming_horizon_days)
	except Exception:
		upcoming_horizon_days = 7	

	# ── counts
	total = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabInquiry` i WHERE {where}", params, as_dict=False
	)[0][0]

	contacted = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabInquiry` i WHERE {where} AND i.first_contacted_at IS NOT NULL",
		params, as_dict=False
	)[0][0]

	# 👇 FIX: use IS NULL (COALESCE ... IS NULL can never be true)
	overdue_first = frappe.db.sql(
		f"""
		SELECT COUNT(*)
		FROM `tabInquiry` i
		WHERE {where}
		  AND i.first_contacted_at IS NULL
		  AND i.first_contact_due_on IS NOT NULL
		  AND i.first_contact_due_on < CURDATE()
		""",
		params, as_dict=False
	)[0][0]

	# ── averages (overall window)
	avg_first = frappe.db.sql(
		f"""
		SELECT AVG(i.response_hours_first_contact)
		FROM `tabInquiry` i
		WHERE {where} AND i.response_hours_first_contact IS NOT NULL
		""",
		params, as_dict=False
	)[0][0] or 0

	avg_from_assign = frappe.db.sql(
		f"""
		SELECT AVG(i.response_hours_from_assign)
		FROM `tabInquiry` i
		WHERE {where} AND i.response_hours_from_assign IS NOT NULL
		""",
		params, as_dict=False
	)[0][0] or 0

	# ── trailing 30d smoothing (bounded by same filters + last 30 days cap)
	fd, td = _resolve_window(filters)
	params30 = dict(params)
	params30["from30"] = f"{max(add_days(td, -30), fd)} 00:00:00"
	params30["to30"] = f"{td} 23:59:59"

	avg_first_30 = frappe.db.sql(
		f"""
		SELECT AVG(i.response_hours_first_contact)
		FROM `tabInquiry` i
		WHERE i.submitted_at >= %(from30)s AND i.submitted_at <= %(to30)s
		  AND ({where})
		  AND i.response_hours_first_contact IS NOT NULL
		""",
		params30, as_dict=False
	)[0][0] or 0

	avg_from_assign_30 = frappe.db.sql(
		f"""
		SELECT AVG(i.response_hours_from_assign)
		FROM `tabInquiry` i
		WHERE i.submitted_at >= %(from30)s AND i.submitted_at <= %(to30)s
		  AND ({where})
		  AND i.response_hours_from_assign IS NOT NULL
		""",
		params30, as_dict=False
	)[0][0] or 0

	# ── monthly averages (YYYY-MM by submitted_at)
	monthly = frappe.db.sql(
		f"""
		SELECT DATE_FORMAT(i.submitted_at, '%%Y-%%m') AS ym,
		       AVG(i.response_hours_first_contact) AS a_first,
		       AVG(i.response_hours_from_assign)  AS a_assign
		FROM `tabInquiry` i
		WHERE {where}
		GROUP BY DATE_FORMAT(i.submitted_at, '%%Y-%%m')
		ORDER BY ym
		""",
		params, as_dict=True
	)

	monthly_series = {
		"labels": [r["ym"] for r in monthly],
		"first_contact": [float(r["a_first"] or 0) for r in monthly],
		"from_assign": [float(r["a_assign"] or 0) for r in monthly],
	}

	# ── who has assignments (assignee distribution)
	assignees = frappe.db.sql(
		f"""
		SELECT i.assigned_to AS label, COUNT(*) AS value
		FROM `tabInquiry` i
		WHERE {where} AND i.assigned_to IS NOT NULL
		GROUP BY i.assigned_to ORDER BY value DESC
		""",
		params, as_dict=True
	)

	# ── inquiry types (composition)
	types = frappe.db.sql(
		f"""
		SELECT COALESCE(i.type_of_inquiry, '—') AS label, COUNT(*) AS value
		FROM `tabInquiry` i
		WHERE {where}
		GROUP BY i.type_of_inquiry ORDER BY value DESC
		""",
		params, as_dict=True
	)

	# ── SLA Breach Monitor: Due Today & Upcoming (first contact)
	# compute horizon dates in Python to avoid `%d` casting issues
	today = nowdate()
	up_from = add_days(today, 1)  # tomorrow
	up_to = add_days(today, upcoming_horizon_days)

	due_today = frappe.db.sql(
		f"""
		SELECT COUNT(*)
		FROM `tabInquiry` i
		WHERE {where}
		  AND i.first_contacted_at IS NULL
		  AND DATE(i.first_contact_due_on) = %(today)s
		""",
		{**params, "today": today},
		as_dict=False
	)[0][0]

	upcoming = frappe.db.sql(
		f"""
		SELECT COUNT(*)
		FROM `tabInquiry` i
		WHERE {where}
		  AND i.first_contacted_at IS NULL
		  AND DATE(i.first_contact_due_on) > %(up_from)s
		  AND DATE(i.first_contact_due_on) <= %(up_to)s
		""",
		{**params, "up_from": up_from, "up_to": up_to},
		as_dict=False
	)[0][0]


	# ── Pipeline by workflow_state
	pipeline = frappe.db.sql(
		f"""
		SELECT COALESCE(i.workflow_state, '—') AS label, COUNT(*) AS value
		FROM `tabInquiry` i
		WHERE {where}
		GROUP BY i.workflow_state
		ORDER BY value DESC
		""",
		params, as_dict=True
	)

	# ── Weekly Inquiry Volume (week starts Monday)
	weekly = frappe.db.sql(
		f"""
		SELECT
			DATE_FORMAT(DATE_SUB(DATE(i.submitted_at), INTERVAL WEEKDAY(i.submitted_at) DAY), '%%Y-%%m-%%d') AS week_start,
			COUNT(*) AS value
		FROM `tabInquiry` i
		WHERE {where}
		GROUP BY week_start
		ORDER BY week_start
		""",
		params, as_dict=True
	)
	weekly_series = {
		"labels": [r["week_start"] for r in weekly],
		"values": [int(r["value"] or 0) for r in weekly],
		"ranges": [
			{
				"from": r["week_start"] + " 00:00:00",
				"to":   frappe.utils.formatdate(
					frappe.utils.add_days(r["week_start"], 6), "yyyy-mm-dd"
				) + " 23:59:59"
			}
			for r in weekly
		],
	}

	# ── SLA % (last 30d), measure by due_date falling in last30d, using non-date filters
	fd, td = _resolve_window(filters)
	params30 = {**rest_params}
	params30["due_from30"] = f"{max(add_days(td, -30), fd)}"
	params30["due_to30"] = f"{td}"

	sla_den = frappe.db.sql(
		f"""
		SELECT COUNT(*)
		FROM `tabInquiry` i
		WHERE i.first_contact_due_on IS NOT NULL
		  AND i.first_contact_due_on BETWEEN %(due_from30)s AND %(due_to30)s
		  AND ({rest_where})
		""",
		params30, as_dict=False
	)[0][0]

	sla_num = frappe.db.sql(
		f"""
		SELECT COUNT(*)
		FROM `tabInquiry` i
		WHERE i.first_contact_due_on IS NOT NULL
		  AND i.first_contact_due_on BETWEEN %(due_from30)s AND %(due_to30)s
		  AND i.first_contacted_at IS NOT NULL
		  AND DATE(i.first_contacted_at) <= i.first_contact_due_on
		  AND ({rest_where})
		""",
		params30, as_dict=False
	)[0][0]

	sla_pct_30 = round((float(sla_num) / sla_den * 100.0), 1) if sla_den else 0.0


	return {
		"counts": {
			"total": total,
			"contacted": contacted,
			"overdue_first_contact": overdue_first,
			"due_today": due_today,
			"upcoming": upcoming
		},
		"pipeline_by_state": pipeline,
		"weekly_volume_series": weekly_series,
		"sla": {
			"pct_30d": sla_pct_30
		},
		"config": {
			"upcoming_horizon_days": upcoming_horizon_days
		},
		"averages": {
			"overall": {
				"first_contact_hours": round(float(avg_first), 2),
				"from_assign_hours": round(float(avg_from_assign), 2)
			},
			"last30d": {
				"first_contact_hours": round(float(avg_first_30), 2),
				"from_assign_hours": round(float(avg_from_assign_30), 2)
			}
		},
		"monthly_avg_series": monthly_series,
		"assignee_distribution": assignees,
		"type_distribution": types
	}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""
		SELECT name
		FROM `tabAcademic Year`
		WHERE name LIKE %(txt)s
		ORDER BY year_start_date DESC, name DESC
		LIMIT %(start)s, %(page_len)s
		""",
		{"txt": f"%{txt}%", "start": start, "page_len": page_len}
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def admission_user_link_query(doctype, txt, searchfield, start, page_len, filters):
	"""Enabled users with Admission Officer/Manager role; match name/full_name/email."""
	return frappe.db.sql(
		"""
		SELECT u.name, u.full_name
		FROM `tabUser` u
		WHERE u.enabled = 1
		  AND u.name IN (
		    SELECT parent FROM `tabHas Role`
		    WHERE role IN ('Admission Officer','Admission Manager')
		  )
		  AND (
		    u.name LIKE %(txt)s
		    OR u.full_name LIKE %(txt)s
		    OR u.email LIKE %(txt)s
		  )
		ORDER BY u.full_name ASC, u.creation DESC
		LIMIT %(start)s, %(page_len)s
		""",
		{"txt": f"%{txt or ''}%", "start": start, "page_len": page_len}
	)



@frappe.whitelist()
def get_inquiry_types():
	# Returns a simple list of distinct, non-empty types (alphabetical)
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT type_of_inquiry
		FROM `tabInquiry`
		WHERE COALESCE(type_of_inquiry, '') <> ''
		ORDER BY type_of_inquiry
		""",
		as_dict=False
	)
	return [r[0] for r in rows]