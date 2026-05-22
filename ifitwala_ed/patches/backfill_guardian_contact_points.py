# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections.abc import Callable
from typing import Any

REQUIRED_TABLES = (
    "Communication Contact Point",
    "Contact Access Log",
    "Guardian",
    "Student",
    "Student Guardian",
)
BATCH_SIZE = 500
CONTACT_POINT_PURPOSE = "school_communication"
CONTACT_POINT_WORKFLOW = "guardian_contact_point_backfill"


def execute():
    import frappe
    from ifitwala_ed.contacts.contact_privacy import sync_guardian_contact_points

    if not _required_tables_exist(frappe):
        return

    backfill_guardian_contact_points(
        frappe,
        sync_function=sync_guardian_contact_points,
    )


def backfill_guardian_contact_points(
    frappe_module,
    *,
    sync_function: Callable[..., list[str]],
    batch_size: int = BATCH_SIZE,
) -> dict[str, int]:
    stats = {
        "guardian_school_links": 0,
        "guardians_eligible": 0,
        "guardians_processed": 0,
        "school_contexts_processed": 0,
        "guardians_missing": 0,
        "contact_points_synced": 0,
        "failures": 0,
    }

    guardian_schools = _guardian_schools_by_student_link(frappe_module)
    stats["guardian_school_links"] = sum(len(schools) for schools in guardian_schools.values())
    stats["guardians_eligible"] = len(guardian_schools)
    if not guardian_schools:
        return stats

    processed_guardians: set[str] = set()
    seen_guardians: set[str] = set()
    for guardian_batch in _chunks(sorted(guardian_schools), batch_size):
        guardian_rows = frappe_module.get_all(
            "Guardian",
            filters={"name": ["in", guardian_batch]},
            fields=["name", "organization", "guardian_email", "guardian_mobile_phone"],
            order_by="creation asc, name asc",
            limit=0,
        )
        for row in guardian_rows or []:
            guardian_name = _clean_data(_row_get(row, "name"))
            if not guardian_name:
                continue
            seen_guardians.add(guardian_name)
            for school_name in sorted(guardian_schools.get(guardian_name) or []):
                try:
                    synced = sync_function(
                        row,
                        school=school_name,
                        purpose=CONTACT_POINT_PURPOSE,
                        workflow=CONTACT_POINT_WORKFLOW,
                    )
                except Exception:
                    stats["failures"] += 1
                    _log_backfill_failure(
                        frappe_module,
                        guardian_name=guardian_name,
                        school=school_name,
                    )
                    continue

                processed_guardians.add(guardian_name)
                stats["school_contexts_processed"] += 1
                stats["contact_points_synced"] += len(synced or [])

    stats["guardians_processed"] = len(processed_guardians)
    stats["guardians_missing"] = len(set(guardian_schools) - seen_guardians)
    return stats


def _required_tables_exist(frappe_module) -> bool:
    table_exists = getattr(frappe_module.db, "table_exists", None)
    if not callable(table_exists):
        return False
    return all(table_exists(doctype) for doctype in REQUIRED_TABLES)


def _guardian_schools_by_student_link(frappe_module) -> dict[str, set[str]]:
    relation_rows = frappe_module.get_all(
        "Student Guardian",
        filters={
            "parenttype": "Student",
            "parentfield": "guardians",
            "guardian": ["is", "set"],
        },
        fields=["parent", "guardian"],
        order_by="parent asc, idx asc",
        limit=0,
    )
    student_names = sorted(
        {
            _clean_data(_row_get(row, "parent"))
            for row in relation_rows or []
            if _clean_data(_row_get(row, "parent"))
        }
    )
    if not student_names:
        return {}

    school_by_student: dict[str, str] = {}
    for student_batch in _chunks(student_names, BATCH_SIZE):
        student_rows = frappe_module.get_all(
            "Student",
            filters={"name": ["in", student_batch]},
            fields=["name", "anchor_school"],
            limit=0,
        )
        for row in student_rows or []:
            student_name = _clean_data(_row_get(row, "name"))
            school_name = _clean_data(_row_get(row, "anchor_school"))
            if student_name and school_name:
                school_by_student[student_name] = school_name

    guardian_schools: dict[str, set[str]] = {}
    for row in relation_rows or []:
        guardian_name = _clean_data(_row_get(row, "guardian"))
        student_name = _clean_data(_row_get(row, "parent"))
        school_name = school_by_student.get(student_name)
        if not guardian_name or not school_name:
            continue
        guardian_schools.setdefault(guardian_name, set()).add(school_name)

    return guardian_schools


def _chunks(values: list[str], batch_size: int):
    size = max(int(batch_size or BATCH_SIZE), 1)
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _row_get(row: Any, fieldname: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(fieldname, default)
    if hasattr(row, "get"):
        return row.get(fieldname, default)
    return getattr(row, fieldname, default)


def _clean_data(value: Any) -> str:
    return str(value or "").strip()


def _log_backfill_failure(frappe_module, *, guardian_name: str, school: str) -> None:
    log_error = getattr(frappe_module, "log_error", None)
    if not callable(log_error):
        return

    traceback = ""
    get_traceback = getattr(frappe_module, "get_traceback", None)
    if callable(get_traceback):
        traceback = get_traceback()

    log_error(
        "\n".join(
            [
                "Guardian Contact Point backfill failed.",
                f"guardian={guardian_name}",
                f"school={school}",
                traceback,
            ]
        ).strip(),
        "Guardian Contact Point Backfill Failed",
    )
