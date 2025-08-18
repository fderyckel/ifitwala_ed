# Copyright (c) 2025, Francois de Ryckel and contributors
# For license information, please see license.txt

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

@frappe.whitelist()
def get_dashboard_data(filters: dict | None = None):
	"""
	Returns summary + datasets for charts & cards.
	All queries parameterized (safe) and scoped by date window/filters.
	"""
	filters = filters or {}
	where, params = _apply_common_conditions(filters)

	# ── counts
	total = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabInquiry` i WHERE {where}", params, as_dict=False
	)[0][0]

	contacted = frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabInquiry` i WHERE {where} AND i.first_contacted_at IS NOT NULL",
		params, as_dict=False
	)[0][0]

	overdue_first = frappe.db.sql(
		f"""
		SELECT COUNT(*)
		FROM `tabInquiry` i
		WHERE {where}
		  AND COALESCE(i.first_contacted_at, '2099-12-31') IS NULL
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

	return {
		"counts": {
			"total": total,
			"contacted": contacted,
			"overdue_first_contact": overdue_first
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
