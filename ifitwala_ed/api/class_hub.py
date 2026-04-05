import json
from collections import defaultdict
from typing import Any, Dict, List, Optional

import frappe
from frappe import _
from frappe.utils import formatdate, get_datetime, getdate, now_datetime, nowdate

from ifitwala_ed.api import teaching_plans as teaching_plans_api
from ifitwala_ed.api.calendar_core import _resolve_employee_for_user, _system_tzinfo, _to_system_datetime
from ifitwala_ed.api.student_groups import _instructor_group_names
from ifitwala_ed.api.student_log import _can_create_student_log_for_session_user
from ifitwala_ed.curriculum import planning


def _assert_instructor(student_group: str) -> None:
    if not student_group or not isinstance(student_group, str):
        frappe.throw("student_group is required")

    if not frappe.db.exists("Student Group", student_group):
        frappe.throw("Student Group not found")

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Login required"))

    if student_group not in _instructor_group_names(user):
        frappe.throw(_("Not permitted to access this class"))


def _get_student_log_permissions() -> Dict[str, bool]:
    return {"can_create_student_log": _can_create_student_log_for_session_user()}


def _get_student_group_row(student_group: str) -> Dict[str, Any]:
    return (
        frappe.db.get_value(
            "Student Group",
            student_group,
            ["student_group_abbreviation", "student_group_name", "course", "academic_year"],
            as_dict=True,
        )
        or {}
    )


def _get_active_roster(student_group: str) -> List[Dict[str, str]]:
    return frappe.get_all(
        "Student Group Student",
        filters={
            "parent": student_group,
            "parenttype": "Student Group",
            "active": 1,
        },
        fields=["student", "student_name"],
        order_by="idx asc",
    )


def _build_group_title(student_group: str, group: Dict[str, Any]) -> str:
    title_parts = []
    if group.get("student_group_abbreviation"):
        title_parts.append(group.get("student_group_abbreviation"))
    if group.get("course"):
        title_parts.append(group.get("course"))
    return " - ".join([part for part in title_parts if part]) or student_group


def _format_time_range(start_dt, end_dt) -> Optional[str]:
    if not start_dt:
        return None

    start_label = get_datetime(start_dt).strftime("%H:%M")
    if not end_dt:
        return start_label

    return f"{start_label}-{get_datetime(end_dt).strftime('%H:%M')}"


def _build_picker_context(
    student_group: str,
    *,
    date: Optional[str] = None,
    block_number: Optional[int] = None,
    location: Optional[str] = None,
    start_dt=None,
    end_dt=None,
) -> Dict[str, Any]:
    group = _get_student_group_row(student_group)
    roster = _get_active_roster(student_group)

    date_iso = date or nowdate()
    students = [
        {
            "student": row.get("student"),
            "student_name": row.get("student_name"),
        }
        for row in roster
        if row.get("student") and row.get("student_name")
    ]

    return {
        "student_group": student_group,
        "title": _build_group_title(student_group, group),
        "academic_year": group.get("academic_year") if group else None,
        "course": group.get("course") if group else None,
        "permissions": _get_student_log_permissions(),
        "now": {
            "date_iso": date_iso,
            "date_label": formatdate(getdate(date_iso), "EEE d MMM"),
            "block_number": block_number,
            "block_label": f"Block {block_number}" if block_number else None,
            "time_range": _format_time_range(start_dt, end_dt),
            "location": location or None,
        },
        "students": students,
    }


def _build_picker_summary(
    student_group: str,
    *,
    date: Optional[str] = None,
    block_number: Optional[int] = None,
    location: Optional[str] = None,
    start_dt=None,
    end_dt=None,
) -> Dict[str, Any]:
    group = _get_student_group_row(student_group)
    date_iso = date or nowdate()
    return {
        "student_group": student_group,
        "title": _build_group_title(student_group, group),
        "academic_year": group.get("academic_year") if group else None,
        "course": group.get("course") if group else None,
        "now": {
            "date_iso": date_iso,
            "date_label": formatdate(getdate(date_iso), "EEE d MMM"),
            "block_number": block_number,
            "block_label": f"Block {block_number}" if block_number else None,
            "time_range": _format_time_range(start_dt, end_dt),
            "location": location or None,
        },
    }


