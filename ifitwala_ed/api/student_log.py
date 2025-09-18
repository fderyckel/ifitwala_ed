# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_log.py

import frappe
from frappe import _

LOG_DOCTYPE = "Student Log"
PAGE_LENGTH_DEFAULT = 20

def _resolve_current_student():
    """Securely map the logged-in portal user to a Student record."""
    user_id = frappe.session.user
    if user_id == "Guest":
        frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

    user_email = frappe.db.get_value("User", user_id, "email") or user_id
    student_name = frappe.db.get_value("Student", {"student_email": user_email}, "name")

    if not student_name:
        frappe.throw(_("No Student record found for your account."), frappe.PermissionError)
    
    return student_name

@frappe.whitelist()
def get_student_logs(start: int = 0, page_length: int = PAGE_LENGTH_DEFAULT):
	"""Fetch a paginated list of student logs visible to the current student (lean SQL)."""
	student_name = _resolve_current_student()

	# NOTE: Using raw SQL here for performance and to bypass DocType perms;
	# we enforce strict filters (student + visible_to_student) and only return minimal columns.
	rows = frappe.db.sql(
		"""
		SELECT
			l.name,
			l.date,
			l.time,
			l.log_type,
			l.author_name,
			l.follow_up_status,
			CASE WHEN rr.reference_name IS NULL THEN 1 ELSE 0 END AS is_unread
		FROM `tabStudent Log` l
		LEFT JOIN `tabPortal Read Receipt` rr
		  ON rr.user = %(user)s
		 AND rr.reference_doctype = %(ref_dt)s
		 AND rr.reference_name = l.name
		WHERE l.student = %(student)s
		  AND l.visible_to_student = 1
		ORDER BY l.date DESC, l.time DESC, l.name DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{
			"user": frappe.session.user,
			"ref_dt": LOG_DOCTYPE,
			"student": student_name,
			"limit": int(page_length),
			"offset": int(start),
		},
		as_dict=True,
	)

	# rows already shaped for the UI
	return rows


@frappe.whitelist()
def get_student_log_detail(log_name: str):
	"""Fetch a single student log (minimal fields) and mark it as read."""
	# Resolve the current student (raises if not a logged-in student)
	student_name = _resolve_current_student()

	# Fetch only what the portal needs (faster than get_doc)
	fields = [
		"name",
		"student",
		"visible_to_student",
		"date",
		"time",
		"log_type",
		"author_name",
		"log",  # the rich text / HTML body
	]
	log = frappe.db.get_value("Student Log", log_name, fields, as_dict=True)
	if not log:
		frappe.throw(_("Log not found."), frappe.DoesNotExistError)

	# Security: student must own the log and it must be visible on portal
	if log.student != student_name or not log.visible_to_student:
		frappe.throw(_("You do not have permission to view this log."), frappe.PermissionError)

	# Mark as read with a lightweight existence check
	rr_filters = {
		"user": frappe.session.user,
		"reference_doctype": "Student Log",
		"reference_name": log_name,
	}
	if not frappe.db.exists("Portal Read Receipt", rr_filters):
		try:
			frappe.get_doc({"doctype": "Portal Read Receipt", **rr_filters}).insert(ignore_permissions=True)
			# No manual commit: Frappe handles request transactions
		except Exception as e:
			# Harmless if a parallel request inserted first; log and continue
			frappe.log_error(f"Read receipt create failed for {log_name}: {e}", "Student Log API")

	return log
