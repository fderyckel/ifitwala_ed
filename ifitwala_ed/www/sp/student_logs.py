# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt
 
import frappe
from frappe import _

DT = "Student Log"
PAGE_LENGTH_DEFAULT = 20

def _resolve_current_student():
	"""
	Map the logged-in portal user to a Student record.
	"""
	user = frappe.session.user
	if not user or user in ("Guest", "Administrator"):
		frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

	for cond in (
		{"student_email": user},
		{"email": user},
		{"student_email_id": user},
		{"user": user},
	):
		row = frappe.db.get_value("Student", cond, ["name", "student_full_name"], as_dict=True)
		if row:
			return row

	frappe.throw(_("No Student record found for your account."), frappe.PermissionError)

def _filters(student_name, extra=None):
	f = {"student": student_name, "visible_to_student": 1}
	if extra:
		f.update(extra)
	return f

def _list_fields():
	# Keep initial list lean; exclude Text Editor body ("log")
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

def _initial_page(student_name):
	return frappe.db.get_values(
		DT,
		filters=_filters(student_name),
		fieldname=_list_fields(),
		as_dict=True,
		order_by="date DESC, time DESC, name DESC",
		start=0,
		page_length=PAGE_LENGTH_DEFAULT,
	)

def _compute_unread_names(initial_names):
	"""
	Return list of names that are UNREAD for the current user using the generic
	Portal Read Receipt table.
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
	Page context only. All AJAX/whitelisted methods live in ifitwala_ed/api_portal.py.
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
