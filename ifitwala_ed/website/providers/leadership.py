# ifitwala_ed/website/providers/leadership.py

from __future__ import annotations

from frappe.utils import cint

from ifitwala_ed.utilities.school_tree import get_descendant_school_scope
from ifitwala_ed.website.public_people import (
    get_public_people_records,
    invalidate_public_people_cache,
)

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


def _resolve_candidate_school_scope(
    school_name: str,
    role_scopes: tuple[tuple[str, str, str, int | None], ...],
) -> tuple[str, ...]:
    current_school_scope = (school_name,)
    scoped_schools = {school_name}
    for schools in _resolve_role_scope_maps(school_name, role_scopes):
        for values in schools.values():
            scoped_schools.update(values or current_school_scope)
    return tuple(sorted(scoped_schools))


def invalidate_leadership_cache(*_args, **_kwargs):
    invalidate_public_people_cache()


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

    candidate_school_scope = _resolve_candidate_school_scope(school.name, role_scopes)
    people_rows = get_public_people_records(
        school_names=candidate_school_scope,
        organization_name=school.organization,
    )
    current_school_scope = (school.name,)
    role_scope_map, role_profile_scope_map = _resolve_role_scope_maps(school.name, role_scopes)

    leadership_candidates = []
    leadership_designations = set(roles)
    for row in people_rows:
        designation_name = (row.get("designation") or "").strip()
        role_profile = (row.get("role_profile") or "").strip()
        row_school = (row.get("school") or "").strip()

        if roles:
            if designation_name not in leadership_designations:
                continue
            allowed_schools = role_scope_map.get(designation_name) or current_school_scope
            if row_school not in allowed_schools:
                continue
        else:
            if role_profile not in role_profiles:
                continue
            allowed_schools = (
                role_scope_map.get(designation_name) or role_profile_scope_map.get(role_profile) or current_school_scope
            )
            if row_school not in allowed_schools:
                continue
            leadership_designations.add(designation_name)

        leadership_candidates.append(row)

    leadership_people = leadership_candidates[:leadership_limit]

    staff_people = []
    if show_staff_carousel:
        for row in people_rows:
            if (row.get("school") or "").strip() != school.name:
                continue
            if leadership_designations and (row.get("designation") or "").strip() in leadership_designations:
                continue
            staff_people.append(row)
            if len(staff_people) >= staff_limit:
                break

    sections = []
    if leadership_people:
        sections.append(
            {
                "key": "leadership",
                "title": (block_props.get("leadership_title") or "").strip() or DEFAULT_LEADERSHIP_TITLE,
                "description": DEFAULT_SECTION_COPY["leadership"],
                "people": leadership_people,
            }
        )

    if show_staff_carousel and staff_people:
        sections.append(
            {
                "key": "staff",
                "title": (block_props.get("staff_title") or "").strip() or DEFAULT_STAFF_TITLE,
                "description": DEFAULT_SECTION_COPY["staff"],
                "people": staff_people,
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
