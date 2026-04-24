from __future__ import annotations

from datetime import datetime
from typing import Any


def coerce_learning_datetime(api, value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = api.get_datetime(value)
        if isinstance(parsed, datetime):
            return parsed
        if isinstance(parsed, str):
            return datetime.fromisoformat(parsed.replace("Z", "+00:00"))
        return None
    except Exception:
        return None


def iter_learning_sessions(api, units: list[dict[str, Any]]):
    for unit in units or []:
        for session in unit.get("sessions") or []:
            yield unit, session


def flatten_assigned_work(
    api,
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append_item(item: dict[str, Any] | None) -> None:
        if not isinstance(item, dict):
            return
        key = api.planning.normalize_text(item.get("task_delivery"))
        if not key or key in seen:
            return
        seen.add(key)
        flattened.append(item)

    for item in general_assigned_work or []:
        append_item(item)

    for unit in units or []:
        for item in unit.get("assigned_work") or []:
            append_item(item)
        for session in unit.get("sessions") or []:
            for item in session.get("assigned_work") or []:
                append_item(item)

    return flattened


def resolve_student_learning_focus(
    api,
    units: list[dict[str, Any]],
    preferred_unit_plan: str | None = None,
    *,
    anchor_date: Any | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not units:
        return None, None

    resolved_unit_plan = api.planning.normalize_text(preferred_unit_plan)
    if resolved_unit_plan:
        selected_unit = next(
            (unit for unit in units if api.planning.normalize_text(unit.get("unit_plan")) == resolved_unit_plan),
            None,
        )
        if selected_unit:
            return selected_unit, resolve_student_learning_session(
                api,
                selected_unit,
                anchor_date=anchor_date,
            )

    resolved_anchor = api._coerce_curriculum_anchor_date(anchor_date)
    in_progress: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []
    upcoming: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []
    undated: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
    previous: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []

    for unit_index, (unit, session) in enumerate(api._iter_learning_sessions(units)):
        session_date = api._coerce_learning_datetime(session.get("session_date"))
        session_status = api.planning.normalize_text(session.get("session_status")).lower()
        if session_status == "in progress":
            in_progress.append((session_date or api.now_datetime(), unit, session))
            continue
        if session_date and session_date.date() >= resolved_anchor:
            upcoming.append((session_date, unit, session))
            continue
        if session_date:
            previous.append((session_date, unit, session))
            continue
        undated.append((unit_index, int(session.get("sequence_index") or 0), unit, session))

    if in_progress:
        _, unit, session = sorted(in_progress, key=lambda row: row[0])[0]
        return unit, session
    if upcoming:
        _, unit, session = sorted(upcoming, key=lambda row: row[0])[0]
        return unit, session
    if undated:
        _, _, unit, session = sorted(undated, key=lambda row: (row[0], row[1]))[0]
        return unit, session
    if previous:
        _, unit, session = sorted(previous, key=lambda row: row[0], reverse=True)[0]
        return unit, session
    return units[0], None


def resolve_student_learning_session(
    api,
    unit: dict[str, Any] | None,
    *,
    anchor_date: Any | None = None,
) -> dict[str, Any] | None:
    if not unit:
        return None

    resolved_anchor = api._coerce_curriculum_anchor_date(anchor_date)
    in_progress: list[tuple[datetime, tuple[int, str], dict[str, Any]]] = []
    exact: list[tuple[tuple[int, str], dict[str, Any]]] = []
    future: list[tuple[datetime, tuple[int, str], dict[str, Any]]] = []
    previous: list[tuple[datetime, tuple[int, str], dict[str, Any]]] = []
    undated: list[tuple[tuple[int, str], dict[str, Any]]] = []

    for session in unit.get("sessions") or []:
        status = api.planning.normalize_text(session.get("session_status")).lower()
        if status in {"changed", "canceled"}:
            continue

        sort_key = (
            int(session.get("sequence_index") or 0),
            api.planning.normalize_text(session.get("class_session")),
        )
        session_date = api._coerce_learning_datetime(session.get("session_date"))
        if status == "in progress":
            in_progress.append((session_date or api.now_datetime(), sort_key, session))
            continue
        if session_date and session_date.date() == resolved_anchor:
            exact.append((sort_key, session))
            continue
        if session_date and session_date.date() > resolved_anchor:
            future.append((session_date, sort_key, session))
            continue
        if session_date:
            previous.append((session_date, sort_key, session))
            continue
        undated.append((sort_key, session))

    if in_progress:
        _, _, session = sorted(in_progress, key=lambda row: (row[0], row[1]))[0]
        return session
    if exact:
        _, session = sorted(exact, key=lambda row: row[0])[0]
        return session
    if future:
        _, _, session = sorted(future, key=lambda row: (row[0], row[1]))[0]
        return session
    if undated:
        _, session = sorted(undated, key=lambda row: row[0])[0]
        return session
    if previous:
        _, _, session = sorted(previous, key=lambda row: (row[0], row[1]), reverse=True)[0]
        return session
    return None


def build_student_focus_statement(
    api,
    unit: dict[str, Any] | None,
    session: dict[str, Any] | None,
) -> str | None:
    if session and api.planning.normalize_long_text(session.get("learning_goal")):
        return api.planning.normalize_long_text(session.get("learning_goal"))
    if unit and api.planning.normalize_long_text(unit.get("essential_understanding")):
        return api.planning.normalize_long_text(unit.get("essential_understanding"))
    if unit and api.planning.normalize_long_text(unit.get("overview")):
        return api.planning.normalize_long_text(unit.get("overview"))
    if unit and api.planning.normalize_text(unit.get("title")):
        return api._("You are currently working through {unit_title}.").format(unit_title=unit.get("title"))
    return None


def build_student_learning_focus(
    api,
    units: list[dict[str, Any]],
    current_unit_plan: str | None = None,
    *,
    anchor_date: Any | None = None,
) -> dict[str, Any]:
    unit, session = api._resolve_student_learning_focus(
        units,
        current_unit_plan,
        anchor_date=anchor_date,
    )
    return {
        "current_unit": (
            {
                "unit_plan": unit.get("unit_plan"),
                "title": unit.get("title"),
            }
            if unit
            else None
        ),
        "current_session": (
            {
                "class_session": session.get("class_session"),
                "title": session.get("title"),
                "session_date": session.get("session_date"),
                "learning_goal": session.get("learning_goal"),
            }
            if session
            else None
        ),
        "statement": api._build_student_focus_statement(unit, session),
    }


def build_student_unit_navigation(
    api,
    units: list[dict[str, Any]],
    current_unit_plan: str | None,
) -> list[dict[str, Any]]:
    current_unit_plan = api.planning.normalize_text(current_unit_plan)
    return [
        {
            "unit_plan": unit.get("unit_plan"),
            "title": unit.get("title"),
            "unit_order": unit.get("unit_order"),
            "session_count": len(unit.get("sessions") or []),
            "assigned_work_count": len(unit.get("assigned_work") or []),
            "is_current": int(api.planning.normalize_text(unit.get("unit_plan")) == current_unit_plan),
        }
        for unit in units or []
    ]


def build_student_next_actions(
    api,
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    actions: list[tuple[int, datetime, dict[str, Any]]] = []
    fallback_date = datetime.max
    seen: set[tuple[str, str]] = set()

    for item in api._flatten_assigned_work(units, general_assigned_work):
        task_delivery = api.planning.normalize_text(item.get("task_delivery"))
        quiz_state = item.get("quiz_state") or {}
        due_at = api._coerce_learning_datetime(item.get("due_date")) or fallback_date
        title = api.planning.normalize_text(item.get("title")) or api._("Assigned work")
        action: dict[str, Any]
        priority = 3
        if (item.get("task_type") or "").strip() == "Quiz" and quiz_state.get("can_continue"):
            priority = 0
            action = {
                "kind": "quiz",
                "label": api._("Continue {title}").format(title=title),
                "supporting_text": quiz_state.get("status_label") or api._("Your attempt is in progress."),
                "task_delivery": task_delivery,
                "class_session": item.get("class_session"),
                "unit_plan": item.get("unit_plan"),
            }
        elif (item.get("task_type") or "").strip() == "Quiz" and quiz_state.get("can_retry"):
            priority = 1
            action = {
                "kind": "quiz",
                "label": api._("Retry {title}").format(title=title),
                "supporting_text": quiz_state.get("status_label") or api._("You can start another attempt."),
                "task_delivery": task_delivery,
                "class_session": item.get("class_session"),
                "unit_plan": item.get("unit_plan"),
            }
        elif (item.get("task_type") or "").strip() == "Quiz" and quiz_state.get("can_start"):
            priority = 1
            action = {
                "kind": "quiz",
                "label": api._("Start {title}").format(title=title),
                "supporting_text": api._("Ready when you are."),
                "task_delivery": task_delivery,
                "class_session": item.get("class_session"),
                "unit_plan": item.get("unit_plan"),
            }
        else:
            action = {
                "kind": "assigned_work",
                "label": api._("Complete {title}").format(title=title),
                "supporting_text": api._("Due {due_date}").format(due_date=item.get("due_date"))
                if item.get("due_date")
                else api._("Assigned for this course."),
                "task_delivery": task_delivery,
                "class_session": item.get("class_session"),
                "unit_plan": item.get("unit_plan"),
            }
            if due_at != fallback_date:
                priority = 2
        key = ("task", task_delivery)
        if task_delivery and key not in seen:
            seen.add(key)
            actions.append((priority, due_at, action))

    today = api.now_datetime().date()
    for unit, session in api._iter_learning_sessions(units):
        session_id = api.planning.normalize_text(session.get("class_session"))
        if not session_id:
            continue
        session_date = api._coerce_learning_datetime(session.get("session_date"))
        if session_date and session_date.date() < today:
            continue
        key = ("session", session_id)
        if key in seen:
            continue
        seen.add(key)
        actions.append(
            (
                4,
                session_date or fallback_date,
                {
                    "kind": "session",
                    "label": api._("Get ready for {title}").format(
                        title=api.planning.normalize_text(session.get("title")) or api._("your next class")
                    ),
                    "supporting_text": api._("Session on {session_date}").format(
                        session_date=session.get("session_date")
                    )
                    if session.get("session_date")
                    else (session.get("learning_goal") or api._("Your class will continue this unit soon.")),
                    "class_session": session_id,
                    "unit_plan": unit.get("unit_plan"),
                },
            )
        )

    actions.sort(key=lambda row: (row[0], row[1], row[2].get("label") or ""))
    return [row[2] for row in actions[:4]]


def resolve_student_selected_task(
    api,
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
    *,
    current_unit_plan: str | None = None,
    current_session_id: str | None = None,
) -> dict[str, Any] | None:
    normalized_unit_plan = api.planning.normalize_text(current_unit_plan)
    normalized_session_id = api.planning.normalize_text(current_session_id)

    def first_non_quiz(items: list[dict[str, Any]] | None) -> dict[str, Any] | None:
        for item in items or []:
            if api.planning.normalize_text(item.get("task_type")).lower() == "quiz":
                continue
            if api.planning.normalize_text(item.get("task_delivery")):
                return item
        return None

    if normalized_session_id:
        for _unit, session in api._iter_learning_sessions(units):
            if api.planning.normalize_text(session.get("class_session")) != normalized_session_id:
                continue
            selected = first_non_quiz(session.get("assigned_work"))
            if selected:
                return selected

    if normalized_unit_plan:
        for unit in units or []:
            if api.planning.normalize_text(unit.get("unit_plan")) != normalized_unit_plan:
                continue
            selected = first_non_quiz(unit.get("assigned_work"))
            if selected:
                return selected
            for session in unit.get("sessions") or []:
                selected = first_non_quiz(session.get("assigned_work"))
                if selected:
                    return selected

    return first_non_quiz(api._flatten_assigned_work(units, general_assigned_work))


def build_student_learning_sections(
    api,
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
    reflection_entries: list[dict[str, Any]] | None = None,
    current_unit_plan: str | None = None,
    *,
    anchor_date: Any | None = None,
) -> dict[str, Any]:
    focus = api._build_student_learning_focus(
        units,
        current_unit_plan,
        anchor_date=anchor_date,
    )
    current_unit_plan = api.planning.normalize_text((focus.get("current_unit") or {}).get("unit_plan"))
    current_session = focus.get("current_session") or {}
    selected_task = resolve_student_selected_task(
        api,
        units,
        general_assigned_work,
        current_unit_plan=current_unit_plan,
        current_session_id=api.planning.normalize_text(current_session.get("class_session")),
    )
    return {
        "focus": focus,
        "next_actions": api._build_student_next_actions(units, general_assigned_work),
        "reflection_entries": reflection_entries or [],
        "selected_context": {
            "unit_plan": current_unit_plan or None,
            "class_session": api.planning.normalize_text(current_session.get("class_session")) or None,
            "task_delivery": api.planning.normalize_text((selected_task or {}).get("task_delivery")) or None,
        },
        "unit_navigation": api._build_student_unit_navigation(units, current_unit_plan),
    }


def fetch_student_learning_reflections(
    api,
    student_name: str,
    *,
    course_id: str,
    student_group: str | None = None,
    academic_year: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {
        "student": student_name,
        "course": course_id,
    }
    if student_group:
        filters["student_group"] = student_group
    if academic_year:
        filters["academic_year"] = academic_year

    rows = api.frappe.get_all(
        "Student Reflection Entry",
        filters=filters,
        fields=[
            "name",
            "entry_date",
            "entry_type",
            "visibility",
            "moderation_state",
            "body",
            "course",
            "student_group",
            "class_session",
            "task_delivery",
            "task_submission",
        ],
        order_by="entry_date desc, modified desc",
        limit=max(int(limit or 0), 1),
    )

    payload: list[dict[str, Any]] = []
    for row in rows or []:
        payload.append(
            {
                "name": row.get("name"),
                "entry_date": api._serialize_scalar(row.get("entry_date")),
                "entry_type": row.get("entry_type"),
                "visibility": row.get("visibility"),
                "moderation_state": row.get("moderation_state"),
                "body": row.get("body"),
                "body_preview": api.strip_html(row.get("body") or "")[:280],
                "course": row.get("course"),
                "student_group": row.get("student_group"),
                "class_session": row.get("class_session"),
                "task_delivery": row.get("task_delivery"),
                "task_submission": row.get("task_submission"),
            }
        )
    return payload


def build_student_learning_space_payload(
    api,
    student_name: str,
    course_id: str,
    student_group: str | None = None,
) -> dict[str, Any]:
    course_id = api.planning.normalize_text(course_id)
    if not course_id:
        api.frappe.throw(api._("Course is required."), api.frappe.ValidationError)

    api._assert_student_course_access(student_name, course_id)
    group_options = api._resolve_student_group_options(student_name, course_id)

    selected_group, class_plan_row = api._resolve_student_plan(course_id, group_options, student_group)
    selected_group_option = next(
        (row for row in group_options if api.planning.normalize_text(row.get("student_group")) == selected_group),
        None,
    )
    if selected_group:
        api._assert_student_group_membership(student_name, selected_group)

    course = api.frappe.db.get_value(
        "Course",
        course_id,
        ["name", "course_name", "course_group", "description", "course_image"],
        as_dict=True,
    )
    if not course:
        api.frappe.throw(api._("Course not found."))

    message = None
    units_payload: list[dict[str, Any]] = []
    resolved_course_plan = None
    resources_payload = {"shared_resources": [], "class_resources": [], "general_assigned_work": []}
    assigned_work_count = 0
    reflection_entries: list[dict[str, Any]] = []
    course_communication_summary: dict[str, Any] = {
        "total_count": 0,
        "unread_count": 0,
        "high_priority_count": 0,
        "has_high_priority": 0,
        "latest_publish_at": None,
    }
    course_plan_row: dict[str, Any] | None = None
    current_unit_plan: str | None = None

    if class_plan_row:
        doc = api.frappe.get_doc("Class Teaching Plan", class_plan_row["name"])
        resolved_course_plan = doc.course_plan
        course_plan_row = api.planning.get_course_plan_row(doc.course_plan)
        unit_lookup = api._build_unit_lookup(doc.course_plan, audience="student")
        unit_rows = api._serialize_backbone_units(doc.name, unit_lookup, audience="student")
        sessions = api._fetch_class_sessions(doc.name, audience="student")
        assigned_work = api._fetch_assigned_work(doc.name, audience="student", student_name=student_name)
        sessions_by_unit: dict[str, list[dict[str, Any]]] = {}
        for session in sessions:
            sessions_by_unit.setdefault(session.get("unit_plan"), []).append(session)
        units_payload = [{**row, "sessions": sessions_by_unit.get(row.get("unit_plan"), [])} for row in unit_rows]
        resources_payload = api._attach_resources_and_work(
            units=units_payload,
            course_plan=doc.course_plan,
            class_teaching_plan=doc.name,
            assigned_work=assigned_work,
        )
        current_unit_plan = api._resolve_current_curriculum_unit(
            units_payload,
            course_plan_row=course_plan_row,
            student_group=selected_group or None,
            class_unit_rows=doc.get("units") or [],
            anchor_date=api.now_datetime(),
            require_staff_access=False,
        ).get("unit_plan")
        assigned_work_count = len(assigned_work)
    else:
        course_plans = api.frappe.get_all(
            "Course Plan",
            filters={"course": course_id, "plan_status": "Active"},
            fields=["name", "title"],
            order_by="modified desc, creation desc",
            limit=2,
        )
        if len(course_plans) == 1:
            resolved_course_plan = course_plans[0]["name"]
            course_plan_row = api.planning.get_course_plan_row(resolved_course_plan)
            unit_lookup = api._build_unit_lookup(resolved_course_plan, audience="student")
            units_payload = [
                {
                    "unit_plan": row.get("name"),
                    "title": row.get("title"),
                    "unit_order": row.get("unit_order"),
                    "program": row.get("program"),
                    "unit_code": row.get("unit_code"),
                    "unit_status": row.get("unit_status"),
                    "version": row.get("version"),
                    "duration": row.get("duration"),
                    "estimated_duration": row.get("estimated_duration"),
                    "overview": row.get("overview"),
                    "essential_understanding": row.get("essential_understanding"),
                    "content": row.get("content"),
                    "skills": row.get("skills"),
                    "concepts": row.get("concepts"),
                    "standards": row.get("standards", []),
                    "shared_resources": [],
                    "assigned_work": [],
                    "sessions": [],
                }
                for row in unit_lookup.values()
            ]
            resources_payload = api._attach_resources_and_work(
                units=units_payload,
                course_plan=resolved_course_plan,
            )
            current_unit_plan = api._resolve_current_curriculum_unit(
                units_payload,
                course_plan_row=course_plan_row,
                anchor_date=api.now_datetime(),
                allow_live_session=False,
            ).get("unit_plan")
            if group_options:
                message = api._(
                    "Your teacher has not published a class teaching plan yet. Showing the shared course plan."
                )
            else:
                message = api._(
                    "Your class is not available yet. Showing the shared course plan while your class is being assigned."
                )
        else:
            if group_options:
                message = api._(
                    "Your learning space is not available yet because the class teaching plan has not been published. Check with your teacher if this class should already be available."
                )
            else:
                message = api._(
                    "Your learning space is not available yet because your class is still being assigned and no shared course plan is published yet. Check with your teacher or academic office if this course should already be available."
                )

    reflections_academic_year = api.planning.normalize_text(
        (class_plan_row or {}).get("academic_year") or (selected_group_option or {}).get("academic_year")
    )
    reflection_entries = api._fetch_student_learning_reflections(
        student_name,
        course_id=course_id,
        student_group=selected_group or None,
        academic_year=reflections_academic_year or None,
    )
    try:
        from ifitwala_ed.api import student_communications as student_communications_api

        course_communication_summary = student_communications_api.get_student_course_communication_summary(
            student_name,
            course_id=course_id,
            student_group=selected_group,
        )
    except Exception:
        api.frappe.log_error(api.frappe.get_traceback(), "Student Learning Space Communication Load Failed")

    return {
        "meta": {
            "generated_at": api._serialize_scalar(api.now_datetime()),
            "course_id": course_id,
        },
        "course": {
            "course": course.get("name"),
            "course_name": course.get("course_name") or course.get("name"),
            "course_group": course.get("course_group"),
            "description": course.get("description"),
            "course_image": course.get("course_image"),
        },
        "access": {
            "student_group_options": group_options,
            "resolved_student_group": selected_group,
            "class_teaching_plan": class_plan_row.get("name") if class_plan_row else None,
            "course_plan": resolved_course_plan,
        },
        "teaching_plan": {
            "source": "class_teaching_plan"
            if class_plan_row
            else ("course_plan_fallback" if resolved_course_plan else "unavailable"),
            "class_teaching_plan": class_plan_row.get("name") if class_plan_row else None,
            "title": class_plan_row.get("title") if class_plan_row else None,
            "planning_status": class_plan_row.get("planning_status") if class_plan_row else None,
            "course_plan": resolved_course_plan,
        },
        "communications": {
            "course_updates_summary": course_communication_summary,
        },
        "message": message,
        "learning": api._build_student_learning_sections(
            units_payload,
            resources_payload.get("general_assigned_work") or [],
            reflection_entries,
            current_unit_plan,
            anchor_date=api.now_datetime(),
        ),
        "resources": resources_payload,
        "curriculum": {
            "units": units_payload,
            "counts": {
                "units": len(units_payload),
                "sessions": sum(len(unit.get("sessions") or []) for unit in units_payload),
                "assigned_work": assigned_work_count,
            },
        },
    }


def resolve_student_group_options(api, student_name: str, course_id: str) -> list[dict[str, Any]]:
    rows = api.frappe.db.sql(
        """
        SELECT
            sg.name AS student_group,
            sg.student_group_name,
            sg.student_group_abbreviation,
            sg.academic_year
        FROM `tabStudent Group Student` sgs
        INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
        WHERE sgs.student = %(student)s
          AND COALESCE(sgs.active, 1) = 1
          AND sg.status = 'Active'
          AND sg.group_based_on = 'Course'
          AND sg.course = %(course)s
        ORDER BY sg.student_group_name ASC, sg.name ASC
        """,
        {"student": student_name, "course": course_id},
        as_dict=True,
    )
    return [
        {
            "student_group": row.get("student_group"),
            "label": row.get("student_group_name") or row.get("student_group_abbreviation") or row.get("student_group"),
            "academic_year": row.get("academic_year"),
        }
        for row in rows or []
        if row.get("student_group")
    ]


def resolve_student_plan(
    api,
    course_id: str,
    student_groups: list[dict[str, Any]],
    requested_group: str | None,
):
    selected_group = api.planning.normalize_text(requested_group)
    valid_groups = {row["student_group"] for row in student_groups if row.get("student_group")}
    if selected_group and selected_group not in valid_groups:
        api.frappe.throw(api._("Selected class is not available for this course."), api.frappe.PermissionError)
    if not selected_group and len(student_groups) == 1:
        selected_group = student_groups[0]["student_group"]
    if not selected_group and student_groups:
        selected_group = student_groups[0]["student_group"]

    class_plan_row = None
    if selected_group:
        rows = api.frappe.get_all(
            "Class Teaching Plan",
            filters={"student_group": selected_group, "planning_status": "Active"},
            fields=["name", "title", "course_plan", "planning_status", "team_note", "academic_year"],
            order_by="modified desc, creation desc",
            limit=1,
        )
        class_plan_row = rows[0] if rows else None

    return selected_group or None, class_plan_row
