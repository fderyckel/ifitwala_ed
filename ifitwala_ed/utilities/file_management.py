# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Optional

import frappe
from frappe import _


def get_settings():
    """Fetch File Management Settings (single)."""
    try:
        return frappe.get_single("File Management Settings")
    except Exception:

        class Dummy:
            students_root = "Home/Students"

        return Dummy()


def validate_admissions_attachment(doc, method: Optional[str] = None):
    """Block direct file inserts for governed surfaces that must use Drive-mediated uploads."""
    del method

    if getattr(doc, "is_folder", 0):
        return
    if not doc.is_new():
        return
    if _is_governed_upload(doc):
        return

    if doc.attached_to_doctype in {
        "Employee",
        "Guardian",
        "Student",
        "Student Applicant",
        "Task Submission",
        "School",
        "Organization",
    }:
        action_map = {
            ("Employee", "employee_image"): _("Upload Employee Image"),
            ("Guardian", "guardian_image"): _("Upload Guardian Photo"),
            ("Student", "student_image"): _("Upload Student Image"),
            ("Student Applicant", "applicant_image"): _("Upload Applicant Image"),
            ("School", "school_logo"): _("Upload School Logo"),
            ("Organization", None): _("the governed organization media upload action"),
            ("Organization", ""): _("the governed organization media upload action"),
        }
        action = action_map.get((doc.attached_to_doctype, doc.attached_to_field))
        if doc.attached_to_doctype == "Task Submission":
            action = _("Upload Submission Attachment")
        if not action:
            action = _("the governed upload action")

        frappe.throw(
            _("Governed upload required for {doctype}. Use {action}.").format(
                doctype=doc.attached_to_doctype,
                action=action,
            )
        )

    if doc.attached_to_doctype != "Student Applicant":
        return
    if doc.attached_to_field == "applicant_image":
        return

    frappe.throw(
        _(
            "Admissions files must use the governed evidence upload so they attach to the submitted-file record (only applicant_image is allowed on Student Applicant)."
        )
    )


def _is_governed_upload(file_doc) -> bool:
    if getattr(file_doc.flags, "governed_upload", False):
        return True

    method = (frappe.form_dict or {}).get("method")
    if method and method.startswith("ifitwala_ed.utilities.governed_uploads."):
        return True

    return False


def build_task_submission_context(*, student: str, task_name: str, settings=None) -> dict[str, str]:
    """Build deterministic folder metadata for task-submission compatibility projections."""
    if not student:
        frappe.throw(_("Cannot determine student for task submission file context."))

    settings = settings or get_settings()
    root = getattr(settings, "students_root", None) or "Home/Students"
    return {
        "root_folder": root,
        "subfolder": f"{student}/Tasks/Task-{task_name}",
        "file_category": "Task Submission",
        "logical_key": f"task_{task_name}",
    }
