# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/assessment_calendar_utils.py

import frappe
import json
from frappe.utils import get_datetime, now_datetime

CACHE_TTL = 300  # seconds
CACHE_PREFIX = "ifitwala:task_calendar:v1"

def _cache_key(start, end, filters, user):
    key_filters = tuple(sorted((filters or {}).items()))
    return f"{CACHE_PREFIX}:{user}:{start}:{end}:{hash(key_filters)}"

def _maybe_get_cache(key):
    try:
        val = frappe.cache().get_value(key)
        if val:
            return json.loads(val)
    except Exception:
        pass
    return None

def _maybe_set_cache(key, val):
    try:
        frappe.cache().set_value(key, frappe.as_json(val), expires_in_sec=CACHE_TTL)
    except Exception:
        pass

@frappe.whitelist()
def get_task_events(start, end, filters=None):
    user = frappe.session.user
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except ValueError:
            filters = {}
    if filters is None:
        filters = {}

    key = _cache_key(start, end, filters, user)
    cached = _maybe_get_cache(key)
    if cached is not None:
        return cached

    Task = frappe.qb.DocType("Task")
    query = (
        frappe.qb.from_(Task)
        .select(
            Task.name,
            Task.title,
            Task.due_date,
            Task.delivery_type,
            Task.is_graded,
            Task.status,
            Task.course,
            Task.program,
            Task.school,
            Task.academic_year,
            Task.student_group,
        )
        .where(Task.due_date.isnotnull())
        .where(Task.due_date >= get_datetime(start))
        .where(Task.due_date <= get_datetime(end))
    )

    # add filters as before ...
    def _add_eq(field, val):
        nonlocal query
        if val:
            query = query.where(field == val)
    def _add_in(field, vals):
        nonlocal query
        if vals:
            query = query.where(field.isin(vals))

    _add_eq(Task.school, filters.get("school"))
    _add_eq(Task.academic_year, filters.get("academic_year"))
    _add_eq(Task.program, filters.get("program"))
    _add_eq(Task.course, filters.get("course"))
    _add_eq(Task.student_group, filters.get("student_group"))

    if "status_in" in filters:
        _add_in(Task.status, filters.get("status_in"))
    elif filters.get("status"):
        _add_eq(Task.status, filters.get("status"))

    if filters.get("delivery_type"):
        _add_eq(Task.delivery_type, filters.get("delivery_type"))

    if filters.get("is_graded") is not None:
        try:
            _add_eq(Task.is_graded, int(filters.get("is_graded")))
        except ValueError:
            pass

    instructor_user = filters.get("instructor_user")
    if instructor_user:
        sgi = frappe.get_all(
            "Student Group Instructor",
            filters={"user_id": instructor_user},
            pluck="parent",
        )
        if sgi:
            query = query.where(Task.student_group.isin(sgi))
        else:
            return []

    student_id = filters.get("student")
    if student_id:
        TS = frappe.qb.DocType("Task Student")
        query = (
            query.join(TS).on(TS.parent == Task.name)
            .where(TS.student == student_id)
        )

    query = query.orderby(Task.due_date).orderby(Task.name)

    rows = query.run(as_dict=True)

    events = []
    for r in rows:
        events.append({
            "name": r.name,
            "title": r.title,
            "start": r.due_date,
            "end": r.due_date,
            "allDay": 0,
            "color": None,
            "doc": {
                "delivery_type": r.delivery_type,
                "is_graded": r.is_graded,
                "status": r.status,
                "course": r.course,
                "program": r.program,
                "school": r.school,
                "academic_year": r.academic_year,
                "student_group": r.student_group,
            }
        })

    _maybe_set_cache(key, events)
    return events
