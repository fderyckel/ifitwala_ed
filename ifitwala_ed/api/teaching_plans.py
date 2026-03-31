from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.api.student_groups import TRIAGE_ROLES, _instructor_group_names
from ifitwala_ed.curriculum import planning


def _serialize_scalar(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _require_logged_in_user() -> str:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to continue."), frappe.AuthenticationError)
    return user


def _assert_staff_group_access(student_group: str) -> None:
    user = _require_logged_in_user()
    roles = set(frappe.get_roles(user))
    if roles & TRIAGE_ROLES:
        return
    if student_group not in _instructor_group_names(user):
        frappe.throw(_("You do not have access to this class."), frappe.PermissionError)


def _require_student_name() -> str:
    user = _require_logged_in_user()
    roles = set(frappe.get_roles(user))
    if "Student" not in roles:
        frappe.throw(_("Student access is required."), frappe.PermissionError)
    student_name = frappe.db.get_value("Student", {"student_email": user}, "name")
    if not student_name:
        frappe.throw(_("No student profile is linked to this login."), frappe.PermissionError)
    return student_name


def _assert_student_group_membership(student_name: str, student_group: str) -> None:
    allowed = frappe.db.exists(
        "Student Group Student",
        {
            "parent": student_group,
            "parenttype": "Student Group",
            "student": student_name,
            "active": 1,
        },
    )
    if not allowed:
        frappe.throw(_("You do not have access to this class."), frappe.PermissionError)


def _group_context(student_group: str) -> dict:
    group = planning.get_student_group_row(student_group)
    if not planning.normalize_text(group.get("course")):
        frappe.throw(_("This class is not linked to a course."), frappe.ValidationError)
    return group


def _serialize_course_plan(row: dict) -> dict[str, Any]:
    return {
        "course_plan": row.get("name"),
        "title": row.get("title") or row.get("name"),
        "academic_year": row.get("academic_year"),
        "cycle_label": row.get("cycle_label"),
        "plan_status": row.get("plan_status"),
    }


def _serialize_class_teaching_plan_row(row: dict) -> dict[str, Any]:
    return {
        "class_teaching_plan": row.get("name"),
        "title": row.get("title") or row.get("name"),
        "course_plan": row.get("course_plan"),
        "planning_status": row.get("planning_status"),
    }


def _fetch_class_sessions(class_teaching_plan: str, audience: str = "staff") -> list[dict[str, Any]]:
    filters: dict[str, Any] = {"class_teaching_plan": class_teaching_plan}
    if audience == "student":
        filters["session_status"] = ["not in", ["Draft", "Canceled"]]

    sessions = frappe.get_all(
        "Class Session",
        filters=filters,
        fields=[
            "name",
            "title",
            "unit_plan",
            "session_status",
            "session_date",
            "sequence_index",
            "learning_goal",
            "teacher_note",
        ],
        order_by="session_date asc, sequence_index asc, creation asc",
        limit=0,
    )
    if not sessions:
        return []

    session_names = [row["name"] for row in sessions if row.get("name")]
    activity_rows = frappe.db.sql(
        """
        SELECT
            parent,
            title,
            activity_type,
            estimated_minutes,
            sequence_index,
            student_direction,
            teacher_prompt,
            resource_note,
            idx
        FROM `tabClass Session Activity`
        WHERE parenttype = 'Class Session'
          AND parentfield = 'activities'
          AND parent IN %(parents)s
        ORDER BY parent ASC, COALESCE(sequence_index, 2147483647) ASC, idx ASC
        """,
        {"parents": tuple(session_names)},
        as_dict=True,
    )
    activities_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in activity_rows or []:
        activity_payload = {
            "title": row.get("title"),
            "activity_type": row.get("activity_type"),
            "estimated_minutes": row.get("estimated_minutes"),
            "sequence_index": row.get("sequence_index"),
            "student_direction": row.get("student_direction"),
            "resource_note": row.get("resource_note"),
        }
        if audience == "staff":
            activity_payload["teacher_prompt"] = row.get("teacher_prompt")
        activities_by_parent[row["parent"]].append(activity_payload)

    payload: list[dict[str, Any]] = []
    for session in sessions:
        session_payload = {
            "class_session": session.get("name"),
            "title": session.get("title") or session.get("name"),
            "unit_plan": session.get("unit_plan"),
            "session_status": session.get("session_status"),
            "session_date": _serialize_scalar(session.get("session_date")),
            "sequence_index": session.get("sequence_index"),
            "learning_goal": session.get("learning_goal"),
            "activities": activities_by_parent.get(session.get("name"), []),
        }
        if audience == "staff":
            session_payload["teacher_note"] = session.get("teacher_note")
        payload.append(session_payload)
    return payload


def _fetch_unit_lookup(course_plan: str) -> dict[str, dict[str, Any]]:
    return {row["name"]: row for row in planning.get_unit_plan_rows(course_plan) if row.get("name")}


def _serialize_backbone_units(class_teaching_plan: str, audience: str = "staff") -> list[dict[str, Any]]:
    rows = frappe.get_all(
        "Class Teaching Plan Unit",
        filters={
            "parent": class_teaching_plan,
            "parenttype": "Class Teaching Plan",
            "parentfield": "units",
        },
        fields=[
            "unit_plan",
            "unit_title",
            "unit_order",
            "governed_required",
            "pacing_status",
            "teacher_focus",
            "pacing_note",
        ],
        order_by="unit_order asc, idx asc",
        limit=0,
    )
    payload = []
    for row in rows:
        unit_payload = {
            "unit_plan": row.get("unit_plan"),
            "title": row.get("unit_title"),
            "unit_order": row.get("unit_order"),
        }
        if audience == "staff":
            unit_payload["governed_required"] = int(row.get("governed_required") or 0)
            unit_payload["pacing_status"] = row.get("pacing_status")
            unit_payload["teacher_focus"] = row.get("teacher_focus")
            unit_payload["pacing_note"] = row.get("pacing_note")
        payload.append(unit_payload)
    return payload


def _resolve_staff_plan(
    student_group: str, requested_plan: str | None
) -> tuple[dict, list[dict], list[dict], str | None]:
    group = _group_context(student_group)
    course_plans = frappe.get_all(
        "Course Plan",
        filters={"course": group["course"], "plan_status": ["!=", "Archived"]},
        fields=["name", "title", "academic_year", "cycle_label", "plan_status"],
        order_by="modified desc, creation desc",
        limit=50,
    )
    class_plans = frappe.get_all(
        "Class Teaching Plan",
        filters={"student_group": student_group},
        fields=["name", "title", "course_plan", "planning_status"],
        order_by="modified desc, creation desc",
        limit=50,
    )

    selected = planning.normalize_text(requested_plan)
    if selected and not any(row.get("name") == selected for row in class_plans):
        frappe.throw(_("Selected class teaching plan does not belong to this class."), frappe.PermissionError)
    if not selected and len(class_plans) == 1:
        selected = class_plans[0]["name"]
    return group, course_plans, class_plans, selected or None


def _build_staff_bundle(student_group: str, class_teaching_plan: str | None = None) -> dict[str, Any]:
    group, course_plans, class_plans, resolved_plan = _resolve_staff_plan(student_group, class_teaching_plan)

    payload: dict[str, Any] = {
        "meta": {
            "generated_at": _serialize_scalar(now_datetime()),
            "student_group": student_group,
        },
        "group": {
            "student_group": group.get("name"),
            "title": group.get("student_group_name") or group.get("student_group_abbreviation") or group.get("name"),
            "course": group.get("course"),
            "academic_year": group.get("academic_year"),
        },
        "course_plans": [_serialize_course_plan(row) for row in course_plans],
        "class_teaching_plans": [_serialize_class_teaching_plan_row(row) for row in class_plans],
        "resolved": {
            "class_teaching_plan": resolved_plan,
            "can_initialize": 1 if course_plans else 0,
            "requires_course_plan_selection": 1 if not resolved_plan and len(course_plans) != 1 else 0,
        },
    }

    if not resolved_plan:
        payload["teaching_plan"] = None
        payload["curriculum"] = {"units": [], "session_count": 0}
        return payload

    doc = frappe.get_doc("Class Teaching Plan", resolved_plan)
    unit_rows = _serialize_backbone_units(doc.name, audience="staff")
    sessions = _fetch_class_sessions(doc.name, audience="staff")
    sessions_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        sessions_by_unit[session.get("unit_plan")].append(session)

    payload["teaching_plan"] = {
        "class_teaching_plan": doc.name,
        "title": doc.title,
        "course_plan": doc.course_plan,
        "planning_status": doc.planning_status,
        "team_note": doc.team_note,
    }
    payload["resolved"]["course_plan"] = doc.course_plan
    payload["curriculum"] = {
        "units": [
            {
                **row,
                "sessions": sessions_by_unit.get(row.get("unit_plan"), []),
            }
            for row in unit_rows
        ],
        "session_count": len(sessions),
    }
    return payload


@frappe.whitelist()
def get_staff_class_planning_surface(student_group: str, class_teaching_plan: str | None = None) -> dict[str, Any]:
    _assert_staff_group_access(student_group)
    return _build_staff_bundle(student_group, class_teaching_plan=class_teaching_plan)


@frappe.whitelist()
def create_class_teaching_plan(student_group: str, course_plan: str) -> dict[str, Any]:
    _assert_staff_group_access(student_group)
    group = _group_context(student_group)
    course_plan_row = planning.get_course_plan_row(course_plan)
    if planning.normalize_text(course_plan_row.get("course")) != planning.normalize_text(group.get("course")):
        frappe.throw(_("The selected course plan does not belong to this class course."), frappe.ValidationError)

    doc = frappe.new_doc("Class Teaching Plan")
    doc.course_plan = course_plan
    doc.student_group = student_group
    doc.insert(ignore_permissions=True)
    return {
        "class_teaching_plan": doc.name,
        "student_group": student_group,
    }


@frappe.whitelist()
def save_class_teaching_plan(
    class_teaching_plan: str,
    planning_status: str | None = None,
    team_note: str | None = None,
) -> dict[str, Any]:
    doc = frappe.get_doc("Class Teaching Plan", planning.normalize_text(class_teaching_plan))
    _assert_staff_group_access(doc.student_group)

    if planning_status not in (None, ""):
        doc.planning_status = planning_status
    doc.team_note = planning.normalize_long_text(team_note)
    doc.save(ignore_permissions=True)
    return {
        "class_teaching_plan": doc.name,
        "planning_status": doc.planning_status,
    }


@frappe.whitelist()
def save_class_teaching_plan_unit(
    class_teaching_plan: str,
    unit_plan: str,
    pacing_status: str | None = None,
    teacher_focus: str | None = None,
    pacing_note: str | None = None,
) -> dict[str, Any]:
    plan_name = planning.normalize_text(class_teaching_plan)
    doc = frappe.get_doc("Class Teaching Plan", plan_name)
    _assert_staff_group_access(doc.student_group)

    matched = None
    for row in doc.get("units") or []:
        if planning.normalize_text(row.unit_plan) == planning.normalize_text(unit_plan):
            matched = row
            break
    if not matched:
        frappe.throw(_("Unit Plan is not part of this class teaching plan."), frappe.ValidationError)

    if pacing_status not in (None, ""):
        matched.pacing_status = pacing_status
    matched.teacher_focus = planning.normalize_long_text(teacher_focus)
    matched.pacing_note = planning.normalize_long_text(pacing_note)
    doc.save(ignore_permissions=True)
    return {
        "class_teaching_plan": doc.name,
        "unit_plan": matched.unit_plan,
        "pacing_status": matched.pacing_status,
    }


@frappe.whitelist()
def save_class_session(
    class_teaching_plan: str,
    unit_plan: str,
    title: str,
    session_status: str | None = None,
    session_date: str | None = None,
    sequence_index: int | None = None,
    learning_goal: str | None = None,
    teacher_note: str | None = None,
    activities_json: str | None = None,
    class_session: str | None = None,
) -> dict[str, Any]:
    plan_doc = frappe.get_doc("Class Teaching Plan", class_teaching_plan)
    _assert_staff_group_access(plan_doc.student_group)

    if class_session:
        doc = frappe.get_doc("Class Session", class_session)
        if planning.normalize_text(doc.class_teaching_plan) != planning.normalize_text(class_teaching_plan):
            frappe.throw(_("Class Session does not belong to this class teaching plan."), frappe.PermissionError)
    else:
        doc = frappe.new_doc("Class Session")
        doc.class_teaching_plan = class_teaching_plan

    doc.unit_plan = unit_plan
    doc.title = title
    if session_status not in (None, ""):
        doc.session_status = session_status
    doc.session_date = session_date or None
    doc.sequence_index = int(sequence_index) if sequence_index not in (None, "") else None
    doc.learning_goal = learning_goal
    doc.teacher_note = teacher_note

    parsed_activities = frappe.parse_json(activities_json) if activities_json else []
    planning.replace_session_activities(doc, parsed_activities)

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    return {
        "class_session": doc.name,
        "class_teaching_plan": class_teaching_plan,
        "session_status": doc.session_status,
    }


def _resolve_student_group_options(student_name: str, course_id: str) -> list[dict[str, Any]]:
    rows = frappe.db.sql(
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


def _resolve_student_plan(course_id: str, student_groups: list[dict[str, Any]], requested_group: str | None):
    selected_group = planning.normalize_text(requested_group)
    valid_groups = {row["student_group"] for row in student_groups if row.get("student_group")}
    if selected_group and selected_group not in valid_groups:
        frappe.throw(_("Selected class is not available for this course."), frappe.PermissionError)
    if not selected_group and len(student_groups) == 1:
        selected_group = student_groups[0]["student_group"]
    if not selected_group and student_groups:
        selected_group = student_groups[0]["student_group"]

    class_plan_row = None
    if selected_group:
        rows = frappe.get_all(
            "Class Teaching Plan",
            filters={"student_group": selected_group, "planning_status": "Active"},
            fields=["name", "title", "course_plan", "planning_status", "team_note"],
            order_by="modified desc, creation desc",
            limit=1,
        )
        class_plan_row = rows[0] if rows else None

    return selected_group, class_plan_row


@frappe.whitelist()
def get_student_learning_space(course_id: str, student_group: str | None = None) -> dict[str, Any]:
    student_name = _require_student_name()
    course_id = planning.normalize_text(course_id)
    if not course_id:
        frappe.throw(_("Course is required."), frappe.ValidationError)

    group_options = _resolve_student_group_options(student_name, course_id)
    if not group_options:
        frappe.throw(_("No class is available for this course yet."), frappe.PermissionError)

    selected_group, class_plan_row = _resolve_student_plan(course_id, group_options, student_group)
    if selected_group:
        _assert_student_group_membership(student_name, selected_group)

    course = frappe.db.get_value(
        "Course",
        course_id,
        ["name", "course_name", "course_group", "description", "course_image"],
        as_dict=True,
    )
    if not course:
        frappe.throw(_("Course not found."))

    message = None
    units_payload: list[dict[str, Any]] = []
    resolved_course_plan = None

    if class_plan_row:
        doc = frappe.get_doc("Class Teaching Plan", class_plan_row["name"])
        resolved_course_plan = doc.course_plan
        unit_rows = _serialize_backbone_units(doc.name, audience="student")
        sessions = _fetch_class_sessions(doc.name, audience="student")
        sessions_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for session in sessions:
            sessions_by_unit[session.get("unit_plan")].append(session)
        units_payload = [{**row, "sessions": sessions_by_unit.get(row.get("unit_plan"), [])} for row in unit_rows]
    else:
        course_plans = frappe.get_all(
            "Course Plan",
            filters={"course": course_id, "plan_status": "Active"},
            fields=["name", "title"],
            order_by="modified desc, creation desc",
            limit=2,
        )
        if len(course_plans) == 1:
            resolved_course_plan = course_plans[0]["name"]
            units_payload = [
                {
                    "unit_plan": row.get("name"),
                    "title": row.get("title"),
                    "unit_order": row.get("unit_order"),
                    "governed_required": 1,
                    "pacing_status": "Not Started",
                    "teacher_focus": None,
                    "pacing_note": None,
                    "sessions": [],
                }
                for row in planning.get_unit_plan_rows(resolved_course_plan)
            ]
            message = _("Your teacher has not published a class teaching plan yet. Showing the shared course plan.")
        else:
            message = _(
                "Your learning space is not available yet because the class teaching plan has not been published."
            )

    return {
        "meta": {
            "generated_at": _serialize_scalar(now_datetime()),
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
        "message": message,
        "curriculum": {
            "units": units_payload,
            "counts": {
                "units": len(units_payload),
                "sessions": sum(len(unit.get("sessions") or []) for unit in units_payload),
            },
        },
    }