def _resolve_bundle_date(date: Optional[str]) -> str:
    try:
        return getdate(date or nowdate()).isoformat()
    except Exception:
        frappe.throw(_("Date must be a valid date."), exc=frappe.ValidationError)


def _build_now_payload(date_iso: str, block_number: Optional[int] = None) -> Dict[str, Any]:
    return {
        "date_iso": date_iso,
        "date_label": formatdate(getdate(date_iso), "EEE d MMM"),
        "rotation_day_label": None,
        "block_number": block_number,
        "block_label": f"Block {block_number}" if block_number else None,
        "time_range": None,
        "location": None,
    }


def _resolve_runtime_context(student_group: str) -> Dict[str, Any]:
    group, course_plans, class_plans, resolved_plan = teaching_plans_api._resolve_staff_plan(student_group, None)
    if not resolved_plan and class_plans:
        resolved_plan = planning.normalize_text(class_plans[0].get("name"))

    context: Dict[str, Any] = {
        "group": group,
        "course_plans": course_plans,
        "class_teaching_plans": class_plans,
        "teaching_plan": None,
        "units": [],
        "resources": {"shared_resources": [], "class_resources": [], "general_assigned_work": []},
    }
    if not resolved_plan:
        return context

    doc = frappe.get_doc("Class Teaching Plan", resolved_plan)
    unit_lookup = teaching_plans_api._build_unit_lookup(doc.course_plan, audience="staff")
    unit_rows = teaching_plans_api._serialize_backbone_units(doc.name, unit_lookup, audience="staff")
    sessions = teaching_plans_api._fetch_class_sessions(doc.name, audience="staff")
    assigned_work = teaching_plans_api._fetch_assigned_work(doc.name, audience="staff")

    sessions_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        unit_plan = planning.normalize_text(session.get("unit_plan"))
        if unit_plan:
            sessions_by_unit[unit_plan].append(session)

    units = [
        {
            **row,
            "sessions": sessions_by_unit.get(planning.normalize_text(row.get("unit_plan")), []),
        }
        for row in unit_rows
    ]
    resources = teaching_plans_api._attach_resources_and_work(
        units=units,
        course_plan=doc.course_plan,
        class_teaching_plan=doc.name,
        assigned_work=assigned_work,
    )

    context["teaching_plan"] = {
        "class_teaching_plan": doc.name,
        "title": doc.title,
        "course_plan": doc.course_plan,
        "planning_status": doc.planning_status,
    }
    context["units"] = units
    context["resources"] = resources
    return context


def _iter_runtime_sessions(units: list[dict[str, Any]]):
    for unit in units or []:
        for session in unit.get("sessions") or []:
            yield unit, session


def _session_priority(session_status: str | None) -> int:
    status = planning.normalize_text(session_status)
    return {
        "In Progress": 0,
        "Planned": 1,
        "Draft": 2,
        "Taught": 3,
        "Changed": 4,
        "Canceled": 5,
    }.get(status, 99)


