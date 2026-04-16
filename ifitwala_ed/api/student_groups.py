# ifitwala_ed/api/student_groups.py

import frappe
from frappe import _

from ifitwala_ed.api.calendar_core import _resolve_employee_for_user
from ifitwala_ed.schedule.attendance_utils import get_student_group_students

TRIAGE_ROLES = {
    "Academic Admin",
    "Academic Staff",
    "Instructor",
    "Academic Assistant",
    "Counselor",
    "System Manager",
    "Administrator",
}


def _user_roles(user: str) -> set[str]:
    return set(frappe.get_roles(user))


def _instructor_group_names(user: str) -> set[str]:
    names: set[str] = set()
    if not user or user == "Guest":
        return names

    def _merge_group_names(filters: dict) -> None:
        for row in frappe.get_all(
            "Student Group Instructor",
            filters={"parenttype": "Student Group", **filters},
            pluck="parent",
            ignore_permissions=True,
        ):
            if row:
                names.add(row)

    _merge_group_names({"user_id": user})

    employee_row = _resolve_employee_for_user(
        user,
        fields=["name"],
        employment_status_filter=["!=", "Inactive"],
    )
    employee_id = (employee_row or {}).get("name")

    instructor_ids = set(
        frappe.get_all(
            "Instructor",
            filters={"linked_user_id": user},
            pluck="name",
            ignore_permissions=True,
        )
        or []
    )

    if employee_id:
        _merge_group_names({"employee": employee_id})
        instructor_ids.update(
            frappe.get_all(
                "Instructor",
                filters={"employee": employee_id},
                pluck="name",
                ignore_permissions=True,
            )
            or []
        )

    if instructor_ids:
        _merge_group_names({"instructor": ["in", sorted(instructor_ids)]})

    return names


def _base_group_filters(program=None, course=None, cohort=None) -> dict:
    filters: dict = {}
    if program:
        filters["program"] = program
    if course:
        filters["course"] = course
    if cohort:
        filters["cohort"] = cohort
    return filters


@frappe.whitelist()
def fetch_groups(program=None, course=None, cohort=None):
    """
    Return student groups visible to the current user.
    * Admin / Academic Admin / Counselor / System Manager see all groups.
    * Instructors (or mapped employees) see only groups they are attached to.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to view student groups."))

    filters = _base_group_filters(program, course, cohort)
    roles = _user_roles(user)

    if roles & TRIAGE_ROLES:
        return frappe.get_all("Student Group", filters=filters, fields=["name", "student_group_name"])

    # Restrict to instructor-linked groups
    group_names = _instructor_group_names(user)
    if not group_names:
        return []

    filters["name"] = ["in", list(group_names)]
    return frappe.get_all("Student Group", filters=filters, fields=["name", "student_group_name"])


@frappe.whitelist()
def fetch_group_students(student_group: str, start: int = 0, page_length: int = 25):
    """
    Return roster for a specific student group. Applies the same instructor/triage permissions.
    """
    if not student_group:
        frappe.throw(_("Student Group is required."))

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to view student groups."))

    roles = _user_roles(user)
    if roles & TRIAGE_ROLES:
        allowed = True
    else:
        group_names = _instructor_group_names(user)
        allowed = student_group in group_names

    if not allowed:
        frappe.throw(_("You do not have access to this student group."))

    students = get_student_group_students(student_group, start, page_length)
    total = frappe.db.count("Student Group Student", {"parent": student_group})

    group = frappe.get_doc("Student Group", student_group)
    group_info = {
        "name": group.name,
        "program": group.program,
        "course": group.course,
        "cohort": group.cohort,
    }

    return {
        "students": students,
        "start": start + page_length,
        "total": total,
        "group_info": group_info,
    }
