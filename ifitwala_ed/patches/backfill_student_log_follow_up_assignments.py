# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import defaultdict

import frappe


def _is_blank(value) -> bool:
    return not str(value or "").strip()


def execute():
    required_tables = ("Student Log", "ToDo")
    if any(not frappe.db.table_exists(doctype) for doctype in required_tables):
        return

    from ifitwala_ed.students.doctype.student_log.student_log import _insert_follow_up_todo

    log_rows = frappe.get_all(
        "Student Log",
        filters={
            "docstatus": 1,
            "requires_follow_up": 1,
            "follow_up_status": ["!=", "Completed"],
        },
        fields=[
            "name",
            "student_name",
            "school",
            "next_step",
            "follow_up_status",
            "follow_up_person",
            "follow_up_role",
        ],
        order_by="creation asc, name asc",
        limit=0,
    )
    if not log_rows:
        return

    log_names = [str(row.get("name") or "").strip() for row in log_rows if str(row.get("name") or "").strip()]
    if not log_names:
        return

    open_todos = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "Student Log",
            "reference_name": ["in", log_names],
            "status": "Open",
        },
        fields=["name", "reference_name", "allocated_to"],
        order_by="creation asc, name asc",
        limit=0,
    )
    open_todos_by_log = defaultdict(list)
    for todo in open_todos or []:
        open_todos_by_log[str(todo.get("reference_name") or "").strip()].append(todo)

    role_check_cache: dict[tuple[str, str], bool] = {}

    def user_has_role(user: str, role: str) -> bool:
        key = (user, role)
        if key not in role_check_cache:
            role_check_cache[key] = bool(frappe.db.exists("Has Role", {"parent": user, "role": role}))
        return role_check_cache[key]

    for row in log_rows:
        log_name = str(row.get("name") or "").strip()
        if not log_name:
            continue

        status = str(row.get("follow_up_status") or "").strip()
        follow_up_role = str(row.get("follow_up_role") or "").strip()
        follow_up_person = str(row.get("follow_up_person") or "").strip()
        open_rows = open_todos_by_log.get(log_name, [])

        if len(open_rows) == 1:
            assignee = str(open_rows[0].get("allocated_to") or "").strip()
            if _is_blank(assignee):
                continue
            if follow_up_role and not user_has_role(assignee, follow_up_role):
                continue

            updates = {}
            if assignee != follow_up_person:
                updates["follow_up_person"] = assignee
            if status != "Open":
                updates["follow_up_status"] = "Open"
            if updates:
                frappe.db.set_value("Student Log", log_name, updates, update_modified=False)
            continue

        if len(open_rows) > 1:
            continue

        if status != "Open" or _is_blank(follow_up_person):
            continue
        if follow_up_role and not user_has_role(follow_up_person, follow_up_role):
            continue

        _insert_follow_up_todo(
            log_name=log_name,
            student_name=row.get("student_name"),
            allocated_to=follow_up_person,
            school=row.get("school"),
            next_step=row.get("next_step"),
        )
