# ifitwala_ed/schedule/api/calendar/quick_create/attendees.py

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _

from ifitwala_ed.schedule.api.calendar.quick_create.constants import (
    ATTENDEE_SEARCH_CACHE_TTL_SECONDS,
    MAX_ATTENDEE_SEARCH_RESULTS,
)
from ifitwala_ed.schedule.api.calendar.quick_create.dto import (
    _coerce_minutes,
    _current_user_label,
    _json_cache_key,
    _normalize_attendee_kinds,
    _safe_text,
)
from ifitwala_ed.schedule.api.calendar.quick_create.scope import (
    _ensure_allowed_team,
    _ensure_can_create_meeting,
    _get_quick_create_scope,
)


def _search_employee_attendees(
    *,
    user: str,
    organization_scope: list[str] | None,
    query: str,
    limit: int,
) -> list[dict]:
    params = {
        "query": f"%{query}%",
        "limit": limit,
        "current_user": user,
    }

    org_sql = ""
    organization_values = [org for org in (organization_scope or []) if org]
    if organization_values:
        org_sql = "AND e.organization IN %(organizations)s"
        params["organizations"] = tuple(organization_values)

    rows = frappe.db.sql(
        f"""
        SELECT
            u.name AS user_id,
            COALESCE(NULLIF(u.full_name, ''), NULLIF(e.employee_full_name, ''), u.name) AS label,
            e.school AS school
        FROM `tabEmployee` e
        INNER JOIN `tabUser` u ON u.name = e.user_id
        WHERE
            e.user_id IS NOT NULL
            AND e.employment_status = 'Active'
            AND COALESCE(u.enabled, 1) = 1
            AND u.name != %(current_user)s
            {org_sql}
            AND (
                u.name LIKE %(query)s
                OR u.full_name LIKE %(query)s
                OR e.name LIKE %(query)s
                OR e.employee_full_name LIKE %(query)s
            )
        ORDER BY label ASC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )
    return [
        {
            "value": row.get("user_id"),
            "label": row.get("label") or row.get("user_id"),
            "meta": row.get("school") or _("Employee"),
            "kind": "employee",
            "availability_mode": "authoritative",
        }
        for row in rows
        if row.get("user_id")
    ]


def _search_student_attendees(*, school_scope: list[str], query: str, limit: int) -> list[dict]:
    if not school_scope:
        return []

    rows = frappe.db.sql(
        """
        SELECT
            u.name AS user_id,
            COALESCE(NULLIF(s.student_preferred_name, ''), NULLIF(s.student_full_name, ''), s.name) AS label,
            s.anchor_school AS school
        FROM `tabStudent` s
        INNER JOIN `tabUser` u ON u.name = s.student_email
        WHERE
            s.enabled = 1
            AND COALESCE(u.enabled, 1) = 1
            AND s.anchor_school IN %(schools)s
            AND (
                s.name LIKE %(query)s
                OR s.student_email LIKE %(query)s
                OR s.student_full_name LIKE %(query)s
                OR s.student_preferred_name LIKE %(query)s
            )
        ORDER BY label ASC
        LIMIT %(limit)s
        """,
        {
            "schools": tuple(school_scope),
            "query": f"%{query}%",
            "limit": limit,
        },
        as_dict=True,
    )
    return [
        {
            "value": row.get("user_id"),
            "label": row.get("label") or row.get("user_id"),
            "meta": row.get("school") or _("Student"),
            "kind": "student",
            "availability_mode": "school_schedule",
        }
        for row in rows
        if row.get("user_id")
    ]


def _search_guardian_attendees(*, school_scope: list[str], query: str, limit: int) -> list[dict]:
    if not school_scope:
        return []

    rows = frappe.db.sql(
        """
        SELECT DISTINCT
            u.name AS user_id,
            COALESCE(NULLIF(u.full_name, ''), NULLIF(g.guardian_full_name, ''), NULLIF(g.guardian_email, ''), u.name) AS label,
            s.student_full_name AS student_name
        FROM `tabGuardian` g
        INNER JOIN `tabUser` u ON u.name = g.user
        INNER JOIN `tabStudent Guardian` sg
            ON sg.guardian = g.name
            AND sg.parenttype = 'Student'
        INNER JOIN `tabStudent` s ON s.name = sg.parent
        WHERE
            g.user IS NOT NULL
            AND s.enabled = 1
            AND COALESCE(u.enabled, 1) = 1
            AND s.anchor_school IN %(schools)s
            AND (
                g.name LIKE %(query)s
                OR g.guardian_full_name LIKE %(query)s
                OR g.guardian_email LIKE %(query)s
                OR u.name LIKE %(query)s
                OR u.full_name LIKE %(query)s
                OR s.student_full_name LIKE %(query)s
            )
        ORDER BY label ASC
        LIMIT %(limit)s
        """,
        {
            "schools": tuple(school_scope),
            "query": f"%{query}%",
            "limit": limit,
        },
        as_dict=True,
    )
    return [
        {
            "value": row.get("user_id"),
            "label": row.get("label") or row.get("user_id"),
            "meta": row.get("student_name") or _("Guardian"),
            "kind": "guardian",
            "availability_mode": "school_meetings_only",
        }
        for row in rows
        if row.get("user_id")
    ]


def _resolve_attendee_contexts(attendees: list[dict], organizer_user: str) -> list[dict]:
    ordered_users: list[str] = []
    requested_kind: dict[str, str] = {}
    requested_label: dict[str, str] = {}

    for attendee in attendees:
        user_id = _safe_text(attendee.get("user"))
        if not user_id:
            continue
        if user_id not in ordered_users:
            ordered_users.append(user_id)
        kind = _safe_text(attendee.get("kind")).lower()
        if kind in {"employee", "student", "guardian"}:
            requested_kind[user_id] = kind
        if _safe_text(attendee.get("label")):
            requested_label[user_id] = _safe_text(attendee.get("label"))

    if organizer_user not in ordered_users:
        ordered_users.insert(0, organizer_user)

    employee_rows = frappe.get_all(
        "Employee",
        filters={"user_id": ["in", ordered_users], "employment_status": "Active"},
        fields=["name", "user_id", "employee_full_name", "school", "organization"],
        limit=max(len(ordered_users), 1),
    )
    employee_by_user = {row.user_id: row for row in employee_rows if row.user_id}

    student_rows = frappe.get_all(
        "Student",
        filters={"student_email": ["in", ordered_users], "enabled": 1},
        fields=["name", "student_email", "student_full_name", "student_preferred_name", "anchor_school"],
        limit=max(len(ordered_users), 1),
    )
    student_by_user = {row.student_email: row for row in student_rows if row.student_email}

    guardian_rows = frappe.get_all(
        "Guardian",
        filters={"user": ["in", ordered_users]},
        fields=["name", "user", "guardian_full_name"],
        limit=max(len(ordered_users), 1),
    )
    guardian_by_user = {row.user: row for row in guardian_rows if row.user}

    user_rows = frappe.get_all(
        "User",
        filters={"name": ["in", ordered_users]},
        fields=["name", "full_name"],
        limit=max(len(ordered_users), 1),
    )
    user_labels = {row.name: (row.full_name or row.name) for row in user_rows if row.name}

    student_groups_by_student: dict[str, set[str]] = defaultdict(set)
    student_names = [row.name for row in student_rows if row.name]
    if student_names:
        memberships = frappe.get_all(
            "Student Group Student",
            filters={"student": ["in", student_names], "active": 1},
            fields=["student", "parent"],
            limit=max(len(student_names) * 5, 20),
        )
        for row in memberships:
            if row.student and row.parent:
                student_groups_by_student[row.student].add(row.parent)

    guardian_school_map: dict[str, set[str]] = defaultdict(set)
    guardian_group_map: dict[str, set[str]] = defaultdict(set)
    guardian_names = [row.name for row in guardian_rows if row.name]
    if guardian_names:
        guardian_students = frappe.get_all(
            "Guardian Student",
            filters={"parent": ["in", guardian_names], "parenttype": "Guardian"},
            fields=["parent", "student"],
            limit=max(len(guardian_names) * 5, 20),
        )
        guardian_student_names = {row.student for row in guardian_students if row.student}
        if guardian_student_names:
            student_meta = frappe.get_all(
                "Student",
                filters={"name": ["in", list(guardian_student_names)], "enabled": 1},
                fields=["name", "anchor_school"],
                limit=max(len(guardian_student_names), 1),
            )
            student_school_map = {row.name: row.anchor_school for row in student_meta if row.name}

            guardian_memberships = frappe.get_all(
                "Student Group Student",
                filters={"student": ["in", list(guardian_student_names)], "active": 1},
                fields=["student", "parent"],
                limit=max(len(guardian_student_names) * 5, 20),
            )
            student_group_map: dict[str, set[str]] = defaultdict(set)
            for row in guardian_memberships:
                if row.student and row.parent:
                    student_group_map[row.student].add(row.parent)

            guardian_name_by_user = {row.user: row.name for row in guardian_rows if row.user and row.name}
            for row in guardian_students:
                guardian_name = row.parent
                student_name = row.student
                if not guardian_name or not student_name:
                    continue
                user_id = next(
                    (user for user, name in guardian_name_by_user.items() if name == guardian_name),
                    None,
                )
                if not user_id:
                    continue
                school = student_school_map.get(student_name)
                if school:
                    guardian_school_map[user_id].add(school)
                guardian_group_map[user_id].update(student_group_map.get(student_name) or set())

    contexts: list[dict] = []
    for user_id in ordered_users:
        employee_row = employee_by_user.get(user_id)
        student_row = student_by_user.get(user_id)
        guardian_row = guardian_by_user.get(user_id)
        requested = requested_kind.get(user_id)

        kind = requested or ""
        if not kind:
            if employee_row:
                kind = "employee"
            elif student_row:
                kind = "student"
            elif guardian_row:
                kind = "guardian"
            else:
                kind = "unknown"

        label = requested_label.get(user_id) or user_labels.get(user_id) or user_id
        if kind == "employee" and employee_row:
            label = employee_row.employee_full_name or label
        elif kind == "student" and student_row:
            label = student_row.student_preferred_name or student_row.student_full_name or label
        elif kind == "guardian" and guardian_row:
            label = guardian_row.guardian_full_name or label

        contexts.append(
            {
                "user": user_id,
                "kind": kind,
                "label": label,
                "employee": employee_row.name if employee_row else None,
                "student": student_row.name if student_row else None,
                "guardian": guardian_row.name if guardian_row else None,
                "school": (employee_row.school if employee_row else None)
                or (student_row.anchor_school if student_row else None),
                "student_groups": student_groups_by_student.get(student_row.name, set()) if student_row else set(),
                "guardian_schools": guardian_school_map.get(user_id, set()),
                "guardian_groups": guardian_group_map.get(user_id, set()),
                "availability_mode": (
                    "authoritative"
                    if kind == "employee"
                    else "school_schedule"
                    if kind == "student"
                    else "school_meetings_only"
                    if kind == "guardian"
                    else "unknown"
                ),
            }
        )

    return contexts


def search_meeting_attendees(
    *,
    query: str | None = None,
    attendee_kinds: object | None = None,
    limit: int | None = None,
):
    user = frappe.session.user
    _ensure_can_create_meeting(user)

    search_query = _safe_text(query)
    if len(search_query) < 2:
        return {"results": [], "notes": []}

    result_limit = _coerce_minutes(
        limit,
        default=MAX_ATTENDEE_SEARCH_RESULTS,
        minimum=1,
        maximum=MAX_ATTENDEE_SEARCH_RESULTS,
        label=_("Result limit"),
    )
    kinds = _normalize_attendee_kinds(attendee_kinds)
    scope = _get_quick_create_scope(user)

    cache_key = _json_cache_key(
        "ifitwala_ed:event_quick_create:attendee_search",
        {
            "user": user,
            "query": search_query.lower(),
            "kinds": kinds,
            "limit": result_limit,
            "employee_collaboration_organization_scope": scope.get("employee_collaboration_organization_scope")
            or scope.get("organization_scope")
            or [],
            "student_scope": scope.get("student_scope") or [],
        },
    )
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached:
        parsed = frappe.parse_json(cached)
        if isinstance(parsed, dict):
            return parsed

    results: list[dict] = []
    if "employee" in kinds:
        results.extend(
            _search_employee_attendees(
                user=user,
                organization_scope=scope.get("employee_collaboration_organization_scope")
                or scope.get("organization_scope")
                or ([scope.get("organization")] if scope.get("organization") else []),
                query=search_query,
                limit=result_limit,
            )
        )
    if "student" in kinds:
        results.extend(
            _search_student_attendees(
                school_scope=scope.get("student_scope") or [],
                query=search_query,
                limit=result_limit,
            )
        )
    if "guardian" in kinds:
        results.extend(
            _search_guardian_attendees(
                school_scope=scope.get("student_scope") or [],
                query=search_query,
                limit=result_limit,
            )
        )

    deduped: list[dict] = []
    seen = set()
    for row in sorted(results, key=lambda item: ((item.get("label") or "").lower(), item.get("kind") or "")):
        key = (row.get("value"), row.get("kind"))
        if not row.get("value") or key in seen:
            continue
        seen.add(key)
        deduped.append(row)
        if len(deduped) >= result_limit:
            break

    payload = {"results": deduped, "notes": []}
    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=ATTENDEE_SEARCH_CACHE_TTL_SECONDS)
    return payload


def get_meeting_team_attendees(*, team: str | None = None):
    user = frappe.session.user
    _ensure_can_create_meeting(user)

    team_value = _ensure_allowed_team(user, team)
    if not team_value:
        frappe.throw(_("Team is required."))

    from ifitwala_ed.setup.doctype.meeting.meeting import get_team_participants

    rows = get_team_participants(team_value) or []
    results = []
    seen = set()
    for row in rows:
        user_id = _safe_text(row.get("user_id"))
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        results.append(
            {
                "value": user_id,
                "label": _safe_text(row.get("full_name")) or _current_user_label(user_id),
                "meta": team_value,
                "kind": "employee",
                "availability_mode": "authoritative",
            }
        )

    return {"team": team_value, "results": results}
