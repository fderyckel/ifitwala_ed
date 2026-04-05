# ifitwala_ed/website/public_people.py

from __future__ import annotations

import copy

import frappe
from frappe.utils.caching import redis_cache

from ifitwala_ed.utilities.image_utils import build_employee_image_variants


def _normalize_school_names(school_names) -> tuple[str, ...]:
    if isinstance(school_names, str):
        school_names = [school_names]

    normalized = sorted({str(name or "").strip() for name in (school_names or []) if str(name or "").strip()})
    return tuple(normalized)


def _build_initials(full_name: str | None) -> str:
    name = (full_name or "").strip()
    if not name:
        return "?"
    parts = [part[0].upper() for part in name.split() if part]
    if not parts:
        return "?"
    return "".join(parts[:2])


def _get_designation_map(designation_names: tuple[str, ...]) -> dict[str, dict]:
    if not designation_names:
        return {}

    rows = frappe.get_all(
        "Designation",
        filters={"name": ["in", list(designation_names)]},
        fields=["name", "designation_name", "default_role_profile"],
        limit=max(len(designation_names), 200),
    )
    return {row["name"]: row for row in rows if row.get("name")}


def _build_public_person(row: dict, designation_row: dict | None) -> dict[str, object]:
    display_name = (row.get("employee_full_name") or row.get("name") or "").strip()
    title = ((designation_row or {}).get("designation_name") or row.get("designation") or "").strip()
    bio = (row.get("small_bio") or "").strip()

    return {
        "employee": (row.get("name") or "").strip(),
        "school": (row.get("school") or "").strip(),
        "organization": (row.get("organization") or "").strip(),
        "designation": (row.get("designation") or "").strip(),
        "role_profile": ((designation_row or {}).get("default_role_profile") or "").strip() or None,
        "name": display_name,
        "title": title or None,
        "bio": bio or None,
        "initials": _build_initials(display_name),
        "public_email": None,
        "public_phone": None,
        "sort_order": None,
        "photo": build_employee_image_variants(
            row.get("name"),
            original_url=row.get("employee_image"),
        ),
    }


def _sort_people(people: list[dict[str, object]]) -> list[dict[str, object]]:
    def sort_key(person: dict[str, object]) -> tuple[int, int, str, str]:
        sort_order = person.get("sort_order")
        has_sort_order = 0 if sort_order is not None else 1
        effective_sort_order = int(sort_order) if sort_order is not None else 999999
        title = str(person.get("title") or "")
        name = str(person.get("name") or "")
        return (has_sort_order, effective_sort_order, title, name)

    return sorted(people, key=sort_key)


@redis_cache(ttl=3600)
def _get_published_public_people_records(
    school_names: tuple[str, ...],
    organization_name: str,
) -> list[dict[str, object]]:
    if not school_names:
        return []

    employee_rows = frappe.get_all(
        "Employee",
        filters={
            "organization": organization_name,
            "school": ["in", list(school_names)],
            "show_on_website": 1,
        },
        fields=[
            "name",
            "employee_full_name",
            "employee_image",
            "designation",
            "small_bio",
            "school",
            "organization",
        ],
        order_by="designation asc, employee_full_name asc",
        limit=max(len(school_names) * 200, 200),
    )
    if not employee_rows:
        return []

    designation_names = tuple(
        sorted({(row.get("designation") or "").strip() for row in employee_rows if row.get("designation")})
    )
    designation_map = _get_designation_map(designation_names)

    people = [
        _build_public_person(
            row,
            designation_map.get((row.get("designation") or "").strip()),
        )
        for row in employee_rows
    ]
    return _sort_people(people)


def invalidate_public_people_cache(*_args, **_kwargs):
    clear_cache = getattr(_get_published_public_people_records, "clear_cache", None)
    if callable(clear_cache):
        clear_cache()


def get_public_people_records(*, school_names, organization_name: str) -> list[dict[str, object]]:
    normalized_school_names = _normalize_school_names(school_names)
    if not normalized_school_names:
        return []
    return copy.deepcopy(
        _get_published_public_people_records(
            school_names=normalized_school_names,
            organization_name=(organization_name or "").strip(),
        )
    )
