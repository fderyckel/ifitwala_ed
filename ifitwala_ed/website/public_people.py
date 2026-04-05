# ifitwala_ed/website/public_people.py

from __future__ import annotations

import copy

import frappe
from frappe import _
from frappe.utils.caching import redis_cache

from ifitwala_ed.utilities.image_utils import build_employee_image_variants

WORKFLOW_DEFAULT_STATE = "Draft"
WORKFLOW_STATES = (
    "Draft",
    "In Review",
    "Approved",
    "Published",
)
WORKFLOW_TRANSITIONS = {
    "request_review": {
        "from_states": ("Draft",),
        "to_state": "In Review",
        "roles": ("Marketing User", "Website Manager", "System Manager"),
    },
    "approve": {
        "from_states": ("In Review",),
        "to_state": "Approved",
        "roles": ("Website Manager", "System Manager"),
    },
    "publish": {
        "from_states": ("Approved",),
        "to_state": "Published",
        "roles": ("Website Manager", "System Manager"),
    },
    "return_to_draft": {
        "from_states": ("In Review", "Approved", "Published"),
        "to_state": "Draft",
        "roles": ("Marketing User", "Website Manager", "System Manager"),
    },
}


def normalize_workflow_state(workflow_state: str | None) -> str:
    value = (workflow_state or "").strip() or WORKFLOW_DEFAULT_STATE
    if value not in WORKFLOW_STATES:
        frappe.throw(
            _("Invalid workflow state: {0}").format(value),
            frappe.ValidationError,
        )
    return value


def compute_employee_profile_status(*, employee_is_public: bool, workflow_state: str) -> str:
    state = normalize_workflow_state(workflow_state)
    if employee_is_public and state == "Published":
        return "Published"
    return "Draft"


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


def _coerce_sort_order(value) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


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


def _get_published_profile_map(employee_names: tuple[str, ...], school_names: tuple[str, ...]) -> dict[str, dict]:
    if not employee_names or not school_names or not frappe.db.exists("DocType", "Employee Website Profile"):
        return {}

    rows = frappe.get_all(
        "Employee Website Profile",
        filters={
            "employee": ["in", list(employee_names)],
            "school": ["in", list(school_names)],
            "status": "Published",
        },
        fields=[
            "name",
            "employee",
            "school",
            "display_name_override",
            "public_title_override",
            "public_bio",
            "public_email",
            "public_phone",
            "sort_order",
        ],
        order_by="modified desc",
        limit=max(len(employee_names) * 2, 200),
    )

    profile_map: dict[str, dict] = {}
    for row in rows:
        employee_name = (row.get("employee") or "").strip()
        if employee_name and employee_name not in profile_map:
            profile_map[employee_name] = row
    return profile_map


def _build_public_person(row: dict, designation_row: dict | None, profile_row: dict | None) -> dict[str, object]:
    display_name = (
        (profile_row or {}).get("display_name_override") or row.get("employee_full_name") or row.get("name") or ""
    ).strip()
    title = (
        (profile_row or {}).get("public_title_override")
        or (designation_row or {}).get("designation_name")
        or row.get("designation")
        or ""
    ).strip()
    bio = ((profile_row or {}).get("public_bio") or row.get("small_bio") or "").strip()

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
        "public_email": ((profile_row or {}).get("public_email") or "").strip() or None,
        "public_phone": ((profile_row or {}).get("public_phone") or "").strip() or None,
        "sort_order": _coerce_sort_order((profile_row or {}).get("sort_order")),
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

    employee_names = tuple((row.get("name") or "").strip() for row in employee_rows if row.get("name"))
    designation_names = tuple(
        sorted({(row.get("designation") or "").strip() for row in employee_rows if row.get("designation")})
    )
    designation_map = _get_designation_map(designation_names)
    profile_map = _get_published_profile_map(employee_names, school_names)

    people = [
        _build_public_person(
            row,
            designation_map.get((row.get("designation") or "").strip()),
            profile_map.get((row.get("name") or "").strip()),
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
