# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/report/active_case_workload/active_case_workload.py
import frappe
from frappe import _
from frappe.utils import cint, getdate

ALLOWED_STRICT_ROLES = {"Counselor", "Academic Admin", "System Manager"}

def execute(filters=None):
	f = frappe._dict(filters or {})
	user = frappe.session.user
	user_roles = set(frappe.get_roles(user))
	can_see_restricted = bool(user_roles & ALLOWED_STRICT_ROLES)

	columns = [
		{"label": _("Case"), "fieldname": "name", "fieldtype": "Link", "options": "Referral Case", "width": 140},
		{"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 150},
		{"label": _("School"), "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 140},
		{"label": _("Severity"), "fieldname": "severity", "fieldtype": "Data", "width": 90},
		{"label": _("Status"), "fieldname": "case_status", "fieldtype": "Data", "width": 110},
		{"label": _("Case Manager"), "fieldname": "case_manager", "fieldtype": "Link", "options": "User", "width": 160},
		{"label": _("Opened On"), "fieldname": "opened_on", "fieldtype": "Date", "width": 110},
		{"label": _("Days Open"), "fieldname": "days_open", "fieldtype": "Int", "width": 90},
		{"label": _("Open Tasks"), "fieldname": "open_tasks", "fieldtype": "Int", "width": 90},
		{"label": _("In Progress"), "fieldname": "in_progress_tasks", "fieldtype": "Int", "width": 100},
		{"label": _("Last Activity"), "fieldname": "last_activity", "fieldtype": "Datetime", "width": 160},
	]

	cond = ["c.case_status != 'Closed'"]
	params = {}

	for key in ("school", "case_manager", "student"):
		if f.get(key):
			cond.append(f"c.{key} = %({key})s")
			params[key] = f.get(key)

	if f.get("severity"):
		cond.append("c.severity IN %(sev)s")
		params["sev"] = tuple(frappe.parse_json(f.severity)) if isinstance(f.severity, str) else tuple(f.severity)

	# Mine-only (as case manager)
	if cint(f.get("only_my_cases")):
		cond.append("c.case_manager = %(user)s")
		params["user"] = user

	# Confidentiality guard
	if not can_see_restricted:
		cond.append("(c.confidentiality_level != 'Restricted' OR c.case_manager = %(user)s)")
		params["user"] = params.get("user") or user

	where = " AND ".join(cond)

	q = f"""
		SELECT
			c.name, c.student, c.school, c.severity, c.case_status, c.case_manager,
			COALESCE(c.opened_on, DATE(c.creation)) AS opened_on,
			DATEDIFF(CURDATE(), COALESCE(c.opened_on, DATE(c.creation))) AS days_open,
			COALESCE(SUM(e.status='Open'), 0) AS open_tasks,
			COALESCE(SUM(e.status='In Progress'), 0) AS in_progress_tasks,
			MAX(e.modified) AS last_activity
		FROM `tabReferral Case` c
		LEFT JOIN `tabReferral Case Entry` e ON e.parent = c.name
		WHERE {where}
		GROUP BY c.name
		ORDER BY days_open DESC, c.modified DESC
	"""
	rows = frappe.db.sql(q, params, as_dict=True)

	# Chart: cases per manager
	per_mgr = {}
	for r in rows:
		m = r.get("case_manager") or "—"
		per_mgr[m] = per_mgr.get(m, 0) + 1
	chart = {
		"data": {
			"labels": list(per_mgr.keys()),
			"datasets": [{"name": _("Open Cases"), "values": list(per_mgr.values())}]
		},
		"type": "bar"
	}

	return columns, rows, None, chart
