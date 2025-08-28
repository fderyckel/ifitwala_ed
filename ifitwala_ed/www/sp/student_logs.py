# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt
#
# Page controller for /sp/student_logs (context only).
# All AJAX endpoints are in ifitwala_ed/api_portal.py and are called from
# ifitwala_ed/public/js/student_portal/student_logs.js.

import frappe
from frappe import _

DT = "Student Log"
PAGE_LENGTH_DEFAULT = 20


def _resolve_current_student():
	"""
	Map the logged-in portal user to a Student record.

	Your app guarantees Student.student_email == User.email (and users
	log in with that email). So we first match on student_email == session user.
	We still include a few conservative fallbacks in case of manual data drift.
	"""
	user = frappe.session.user
	if not user or user in ("Guest", "Administrator"):
		frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

	# Primary / fast path
	row = frappe.db.get_value("Student", {"student_email": user}, ["name", "student_full_name"], as_dict=True)
	if row:
		return row

	# Fallbacks (older conventions or edited data)
	for cond in ({"email": user}, {"student_email_id": user}, {"user": user}):
		row = frappe.db.get_value("Student", cond, ["name", "student_full_name"], as_dict=True)
		if row:
			return row

	frappe.throw(_("No Student record found for your account."), frappe.PermissionError)


def _filters(student_name, extra=None):
	"""Always scope to this student and only show logs flagged for students."""
	f = {"student": student_name, "visible_to_student": 1}
	if extra:
		f.update(extra)
	return f


def _list_fields():
	"""
	Fields needed by the template and by the JS when rendering additional rows.
	(Exclude the heavy Text Editor body here; details are fetched on demand.)
	"""
	return [
		"name",
		"date",
		"time",
		"log_type",
		"author_name",
		"follow_up_status",
		"program",
		"academic_year",
		"reference_type",
		"reference_name",
	]


def _initial_page(student_name: str, start: int = 0, page_length: int = PAGE_LENGTH_DEFAULT):
	"""
	Use frappe.get_list for stable pagination parameters (start/page_length).
	Order matches the API used by JS for consistent scrolling.
	"""
	return frappe.get_list(
		DT,
		filters=_filters(student_name),
		fields=_list_fields(),
		order_by="date desc, time desc, name desc",
		start=int(start or 0),
		page_length=int(page_length or PAGE_LENGTH_DEFAULT),
	)


def _compute_unread_names(initial_names):
	"""
	Return the subset of initial_names that are UNREAD for the current user.

	We keep this lean and indexed: a single SELECT on Portal Read Receipt and a
	small set difference in Python. Avoid frappe.get_all for cost/perf reasons.
	"""
	if not initial_names:
		return []

	seen = frappe.db.get_values(
		"Portal Read Receipt",
		{
			"user": frappe.session.user,
			"reference_doctype": DT,
			"reference_name": ["in", initial_names],
		},
		["reference_name"],
		as_dict=True,
	)
	seen_set = {r["reference_name"] for r in seen}
	return [n for n in initial_names if n not in seen_set]


def get_context(context):
	"""
	Page context only. Initial payload is rendered server-side so the page is
	usable even if JS fails. All dynamic actions happen via api_portal.py.
	"""
	student = _resolve_current_student()

	context.no_cache = 1
	context.page_title = _("My Student Logs")
	context.student_name = student.student_full_name
	context.student_id = student.name
	context.page_length = PAGE_LENGTH_DEFAULT

	first_page = _initial_page(student.name)
	context.initial_logs = first_page
	context.initial_count = len(first_page)

	initial_names = [r["name"] for r in first_page]
	context.unread_names = _compute_unread_names(initial_names)
