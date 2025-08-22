# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

PAGE_LENGTH_DEFAULT = 20

def _resolve_current_student() -> dict:
	"""
	Map the logged-in user (email == User.name) to Student.
	We try common email/user fieldnames to keep it robust across your schema.
	"""
	user = frappe.session.user
	if not user or user in ("Guest", "Administrator"):
		frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

	# Try likely fieldnames in order of preference
	candidates = [
		{"student_email": user},
		{"email": user},
		{"student_email_id": user},
		{"user": user},  # in case you directly store the portal user on Student
	]

	for cond in candidates:
		row = frappe.db.get_value("Student", cond, ["name", "student_full_name"], as_dict=True)
		if row:
			return row

	# As a final fallback, if your Student has a Contact link mapping to this user, add it here later.
	frappe.throw(_("No Student record found for your account."), frappe.PermissionError)


def _authorized_log_filters(student_name: str, extra: dict | None = None) -> dict:
	filters = {
		"student": student_name,
		"visible_to_student": 1
	}
	if extra:
		filters.update(extra)
	return filters


def _list_fields() -> List[str]:
	# Keep initial list lean; exclude heavy Text Editor until detail fetch
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


def _detail_fields() -> List[str]:
	# Fields for the modal detail request
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
		"log",
	]


def get_context(context):
	"""
	Initial page render: resolve current student and load the first page (lean).
	"""
	student = _resolve_current_student()
	context.no_cache = 1
	context.page_title = _("My Student Logs")
	context.student_name = student.student_full_name
	context.student_id = student.name

	# First page
	first_page = frappe.db.get_values(
		"Student Log",
		filters=_authorized_log_filters(student.name),
		fieldname=_list_fields(),
		as_dict=True,
		order_by="date DESC, time DESC, name DESC",
		start=0,
		page_length=PAGE_LENGTH_DEFAULT,
	)

	context.initial_logs = first_page
	context.page_length = PAGE_LENGTH_DEFAULT


@frappe.whitelist()
def get_student_logs(start: int = 0, page_length: int = PAGE_LENGTH_DEFAULT, 
									  log_type: str | None = None, 
										status: str | None = None, 
										date_from: str | None = None, 
										date_to: str | None = None):
	"""
	Paginated fetch for the current student's visible logs.
	All filters are optional for v1; they’re here so we can expand later without changing signature.
	"""
	student = _resolve_current_student()
	extra = {}

	if log_type:
		extra["log_type"] = log_type
	if status:
		extra["follow_up_status"] = status
	if date_from and date_to:
		extra["date"] = ["between", [date_from, date_to]]
	elif date_from:
		extra["date"] = [">=", date_from]
	elif date_to:
		extra["date"] = ["<=", date_to]

	rows = frappe.db.get_values(
		"Student Log",
		filters=_authorized_log_filters(student.name, extra),
		fieldname=_list_fields(),
		as_dict=True,
		order_by="date DESC, time DESC, name DESC",
		start=int(start or 0),
		page_length=int(page_length or PAGE_LENGTH_DEFAULT),
	)
	return rows


@frappe.whitelist()
def get_log_detail(name: str):
	"""
	Fetch full details (including HTML log body) for one log, with authorization.
	"""
	if not name:
		frappe.throw(_("Missing log id"))

	student = _resolve_current_student()
	doc = frappe.db.get_value(
		"Student Log",
		{"name": name},
		_detail_fields(),
		as_dict=True
	)

	if not doc:
		frappe.throw(_("Log not found."), frappe.PermissionError)

	# Enforce visibility and ownership (defense-in-depth)
	ok = frappe.db.exists("Student Log", {
		"name": name,
		"student": student.name,
		"visible_to_student": 1
	})
	if not ok:
		frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

	# Prepare a minimal response payload
	return {
		"name": doc.name,
		"date": doc.date,
		"time": doc.time,
		"log_type": doc.log_type,
		"author_name": doc.author_name,
		"follow_up_status": doc.follow_up_status,
		"program": doc.program,
		"academic_year": doc.academic_year,
		"reference_type": doc.reference_type,
		"reference_name": doc.reference_name,
		"log_html": doc.log or ""
	}
