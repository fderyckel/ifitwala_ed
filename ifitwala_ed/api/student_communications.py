# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_communications.py

from __future__ import annotations

from collections import Counter
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime, strip_html, today

from ifitwala_ed.api.org_comm_utils import build_audience_summary, check_audience_match
from ifitwala_ed.api.org_communication_archive import get_audience_label
from ifitwala_ed.api.org_communication_interactions import get_seen_org_communication_names
from ifitwala_ed.utilities.school_tree import get_ancestor_schools

RECENT_WINDOW_DAYS = 90
SOURCE_FILTERS = {"all", "course", "activity", "school", "pastoral", "cohort"}


def _serialize_scalar(value: Any) -> Any:
    if value in (None, ""):
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return value
    return value


def _recent_start_date():
    return add_days(getdate(today()), -RECENT_WINDOW_DAYS)


def _build_course_href(
    course_id: str,
    *,
    student_group: str | None = None,
    open_class_updates: bool = False,
    communication_name: str | None = None,
) -> dict[str, Any]:
    href: dict[str, Any] = {
        "name": "student-course-detail",
        "params": {"course_id": course_id},
    }
    query: dict[str, str] = {}
    if student_group:
        query["student_group"] = student_group
    if open_class_updates:
        query["class_updates"] = "1"
    if communication_name:
        query["communication"] = communication_name
    if query:
        href["query"] = query
    return href


def _build_activity_href(program_offering: str | None = None) -> dict[str, Any]:
    href: dict[str, Any] = {"name": "student-activities"}
    if program_offering:
        href["query"] = {"program_offering": program_offering}
    return href


def _build_center_href(*, source: str | None = None, item: str | None = None) -> dict[str, Any]:
    href: dict[str, Any] = {"name": "student-communications"}
    query = {
        "source": source,
        "item": item,
    }
    query = {key: value for key, value in query.items() if value}
    if query:
        href["query"] = query
    return href


def _clean_source_filter(source: str | None) -> str:
    value = str(source or "").strip().lower() or "all"
    if value not in SOURCE_FILTERS:
        return "all"
    return value


def _snippet_from_html(value: str | None, limit: int = 260) -> str:
    raw_text = strip_html(value or "") if value else ""
    if raw_text and len(raw_text) > limit:
        return raw_text[:limit] + "..."
    return raw_text


def _require_student_name_for_session_user() -> str:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in to view this page."), frappe.AuthenticationError)

    roles = set(frappe.get_roles(user))
    if "Student" not in roles:
        frappe.throw(_("Student access is required."), frappe.PermissionError)

    student_name = frappe.db.get_value("Student", {"student_email": user}, "name")
    if not student_name:
        user_email = frappe.db.get_value("User", user, "email")
        if user_email and user_email != user:
            student_name = frappe.db.get_value("Student", {"student_email": user_email}, "name")

    if not student_name:
        frappe.throw(_("No student profile linked to this login yet."), frappe.PermissionError)
    return student_name


