# ifitwala_ed/website/providers/leadership.py

from __future__ import annotations

import frappe
from frappe.utils import cint
from frappe.utils.caching import redis_cache

from ifitwala_ed.utilities.image_utils import build_employee_image_variants

DEFAULT_ROLE_PROFILES = ("Academic Admin",)
DEFAULT_LEADERSHIP_TITLE = "Academic Leadership"
DEFAULT_STAFF_TITLE = "Faculty & Staff"
DEFAULT_SECTION_COPY = {
    "leadership": "Academic leaders shaping learning, culture, and day-to-day school life.",
    "staff": "The educators and professionals who bring the school community to life.",
}


def _normalize_string_list(values) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = [values]

    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in output:
            output.append(text)
    return tuple(output)


def _normalize_limit(value, fallback: int) -> int:
    if value in (None, "", "Null"):
        return fallback
    return max(cint(value), 1)


def _build_initials(full_name: str | None) -> str:
    name = (full_name or "").strip()
    if not name:
        return "?"
    parts = [part[0].upper() for part in name.split() if part]
    if not parts:
        return "?"
    return "".join(parts[:2])


@redis_cache(ttl=3600)
def _get_staff_showcase(
    school_name: str,
    organization_name: str,
    roles: tuple[str, ...],
    role_profiles: tuple[str, ...],
    leadership_limit: int,
    staff_limit: int,
    show_staff_carousel: int,
):
    leadership_designations = set(roles)
    if not leadership_designations and role_profiles:
        designation_rows = frappe.get_all(
            "Designation",
            filters={
                "organization": organization_name,
                "archived": 0,
                "default_role_profile": ["in", list(role_profiles)],
            },
            fields=["name", "school"],
            order_by="designation_name asc",
            limit=200,
        )
        leadership_designations = {
            row.name
            for row in designation_rows
            if not (row.school or "").strip() or (row.school or "").strip() == school_name
        }

    rows = frappe.get_all(
        "Employee",
        filters={
            "school": school_name,
            "show_on_website": 1,
        },
        fields=["name", "employee_full_name", "employee_image", "designation", "small_bio"],
        order_by="designation asc, employee_full_name asc",
        limit=200,
    )

    leadership_people = []
    staff_people = []
    for row in rows:
        person = {
            "name": (row.get("employee_full_name") or row.get("name") or "").strip(),
            "title": (row.get("designation") or "").strip() or None,
            "bio": (row.get("small_bio") or "").strip() or None,
            "initials": _build_initials(row.get("employee_full_name")),
            "photo": build_employee_image_variants(
                row.get("name"),
                original_url=row.get("employee_image"),
            ),
        }

        if (row.get("designation") or "").strip() in leadership_designations:
            if len(leadership_people) < leadership_limit:
                leadership_people.append(person)
            continue

        if show_staff_carousel and len(staff_people) < staff_limit:
            staff_people.append(person)

    return {
        "leadership": leadership_people,
        "staff": staff_people,
    }


def invalidate_leadership_cache():
    clear_cache = getattr(_get_staff_showcase, "clear_cache", None)
    if callable(clear_cache):
        clear_cache()


def get_context(*, school, page, block_props):
    """
    Leadership / staff showcase block.
    """
    roles = _normalize_string_list(block_props.get("roles"))
    role_profiles = _normalize_string_list(block_props.get("role_profiles")) or DEFAULT_ROLE_PROFILES
    leadership_limit = _normalize_limit(block_props.get("limit"), 4)
    staff_limit = _normalize_limit(block_props.get("staff_limit"), max(leadership_limit * 2, 8))
    show_staff_carousel = 0 if not block_props.get("show_staff_carousel", True) else 1

    payload = _get_staff_showcase(
        school_name=school.name,
        organization_name=school.organization,
        roles=roles,
        role_profiles=role_profiles,
        leadership_limit=leadership_limit,
        staff_limit=staff_limit,
        show_staff_carousel=show_staff_carousel,
    )

    sections = []
    if payload["leadership"]:
        sections.append(
            {
                "key": "leadership",
                "title": (block_props.get("leadership_title") or "").strip() or DEFAULT_LEADERSHIP_TITLE,
                "description": DEFAULT_SECTION_COPY["leadership"],
                "people": payload["leadership"],
            }
        )

    if show_staff_carousel and payload["staff"]:
        sections.append(
            {
                "key": "staff",
                "title": (block_props.get("staff_title") or "").strip() or DEFAULT_STAFF_TITLE,
                "description": DEFAULT_SECTION_COPY["staff"],
                "people": payload["staff"],
            }
        )

    return {
        "data": {
            "title": (block_props.get("title") or "").strip() or None,
            "description": (block_props.get("description") or "").strip() or None,
            "sections": sections,
            "has_people": bool(sections),
        }
    }
