# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/task.py

# Task Planning API Controller (Teacher Planning Loop)
# - Search / Browse Task Library
# - Get Task Definitions
# - Create Task Delivery (Assign)
#
# REGRESSION TRAP:
# Controllers must not write official_* fields to Task Outcome.
# Use services (task_outcome_service, task_delivery_service) for all writes.

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.assessment import task_delivery_service


@frappe.whitelist()
def search_tasks(filters=None, query=None, limit=20, start=0):
    """
    Search for Tasks definitions (Library).
    """
    filters = filters or {}
    if query:
        filters["title"] = ["like", f"%{query}%"]

    tasks = frappe.get_all(
        "Task",
        filters=filters,
        fields=["name", "title", "task_type", "default_course", "is_template", "is_archived"],
        limit_page_length=limit,
        start=start,
        order_by="modified desc",
    )
    return tasks


@frappe.whitelist()
def get_task_for_delivery(task):
    """
    Get Task details payload for the Assign Wizard.
    """
    if not task:
        frappe.throw(_("Task is required."))

    doc = frappe.get_doc("Task", task)

    # Minimal payload for the wizard
    return {
        "name": doc.name,
        "title": doc.title,
        "description": doc.description,
        "task_type": doc.task_type,
        "default_course": doc.default_course,
        "grading_defaults": {
            "default_max_points": doc.default_max_points,
            "default_grade_scale": doc.default_grade_scale,
        },
    }


@frappe.whitelist()
def create_task_delivery(payload):
    """
    Orchestrate Task Delivery creation.
    Delegates strictly to task_delivery_service.
    """
    # Check permissions
    if not _can_manage_tasks():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    return task_delivery_service.create_delivery(payload)


def _has_role(*roles):
    user_roles = set(frappe.get_roles(frappe.session.user))
    return any(r in user_roles for r in roles)


def _can_manage_tasks():
    # Allow Instructors, Curriculum Coordinators, Academic Admins
    return _has_role("System Manager", "Academic Admin", "Curriculum Coordinator", "Instructor")
