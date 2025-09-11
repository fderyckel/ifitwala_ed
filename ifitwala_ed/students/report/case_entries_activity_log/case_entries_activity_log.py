# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/report/case_entry_activity_log/case_entry_activity_log.py

import frappe
from frappe import _
from frappe.utils import getdate

ALLOWED = {"Counselor", "Academic Admin", "System Manager"}

def execute(filters=None):
	filters = frappe._dict(filters or {})
	_guard_roles()

	# Parse dates (inclusive)
	date_from = getdate(filters.get("from_date")) if filters.get("from_date") else None
	date_to   = getdate(filters.get("to_date"))   if filters.get("to_date")   else None

	where, params = _build_where(filters, date_from, date_to)

	q = f"""
		SELECT
			rce.entry_datetime,
			rc.name                    AS referral_case,
			rc.referral                AS referral,
			rc.student                 AS student,
			rc.school                  AS school,
			rc.program                 AS program,
			rc.academic_year           AS academic_year,
			rc.case_manager            AS case_manager,
			rc.severity                AS case_severity,
			rc.case_status             AS case_status,
			rce.entry_type             AS entry_type,
			rce.assignee               AS assignee,
			rce.status                 AS entry_status,
			LEFT(rce.summary, 300)     AS summary_snippet
		FROM `tabReferral Case` rc
		JOIN `tabReferral Case Entry` rce
		  ON rce.parent = rc.name
		{('WHERE ' + ' AND '.join(where)) if where else ''}
		ORDER BY rce.entry_datetime DESC, rc.name ASC
	"""

	rows = frappe.db.sql(q, params, as_dict=True)

	columns = [
		{"label": _("Entry Date/Time"), "fieldname": "entry_datetime", "fieldtype": "Datetime", "width": 160},
		{"label": _("Case"),            "fieldname": "referral_case",  "fieldtype": "Link", "options": "Referral Case", "width": 150},
		{"label": _("Referral"),        "fieldname": "referral",       "fieldtype": "Link", "options": "Student Referral", "width": 150},
		{"label": _("Student"),         "fieldname": "student",        "fieldtype": "Link", "options": "Student", "width": 170},
		{"label": _("School"),          "fieldname": "school",         "fieldtype": "Link", "options": "School", "width": 140},
		{"label": _("Program"),         "fieldname": "program",        "fieldtype": "Link", "options": "Program", "width": 140},
		{"label": _("Academic Year"),   "fieldname": "academic_year",  "fieldtype": "Link", "options": "Academic Year", "width": 140},
		{"label": _("Case Manager"),    "fieldname": "case_manager",   "fieldtype": "Link", "options": "User", "width": 170},
		{"label": _("Case Severity"),   "fieldname": "case_severity",  "fieldtype": "Data", "width": 110},
		{"label": _("Case Status"),     "fieldname": "case_status",    "fieldtype": "Data", "width": 110},
		{"label": _("Entry Type"),      "fieldname": "entry_type",     "fieldtype": "Data", "width": 150},
		{"label": _("Assignee"),        "fieldname": "assignee",       "fieldtype": "Link", "options": "User", "width": 170},
		{"label": _("Entry Status"),    "fieldname": "entry_status",   "fieldtype": "Data", "width": 110},
		{"label": _("Summary (snippet)"), "fieldname": "summary_snippet", "fieldtype": "Small Text", "width": 350}
	]

	return columns, rows


def _guard_roles():
	user = frappe.session.user
	if user == "Administrator":
		return
	roles = set(frappe.get_roles(user))
	if not (roles & ALLOWED):
		frappe.throw(_("You are not permitted to run this report."))


def _build_where(f, date_from, date_to):
	where = []
	params = {}

	if date_from:
		where.append("DATE(rce.entry_datetime) >= %(df)s")
		params["df"] = date_from
	if date_to:
		where.append("DATE(rce.entry_datetime) <= %(dt)s")
		params["dt"] = date_to

	if f.get("student"):
		where.append("rc.student = %(student)s")
		params["student"] = f.student

	if f.get("referral"):
		where.append("rc.referral = %(referral)s")
		params["referral"] = f.referral

	if f.get("school"):
		where.append("rc.school = %(school)s")
		params["school"] = f.school

	if f.get("program"):
		where.append("rc.program = %(program)s")
		params["program"] = f.program

	if f.get("academic_year"):
		where.append("rc.academic_year = %(ay)s")
		params["ay"] = f.academic_year

	if f.get("case_manager"):
		where.append("rc.case_manager = %(cm)s")
		params["cm"] = f.case_manager

	if f.get("assignee"):
		where.append("rce.assignee = %(assignee)s")
		params["assignee"] = f.assignee

	if f.get("entry_type"):
		where.append("rce.entry_type = %(et)s")
		params["et"] = f.entry_type

	if f.get("entry_status"):
		where.append("rce.status = %(es)s")
		params["es"] = f.entry_status

	if f.get("case_severity"):
		where.append("rc.severity = %(sev)s")
		params["sev"] = f.case_severity

	if f.get("case_status"):
		where.append("rc.case_status = %(cs)s")
		params["cs"] = f.case_status

	return where, params

