# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/portal.py

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.api.attendance import ADMIN_ROLES, COUNSELOR_ROLES, INSTRUCTOR_ROLES
from ifitwala_ed.api.enrollment_analytics import ALLOWED_ANALYTICS_ROLES as ENROLLMENT_ANALYTICS_ROLES
from ifitwala_ed.api.inquiry import ALLOWED_ANALYTICS_ROLES as INQUIRY_ANALYTICS_ROLES
from ifitwala_ed.api.policy_signature import (
    POLICY_SIGNATURE_ANALYTICS_ROLES,
    POLICY_SIGNATURE_MANAGER_ROLES,
)
from ifitwala_ed.api.room_utilization import ANALYTICS_ROLES as SCHEDULING_ROLES
from ifitwala_ed.api.student_demographics_dashboard import (
    ALLOWED_ANALYTICS_ROLES as STUDENT_DEMOGRAPHICS_ANALYTICS_ROLES,
)
from ifitwala_ed.api.student_log_dashboard import ALLOWED_ANALYTICS_ROLES as WELLBEING_ANALYTICS_ROLES
from ifitwala_ed.api.users import STAFF_ROLES

CACHE_TTL_SECONDS = 3600
HR_ROLES = frozenset({"HR User", "HR Manager"})
ADMISSIONS_ANALYTICS_ROLES = frozenset(ADMISSIONS_ROLES | INQUIRY_ANALYTICS_ROLES | ENROLLMENT_ANALYTICS_ROLES)
DEMOGRAPHICS_ANALYTICS_ROLES = frozenset(STUDENT_DEMOGRAPHICS_ANALYTICS_ROLES)


def _resolve_staff_first_name(user: str, user_first_name: str | None, user_full_name: str | None) -> str:
    """
    Resolve the preferred greeting name for StaffHome.

    Priority:
    1) Employee Preferred Name
    2) Employee First Name
    3) User.first_name
    4) First token of User.full_name
    5) "Staff"
    """
    # Employee-based name (preferred)
    emp = frappe.db.get_value(
        "Employee",
        {"user_id": user, "employment_status": "Active"},
        ["employee_preferred_name", "employee_first_name"],
        as_dict=True,
    )

    if emp:
        preferred = (emp.employee_preferred_name or "").strip()
        if preferred:
            return preferred

        first = (emp.employee_first_name or "").strip()
        if first:
            return first

    # Fallback to User fields
    first = (user_first_name or "").strip()
    if first:
        return first

    full = (user_full_name or "").strip()
    if full:
        # Avoid clever parsing; just take the first token deterministically.
        return full.split(" ")[0].strip() or "Staff"

    return "Staff"


def _build_staff_home_capabilities(roles: set[str]) -> dict[str, bool]:
    attendance_roles = set(ADMIN_ROLES) | set(COUNSELOR_ROLES) | set(INSTRUCTOR_ROLES)
    return {
        "analytics_attendance": bool(roles & attendance_roles),
        "analytics_attendance_admin": bool(roles & set(ADMIN_ROLES)),
        "analytics_wellbeing": bool(roles & set(WELLBEING_ANALYTICS_ROLES)),
        "analytics_hr": bool(roles & (set(HR_ROLES) | set(ADMIN_ROLES))),
        "analytics_admissions": bool(roles & set(ADMISSIONS_ANALYTICS_ROLES)),
        "analytics_demographics": bool(roles & set(DEMOGRAPHICS_ANALYTICS_ROLES)),
        "analytics_scheduling": bool(roles & (set(SCHEDULING_ROLES) | set(ADMIN_ROLES))),
        "analytics_policy_signatures": bool(roles & set(POLICY_SIGNATURE_ANALYTICS_ROLES)),
        "manage_policy_signatures": bool(roles & set(POLICY_SIGNATURE_MANAGER_ROLES)),
        "can_open_desk": bool(roles & set(STAFF_ROLES)),
    }


def _resolve_student_row_for_user(user: str):
    student = frappe.db.get_value(
        "Student",
        {"student_email": user},
        [
            "name",
            "student_preferred_name",
            "student_first_name",
            "student_full_name",
            "student_image",
        ],
        as_dict=True,
    )
    if student:
        return student

    user_email = frappe.db.get_value("User", user, "email") or user
    return frappe.db.get_value(
        "Student",
        {"student_email": user_email},
        [
            "name",
            "student_preferred_name",
            "student_first_name",
            "student_full_name",
            "student_image",
        ],
        as_dict=True,
    )


def _resolve_student_display_name(student_row, user_first_name: str | None, user_full_name: str | None) -> str:
    if student_row:
        preferred = (student_row.get("student_preferred_name") or "").strip()
        if preferred:
            return preferred

        first = (student_row.get("student_first_name") or "").strip()
        if first:
            return first

        full = (student_row.get("student_full_name") or "").strip()
        if full:
            return full.split(" ")[0].strip() or "Student"

    first = (user_first_name or "").strip()
    if first:
        return first

    full = (user_full_name or "").strip()
    if full:
        return full.split(" ")[0].strip() or "Student"

    return "Student"


@frappe.whitelist()
def get_staff_home_header():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    cache = frappe.cache()
    cache_key = f"staff_home:header:v4:{user}"
    cached = cache.get_value(cache_key)
    if cached:
        try:
            return frappe.parse_json(cached)
        except Exception:
            pass

    row = frappe.db.get_value("User", user, ["name", "first_name", "full_name"], as_dict=True)
    if not row:
        frappe.throw(_("User not found."), frappe.DoesNotExistError)

    first_name = _resolve_staff_first_name(user, row.first_name, row.full_name)
    roles = set(frappe.get_roles(user))

    payload = {
        "user": row.name,
        "first_name": first_name,
        "full_name": row.full_name,
        "capabilities": _build_staff_home_capabilities(roles),
    }

    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=CACHE_TTL_SECONDS)
    return payload


@frappe.whitelist()
def get_student_portal_identity():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    cache = frappe.cache()
    cache_key = f"student_portal:identity:v1:{user}"
    cached = cache.get_value(cache_key)
    if cached:
        try:
            return frappe.parse_json(cached)
        except Exception:
            pass

    user_row = frappe.db.get_value("User", user, ["name", "first_name", "full_name"], as_dict=True)
    if not user_row:
        frappe.throw(_("User not found."), frappe.DoesNotExistError)

    student_row = _resolve_student_row_for_user(user)
    display_name = _resolve_student_display_name(
        student_row,
        user_row.get("first_name"),
        user_row.get("full_name"),
    )

    payload = {
        "user": user_row.get("name"),
        "student": student_row.get("name") if student_row else None,
        "display_name": display_name,
        "preferred_name": (student_row.get("student_preferred_name") if student_row else None) or None,
        "first_name": (student_row.get("student_first_name") if student_row else None) or None,
        "full_name": (student_row.get("student_full_name") if student_row else None) or user_row.get("full_name"),
        "image_url": (student_row.get("student_image") if student_row else None) or None,
    }

    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=CACHE_TTL_SECONDS)
    return payload
