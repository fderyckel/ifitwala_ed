from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.utilities.employee_utils import get_user_base_school
from ifitwala_ed.utilities.school_tree import get_descendant_schools

EDITOR_ROLES = {
    "System Manager",
    "Website Manager",
    "Marketing User",
    "Academic Admin",
}
WEBSITE_STORY_CONTENT_OWNER_ROLES = (
    "Marketing User",
    "Website Manager",
    "System Manager",
)


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


def is_eligible_website_story_content_owner(*, user: str | None, school: str | None) -> bool:
    if not user or not school:
        return False

    user_row = frappe.db.get_value("User", user, ["name", "enabled", "user_type"], as_dict=True)
    if not user_row:
        return False
    if int(user_row.get("enabled") or 0) != 1:
        return False
    if (user_row.get("user_type") or "").strip() != "System User":
        return False

    user_roles = set(frappe.get_roles(user))
    if not user_roles.intersection(set(WEBSITE_STORY_CONTENT_OWNER_ROLES)):
        return False

    if _can_bypass_scope(user):
        return True

    scope = set(_get_user_school_scope(user))
    if not scope:
        return False
    return school in scope


def validate_website_story_content_owner(*, user: str | None, school: str | None) -> None:
    if not user:
        return
    if not school:
        frappe.throw(_("Select a School before setting Content Owner."), frappe.ValidationError)

    if is_eligible_website_story_content_owner(user=user, school=school):
        return

    frappe.throw(
        _(
            "Content Owner must be an enabled System User with one of these roles: {roles}. The user must also be scoped for this School. Portal Website Users are not allowed."
        ).format(roles=", ".join(WEBSITE_STORY_CONTENT_OWNER_ROLES)),
        frappe.ValidationError,
    )


@frappe.whitelist()
def get_website_story_content_owner_options(doctype, txt, searchfield, start, page_len, filters):
    query_filters = filters or {}
    if isinstance(query_filters, str):
        query_filters = frappe.parse_json(query_filters) or {}

    school = str(query_filters.get("school") or "").strip()
    if not school:
        return []

    candidate_names = sorted(
        {
            parent
            for parent in frappe.get_all(
                "Has Role",
                filters={
                    "role": ["in", list(WEBSITE_STORY_CONTENT_OWNER_ROLES)],
                    "parenttype": "User",
                },
                pluck="parent",
                limit=5000,
            )
            if parent
        }
    )
    if not candidate_names:
        return []

    user_rows = frappe.get_all(
        "User",
        filters={
            "name": ["in", candidate_names],
            "enabled": 1,
            "user_type": "System User",
        },
        fields=["name", "full_name"],
        limit=max(len(candidate_names), 20),
        order_by="name asc",
    )

    needle = str(txt or "").strip().casefold()
    eligible_rows = []
    for row in user_rows:
        name = str(row.get("name") or "")
        full_name = str(row.get("full_name") or "")
        if needle and needle not in name.casefold() and needle not in full_name.casefold():
            continue
        if not is_eligible_website_story_content_owner(user=name, school=school):
            continue
        eligible_rows.append((name, full_name or name))

    start_idx = int(start or 0)
    page_size = int(page_len or 20)
    return eligible_rows[start_idx : start_idx + page_size]
