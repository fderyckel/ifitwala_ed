# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from typing import Dict, List
import frappe
from frappe import _
from ifitwala_ed.portal.utils.portal_receipts import mark_read, unread_names_for

DT = "Student Log"
PAGE_LENGTH_DEFAULT = 20

def _resolve_current_student():
    user = frappe.session.user
    if not user or user in ("Guest", "Administrator"):
        frappe.throw(_("You must be logged in as a student to view this page."), frappe.PermissionError)

    # Student.student_email is the login; match on that
    student = frappe.db.get_value(
        "Student",
        {"student_email": user},
        ["name", "student_full_name"],
        as_dict=True,
    )
    if not student:
        frappe.throw(_("No Student record found for your account."), frappe.PermissionError)

    return student

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
    student = _resolve_current_student()
    rows = frappe.get_list(
        DT,
        filters={"student": student.name, "visible_to_student": 1},
        fields=_list_fields(),
        order_by="date DESC, time DESC, name DESC",
        start=int(start or 0),
        page_length=int(page_length or PAGE_LENGTH_DEFAULT),
    )
    names = [r["name"] for r in rows]
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
def student_logs_get(start: int = 0, page_length: int = PAGE_LENGTH_DEFAULT):
    student = _resolve_current_student()
    rows = frappe.get_list(
        DT,
        filters={"student": student.name, "visible_to_student": 1},
        fields=_list_fields(),
        order_by="date DESC, time DESC, name DESC",
        start=int(start or 0),
        page_length=int(page_length or PAGE_LENGTH_DEFAULT),
    )
    return {"rows": rows}

@frappe.whitelist()
def student_log_detail_mark_read(name):
    return get_log_detail_and_mark_read(name=name)