def _select_runtime_session(
    units: list[dict[str, Any]], target_date: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for unit, session in _iter_runtime_sessions(units):
        session_status = planning.normalize_text(session.get("session_status"))
        if session_status in {"Changed", "Canceled"}:
            continue
        if planning.normalize_text(session.get("session_date")) != target_date:
            continue
        candidates.append((unit, session))

    if not candidates:
        return None, None

    candidates.sort(
        key=lambda row: (
            _session_priority(row[1].get("session_status")),
            int(row[1].get("sequence_index") or 0),
            planning.normalize_text(row[1].get("class_session")),
        )
    )
    return candidates[0]


def _unit_has_taught_session(unit: dict[str, Any]) -> bool:
    for session in unit.get("sessions") or []:
        if planning.normalize_text(session.get("session_status")) == "Taught":
            return True
    return False


def _select_runtime_unit(units: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not units:
        return None

    for unit in units:
        if planning.normalize_text(unit.get("pacing_status")) == "In Progress":
            return unit

    for unit in units:
        if not _unit_has_taught_session(unit):
            return unit

    ranked = sorted(
        units,
        key=lambda unit: (
            int(unit.get("unit_order") or 0) <= 0,
            int(unit.get("unit_order") or 0),
            planning.normalize_text(unit.get("unit_plan")),
        ),
    )
    return ranked[0] if ranked else None


def _collect_relevant_work(
    current_session: dict[str, Any] | None,
    current_unit: dict[str, Any] | None,
    general_assigned_work: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append_rows(rows: list[dict[str, Any]] | None) -> None:
        for row in rows or []:
            delivery = planning.normalize_text(row.get("task_delivery"))
            if not delivery or delivery in seen:
                continue
            seen.add(delivery)
            collected.append(row)

    append_rows((current_session or {}).get("assigned_work"))
    append_rows((current_unit or {}).get("assigned_work"))
    append_rows(general_assigned_work)
    return collected


def _build_task_status_label(item: dict[str, Any]) -> str:
    due_date = planning.normalize_text(item.get("due_date"))
    if due_date:
        try:
            return _("Due {date}").format(date=formatdate(getdate(due_date), "d MMM"))
        except Exception:
            return _("Due soon")

    available_from = planning.normalize_text(item.get("available_from"))
    if available_from:
        try:
            return _("Available {date}").format(date=formatdate(getdate(available_from), "d MMM"))
        except Exception:
            return _("Available")

    delivery_mode = planning.normalize_text(item.get("delivery_mode"))
    if delivery_mode:
        return delivery_mode

    return _("Assigned work")


def _build_task_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        task_delivery = planning.normalize_text(item.get("task_delivery"))
        task_name = planning.normalize_text(item.get("task"))
        title = planning.normalize_text(item.get("title")) or task_name or _("Assigned work")
        payload.append(
            {
                "id": task_delivery or task_name or f"task-{index}",
                "title": title,
                "status_label": _build_task_status_label(item),
                "pending_count": None,
                "overlay": "TaskReview",
                "payload": {
                    "task_delivery": task_delivery or None,
                    "task": task_name or None,
                    "title": title,
                },
            }
        )
    return payload


def _serialize_doc_activities(rows: list[Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row in rows or []:
        payload.append(
            {
                "title": getattr(row, "title", None),
                "activity_type": getattr(row, "activity_type", None),
                "estimated_minutes": getattr(row, "estimated_minutes", None),
                "sequence_index": getattr(row, "sequence_index", None),
                "student_direction": getattr(row, "student_direction", None),
                "teacher_prompt": getattr(row, "teacher_prompt", None),
                "resource_note": getattr(row, "resource_note", None),
            }
        )
    return payload


def _build_today_items(
    current_session: dict[str, Any] | None,
    task_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if current_session:
        items.append(
            {
                "id": "today-evidence",
                "label": _("Capture evidence for this session"),
                "overlay": "QuickEvidence",
                "payload": {},
            }
        )
        items.append(
            {
                "id": "today-cfu",
                "label": _("Run a quick check for understanding"),
                "overlay": "QuickCFU",
                "payload": {},
            }
        )

    for task in task_items[:2]:
        items.append(
            {
                "id": f"today-{task['id']}",
                "label": task["title"],
                "overlay": "TaskReview",
                "payload": task["payload"],
            }
        )
    return items


def _build_pulse_items(
    *,
    student_group: str,
    current_session: dict[str, Any] | None,
    current_unit: dict[str, Any] | None,
    task_items: list[dict[str, Any]],
    date_iso: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if current_session:
        resource_count = len(current_session.get("resources") or [])
        if resource_count:
            items.append(
                {
                    "id": "pulse-session-resources",
                    "label": _("{count} session resources ready").format(count=resource_count),
                    "route": {"name": "staff-class-planning", "params": {"studentGroup": student_group}},
                }
            )
        if task_items:
            items.append(
                {
                    "id": "pulse-session-work",
                    "label": _("{count} work items linked to this class").format(count=len(task_items)),
                    "route": {"name": "staff-class-planning", "params": {"studentGroup": student_group}},
                }
            )
        return items

    if current_unit:
        items.append(
            {
                "id": "pulse-plan-session",
                "label": _("No class session is planned for {date}.").format(
                    date=formatdate(getdate(date_iso), "d MMM")
                ),
                "route": {"name": "staff-class-planning", "params": {"studentGroup": student_group}},
            }
        )
    return items


def _session_runtime_status(session_status: str | None) -> str:
    status = planning.normalize_text(session_status)
    if status == "In Progress":
        return "active"
    if status in {"Draft", "Planned"}:
        return "planned"
    if status in {"Taught", "Changed", "Canceled"}:
        return "ended"
    return "none"


def _build_session_payload(
    teaching_plan: dict[str, Any] | None,
    current_unit: dict[str, Any] | None,
    current_session: dict[str, Any] | None,
) -> dict[str, Any]:
    if not current_session:
        return {
            "class_session": None,
            "class_teaching_plan": (teaching_plan or {}).get("class_teaching_plan"),
            "title": None,
            "session_status": None,
            "session_date": None,
            "unit_plan": (current_unit or {}).get("unit_plan"),
            "status": "none",
            "live_success_criteria": planning.normalize_text((current_unit or {}).get("teacher_focus"))
            or planning.normalize_text((current_unit or {}).get("essential_understanding")),
        }

    return {
        "class_session": current_session.get("class_session"),
        "class_teaching_plan": (teaching_plan or {}).get("class_teaching_plan"),
        "title": current_session.get("title"),
        "session_status": current_session.get("session_status"),
        "session_date": current_session.get("session_date"),
        "unit_plan": current_session.get("unit_plan"),
        "status": _session_runtime_status(current_session.get("session_status")),
        "live_success_criteria": planning.normalize_text(current_session.get("learning_goal"))
        or planning.normalize_text((current_unit or {}).get("teacher_focus"))
        or planning.normalize_text((current_unit or {}).get("essential_understanding")),
    }


def _build_bundle_message(
    *,
    teaching_plan: dict[str, Any] | None,
    units: list[dict[str, Any]],
    current_session: dict[str, Any] | None,
    date_iso: str,
) -> str | None:
    if not teaching_plan:
        return _(
            "This class does not have a class teaching plan yet. Open Class Planning to initialize the class-owned plan before teaching from the Hub."
        )
    if not units:
        return _(
            "This class teaching plan does not have any governed units yet. Open Class Planning to sync the class with the shared course plan before starting a session."
        )
    if not current_session:
        return _(
            "No class session is planned for {date} yet. Start Session to create one from the current unit."
        ).format(date=formatdate(getdate(date_iso), "d MMM"))
    return None


def _list_staff_home_groups(user: str) -> List[Dict[str, Any]]:
    group_names = sorted(_instructor_group_names(user))
    if not group_names:
        return []

    rows = frappe.get_all(
        "Student Group",
        filters={"name": ["in", group_names]},
        fields=[
            "name",
            "student_group_name",
            "student_group_abbreviation",
            "course",
            "academic_year",
        ],
        order_by="student_group_name asc, name asc",
    )

    return [
        {
            "student_group": row.get("name"),
            "student_group_name": row.get("student_group_name") or row.get("name"),
            "title": _build_group_title(row.get("name"), row),
            "course": row.get("course") or None,
            "academic_year": row.get("academic_year") or None,
        }
        for row in rows
        if row.get("name")
    ]


def _resolve_live_class_rows(employee_id: str) -> tuple[list[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not employee_id or not frappe.db.table_exists("Employee Booking"):
        return [], None

    tzinfo = _system_tzinfo()
    anchor_dt = _to_system_datetime(now_datetime(), tzinfo)

    current_rows = frappe.db.sql(
        """
        SELECT
            eb.name AS booking_name,
            eb.source_name AS student_group,
            eb.from_datetime,
            eb.to_datetime,
            eb.location
        FROM `tabEmployee Booking` eb
        WHERE eb.employee = %(employee)s
          AND eb.source_doctype = 'Student Group'
          AND eb.docstatus < 2
          AND eb.from_datetime <= %(anchor)s
          AND (eb.to_datetime IS NULL OR eb.to_datetime >= %(anchor)s)
        ORDER BY eb.from_datetime ASC, eb.name ASC
        """,
        {"employee": employee_id, "anchor": anchor_dt},
        as_dict=True,
    )

    next_rows = frappe.db.sql(
        """
        SELECT
            eb.name AS booking_name,
            eb.source_name AS student_group,
            eb.from_datetime,
            eb.to_datetime,
            eb.location
        FROM `tabEmployee Booking` eb
        WHERE eb.employee = %(employee)s
          AND eb.source_doctype = 'Student Group'
          AND eb.docstatus < 2
          AND eb.from_datetime > %(anchor)s
        ORDER BY eb.from_datetime ASC, eb.name ASC
        LIMIT 1
        """,
        {"employee": employee_id, "anchor": anchor_dt},
        as_dict=True,
    )

    return current_rows or [], (next_rows[0] if next_rows else None)


def _serialize_booking_row(row: Dict[str, Any]) -> Dict[str, Any]:
    tzinfo = _system_tzinfo()
    start_dt = _to_system_datetime(row.get("from_datetime"), tzinfo) if row.get("from_datetime") else None
    end_dt = _to_system_datetime(row.get("to_datetime"), tzinfo) if row.get("to_datetime") else None

    return {
        "student_group": row.get("student_group"),
        "date": start_dt.date().isoformat() if start_dt else nowdate(),
        "location": row.get("location") or None,
        "start_dt": start_dt,
        "end_dt": end_dt,
    }


def _build_bundle(
    student_group: str,
    date: Optional[str] = None,
    block_number: Optional[int] = None,
) -> Dict[str, Any]:
    date_iso = _resolve_bundle_date(date)
    runtime = _resolve_runtime_context(student_group)
    group = runtime.get("group") or _get_student_group_row(student_group)
    roster = _get_active_roster(student_group)
    students = [
        {
            "student": row.get("student"),
            "student_name": row.get("student_name"),
            "evidence_count_today": 0,
            "signal": None,
            "has_note_today": False,
        }
        for row in roster
        if row.get("student") and row.get("student_name")
    ]
    focus_students = [{"student": row["student"], "student_name": row["student_name"]} for row in students[:3]]
    current_unit, current_session = _select_runtime_session(runtime.get("units") or [], date_iso)
    if not current_unit:
        current_unit = _select_runtime_unit(runtime.get("units") or [])
    relevant_work = _collect_relevant_work(
        current_session,
        current_unit,
        (runtime.get("resources") or {}).get("general_assigned_work"),
    )
    task_items = _build_task_items(relevant_work)
    title = _build_group_title(student_group, group)

    return {
        "message": _build_bundle_message(
            teaching_plan=runtime.get("teaching_plan"),
            units=runtime.get("units") or [],
            current_session=current_session,
            date_iso=date_iso,
        ),
        "header": {
            "student_group": student_group,
            "title": title,
            "academic_year": group.get("academic_year") if group else None,
            "course": group.get("course") if group else None,
        },
        "permissions": _get_student_log_permissions(),
        "now": _build_now_payload(date_iso, block_number=block_number),
        "session": _build_session_payload(runtime.get("teaching_plan"), current_unit, current_session),
        "today_items": _build_today_items(current_session, task_items),
        "focus_students": focus_students,
        "students": students,
        "notes_preview": [],
        "task_items": task_items,
        "pulse_items": _build_pulse_items(
            student_group=student_group,
            current_session=current_session,
            current_unit=current_unit,
            task_items=task_items,
            date_iso=date_iso,
        ),
        "follow_up_items": [],
    }


@frappe.whitelist()
def get_bundle(
    student_group: str,
    date: Optional[str] = None,
    block_number: Optional[int] = None,
) -> Dict[str, Any]:
    _assert_instructor(student_group)
    return _build_bundle(student_group, date=date, block_number=block_number)


@frappe.whitelist()
def resolve_staff_home_entry() -> Dict[str, Any]:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Login required"))

    groups = _list_staff_home_groups(user)
    if len(groups) == 1:
        return {"status": "single", "message": None, "groups": groups}

    if groups:
        return {
            "status": "choose",
            "message": _("Choose the class hub you want to open."),
            "groups": groups,
        }

    return {
        "status": "empty",
        "message": _(
            "You are not assigned to any student groups yet. Ask an academic admin to add you as an instructor on a student group."
        ),
        "groups": [],
    }


@frappe.whitelist()
def resolve_current_picker_context() -> Dict[str, Any]:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Login required"))

    employee_row = _resolve_employee_for_user(user, fields=["name"], employment_status_filter=["!=", "Inactive"])
    employee_id = (employee_row or {}).get("name")
    if not employee_id:
        return {
            "status": "unavailable",
            "message": _("We could not resolve your live class right now."),
            "contexts": [],
            "next_class": None,
        }

    allowed_groups = _instructor_group_names(user)
    current_rows, next_row = _resolve_live_class_rows(employee_id)
    current_rows = [row for row in current_rows if row.get("student_group") in allowed_groups]
    next_row = next_row if next_row and next_row.get("student_group") in allowed_groups else None

    if len(current_rows) == 1:
        booking = _serialize_booking_row(current_rows[0])
        return {
            "status": "ready",
            "message": None,
            "contexts": [
                _build_picker_context(
                    booking["student_group"],
                    date=booking["date"],
                    location=booking["location"],
                    start_dt=booking["start_dt"],
                    end_dt=booking["end_dt"],
                )
            ],
            "next_class": None,
        }

    if len(current_rows) > 1:
        contexts = []
        for row in current_rows:
            booking = _serialize_booking_row(row)
            contexts.append(
                _build_picker_context(
                    booking["student_group"],
                    date=booking["date"],
                    location=booking["location"],
                    start_dt=booking["start_dt"],
                    end_dt=booking["end_dt"],
                )
            )
        return {
            "status": "multiple_current",
            "message": _("You have more than one class live right now. Choose the class you want to use."),
            "contexts": contexts,
            "next_class": None,
        }

    next_class = None
    if next_row:
        booking = _serialize_booking_row(next_row)
        next_class = _build_picker_summary(
            booking["student_group"],
            date=booking["date"],
            location=booking["location"],
            start_dt=booking["start_dt"],
            end_dt=booking["end_dt"],
        )

    return {
        "status": "no_current_class",
        "message": (
            _("You do not have a live class right now. Your next class is shown below.")
            if next_class
            else _("You do not have a live class right now.")
        ),
        "contexts": [],
        "next_class": next_class,
    }


@frappe.whitelist()
def start_session(
    student_group: str,
    date: Optional[str] = None,
    block_number: Optional[int] = None,
) -> Dict[str, Any]:
    _assert_instructor(student_group)
    date_iso = _resolve_bundle_date(date)
    runtime = _resolve_runtime_context(student_group)
    teaching_plan = runtime.get("teaching_plan")
    if not teaching_plan:
        frappe.throw(
            _(
                "This class needs a class teaching plan before you can start a session. Open Class Planning to initialize the class-owned plan first."
            ),
            exc=frappe.ValidationError,
        )

    units = runtime.get("units") or []
    current_unit, current_session = _select_runtime_session(units, date_iso)
    created = 0

    if current_session:
        if planning.normalize_text(current_session.get("session_status")) == "In Progress":
            return {
                "class_session": current_session.get("class_session"),
                "status": "active",
                "session_status": "In Progress",
                "created": created,
                "started_at": now_datetime().isoformat(sep=" "),
            }

        saved = teaching_plans_api.save_class_session(
            class_teaching_plan=teaching_plan["class_teaching_plan"],
            unit_plan=current_session.get("unit_plan"),
            title=current_session.get("title") or _("Class Session"),
            session_status="In Progress",
            session_date=current_session.get("session_date") or date_iso,
            sequence_index=current_session.get("sequence_index"),
            learning_goal=current_session.get("learning_goal"),
            teacher_note=current_session.get("teacher_note"),
            activities_json=json.dumps(current_session.get("activities") or []),
            class_session=current_session.get("class_session"),
        )
        return {
            "class_session": saved.get("class_session"),
            "status": "active",
            "session_status": saved.get("session_status") or "In Progress",
            "created": created,
            "started_at": now_datetime().isoformat(sep=" "),
        }

    current_unit = _select_runtime_unit(units)
    if not current_unit:
        frappe.throw(
            _(
                "This class teaching plan does not have any governed units yet. Open Class Planning to sync the class with the shared course plan before starting a session."
            ),
            exc=frappe.ValidationError,
        )

    saved = teaching_plans_api.save_class_session(
        class_teaching_plan=teaching_plan["class_teaching_plan"],
        unit_plan=current_unit.get("unit_plan"),
        title=planning.normalize_text(current_unit.get("title")) or _("Class Session"),
        session_status="In Progress",
        session_date=date_iso,
        sequence_index=None,
        learning_goal=planning.normalize_long_text(current_unit.get("teacher_focus"))
        or planning.normalize_long_text(current_unit.get("essential_understanding")),
        teacher_note=None,
        activities_json="[]",
        class_session=None,
    )
    created = 1
    return {
        "class_session": saved.get("class_session"),
        "status": "active",
        "session_status": saved.get("session_status") or "In Progress",
        "created": created,
        "started_at": now_datetime().isoformat(sep=" "),
    }


@frappe.whitelist()
def end_session(class_session: str) -> Dict[str, Any]:
    if not class_session:
        frappe.throw("class_session is required")
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))

    doc = frappe.get_doc("Class Session", class_session)
    _assert_instructor(doc.student_group)

    saved = teaching_plans_api.save_class_session(
        class_teaching_plan=doc.class_teaching_plan,
        unit_plan=doc.unit_plan,
        title=doc.title,
        session_status="Taught",
        session_date=doc.session_date,
        sequence_index=doc.sequence_index,
        learning_goal=doc.learning_goal,
        teacher_note=doc.teacher_note,
        activities_json=json.dumps(_serialize_doc_activities(doc.get("activities") or [])),
        class_session=doc.name,
    )
    return {
        "class_session": saved.get("class_session"),
        "status": "ended",
        "session_status": saved.get("session_status") or "Taught",
        "ended_at": now_datetime().isoformat(sep=" "),
    }


@frappe.whitelist()
def save_signals(class_session: str, signals_json: str) -> Dict[str, Any]:
    if not class_session:
        frappe.throw("class_session is required")
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))

    student_group = frappe.db.get_value("Class Session", class_session, "student_group")
    if not student_group:
        frappe.throw(_("Class Session not found."))
    _assert_instructor(student_group)

    try:
        signals = json.loads(signals_json or "[]")
    except json.JSONDecodeError:
        frappe.throw("signals_json must be valid JSON")

    if not isinstance(signals, list):
        frappe.throw("signals_json must be a JSON list")

    return {"class_session": class_session, "saved": len(signals)}


@frappe.whitelist()
def quick_evidence(payload_json: str) -> Dict[str, Any]:
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))

    try:
        payload = json.loads(payload_json or "{}")
    except json.JSONDecodeError:
        frappe.throw("payload_json must be valid JSON")

    if not isinstance(payload, dict):
        frappe.throw("payload_json must be a JSON object")

    student_group = planning.normalize_text(payload.get("student_group"))
    if not student_group:
        frappe.throw(_("student_group is required"))
    _assert_instructor(student_group)

    class_session = planning.normalize_text(payload.get("class_session"))
    if class_session:
        session_group = frappe.db.get_value("Class Session", class_session, "student_group")
        if planning.normalize_text(session_group) != student_group:
            frappe.throw(_("Class Session does not belong to this class."), frappe.PermissionError)

    students = payload.get("students") or []
    if not isinstance(students, list):
        frappe.throw("students must be a list")

    return {
        "created": len(students),
        "submission_origin": "Teacher Observation",
    }
