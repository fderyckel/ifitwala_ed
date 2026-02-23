# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/student_group_scheduling.py

"""
Student Group Scheduling Utilities

This module centralizes high-level scheduling logic related to Student Groups,
but *outside* of the Student Group DocType itself.

Responsibilities:

1. Cross-group conflict detection
   - instructor/staff double-booking across Student Groups
   - student double-booking across Student Groups
   - slot-level conflict aggregation helpers

2. Slot helpers
   - internal utilities to normalize and aggregate (rotation_day, block_number)
     pairs for SQL and for UI consumption

NO DocTypes live here.
"""

# IMPORTANT:
# This module performs conflict detection ONLY at the timetable level.
# It does NOT consider concrete bookings (Meetings, Events).
# Location conflicts are delegated to the canonical room conflict helper.

from __future__ import annotations

import json
from collections import defaultdict
from typing import Dict, List, Tuple

import frappe
from frappe import _


def _extract(obj, attr):
    """Return obj[attr] or obj.attr, whichever exists (None if missing)."""
    if isinstance(obj, dict):
        return obj.get(attr)
    return getattr(obj, attr, None)


def _uniq(seq):
    """Return list of unique, truthy items preserving order."""
    seen = set()
    out = []
    for item in seq:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _get_display_map(doctype: str, label_field: str, ids: Tuple[str, ...]) -> Dict[str, str]:
    """Return {id: display_label} for the given ids."""
    if not ids:
        return {}

    unique_ids = list(dict.fromkeys([i for i in ids if i]))
    if not unique_ids:
        return {}

    rows = frappe.db.get_all(
        doctype,
        filters={"name": ["in", unique_ids]},
        fields=["name", label_field],
    )
    return {row["name"]: row.get(label_field) or row["name"] for row in rows}


def _build_slot_conditions(slots: List[Tuple[int, int]]) -> Tuple[str, dict]:
    """Return SQL snippet + params for (rotation_day, block_number) pairs."""
    conds = []
    params = {}
    for idx, (rot, blk) in enumerate(slots):
        conds.append(f"(gs.rotation_day = %(rot_{idx})s AND gs.block_number = %(blk_{idx})s)")
        params[f"rot_{idx}"] = rot
        params[f"blk_{idx}"] = blk
    return " OR ".join(conds), params


def _aggregate_conflicts(rows, label_map):
    """Group rows by (rotation_day, block_number) with deduped ids & groups."""
    slots = {}
    for row in rows:
        rot = row.get("rotation_day")
        blk = row.get("block_number")
        entity = row.get("entity")
        group = row.get("student_group")

        if rot is None or blk is None or not entity:
            continue
        try:
            rot = int(rot)
            blk = int(blk)
        except Exception:
            continue

        key = (rot, blk)
        entry = slots.setdefault(
            key,
            {"rotation_day": rot, "block_number": blk, "ids": [], "groups": []},
        )
        entry["ids"].append(entity)
        entry["groups"].append(group)

    out = []
    for entry in slots.values():
        ids = tuple(_uniq(entry["ids"]))
        out.append(
            {
                "rotation_day": entry["rotation_day"],
                "block_number": entry["block_number"],
                "ids": ids,
                "labels": tuple(label_map.get(i, i) for i in ids),
                "groups": tuple(_uniq(entry["groups"])),
            }
        )
    return out


