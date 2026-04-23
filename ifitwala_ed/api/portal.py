# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/portal.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.api import guardian_communications as guardian_communications_api
from ifitwala_ed.api import student_communications as student_communications_api
from ifitwala_ed.api.attendance import ADMIN_ROLES, COUNSELOR_ROLES, INSTRUCTOR_ROLES
from ifitwala_ed.api.enrollment_analytics import ALLOWED_ANALYTICS_ROLES as ENROLLMENT_ANALYTICS_ROLES
from ifitwala_ed.api.inquiry import ALLOWED_ANALYTICS_ROLES as INQUIRY_ANALYTICS_ROLES
from ifitwala_ed.api.org_communication_quick_create import (
    get_org_communication_quick_create_capability,
)
from ifitwala_ed.api.policy_signature import (
    POLICY_LIBRARY_ROLES,
    POLICY_SIGNATURE_ANALYTICS_ROLES,
    POLICY_SIGNATURE_MANAGER_ROLES,
)
from ifitwala_ed.api.room_utilization import ANALYTICS_ROLES as SCHEDULING_ROLES
from ifitwala_ed.api.student_demographics_dashboard import (
    ALLOWED_ANALYTICS_ROLES as STUDENT_DEMOGRAPHICS_ANALYTICS_ROLES,
)
from ifitwala_ed.api.student_log_dashboard import ALLOWED_ANALYTICS_ROLES as WELLBEING_ANALYTICS_ROLES
from ifitwala_ed.api.student_overview_roles import ALLOWED_STAFF_ROLES as STUDENT_OVERVIEW_STAFF_ROLES
from ifitwala_ed.api.users import STAFF_ROLES
from ifitwala_ed.utilities.image_utils import (
    get_preferred_guardian_avatar_url,
    get_preferred_student_avatar_url,
)
from ifitwala_ed.utilities.portal_identity_cache import (
    CACHE_TTL_SECONDS,
    student_portal_identity_cache_key,
)

HR_ROLES = frozenset({"HR User", "HR Manager"})
ROLE_INSTRUCTOR = "Instructor"
ROLE_ACADEMIC_STAFF = "Academic Staff"
ADMISSIONS_ANALYTICS_ROLES = frozenset(ADMISSIONS_ROLES | INQUIRY_ANALYTICS_ROLES | ENROLLMENT_ANALYTICS_ROLES)
DEMOGRAPHICS_ANALYTICS_ROLES = frozenset(STUDENT_DEMOGRAPHICS_ANALYTICS_ROLES)
MEETING_CREATE_ROLES = frozenset({"Employee", "System Manager"})
SCHOOL_EVENT_CREATE_ROLES = frozenset({"System Manager", "Academic Admin", "Academic Assistant", "Organization IT"})
ORG_COMMUNICATION_CREATE_ROLES = frozenset({"System Manager", "Academic Staff", "Academic Admin", "Employee"})
PROFESSIONAL_DEVELOPMENT_PORTAL_ROLES = frozenset(
    {
        "Employee",
        "Academic Staff",
        "Instructor",
        "HR User",
        "HR Manager",
        "Academic Admin",
        "System Manager",
    }
)


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


