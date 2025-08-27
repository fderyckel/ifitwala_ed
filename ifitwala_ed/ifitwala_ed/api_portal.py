# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from typing import Dict, List
import frappe
from frappe import _
from ifitwala_ed.portal.utils.portal_receipts import mark_read, unread_names_for

DT = "Student Log"
PAGE_LENGTH_DEFAULT = 20

def _resolve_current_student() -> Dict:
    """
    Resolve the currently logged-in user to a Student record.

    This helper first matches on the user's primary email (via ``User.email``) against
    ``Student.student_email``.  It then falls back to matching the User ID across
    several other common fields to support various mapping conventions.

    :returns: A ``frappe._dict`` with keys ``name`` and ``student_full_name``.
    :raises frappe.PermissionError: if no matching Student is found or the user is not logged in.
    """
    user_id = frappe.session.user
    # Block guests and administrators
    if not user_id or user_id in ("Guest", "Administrator"):
        frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

    # Determine user's primary email; fallback to user_id if missing
    user_email = frappe.db.get_value("User", user_id, "email") or user_id

    # Preferred mapping: Student.student_email = user's email
    row = frappe.db.get_value(
        "Student",
        {"student_email": user_email},
        ["name", "student_full_name"],
        as_dict=True,
    )
    if row:
        return row

    # Fallback mapping using user_id across other possible fields
    for cond in (
        {"student_email": user_id},
        {"email": user_id},
        {"student_email_id": user_id},
        {"user": user_id},
    ):
        row = frappe.db.get_value("Student", cond, ["name", "student_full_name"], as_dict=True)
        if row:
            return row

    frappe.throw(_("No Student record found for your account."), frappe.PermissionError)

def _list_fields() -> List[str]:
	return ["name","date","time","log_type","author_name","follow_up_status",
	        "program","academic_year","reference_type","reference_name"]

def _detail_fields() -> List[str]:
	return ["name","date","time","log_type","author_name","follow_up_status",
	        "program","academic_year","reference_type","reference_name","log"]

def _filters(student_name: str, extra: Dict|None=None) -> Dict:
	f = {"student": student_name, "visible_to_student": 1}
	if extra: f.update(extra)
	return f

@frappe.whitelist()
def get_student_logs(start: int = 0, page_length: int = PAGE_LENGTH_DEFAULT):
    """
    Retrieve a paginated list of student logs for the current portal user.

    This helper resolves the currently logged-in student (via their email) and then
    fetches log records using ``frappe.get_list`` for efficient pagination.  It
    also returns a list of unread log names by consulting the Portal Read Receipt table.

    :param start: Index of the first record to return (0-based)
    :param page_length: Maximum number of records to return
    :returns: A dict with keys `rows` and `unread`
    """
    student = _resolve_current_student()
    # Use get_list for paginated queries (supports start / page_length)
    rows = frappe.get_list(
        DT,
        filters={"student": student.name, "visible_to_student": 1},
        fields=_list_fields(),
        order_by="date desc, time desc, creation desc",
        start=int(start or 0),
        page_length=int(page_length or PAGE_LENGTH_DEFAULT),
    )
    # Determine which of these logs are unread for the current user
    names = [r.get("name") for r in rows]
    unread = unread_names_for(frappe.session.user, DT, names)
    return {"rows": rows, "unread": unread}

@frappe.whitelist()
def get_log_detail_and_mark_read(name: str):
	if not name:
		frappe.throw(_("Missing log id"))
	student = _resolve_current_student()
	ok = frappe.db.exists(DT, {"name": name, "student": student.name, "visible_to_student": 1})
	if not ok:
		frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)
	doc = frappe.db.get_value(DT, {"name": name}, _detail_fields(), as_dict=True)
	if not doc:
		frappe.throw(_("Log not found."), frappe.PermissionError)
	mark_read(frappe.session.user, DT, name)  # idempotent
	return {
		"name": doc.name, "date": doc.date, "time": doc.time, "log_type": doc.log_type,
		"author_name": doc.author_name, "follow_up_status": doc.follow_up_status,
		"program": doc.program, "academic_year": doc.academic_year,
		"reference_type": doc.reference_type, "reference_name": doc.reference_name,
		"log_html": doc.log or ""
	}

@frappe.whitelist()
def student_logs_get(start=0, page_length=PAGE_LENGTH_DEFAULT):
    return get_student_logs(start=start, page_length=page_length)

@frappe.whitelist()
def student_log_detail_mark_read(name):
    return get_log_detail_and_mark_read(name=name)