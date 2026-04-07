# ifitwala_ed/website/providers/staff_directory.py

from __future__ import annotations

from frappe.utils import cint

from ifitwala_ed.website.public_people import get_public_people_records

DEFAULT_TITLE = "Faculty & Staff"
DEFAULT_EMPTY_STATE_TITLE = "No staff profiles available yet"
DEFAULT_EMPTY_STATE_TEXT = "This directory fills automatically when employees are marked to show on the website."


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


def _normalize_limit(value) -> int | None:
    if value in (None, "", "Null"):
        return None
    return max(cint(value), 1)


def _matches_include_filters(
    person: dict[str, object],
    *,
    designations: tuple[str, ...],
    role_profiles: tuple[str, ...],
) -> bool:
    if not designations and not role_profiles:
        return True

    designation = str(person.get("designation") or "").strip()
    role_profile = str(person.get("role_profile") or "").strip()
    return designation in designations or role_profile in role_profiles


def _build_search_text(person: dict[str, object]) -> str:
    parts = [
        person.get("name"),
        person.get("title"),
        person.get("bio"),
        person.get("designation"),
        person.get("role_profile"),
    ]
    return " ".join(str(part or "").strip() for part in parts if str(part or "").strip()).lower()


def _build_designation_options(people: list[dict[str, object]]) -> list[dict[str, str]]:
    option_map: dict[str, str] = {}
    for person in people:
        value = str(person.get("designation") or "").strip()
        label = str(person.get("title") or person.get("designation") or "").strip()
        if value and value not in option_map:
            option_map[value] = label or value

    return [
        {"value": value, "label": option_map[value]}
        for value in sorted(option_map, key=lambda item: option_map[item].lower())
    ]


def _build_role_profile_options(people: list[dict[str, object]]) -> list[dict[str, str]]:
    values = sorted(
        {
            str(person.get("role_profile") or "").strip()
            for person in people
            if str(person.get("role_profile") or "").strip()
        }
    )
    return [{"value": value, "label": value} for value in values]


def get_context(*, school, page, block_props):
    designations = _normalize_string_list(block_props.get("designations"))
    role_profiles = _normalize_string_list(block_props.get("role_profiles"))
    limit = _normalize_limit(block_props.get("limit"))

    people = [
        {
            **person,
            "search_text": _build_search_text(person),
        }
        for person in get_public_people_records(
            school_names=(school.name,),
            organization_name=school.organization,
        )
        if _matches_include_filters(
            person,
            designations=designations,
            role_profiles=role_profiles,
        )
    ]

    if limit is not None:
        people = people[:limit]

    designation_options = _build_designation_options(people)
    role_profile_options = _build_role_profile_options(people)
    show_search = bool(block_props.get("show_search", True))
    show_designation_filter = bool(block_props.get("show_designation_filter", True)) and len(designation_options) > 1
    show_role_profile_filter = bool(block_props.get("show_role_profile_filter", True)) and len(role_profile_options) > 1

    return {
        "data": {
            "title": (block_props.get("title") or "").strip() or DEFAULT_TITLE,
            "description": (block_props.get("description") or "").strip() or None,
            "people": people,
            "people_count": len(people),
            "designation_options": designation_options,
            "role_profile_options": role_profile_options,
            "show_search": show_search,
            "show_designation_filter": show_designation_filter,
            "show_role_profile_filter": show_role_profile_filter,
            "has_filters": bool(show_search or show_designation_filter or show_role_profile_filter),
            "has_people": bool(people),
            "empty_state_title": (block_props.get("empty_state_title") or "").strip() or DEFAULT_EMPTY_STATE_TITLE,
            "empty_state_text": (block_props.get("empty_state_text") or "").strip() or DEFAULT_EMPTY_STATE_TEXT,
        }
    }
