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
    """Fetch a paginated list of student logs visible to the student."""
    student_name = _resolve_current_student()
    
    logs = frappe.get_list(
        LOG_DOCTYPE,
        filters={"student": student_name, "visible_to_student": 1},
        fields=["name", "date", "time", "log_type", "author_name", "follow_up_status"],
        order_by="date desc, time desc, name desc",
        limit_start=start,
        limit_page_length=page_length,
    )

    if not logs:
        return []

    # Efficiently check for unread logs in a single query
    log_names = [log.name for log in logs]
    seen_logs = frappe.get_all(
        "Portal Read Receipt",
        filters={
            "user": frappe.session.user,
            "reference_doctype": LOG_DOCTYPE,
            "reference_name": ["in", log_names],
        },
        pluck="reference_name",
    )
    seen_set = set(seen_logs)

    # Add the is_unread flag to each log
    for log in logs:
        log["is_unread"] = log.name not in seen_set
    
    return logs

@frappe.whitelist()
def get_student_log_detail(log_name: str):
    """Fetch the full detail of a single student log and mark it as read."""
    student_name = _resolve_current_student()
    
    # Fetch the log
    log = frappe.get_doc(LOG_DOCTYPE, log_name)
    
    # Security check: ensure the student owns this log and it's visible
    if log.student != student_name or not log.visible_to_student:
        frappe.throw(_("You do not have permission to view this log."), frappe.PermissionError)

    # Mark the log as read by creating a Portal Read Receipt
    # Use frappe.db.exists to avoid potential duplicate key errors
    if not frappe.db.exists(
        "Portal Read Receipt",
        {
            "user": frappe.session.user,
            "reference_doctype": LOG_DOCTYPE,
            "reference_name": log_name,
        },
    ):
        try:
            frappe.get_doc({
                "doctype": "Portal Read Receipt",
                "user": frappe.session.user,
                "reference_doctype": LOG_DOCTYPE,
                "reference_name": log_name,
            }).insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Failed to create read receipt for {log_name}: {e}", "Student Log API Error")


    return log