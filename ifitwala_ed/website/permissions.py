from __future__ import annotations

import frappe

from ifitwala_ed.utilities.employee_utils import get_user_base_school
from ifitwala_ed.utilities.school_tree import get_descendant_schools

EDITOR_ROLES = {
    "System Manager",
    "Website Manager",
    "Marketing User",
    "Academic Admin",
}


def _can_bypass_scope(user: str | None = None) -> bool:
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return "System Manager" in set(frappe.get_roles(user))


def _get_user_school_scope(user: str | None = None) -> list[str]:
    user = user or frappe.session.user
    school = frappe.defaults.get_user_default("school", user=user) or get_user_base_school(user)
    if not school:
        return []
    scope = get_descendant_schools(school) or [school]
    return list(dict.fromkeys([school, *scope]))


def _quoted_scope(scope: list[str]) -> str:
    return ", ".join(frappe.db.escape(name) for name in scope)


def get_school_scoped_permission_query_conditions(
    user: str | None, *, doctype: str, school_field: str = "school"
) -> str | None:
    user = user or frappe.session.user
    if _can_bypass_scope(user):
        return None

    if not set(frappe.get_roles(user)).intersection(EDITOR_ROLES):
        return "1=0"

    scope = _get_user_school_scope(user)
    if not scope:
        return "1=0"

    table = f"`tab{doctype}`"
    quoted = _quoted_scope(scope)
    return f"{table}.`{school_field}` IN ({quoted})"


def has_school_scoped_permission(doc, user: str | None = None, *, school_field: str = "school") -> bool:
    user = user or frappe.session.user
    if _can_bypass_scope(user):
        return True

    if not set(frappe.get_roles(user)).intersection(EDITOR_ROLES):
        return False

    scope = set(_get_user_school_scope(user))
    if not scope:
        return False
    return (getattr(doc, school_field, None) or "") in scope


def get_school_website_page_permission_query_conditions(user: str | None = None) -> str | None:
    return get_school_scoped_permission_query_conditions(user, doctype="School Website Page")


def school_website_page_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return has_school_scoped_permission(doc, user=user)


def get_website_story_permission_query_conditions(user: str | None = None) -> str | None:
    return get_school_scoped_permission_query_conditions(user, doctype="Website Story")


def website_story_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return has_school_scoped_permission(doc, user=user)


def get_program_website_profile_permission_query_conditions(user: str | None = None) -> str | None:
    return get_school_scoped_permission_query_conditions(user, doctype="Program Website Profile")


def program_website_profile_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return has_school_scoped_permission(doc, user=user)


def get_course_website_profile_permission_query_conditions(user: str | None = None) -> str | None:
    return get_school_scoped_permission_query_conditions(user, doctype="Course Website Profile")


def course_website_profile_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return has_school_scoped_permission(doc, user=user)


def get_website_notice_permission_query_conditions(user: str | None = None) -> str | None:
    return get_school_scoped_permission_query_conditions(user, doctype="Website Notice")


def website_notice_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return has_school_scoped_permission(doc, user=user)
