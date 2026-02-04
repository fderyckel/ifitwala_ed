import json
from typing import Any, Dict, List, Optional

import frappe
from frappe.utils import formatdate, getdate, nowdate


def _assert_instructor(student_group: str) -> None:
    if not student_group or not isinstance(student_group, str):
        frappe.throw("student_group is required")

    if not frappe.db.exists("Student Group", student_group):
        frappe.throw("Student Group not found")

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Login required")

    is_instructor = frappe.db.exists(
        "Student Group Instructor",
        {
            "parent": student_group,
            "parenttype": "Student Group",
            "user_id": user,
        },
    )

    if not is_instructor:
        frappe.throw("Not permitted to access this class")


def _demo_students(seed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if seed:
        return seed

    names = [
        "Amina Dar", "Leo Mendez", "Priya Shah", "Samir Khan", "Noah Park",
        "Maya Singh", "Iris Chan", "Luis Ortega", "Zara Ali", "Omar Haddad",
        "Nina Patel", "Ethan Cole", "Ava Brooks", "Milo Reyes", "Sana Noor",
        "Hugo Silva", "Riya Kapoor", "Jun Park", "Layla Haddad", "Aria Klein",
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


def _build_bundle(
    student_group: str,
    date: Optional[str] = None,
    block_number: Optional[int] = None,
) -> Dict[str, Any]:
    group = frappe.db.get_value(
        "Student Group",
        student_group,
        ["student_group_abbreviation", "student_group_name", "course", "academic_year"],
        as_dict=True,
    )

    roster = frappe.get_all(
        "Student Group Student",
        filters={
            "parent": student_group,
            "parenttype": "Student Group",
            "active": 1,
        },
        fields=["student", "student_name"],
        order_by="idx asc",
    )

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

    focus_students = [
        {"student": row["student"], "student_name": row["student_name"]}
        for row in students[:3]
    ]

    today_iso = date or nowdate()
    today_label = formatdate(getdate(today_iso), "EEE d MMM")

    title_parts = []
    if group:
        if group.get("student_group_abbreviation"):
            title_parts.append(group.get("student_group_abbreviation"))
        if group.get("course"):
            title_parts.append(group.get("course"))
    title = " - ".join([p for p in title_parts if p]) or student_group

    block_label = f"Block {block_number}" if block_number else None

    return {
        "header": {
            "student_group": student_group,
            "title": title,
            "academic_year": group.get("academic_year") if group else None,
            "course": group.get("course") if group else None,
        },
        "now": {
            "date_label": today_label,
            "rotation_day_label": "Rotation Day 3",
            "block_label": block_label,
            "time_range": "08:45-09:30",
            "location": "Room 204",
        },
        "session": {
            "lesson_instance": None,
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
        "notes_preview": [
            {
                "id": "note-1",
                "student_name": students[1]["student_name"],
                "preview": "Needs support on the lab write-up.",
                "created_at_label": "Today",
            },
            {
                "id": "note-2",
                "student_name": students[2]["student_name"],
                "preview": "Great use of vocabulary during discussion.",
                "created_at_label": "Today",
            },
            {
                "id": "note-3",
                "student_name": students[3]["student_name"],
                "preview": "Still working on organizing evidence.",
                "created_at_label": "Yesterday",
            },
        ],
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
def start_session(
    student_group: str,
    date: Optional[str] = None,
    block_number: Optional[int] = None,
) -> Dict[str, Any]:
    _assert_instructor(student_group)
    return {
        "lesson_instance": "LI-DEMO-0001",
        "status": "active",
        "started_at": nowdate(),
    }


@frappe.whitelist()
def end_session(lesson_instance: str) -> Dict[str, Any]:
    if not lesson_instance:
        frappe.throw("lesson_instance is required")
    if frappe.session.user == "Guest":
        frappe.throw("Login required")
    return {
        "lesson_instance": lesson_instance,
        "status": "ended",
        "ended_at": nowdate(),
    }


@frappe.whitelist()
def save_signals(lesson_instance: str, signals_json: str) -> Dict[str, Any]:
    if not lesson_instance:
        frappe.throw("lesson_instance is required")
    if frappe.session.user == "Guest":
        frappe.throw("Login required")

    try:
        signals = json.loads(signals_json or "[]")
    except json.JSONDecodeError:
        frappe.throw("signals_json must be valid JSON")

    if not isinstance(signals, list):
        frappe.throw("signals_json must be a JSON list")

    return {"lesson_instance": lesson_instance, "saved": len(signals)}


@frappe.whitelist()
def quick_evidence(payload_json: str) -> Dict[str, Any]:
    if frappe.session.user == "Guest":
        frappe.throw("Login required")

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
