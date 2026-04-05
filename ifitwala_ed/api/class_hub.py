import json
from typing import Any, Dict, List, Optional

import frappe
from frappe import _
from frappe.utils import formatdate, get_datetime, getdate, now_datetime, nowdate

from ifitwala_ed.api.calendar_core import _resolve_employee_for_user, _system_tzinfo, _to_system_datetime
from ifitwala_ed.api.student_groups import _instructor_group_names
from ifitwala_ed.api.student_log import _can_create_student_log_for_session_user


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


def _demo_students(seed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if seed:
        return seed

    names = [
        "Amina Dar",
        "Leo Mendez",
        "Priya Shah",
        "Samir Khan",
        "Noah Park",
        "Maya Singh",
        "Iris Chan",
        "Luis Ortega",
        "Zara Ali",
        "Omar Haddad",
        "Nina Patel",
        "Ethan Cole",
        "Ava Brooks",
        "Milo Reyes",
        "Sana Noor",
        "Hugo Silva",
        "Riya Kapoor",
        "Jun Park",
        "Layla Haddad",
        "Aria Klein",
    ]

    demo: List[Dict[str, Any]] = []
    for idx, name in enumerate(names, start=1):
        demo.append(
            {
                "student": f"STU-DEMO-{idx:03d}",
                "student_name": name,
                "evidence_count_today": (idx * 3) % 5,
                "signal": [None, "Not Yet", "Almost", "Got It", "Exceeded"][idx % 5],
                "has_note_today": idx % 4 == 0,
            }
        )

    return demo


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
    group = _get_student_group_row(student_group)
    roster = _get_active_roster(student_group)

    students = _demo_students(
        [
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
    )

    focus_students = [{"student": row["student"], "student_name": row["student_name"]} for row in students[:3]]

    today_iso = date or nowdate()
    today_label = formatdate(getdate(today_iso), "EEE d MMM")
    title = _build_group_title(student_group, group)

    block_label = f"Block {block_number}" if block_number else None
    note_templates = [
        "Needs support on the lab write-up.",
        "Great use of vocabulary during discussion.",
        "Still working on organizing evidence.",
    ]
    note_labels = ["Today", "Today", "Yesterday"]
    notes_preview = []
    for idx, student in enumerate(students[1:4]):
        notes_preview.append(
            {
                "id": f"note-{idx + 1}",
                "student_name": student["student_name"],
                "preview": note_templates[idx],
                "created_at_label": note_labels[idx],
            }
        )

    return {
        "header": {
            "student_group": student_group,
            "title": title,
            "academic_year": group.get("academic_year") if group else None,
            "course": group.get("course") if group else None,
        },
        "permissions": _get_student_log_permissions(),
        "now": {
            "date_label": today_label,
            "rotation_day_label": "Rotation Day 3",
            "block_label": block_label,
            "time_range": "08:45-09:30",
            "location": "Room 204",
        },
        "session": {
            "class_session": None,
            "status": "none",
            "live_success_criteria": "Draft a hypothesis using clear evidence.",
        },
        "today_items": [
            {
                "id": "today-cfu",
                "label": "Quick CFU: Thumbs check",
                "overlay": "QuickCFU",
                "payload": {},
            },
            {
                "id": "today-evidence",
                "label": "Capture evidence for 3 students",
                "overlay": "QuickEvidence",
                "payload": {},
            },
            {
                "id": "today-student",
                "label": "Follow up with Amina Dar",
                "overlay": "StudentContext",
                "payload": {
                    "student": students[0]["student"],
                    "student_name": students[0]["student_name"],
                },
            },
        ],
        "focus_students": focus_students,
        "students": students,
        "notes_preview": notes_preview,
        "task_items": [
            {
                "id": "task-1",
                "title": "Exit ticket review",
                "status_label": "3 submissions pending",
                "pending_count": 3,
                "overlay": "TaskReview",
                "payload": {"title": "Exit ticket review"},
            },
            {
                "id": "task-2",
                "title": "Lab observation notes",
                "status_label": "Needs quick scan",
                "pending_count": 1,
                "overlay": "TaskReview",
                "payload": {"title": "Lab observation notes"},
            },
        ],
        "pulse_items": [
            {
                "id": "pulse-1",
                "label": "3 students marked Not Yet",
                "route": {"name": "staff-student-overview"},
            },
            {
                "id": "pulse-2",
                "label": "5 students missing evidence today",
                "route": {"name": "staff-student-overview"},
            },
        ],
        "follow_up_items": [
            {
                "id": "follow-1",
                "label": "Check in with Leo Mendez",
                "overlay": "StudentContext",
                "payload": {
                    "student": students[1]["student"],
                    "student_name": students[1]["student_name"],
                },
            }
        ],
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
    return {
        "class_session": "CLASS-SESSION-DEMO-0001",
        "status": "active",
        "started_at": nowdate(),
    }


@frappe.whitelist()
def end_session(class_session: str) -> Dict[str, Any]:
    if not class_session:
        frappe.throw("class_session is required")
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))
    return {
        "class_session": class_session,
        "status": "ended",
        "ended_at": nowdate(),
    }


@frappe.whitelist()
def save_signals(class_session: str, signals_json: str) -> Dict[str, Any]:
    if not class_session:
        frappe.throw("class_session is required")
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))

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

    students = payload.get("students") or []
    if not isinstance(students, list):
        frappe.throw("students must be a list")

    return {
        "created": len(students),
        "submission_origin": "Teacher Observation",
    }
