# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt
 
import frappe
from frappe import _

DT = "Student Log"
PAGE_LENGTH_DEFAULT = 20

def _resolve_current_student():
    """
    Map the logged-in portal user to a Student record.

    This helper tries multiple mappings:

    1. Match the user's primary email (via ``User.email``) to ``Student.student_email``.  In many
       deployments the Student record stores the user's email rather than their User ID.
    2. Fall back to matching the User ID against a few common fields: ``student_email``, ``email``,
       ``student_email_id`` and ``user``.  These cover various older conventions.

    Throws ``PermissionError`` if no matching Student is found.
    """
    user_id = frappe.session.user
    # Guests cannot access student-only pages
    if not user_id or user_id in ("Guest", "Administrator"):
        frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

    # Fetch the user's primary email. Fallback to user_id if email isn't set.
    user_email = frappe.db.get_value("User", user_id, "email") or user_id

    # Preferred: match on student_email using the user's email
    row = frappe.db.get_value(
        "Student",
        {"student_email": user_email},
        ["name", "student_full_name"],
        as_dict=True,
    )
    if row:
        return row

    # Fallbacks: match using user_id across other possible fields
    for cond in (
        {"student_email": user_id},
        {"email": user_id},
        {"student_email_id": user_id},
        {"user": user_id},
    ):
        row = frappe.db.get_value("Student", cond, ["name", "student_full_name"], as_dict=True)
        if row:
            return row

    # No matching record → deny access
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

def _initial_page(student_name: str, start: int = 0, page_length: int = PAGE_LENGTH_DEFAULT):
    """
    Fetch the initial page of student logs for the given student name.

    This helper uses `limit_start` and `limit_page_length` instead of the old
    `start`/`page_length` parameters when calling `frappe.db.get_values`. It
    ensures that results are returned as dictionaries for easier templating.

    :param student_name: Name of the student whose logs should be fetched
    :param start: Starting index (0-based) for pagination
    :param page_length: Maximum number of records to return
    :returns: A list of dictionaries representing log records
    """
    return frappe.db.get_values(
        DT,
        filters=_filters(student_name),
        fieldname=_list_fields(),
        as_dict=True,
        order_by="date DESC, time DESC, name DESC",
        limit_start=start,
        limit_page_length=page_length,
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