def _resolve_student_context(student_name: str | None = None) -> dict[str, Any]:
    user = frappe.session.user
    roles = set(frappe.get_roles(user))
    resolved_student = student_name or _require_student_name_for_session_user()

    student_row = frappe.db.get_value(
        "Student",
        resolved_student,
        ["name", "anchor_school"],
        as_dict=True,
    )
    if not student_row:
        frappe.throw(_("Student profile could not be resolved."), frappe.DoesNotExistError)

    group_rows = frappe.db.sql(
        """
        SELECT
            sg.name AS student_group,
            sg.student_group_name,
            sg.student_group_abbreviation,
            sg.group_based_on,
            sg.course,
            sg.program_offering,
            sg.school
        FROM `tabStudent Group Student` sgs
        INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
        WHERE sgs.student = %(student)s
          AND COALESCE(sgs.active, 1) = 1
          AND COALESCE(sg.status, 'Active') = 'Active'
        ORDER BY sg.student_group_name ASC, sg.name ASC
        """,
        {"student": resolved_student},
        as_dict=True,
    )

    group_map: dict[str, dict[str, Any]] = {}
    course_group_names: set[str] = set()
    activity_group_names: set[str] = set()
    activity_program_offerings: set[str] = set()
    school_names: set[str] = set()

    anchor_school = (student_row or {}).get("anchor_school")
    if anchor_school:
        school_names.add(anchor_school)

    for row in group_rows or []:
        group_name = row.get("student_group")
        if not group_name:
            continue
        group_map[group_name] = row
        based_on = (row.get("group_based_on") or "").strip()
        if based_on == "Course":
            course_group_names.add(group_name)
        if based_on == "Activity":
            activity_group_names.add(group_name)
            if row.get("program_offering"):
                activity_program_offerings.add(row.get("program_offering"))
        if row.get("school"):
            school_names.add(row.get("school"))

    eligible_school_targets = set(school_names)
    for school_name in list(school_names):
        try:
            eligible_school_targets.update(get_ancestor_schools(school_name) or [])
        except Exception:
            continue

    audience_scope = frappe._dict(
        name=None,
        school=anchor_school or next(iter(sorted(school_names)), None),
        organization=None,
        student_name=resolved_student,
        student_groups=sorted(group_map.keys()),
        school_names=sorted(school_names),
    )

    return {
        "user": user,
        "roles": roles,
        "student_name": resolved_student,
        "student": student_row,
        "group_rows": group_rows or [],
        "group_map": group_map,
        "group_names": set(group_map.keys()),
        "course_group_names": course_group_names,
        "activity_group_names": activity_group_names,
        "activity_program_offerings": activity_program_offerings,
        "school_names": school_names,
        "eligible_school_targets": eligible_school_targets,
        "audience_scope": audience_scope,
    }


def _org_comm_status_conditions(conditions: list[str]):
    conditions.append("oc.status IN ('Published', 'Archived')")


def _org_comm_recent_conditions(conditions: list[str], values: dict[str, Any]):
    conditions.append("oc.publish_from >= %(recent_start)s")
    values["recent_start"] = _recent_start_date()


def _fetch_matching_student_group_rows(comm_names: list[str], group_names: set[str]) -> dict[str, str]:
    if not comm_names or not group_names:
        return {}

    rows = frappe.db.sql(
        """
        SELECT parent AS org_communication, student_group, idx
        FROM `tabOrg Communication Audience`
        WHERE parent IN %(comm_names)s
          AND target_mode = 'Student Group'
          AND student_group IN %(group_names)s
        ORDER BY parent ASC, idx ASC
        """,
        {
            "comm_names": tuple(comm_names),
            "group_names": tuple(sorted(group_names)),
        },
        as_dict=True,
    )

    matched: dict[str, str] = {}
    for row in rows or []:
        comm_name = row.get("org_communication")
        if not comm_name or comm_name in matched:
            continue
        matched[comm_name] = row.get("student_group")
    return matched


def _resolve_org_comm_context(
    row: dict[str, Any],
    context: dict[str, Any],
    matched_student_group: str | None,
) -> dict[str, Any]:
    group_name = matched_student_group or row.get("activity_student_group")
    group_row = (context.get("group_map") or {}).get(group_name) if group_name else None

    if group_row:
        group_label = group_row.get("student_group_name") or group_row.get("student_group_abbreviation") or group_name
        based_on = (group_row.get("group_based_on") or "").strip()

        if based_on == "Course" and group_row.get("course"):
            return {
                "source_type": "course",
                "source_label": "Class Update",
                "context_label": group_label,
                "href": _build_course_href(
                    group_row.get("course"),
                    student_group=group_name,
                    open_class_updates=True,
                    communication_name=row.get("name"),
                ),
                "href_label": "Open class",
            }

        if based_on == "Activity":
            program_offering = row.get("activity_program_offering") or group_row.get("program_offering")
            return {
                "source_type": "activity",
                "source_label": "Activity Update",
                "context_label": group_label,
                "href": _build_activity_href(program_offering),
                "href_label": "Open activity",
            }

        if based_on == "Pastoral":
            return {
                "source_type": "pastoral",
                "source_label": "Pastoral Update",
                "context_label": group_label,
                "href": _build_center_href(source="pastoral", item=f"org::{row['name']}"),
                "href_label": "Open center",
            }

        if based_on == "Cohort":
            return {
                "source_type": "cohort",
                "source_label": "Cohort Update",
                "context_label": group_label,
                "href": _build_center_href(source="cohort", item=f"org::{row['name']}"),
                "href_label": "Open center",
            }

    if row.get("activity_program_offering"):
        return {
            "source_type": "activity",
            "source_label": "Activity Update",
            "context_label": row.get("activity_program_offering"),
            "href": _build_activity_href(row.get("activity_program_offering")),
            "href_label": "Open activity",
        }

    return {
        "source_type": "school",
        "source_label": "School Update",
        "context_label": row.get("school"),
        "href": _build_center_href(source="school", item=f"org::{row['name']}"),
        "href_label": "Open center",
    }


