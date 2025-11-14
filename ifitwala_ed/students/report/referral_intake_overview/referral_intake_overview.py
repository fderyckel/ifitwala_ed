# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/report/referral_intake_overview/referral_intake_overview.py
import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

ALLOWED_STRICT_ROLES = {"Counselor", "Academic Admin", "System Manager"}

def execute(filters=None):
	f = frappe._dict(filters or {})
	user = frappe.session.user
	user_roles = set(frappe.get_roles(user))
	can_see_restricted = bool(user_roles & ALLOWED_STRICT_ROLES)
	site_tz = frappe.utils.get_system_timezone() or "UTC"
	site_now = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	columns = [
		{"label": _("Referral"), "fieldname": "name", "fieldtype": "Link", "options": "Student Referral", "width": 140},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 150},
		{"label": _("Program"), "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 120},
		{"label": _("School"), "fieldname": "school", "fieldtype": "Link", "options": "School", "width": 140},
		{"label": _("Severity"), "fieldname": "severity", "fieldtype": "Data", "width": 90},
		{"label": _("Category"), "fieldname": "referral_category", "fieldtype": "Data", "width": 120},
		{"label": _("Source"), "fieldname": "referral_source", "fieldtype": "Data", "width": 120},
		{"label": _("Immediate?"), "fieldname": "requires_immediate_action", "fieldtype": "Check", "width": 90},
		{"label": _("Mandated?"), "fieldname": "mandated_reporting_triggered", "fieldtype": "Check", "width": 90},
		{"label": _("SLA Due"), "fieldname": "sla_due", "fieldtype": "Datetime", "width": 160},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Check", "width": 80},
		{"label": _("Case"), "fieldname": "referral_case", "fieldtype": "Link", "options": "Referral Case", "width": 140},
		{"label": _("Case Manager"), "fieldname": "assigned_case_manager", "fieldtype": "Link", "options": "User", "width": 160},
	]

	# Filters
	cond = ["r.docstatus=1"]
	params = {"site_tz": site_tz, "site_now": site_now}

	if f.get("from_date"):
		cond.append("r.date >= %(from_date)s")
		params["from_date"] = getdate(f.from_date)
	if f.get("to_date"):
		cond.append("r.date <= %(to_date)s")
		params["to_date"] = getdate(f.to_date)

	for key in ("school", "program", "student"):
		if f.get(key):
			cond.append(f"r.{key} = %({key})s")
			params[key] = f.get(key)

	if f.get("severity"):
		cond.append("r.severity IN %(sev)s")
		params["sev"] = tuple(frappe.parse_json(f.severity)) if isinstance(f.severity, str) else tuple(f.severity)

	if f.get("referral_category"):
		cond.append("r.referral_category IN %(cats)s")
		params["cats"] = tuple(frappe.parse_json(f.referral_category)) if isinstance(f.referral_category, str) else tuple(f.referral_category)

	if f.get("referral_source"):
		cond.append("r.referral_source IN %(srcs)s")
		params["srcs"] = tuple(frappe.parse_json(f.referral_source)) if isinstance(f.referral_source, str) else tuple(f.referral_source)

	if f.get("confidentiality_level"):
		cond.append("r.confidentiality_level = %(cfl)s")
		params["cfl"] = f.confidentiality_level

	# Confidentiality guard: if not counselor/admin/system, hide Restricted
	if not can_see_restricted:
		cond.append("(r.confidentiality_level != 'Restricted' OR r.assigned_case_manager = %(user)s OR r.referrer = %(user)s)")
		params["user"] = user

	# Mine-only
	if cint(f.get("mine_only")):
		cond.append("(r.referrer = %(user)s OR r.assigned_case_manager = %(user)s)")
		params["user"] = user

	where = " AND ".join(cond)

	sla_due_local = "CONVERT_TZ(r.sla_due, 'UTC', %(site_tz)s)"
	q = f"""
		SELECT
			r.name, r.date, r.student, r.program, r.school,
			r.severity, r.referral_category, r.referral_source,
			IFNULL(r.requires_immediate_action, 0) AS requires_immediate_action,
			IFNULL(r.mandated_reporting_triggered, 0) AS mandated_reporting_triggered,
			r.sla_due, r.referral_case, r.assigned_case_manager,
			CASE WHEN r.sla_due IS NOT NULL AND {sla_due_local} < %(site_now)s THEN 1 ELSE 0 END AS overdue
		FROM `tabStudent Referral` r
		WHERE {where}
		ORDER BY r.date DESC, r.modified DESC
	"""
	rows = frappe.db.sql(q, params, as_dict=True)

	# Small chart: count by severity
	counts = {}
	for r in rows:
		key = r.get("severity") or "—"
		counts[key] = counts.get(key, 0) + 1
	chart = {
		"data": {
			"labels": list(counts.keys()),
			"datasets": [{"name": _("Referrals"), "values": list(counts.values())}]
		},
		"type": "bar"
	}

	return columns, rows, None, chart