def _build_staff_home_capabilities(
    roles: set[str],
    user: str | None = None,
    *,
    org_communication_quick_action_state: dict[str, bool | str | None] | None = None,
) -> dict[str, bool]:
    attendance_roles = set(ADMIN_ROLES) | set(COUNSELOR_ROLES) | set(INSTRUCTOR_ROLES)
    has_instructor_role = ROLE_INSTRUCTOR in roles
    has_academic_staff_role = ROLE_ACADEMIC_STAFF in roles

    if user:
        can_create_meeting = bool(frappe.has_permission("Meeting", ptype="create", user=user))
        can_create_school_event = bool(frappe.has_permission("School Event", ptype="create", user=user))
        org_communication_quick_action_state = (
            org_communication_quick_action_state
            if org_communication_quick_action_state is not None
            else get_org_communication_quick_create_capability(user=user)
        )
        can_create_org_communication = bool(org_communication_quick_action_state.get("enabled"))
    else:
        can_create_meeting = bool(roles & set(MEETING_CREATE_ROLES))
        can_create_school_event = bool(roles & set(SCHOOL_EVENT_CREATE_ROLES))
        can_create_org_communication = bool(roles & set(ORG_COMMUNICATION_CREATE_ROLES))

    return {
        "analytics_attendance": bool(roles & attendance_roles),
        "analytics_attendance_admin": bool(roles & set(ADMIN_ROLES)),
        "analytics_wellbeing": bool(roles & set(WELLBEING_ANALYTICS_ROLES)),
        "analytics_hr": bool(roles & (set(HR_ROLES) | set(ADMIN_ROLES))),
        "analytics_admissions": bool(roles & set(ADMISSIONS_ANALYTICS_ROLES)),
        "analytics_demographics": bool(roles & set(DEMOGRAPHICS_ANALYTICS_ROLES)),
        "analytics_student_overview": bool(roles & set(STUDENT_OVERVIEW_STAFF_ROLES)),
        "room_utilization_page": bool(roles & set(STAFF_ROLES)),
        "analytics_scheduling": bool(roles & (set(SCHEDULING_ROLES) | set(ADMIN_ROLES))),
        "analytics_academic_load": bool(
            roles
            & {
                "Academic Admin",
                "Academic Assistant",
                "Curriculum Coordinator",
                "System Manager",
                "Administrator",
            }
        ),
        "analytics_policy_signatures": bool(roles & set(POLICY_SIGNATURE_ANALYTICS_ROLES)),
        "manage_policy_signatures": bool(roles & set(POLICY_SIGNATURE_MANAGER_ROLES)),
        "staff_policy_library": bool(roles & set(POLICY_LIBRARY_ROLES)),
        "quick_action_class_hub": has_instructor_role,
        "quick_action_create_task": has_instructor_role,
        "quick_action_gradebook": has_instructor_role,
        "quick_action_student_log": has_academic_staff_role,
        "quick_action_create_meeting": can_create_meeting,
        "quick_action_create_school_event": can_create_school_event,
        "quick_action_create_event": can_create_meeting or can_create_school_event,
        "quick_action_org_communication": can_create_org_communication,
        "can_open_desk": bool(roles & set(STAFF_ROLES)),
        "staff_professional_development": bool(roles & set(PROFESSIONAL_DEVELOPMENT_PORTAL_ROLES)),
        "professional_development_decide": bool(roles & {"HR User", "HR Manager", "Academic Admin", "System Manager"}),
        "professional_development_liquidate": bool(roles & {"Accounts Manager", "Accounts User", "System Manager"}),
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
        student["student_image"] = get_preferred_student_avatar_url(
            student.get("name"),
            original_url=student.get("student_image"),
        )
        return student

    user_email = frappe.db.get_value("User", user, "email") or user
    student = frappe.db.get_value(
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
    if student:
        student["student_image"] = get_preferred_student_avatar_url(
            student.get("name"),
            original_url=student.get("student_image"),
        )
    return student


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


def _resolve_guardian_row_for_user(user: str):
    guardian = frappe.db.get_value(
        "Guardian",
        {"user": user},
        [
            "name",
            "guardian_full_name",
            "guardian_first_name",
            "guardian_last_name",
            "guardian_image",
        ],
        as_dict=True,
    )
    if guardian:
        guardian["guardian_image"] = get_preferred_guardian_avatar_url(
            guardian.get("name"),
            original_url=guardian.get("guardian_image"),
        )
    return guardian


def _resolve_guardian_display_name(guardian_row, user_first_name: str | None, user_full_name: str | None) -> str:
    if guardian_row:
        full = (guardian_row.get("guardian_full_name") or "").strip()
        if full:
            return full

        combined = " ".join(
            filter(
                None,
                [
                    (guardian_row.get("guardian_first_name") or "").strip(),
                    (guardian_row.get("guardian_last_name") or "").strip(),
                ],
            )
        ).strip()
        if combined:
            return combined

    full = (user_full_name or "").strip()
    if full:
        return full

    first = (user_first_name or "").strip()
    if first:
        return first

    return "Guardian"


@frappe.whitelist()
def get_staff_home_header():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    cache = frappe.cache()
    cache_key = f"staff_home:header:v6:{user}"
    cached = cache.get_value(cache_key)
    if cached:
        try:
            return frappe.parse_json(cached)
        except Exception:
            pass

    row = frappe.db.get_value("User", user, ["name", "first_name", "full_name"], as_dict=True)
    if not row:
        frappe.throw(_("User not found."), frappe.DoesNotExistError)

    row_name = row.get("name") if isinstance(row, dict) else row.name
    row_first_name = row.get("first_name") if isinstance(row, dict) else row.first_name
    row_full_name = row.get("full_name") if isinstance(row, dict) else row.full_name

    first_name = _resolve_staff_first_name(user, row_first_name, row_full_name)
    roles = set(frappe.get_roles(user))
    org_communication_quick_action_state = get_org_communication_quick_create_capability(user=user)

    payload = {
        "user": row_name,
        "first_name": first_name,
        "full_name": row_full_name,
        "capabilities": _build_staff_home_capabilities(
            roles,
            user=user,
            org_communication_quick_action_state=org_communication_quick_action_state,
        ),
        "quick_actions": {
            "org_communication": org_communication_quick_action_state,
        },
    }

    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=CACHE_TTL_SECONDS)
    return payload


@frappe.whitelist()
def get_student_portal_identity():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    cache = frappe.cache()
    cache_key = student_portal_identity_cache_key(user)
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


@frappe.whitelist()
def get_guardian_portal_identity():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    user_row = frappe.db.get_value("User", user, ["name", "first_name", "full_name", "email"], as_dict=True)
    if not user_row:
        frappe.throw(_("User not found."), frappe.DoesNotExistError)

    guardian_row = _resolve_guardian_row_for_user(user)
    display_name = _resolve_guardian_display_name(
        guardian_row,
        user_row.get("first_name"),
        user_row.get("full_name"),
    )

    payload = {
        "user": user_row.get("name"),
        "guardian": guardian_row.get("name") if guardian_row else None,
        "display_name": display_name,
        "full_name": (guardian_row.get("guardian_full_name") if guardian_row else None)
        or user_row.get("full_name")
        or display_name,
        "email": user_row.get("email") or user_row.get("name"),
        "image_url": (guardian_row.get("guardian_image") if guardian_row else None) or None,
    }

    return payload


def _build_portal_chrome_payload(*, unread_communications: int) -> dict[str, dict[str, int]]:
    return {
        "counts": {
            "unread_communications": max(int(unread_communications or 0), 0),
        }
    }


@frappe.whitelist()
def get_student_portal_chrome():
    unread_count = student_communications_api.get_student_portal_communication_unread_count()
    return _build_portal_chrome_payload(unread_communications=unread_count)


@frappe.whitelist()
def get_guardian_portal_chrome():
    unread_count = guardian_communications_api.get_guardian_portal_communication_unread_count()
    return _build_portal_chrome_payload(unread_communications=unread_count)