def _serialize_org_communication_item(
    row: dict[str, Any],
    *,
    context: dict[str, Any],
    matched_student_group: str | None,
) -> dict[str, Any]:
    context_meta = _resolve_org_comm_context(row, context, matched_student_group)
    item = {
        "name": row.get("name"),
        "title": row.get("title"),
        "communication_type": row.get("communication_type"),
        "status": row.get("status"),
        "priority": row.get("priority"),
        "portal_surface": row.get("portal_surface"),
        "school": row.get("school"),
        "organization": row.get("organization"),
        "publish_from": _serialize_scalar(row.get("publish_from")),
        "publish_to": _serialize_scalar(row.get("publish_to")),
        "brief_start_date": _serialize_scalar(row.get("brief_start_date")),
        "brief_end_date": _serialize_scalar(row.get("brief_end_date")),
        "interaction_mode": row.get("interaction_mode"),
        "allow_private_notes": row.get("allow_private_notes"),
        "allow_public_thread": row.get("allow_public_thread"),
        "activity_program_offering": row.get("activity_program_offering"),
        "activity_booking": row.get("activity_booking"),
        "activity_student_group": row.get("activity_student_group"),
        "snippet": _snippet_from_html(row.get("message")),
        "has_active_thread": row.get("allow_public_thread"),
        "audience_label": get_audience_label(row.get("name")),
        "audience_summary": build_audience_summary(row.get("name")),
    }
    return {
        "kind": "org_communication",
        "item_id": f"org::{row.get('name')}",
        "sort_at": _serialize_scalar(row.get("publish_from") or row.get("creation")),
        "source_type": context_meta["source_type"],
        "source_label": context_meta["source_label"],
        "context_label": context_meta.get("context_label"),
        "href": context_meta.get("href"),
        "href_label": context_meta.get("href_label"),
        "org_communication": item,
    }


def _fetch_student_org_communications(
    context: dict[str, Any],
    *,
    target_student_groups: set[str] | None = None,
    activity_program_offerings: set[str] | None = None,
    include_school_scope: bool = True,
) -> list[dict[str, Any]]:
    if target_student_groups is None:
        target_groups = set(context.get("group_names") or [])
    else:
        target_groups = set(target_student_groups or [])

    activity_offerings = set(activity_program_offerings or [])

    audience_clauses: list[str] = []
    conditions: list[str] = []
    values: dict[str, Any] = {}

    _org_comm_status_conditions(conditions)
    _org_comm_recent_conditions(conditions, values)

    if target_groups:
        audience_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM `tabOrg Communication Audience` a
                WHERE a.parent = oc.name
                  AND a.parenttype = 'Org Communication'
                  AND a.parentfield = 'audiences'
                  AND a.target_mode = 'Student Group'
                  AND a.student_group IN %(student_groups)s
                  AND COALESCE(a.to_students, 0) = 1
            )
            """
        )
        values["student_groups"] = tuple(sorted(target_groups))

    if include_school_scope and context.get("eligible_school_targets"):
        audience_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM `tabOrg Communication Audience` a
                WHERE a.parent = oc.name
                  AND a.parenttype = 'Org Communication'
                  AND a.parentfield = 'audiences'
                  AND a.target_mode = 'School Scope'
                  AND a.school IN %(school_targets)s
                  AND COALESCE(a.to_students, 0) = 1
            )
            """
        )
        values["school_targets"] = tuple(sorted(context.get("eligible_school_targets") or []))

    if not audience_clauses:
        return []

    conditions.append("(" + " OR ".join(clause.strip() for clause in audience_clauses) + ")")

    if activity_offerings:
        conditions.append("oc.activity_program_offering IN %(activity_program_offerings)s")
        values["activity_program_offerings"] = tuple(sorted(activity_offerings))

    sql = f"""
        SELECT
            oc.name,
            oc.title,
            oc.message,
            oc.communication_type,
            oc.status,
            oc.priority,
            oc.portal_surface,
            oc.school,
            oc.organization,
            oc.publish_from,
            oc.publish_to,
            oc.brief_start_date,
            oc.brief_end_date,
            oc.interaction_mode,
            oc.allow_private_notes,
            oc.allow_public_thread,
            oc.activity_program_offering,
            oc.activity_booking,
            oc.activity_student_group,
            oc.creation
        FROM `tabOrg Communication` oc
        WHERE {" AND ".join(condition.strip() for condition in conditions)}
        ORDER BY oc.publish_from DESC, oc.creation DESC
    """

    candidates = frappe.db.sql(sql, values, as_dict=True)
    matched_groups = _fetch_matching_student_group_rows(
        [row.get("name") for row in (candidates or []) if row.get("name")],
        set(context.get("group_names") or []),
    )

    visible_items: list[dict[str, Any]] = []
    for row in candidates or []:
        if not check_audience_match(
            row.get("name"),
            context.get("user"),
            context.get("roles"),
            context.get("audience_scope"),
        ):
            continue
        visible_items.append(
            _serialize_org_communication_item(
                row,
                context=context,
                matched_student_group=matched_groups.get(row.get("name")),
            )
        )

    return visible_items