@frappe.whitelist()
def check_slot_conflicts(group_doc):
    """Scan existing Student Group schedules for clashes.

    Returns a dict keyed by category (instructor / student) with a list of
    payload dicts:
            {
                    "rotation_day": <int>,
                    "block_number": <int>,
                    "ids": (<entity ids>, ...),
                    "labels": (<readable names>, ...),
                    "groups": (<student groups>, ...)
            }

    Room/location clashes are handled by the canonical room conflict helper.
    """
    # This function MUST NOT reason about rooms or locations.
    # Room conflicts are handled exclusively by the canonical room conflict helper
    # Normalize input: client calls send JSON string, server calls may send a dict/doc
    if isinstance(group_doc, str):
        group_doc = frappe._dict(json.loads(group_doc))

    # Ensure .name is never NULL for the SQL filter (gs.parent != %(grp)s)
    group_name = group_doc.get("name") or "__new__"

    conflicts = defaultdict(list)

    # Pre-collect instructors & students once (avoid per-slot sub-queries)
    instructors = group_doc.get("instructors") or []
    students = group_doc.get("students") or []
    slots = group_doc.get("student_group_schedule") or []

    instructor_entities = [
        _extract(i, "employee") or _extract(i, "instructor")
        for i in instructors
        if _extract(i, "employee") or _extract(i, "instructor")
    ]
    instructor_ids = tuple(_uniq(instructor_entities))
    student_ids = tuple(_extract(s, "student") for s in students if _extract(s, "student"))

    normalized_slots: List[Tuple[int, int]] = []
    for slot in slots:
        rot = _extract(slot, "rotation_day")
        blk = _extract(slot, "block_number")
        if rot is None or blk is None:
            continue
        try:
            rot = int(rot)
            blk = int(blk)
        except Exception:
            continue
        normalized_slots.append((rot, blk))

    if not normalized_slots:
        return {}

    slot_clause, slot_params = _build_slot_conditions(normalized_slots)
    if not slot_clause:
        return {}

    def _instructor_label_map(entities) -> Dict[str, str]:
        """
        Map Employee IDs → human-readable labels.

        We try, in order of preference:
        - employee_full_name (your new field)
        - employee_name      (legacy ERPNext field, if present)
        - first_name + last_name
        - fallback to the Employee ID itself
        """
        if not entities:
            return {}

        ids = list({e for e in entities if e})
        if not ids:
            return {}

        # Build a safe field list that matches your Employee schema
        fields = ["name"]

        # New schema (your current Employee)
        if frappe.db.has_column("Employee", "employee_full_name"):
            fields.append("employee_full_name")

        # Legacy ERPNext-style field – keep for compatibility on other sites
        if frappe.db.has_column("Employee", "employee_name"):
            fields.append("employee_name")

        # Extra safety: if you ever rely on first/last names
        if frappe.db.has_column("Employee", "employee_first_name"):
            fields.append("employee_first_name")
        if frappe.db.has_column("Employee", "employee_last_name"):
            fields.append("employee_last_name")

        emp_rows = frappe.get_all(
            "Employee",
            filters={"name": ["in", ids]},
            fields=fields,
            ignore_permissions=True,
        )

        label_map: Dict[str, str] = {}

        for row in emp_rows:
            # frappe.get_all → dict rows
            name = row.get("name")

            label = (
                row.get("employee_full_name")
                or row.get("employee_name")
                or " ".join(
                    [
                        (row.get("employee_first_name") or "").strip(),
                        (row.get("employee_last_name") or "").strip(),
                    ]
                ).strip()
                or name
            )

            if name:
                label_map[name] = label

        return label_map

    instructor_labels = _instructor_label_map(instructor_ids)
    student_labels = _get_display_map("Student", "student_full_name", student_ids)

    if instructor_ids:
        params = {"grp": group_name, "ids": instructor_ids}
        params.update(slot_params)
        rows = frappe.db.sql(
            f"""
            SELECT coalesce(gi.employee, gi.instructor) AS entity,
                   gs.rotation_day,
                   gs.block_number,
                   gs.parent AS student_group
            FROM `tabStudent Group Instructor` gi
            JOIN `tabStudent Group Schedule`  gs ON gs.parent = gi.parent
            WHERE coalesce(gi.employee, gi.instructor) IN %(ids)s
                AND gs.parent != %(grp)s
                AND gs.docstatus < 2
                AND ({slot_clause})
            """,
            params,
            as_dict=True,
        )
        conflicts["instructor"] = _aggregate_conflicts(rows, instructor_labels)

    if student_ids:
        params = {"grp": group_name, "ids": student_ids}
        params.update(slot_params)
        rows = frappe.db.sql(
            f"""
            SELECT st.student AS entity,
                   gs.rotation_day,
                   gs.block_number,
                   gs.parent AS student_group
            FROM `tabStudent Group Student` st
            JOIN `tabStudent Group Schedule` gs ON gs.parent = st.parent
            WHERE st.student IN %(ids)s
                AND gs.parent != %(grp)s
                AND gs.docstatus < 2
                AND ({slot_clause})
            """,
            params,
            as_dict=True,
        )
        conflicts["student"] = _aggregate_conflicts(rows, student_labels)

    return dict(conflicts)


def get_school_for_student_group(student_group: str) -> str | None:
    """
    Return the School linked to the Student Group.

    Priority:
    1) Student Group.school
    2) Program Offering.school
    3) Academic Year's school

    This is SG-domain logic and should not live in schedule_utils.
    """
    if not student_group:
        return None

    sg = frappe.get_cached_doc("Student Group", student_group)

    if sg.school:
        return sg.school

    if sg.program_offering:
        school = frappe.db.get_value("Program Offering", sg.program_offering, "school")
        if school:
            return school

    if sg.academic_year:
        school = frappe.db.get_value("Academic Year", sg.academic_year, "school")
        if school:
            return school

    return None


@frappe.whitelist()
def fetch_block_grid(schedule_name: str | None = None, sg: str | None = None) -> dict:
    """
    Return rotation-day metadata to build the quick-add matrix for a Student Group.

    Args:
        schedule_name: explicit School Schedule name (may be None)
        sg: Student Group name – used to infer schedule & instructors

    Behaviour:
    - If schedule_name is not supplied, resolve it from the Student Group via _get_school_schedule().
    - Returns:
        {
          "schedule_name": <str>,
          "days": [1, 2, ...],
          "grid": {
            1: [{"block": 1, "label": "B1", "from": <time>, "to": <time>}, ...],
            ...
          },
          "instructors": [{"value": <instructor id>, "label": <name>}, ...]
        }
    """
    # Resolve schedule when not supplied
    if not schedule_name:
        sg = sg or frappe.form_dict.get("sg")  # backward compatibility for old calls
        if not sg:
            frappe.throw(_("Either schedule_name or sg is required."))

        sg_doc = frappe.get_doc("Student Group", sg)
        schedule = sg_doc._get_school_schedule()
        if not schedule:
            frappe.throw(_("Could not resolve a School Schedule for this Student Group."))
        schedule_name = schedule.name
    else:
        # still need sg for instructor list; fall back to form_dict
        sg = sg or frappe.form_dict.get("sg")

    doc = frappe.get_cached_doc("School Schedule", schedule_name)

    grid: dict[int, list[dict]] = {}
    for blk in doc.school_schedule_block:  # variable blocks per day
        grid.setdefault(blk.rotation_day, []).append(
            {
                "block": blk.block_number,
                "label": f"B{blk.block_number}",
                "from": blk.from_time,
                "to": blk.to_time,
            }
        )

    # sort blocks inside each day
    for day in grid:
        grid[day].sort(key=lambda b: b["block"])

    # instructor list is purely SG-based; optional if sg is missing
    instructors = []
    if sg:
        sg_doc = frappe.get_doc("Student Group", sg)
        instructors = [
            {"value": i.instructor, "label": i.instructor_name or i.instructor}
            for i in (sg_doc.instructors or [])
            if i.instructor
        ]

    return {
        "schedule_name": schedule_name,
        "days": sorted(grid.keys()),
        "grid": grid,
        "instructors": instructors,
    }
