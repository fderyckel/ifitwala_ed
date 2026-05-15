# ifitwala_ed/api/calendar_invalidation.py

from __future__ import annotations

from typing import Iterable

import frappe

from ifitwala_ed.hr.utils import invalidate_staff_portal_calendar_cache
from ifitwala_ed.utilities.school_tree import get_descendant_schools

STAFF_SCHOOL_EVENT_AUDIENCE_TYPES = {
    "All Students, Guardians, and Employees",
    "All Employees",
}


def _clean_values(values: Iterable[str | None]) -> list[str]:
    return sorted({str(value or "").strip() for value in values if str(value or "").strip()})


def active_employee_names_for_users(users: Iterable[str | None]) -> list[str]:
    user_names = _clean_values(users)
    if not user_names:
        return []
    return (
        frappe.get_all(
            "Employee",
            filters={
                "user_id": ["in", user_names],
                "employment_status": ["!=", "Inactive"],
            },
            pluck="name",
            limit=0,
            ignore_permissions=True,
        )
        or []
    )


def active_employee_names_for_school_scope(school: str | None) -> list[str]:
    school_name = str(school or "").strip()
    if not school_name:
        return []
    schools = get_descendant_schools(school_name) or [school_name]
    return (
        frappe.get_all(
            "Employee",
            filters={
                "school": ["in", schools],
                "employment_status": ["!=", "Inactive"],
            },
            pluck="name",
            limit=0,
            ignore_permissions=True,
        )
        or []
    )


def active_employee_names_for_teams(teams: Iterable[str | None]) -> list[str]:
    team_names = _clean_values(teams)
    if not team_names:
        return []

    member_employees = (
        frappe.get_all(
            "Team Member",
            filters={
                "parent": ["in", team_names],
                "parenttype": "Team",
                "parentfield": "members",
            },
            pluck="employee",
            limit=0,
            ignore_permissions=True,
        )
        or []
    )
    employee_names = _clean_values(member_employees)
    if not employee_names:
        return []

    return (
        frappe.get_all(
            "Employee",
            filters={
                "name": ["in", employee_names],
                "employment_status": ["!=", "Inactive"],
            },
            pluck="name",
            limit=0,
            ignore_permissions=True,
        )
        or []
    )


def invalidate_staff_calendar_for_employees(employees: Iterable[str | None]) -> None:
    for employee in _clean_values(employees):
        invalidate_staff_portal_calendar_cache(employee)


def invalidate_staff_calendar_for_users(users: Iterable[str | None]) -> None:
    invalidate_staff_calendar_for_employees(active_employee_names_for_users(users))


def invalidate_staff_calendar_for_school_scope(school: str | None) -> None:
    invalidate_staff_calendar_for_employees(active_employee_names_for_school_scope(school))