def _resolve_course_target_groups(
    context: dict[str, Any],
    *,
    course_id: str,
    student_group: str | None = None,
) -> set[str]:
    requested_group = str(student_group or "").strip()
    if requested_group:
        group_row = (context.get("group_map") or {}).get(requested_group) or {}
        if (group_row.get("group_based_on") or "").strip() == "Course" and group_row.get("course") == course_id:
            return {requested_group}
        return set()

    return {
        row.get("student_group")
        for row in (context.get("group_rows") or [])
        if (row.get("group_based_on") or "").strip() == "Course" and row.get("course") == course_id
    }


def _course_communication_summary(*, user: str, items: list[dict[str, Any]]) -> tuple[dict[str, Any], set[str]]:
    communication_names = [
        item.get("org_communication", {}).get("name")
        for item in items
        if item.get("kind") == "org_communication" and item.get("org_communication", {}).get("name")
    ]
    seen_names = get_seen_org_communication_names(user=user, communication_names=communication_names)
    high_priority_count = sum(
        1 for item in items if (item.get("org_communication", {}).get("priority") or "").strip() in {"High", "Critical"}
    )
    unread_count = sum(1 for comm_name in communication_names if comm_name not in seen_names)
    latest_publish_at = items[0].get("sort_at") if items else None
    return (
        {
            "total_count": len(items),
            "unread_count": unread_count,
            "high_priority_count": high_priority_count,
            "has_high_priority": 1 if high_priority_count else 0,
            "latest_publish_at": latest_publish_at,
        },
        seen_names,
    )


def _annotate_unread_course_items(items: list[dict[str, Any]], *, seen_names: set[str]) -> list[dict[str, Any]]:
    annotated_items: list[dict[str, Any]] = []
    for item in items:
        if item.get("kind") != "org_communication":
            annotated_items.append(item)
            continue
        communication_name = item.get("org_communication", {}).get("name")
        annotated_items.append(
            {
                **item,
                "is_unread": bool(communication_name and communication_name not in seen_names),
            }
        )
    return annotated_items


def _get_student_course_communication_items(
    context: dict[str, Any],
    *,
    course_id: str,
    student_group: str | None = None,
) -> list[dict[str, Any]]:
    target_groups = _resolve_course_target_groups(
        context,
        course_id=course_id,
        student_group=student_group,
    )
    if not target_groups:
        return []

    return _sort_items(
        _fetch_student_org_communications(
            context,
            target_student_groups=target_groups,
            include_school_scope=False,
        )
    )


