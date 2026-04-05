# ifitwala_ed/website/providers/leadership.py

from __future__ import annotations

import frappe
from frappe.utils import cint
from frappe.utils.caching import redis_cache

from ifitwala_ed.utilities.image_utils import build_employee_image_variants
from ifitwala_ed.utilities.school_tree import get_descendant_school_scope

DEFAULT_ROLE_PROFILES = ("Academic Admin",)
DEFAULT_LEADERSHIP_TITLE = "Academic Leadership"
DEFAULT_STAFF_TITLE = "Faculty & Staff"
DEFAULT_SCHOOL_SCOPE = "current"
DESCENDANT_SCHOOL_SCOPE = "current_and_descendants"
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


def _normalize_role_scopes(values) -> tuple[tuple[str, str, str, int | None], ...]:
    if not isinstance(values, (list, tuple)):
        return ()

    normalized: dict[tuple[str, str], tuple[str, int | None]] = {}
    for item in values:
        if not isinstance(item, dict):
            continue

        role = str(item.get("role") or "").strip()
        role_profile = str(item.get("role_profile") or "").strip()
        if bool(role) == bool(role_profile):
            continue

        school_scope = str(item.get("school_scope") or "").strip() or DEFAULT_SCHOOL_SCOPE
        if school_scope not in {DEFAULT_SCHOOL_SCOPE, DESCENDANT_SCHOOL_SCOPE}:
            school_scope = DEFAULT_SCHOOL_SCOPE

        if school_scope != DESCENDANT_SCHOOL_SCOPE or item.get("descendant_depth") in (None, "", "Null"):
            descendant_depth = None
        else:
            descendant_depth = max(cint(item.get("descendant_depth")), 1)

        if role:
            normalized[("role", role)] = (school_scope, descendant_depth)
        else:
            normalized[("role_profile", role_profile)] = (school_scope, descendant_depth)

    return tuple(
        (target_type, target_value, school_scope, descendant_depth)
        for (target_type, target_value), (school_scope, descendant_depth) in sorted(normalized.items())
    )


def _resolve_role_school_scope(
    school_name: str,
    school_scope: str,
    descendant_depth: int | None,
) -> tuple[str, ...]:
    if school_scope != DESCENDANT_SCHOOL_SCOPE:
        return (school_name,)
    return tuple(get_descendant_school_scope(school_name, max_depth=descendant_depth) or [school_name])


def _resolve_role_scope_maps(
    school_name: str,
    role_scopes: tuple[tuple[str, str, str, int | None], ...],
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    role_scope_map: dict[str, tuple[str, ...]] = {}
    role_profile_scope_map: dict[str, tuple[str, ...]] = {}
    for target_type, target_value, school_scope, descendant_depth in role_scopes:
        resolved_scope = _resolve_role_school_scope(
            school_name,
            school_scope,
            descendant_depth,
        )
        if target_type == "role":
            role_scope_map[target_value] = resolved_scope
        else:
            role_profile_scope_map[target_value] = resolved_scope
    return role_scope_map, role_profile_scope_map


def _build_initials(full_name: str | None) -> str:
    name = (full_name or "").strip()
    if not name:
        return "?"
    parts = [part[0].upper() for part in name.split() if part]
    if not parts:
        return "?"
    return "".join(parts[:2])


def _build_person(row) -> dict[str, object]:
    return {
        "name": (row.get("employee_full_name") or row.get("name") or "").strip(),
        "title": (row.get("designation") or "").strip() or None,
        "bio": (row.get("small_bio") or "").strip() or None,
        "initials": _build_initials(row.get("employee_full_name")),
        "photo": build_employee_image_variants(
            row.get("name"),
            original_url=row.get("employee_image"),
        ),
    }


@redis_cache(ttl=3600)
def _get_staff_showcase(
    school_name: str,
    organization_name: str,
    roles: tuple[str, ...],
    role_profiles: tuple[str, ...],
    role_scopes: tuple[tuple[str, str, str, int | None], ...],
    leadership_limit: int,
    staff_limit: int,
    show_staff_carousel: int,
):
    current_school_scope = (school_name,)
    role_scope_map, role_profile_scope_map = _resolve_role_scope_maps(school_name, role_scopes)

    leadership_designations = set(roles)
    designation_school_scope: dict[str, tuple[str, ...]] = {}
    if leadership_designations:
        for designation_name in leadership_designations:
            designation_school_scope[designation_name] = role_scope_map.get(designation_name) or current_school_scope

    if not leadership_designations and role_profiles:
        designation_rows = frappe.get_all(
            "Designation",
            filters={
                "organization": organization_name,
                "archived": 0,
                "default_role_profile": ["in", list(role_profiles)],
            },
            fields=["name", "school", "default_role_profile"],
            order_by="designation_name asc",
            limit=200,
        )
        for row in designation_rows:
            designation_name = (row.get("name") or "").strip()
            if not designation_name:
                continue

            allowed_schools = (
                role_scope_map.get(designation_name)
                or role_profile_scope_map.get((row.get("default_role_profile") or "").strip())
                or current_school_scope
            )
            row_school = (row.get("school") or "").strip()
            if row_school and row_school not in allowed_schools:
                continue

            leadership_designations.add(designation_name)
            designation_school_scope[designation_name] = allowed_schools

    leadership_school_scope = sorted(
        {school for schools in designation_school_scope.values() for school in schools if str(school or "").strip()}
    )

    leadership_rows = []
    if leadership_designations:
        leadership_rows = frappe.get_all(
            "Employee",
            filters={
                "school": ["in", leadership_school_scope],
                "show_on_website": 1,
                "designation": ["in", sorted(leadership_designations)],
            },
            fields=[
                "name",
                "employee_full_name",
                "employee_image",
                "designation",
                "small_bio",
                "school",
            ],
            order_by="designation asc, employee_full_name asc",
            limit=max(leadership_limit * 6, 200),
        )

    leadership_people = []
    for row in leadership_rows:
        designation_name = (row.get("designation") or "").strip()
        row_school = (row.get("school") or "").strip()
        allowed_schools = designation_school_scope.get(designation_name) or current_school_scope
        if row_school not in allowed_schools:
            continue

        leadership_people.append(_build_person(row))
        if len(leadership_people) >= leadership_limit:
            break

    staff_people = []
    if show_staff_carousel:
        staff_filters = {
            "school": school_name,
            "show_on_website": 1,
        }
        if leadership_designations:
            staff_filters["designation"] = ["not in", sorted(leadership_designations)]

        staff_rows = frappe.get_all(
            "Employee",
            filters=staff_filters,
            fields=["name", "employee_full_name", "employee_image", "designation", "small_bio"],
            order_by="designation asc, employee_full_name asc",
            limit=max(staff_limit * 6, 200),
        )
        for row in staff_rows:
            staff_people.append(_build_person(row))
            if len(staff_people) >= staff_limit:
                break

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
    role_scopes = _normalize_role_scopes(block_props.get("role_scopes"))
    leadership_limit = _normalize_limit(block_props.get("limit"), 4)
    staff_limit = _normalize_limit(block_props.get("staff_limit"), max(leadership_limit * 2, 8))
    show_staff_carousel = 0 if not block_props.get("show_staff_carousel", True) else 1

    payload = _get_staff_showcase(
        school_name=school.name,
        organization_name=school.organization,
        roles=roles,
        role_profiles=role_profiles,
        role_scopes=role_scopes,
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
