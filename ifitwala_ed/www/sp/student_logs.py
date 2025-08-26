# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt
 
import frappe
from frappe import _

# constants / imports assumed above
PAGE_LENGTH_DEFAULT = 20
DT = "Student Log"  # if you already have this constant, keep using it

def _initial_page(student_name: str, start: int = 0, page_length: int = PAGE_LENGTH_DEFAULT):
	fields = [
		"name",
		"date",
		"time",
		"log_type",
		"follow_up_status",
		"author_name",
		"program",
		"academic_year",
		"reference_type",
		"reference_name",
	]
	return frappe.get_list(
		DT,
		filters={"student": student_name, "visible_to_student": 1},
		fields=fields,
		order_by="date desc, time desc, creation desc",
		start=int(start or 0),
		page_length=int(page_length or PAGE_LENGTH_DEFAULT),
	)



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

def _compute_unread_names(initial_names):
	if not initial_names:
		return []

	chunk_size = 500
	seen_set = set()

	for i in range(0, len(initial_names), chunk_size):
		chunk = initial_names[i:i + chunk_size]
		placeholders = ", ".join(["%s"] * len(chunk))
		sql = f"""
			select reference_name
			from `tabPortal Read Receipt`
			where user=%s
			  and reference_doctype=%s
			  and reference_name in ({placeholders})
		"""
		params = [frappe.session.user, DT, *chunk]
		rows = frappe.db.sql(sql, params, as_dict=False)
		seen_set.update(x[0] for x in rows)

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