def _fetch_student_school_events(context: dict[str, Any]) -> list[dict[str, Any]]:
    conditions = [
        "se.docstatus < 2",
        "COALESCE(se.ends_on, se.starts_on) >= %(recent_start)s",
    ]
    values: dict[str, Any] = {
        "recent_start": _recent_start_date(),
        "user": context.get("user"),
    }

    audience_clauses = [
        """
        EXISTS (
            SELECT 1
            FROM `tabSchool Event Audience` sea
            WHERE sea.parent = se.name
              AND sea.audience_type IN ('Whole School Community', 'All Students')
        )
        """
    ]

    if context.get("group_names"):
        audience_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM `tabSchool Event Audience` sea
                WHERE sea.parent = se.name
                  AND sea.audience_type = 'Students in Student Group'
                  AND sea.student_group IN %(event_student_groups)s
            )
            """
        )
        values["event_student_groups"] = tuple(sorted(context.get("group_names") or []))

    audience_clauses.append(
        """
        EXISTS (
            SELECT 1
            FROM `tabSchool Event Participant` sep
            WHERE sep.parent = se.name
              AND sep.parenttype = 'School Event'
              AND sep.participant = %(user)s
        )
        """
    )

    sql = f"""
        SELECT
            se.name,
            se.subject,
            se.school,
            se.location,
            se.event_category,
            se.description,
            se.starts_on,
            se.ends_on,
            se.all_day,
            se.creation
        FROM `tabSchool Event` se
        WHERE {" AND ".join(condition.strip() for condition in conditions)}
          AND ({" OR ".join(clause.strip() for clause in audience_clauses)})
        ORDER BY se.starts_on DESC, se.creation DESC
    """

    rows = frappe.db.sql(sql, values, as_dict=True)
    items: list[dict[str, Any]] = []
    for row in rows or []:
        items.append(
            {
                "kind": "school_event",
                "item_id": f"event::{row.get('name')}",
                "sort_at": _serialize_scalar(row.get("starts_on") or row.get("creation")),
                "source_type": "school",
                "source_label": "School Event",
                "context_label": row.get("school"),
                "href": _build_center_href(source="school", item=f"event::{row.get('name')}"),
                "href_label": "Open center",
                "school_event": {
                    "name": row.get("name"),
                    "subject": row.get("subject") or _("School Event"),
                    "school": row.get("school"),
                    "location": row.get("location"),
                    "event_type": row.get("event_type"),
                    "event_category": row.get("event_category"),
                    "description": row.get("description") or "",
                    "snippet": _snippet_from_html(row.get("description"), limit=220),
                    "starts_on": _serialize_scalar(row.get("starts_on")),
                    "ends_on": _serialize_scalar(row.get("ends_on")),
                    "all_day": 1 if row.get("all_day") else 0,
                },
            }
        )
    return items


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (str(item.get("sort_at") or ""), str(item.get("item_id") or "")),
        reverse=True,
    )


def _build_summary_entry(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("kind") == "org_communication":
        comm = item.get("org_communication") or {}
        return {
            "kind": item.get("source_type"),
            "title": comm.get("title"),
            "subtitle": item.get("context_label") or item.get("source_label"),
            "publish_at": item.get("sort_at"),
            "href": item.get("href"),
            "href_label": item.get("href_label"),
            "item_id": item.get("item_id"),
            "source_label": item.get("source_label"),
        }

    school_event = item.get("school_event") or {}
    return {
        "kind": "school",
        "title": school_event.get("subject"),
        "subtitle": school_event.get("location") or school_event.get("school") or _("School Event"),
        "publish_at": item.get("sort_at"),
        "href": _build_center_href(source="school", item=item.get("item_id")),
        "href_label": "Open center",
        "item_id": item.get("item_id"),
        "source_label": item.get("source_label"),
    }


def get_student_home_communication_summary(student_name: str) -> dict[str, Any]:
    context = _resolve_student_context(student_name)

    course_items = _sort_items(
        _fetch_student_org_communications(
            context,
            target_student_groups=set(context.get("course_group_names") or []),
            include_school_scope=False,
        )
    )
    activity_items = _sort_items(
        _fetch_student_org_communications(
            context,
            target_student_groups=set(context.get("activity_group_names") or []),
            activity_program_offerings=set(context.get("activity_program_offerings") or []),
            include_school_scope=True,
        )
    )

    school_items = [
        item
        for item in _sort_items(
            _fetch_student_org_communications(
                context,
                target_student_groups=set(),
                include_school_scope=True,
            )
        )
        if item.get("source_type") == "school"
    ]
    school_items.extend(_fetch_student_school_events(context))
    school_items = _sort_items(school_items)

    return {
        "center_href": _build_center_href(),
        "latest_course_update": _build_summary_entry(course_items[0]) if course_items else None,
        "latest_activity_update": _build_summary_entry(activity_items[0]) if activity_items else None,
        "latest_school_update": _build_summary_entry(school_items[0]) if school_items else None,
    }


def get_student_course_communications(
    student_name: str,
    *,
    course_id: str,
    student_group: str | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    context = _resolve_student_context(student_name)
    items = _get_student_course_communication_items(
        context,
        course_id=course_id,
        student_group=student_group,
    )
    return items[: max(1, int(limit or 6))]


def get_student_course_communication_summary(
    student_name: str,
    *,
    course_id: str,
    student_group: str | None = None,
) -> dict[str, Any]:
    context = _resolve_student_context(student_name)
    items = _get_student_course_communication_items(
        context,
        course_id=course_id,
        student_group=student_group,
    )
    summary, _ = _course_communication_summary(user=context.get("user"), items=items)
    return summary


@frappe.whitelist()
def get_student_course_communication_drawer(
    course_id: str,
    student_group: str | None = None,
    focus_communication: str | None = None,
    start: int = 0,
    page_length: int = 24,
) -> dict[str, Any]:
    context = _resolve_student_context()
    items = _get_student_course_communication_items(
        context,
        course_id=course_id,
        student_group=student_group,
    )
    summary, seen_names = _course_communication_summary(user=context.get("user"), items=items)
    annotated_items = _annotate_unread_course_items(items, seen_names=seen_names)

    focus_name = str(focus_communication or "").strip()
    offset = max(int(start or 0), 0)
    page_len = max(int(page_length or 24), 1)
    paged_items = annotated_items[offset : offset + page_len]

    if focus_name:
        focused_item = next(
            (item for item in annotated_items if item.get("org_communication", {}).get("name") == focus_name),
            None,
        )
        if focused_item and not any(row.get("org_communication", {}).get("name") == focus_name for row in paged_items):
            paged_items = [focused_item] + [
                row for row in paged_items if row.get("org_communication", {}).get("name") != focus_name
            ]
            paged_items = paged_items[:page_len]

    return {
        "meta": {
            "generated_at": _serialize_scalar(now_datetime()),
            "course_id": course_id,
            "student_group": student_group or None,
            "focus_communication": focus_name or None,
        },
        "summary": summary,
        "items": paged_items,
        "total_count": len(annotated_items),
        "has_more": (offset + page_len) < len(annotated_items),
        "start": offset,
        "page_length": page_len,
    }


def get_student_activity_communications(
    student_name: str,
    *,
    activity_program_offering: str | None = None,
    activity_student_group: str | None = None,
    start: int = 0,
    page_length: int = 30,
) -> dict[str, Any]:
    context = _resolve_student_context(student_name)
    target_groups = (
        {activity_student_group} if activity_student_group else set(context.get("activity_group_names") or [])
    )
    target_offerings = (
        {activity_program_offering}
        if activity_program_offering
        else set(context.get("activity_program_offerings") or [])
    )

    items = _sort_items(
        _fetch_student_org_communications(
            context,
            target_student_groups=target_groups,
            activity_program_offerings=target_offerings,
            include_school_scope=True,
        )
    )

    offset = max(int(start or 0), 0)
    page_len = max(int(page_length or 30), 1)
    paged_items = [item.get("org_communication") for item in items[offset : offset + page_len]]

    return {
        "items": [item for item in paged_items if item],
        "total_count": len(items),
        "has_more": (offset + page_len) < len(items),
        "start": offset,
        "page_length": page_len,
    }


@frappe.whitelist()
def get_student_communication_center(
    source: str | None = None,
    start: int = 0,
    page_length: int = 24,
) -> dict[str, Any]:
    context = _resolve_student_context()
    source_filter = _clean_source_filter(source)

    items = _fetch_student_org_communications(context, include_school_scope=True)
    items.extend(_fetch_student_school_events(context))
    items = _sort_items(items)

    if source_filter != "all":
        items = [item for item in items if item.get("source_type") == source_filter]

    summary_counts = Counter(item.get("source_type") or "other" for item in items)

    offset = max(int(start or 0), 0)
    page_len = max(int(page_length or 24), 1)
    paged_items = items[offset : offset + page_len]

    return {
        "meta": {
            "generated_at": _serialize_scalar(now_datetime()),
            "source": source_filter,
        },
        "summary": {
            "total_items": len(items),
            "source_counts": dict(summary_counts),
        },
        "items": paged_items,
        "total_count": len(items),
        "has_more": (offset + page_len) < len(items),
        "start": offset,
        "page_length": page_len,
    }
