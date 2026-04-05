from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from time import perf_counter
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from ifitwala_ed.api.file_access import resolve_academic_file_open_url
from ifitwala_ed.api.student_groups import TRIAGE_ROLES, _instructor_group_names
from ifitwala_ed.assessment import quiz_service
from ifitwala_ed.curriculum import materials as materials_domain
from ifitwala_ed.curriculum import planning
from ifitwala_ed.utilities import governed_uploads

PLANNING_RESOURCE_ANCHORS = {
    "Course Plan",
    "Unit Plan",
    "Class Teaching Plan",
    "Class Session",
}
GOVERNED_PLANNING_RESOURCE_ANCHORS = {"Course Plan", "Unit Plan"}
STUDENT_LEARNING_SPACE_WARN_ELAPSED_MS = 1200
STUDENT_LEARNING_SPACE_WARN_PAYLOAD_BYTES = 350_000


def _serialize_scalar(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _normalize_payload(value) -> dict[str, Any]:
    if isinstance(value, str):
        value = frappe.parse_json(value)
    if not isinstance(value, dict):
        frappe.throw(_("Payload must be a dict."))
    return value


def _normalize_rows_payload(value, *, label: str) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    rows = frappe.parse_json(value) if isinstance(value, str) else value
    if not isinstance(rows, list):
        frappe.throw(_("{label} must be a list.").format(label=label))
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            frappe.throw(_("{label} rows must be objects.").format(label=label))
        normalized.append(row)
    return normalized


def _require_logged_in_user() -> str:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to continue."), frappe.AuthenticationError)
    return user


def _resolve_planning_resource_anchor(anchor_doctype: str, anchor_name: str, *, ptype: str = "write") -> dict[str, Any]:
    anchor_doctype = planning.normalize_text(anchor_doctype)
    anchor_name = planning.normalize_text(anchor_name)
    if anchor_doctype not in PLANNING_RESOURCE_ANCHORS:
        frappe.throw(
            _("Planning resources must be attached to a course plan, unit plan, class plan, or class session.")
        )
    context = materials_domain.resolve_anchor_context(anchor_doctype, anchor_name)
    if anchor_doctype in GOVERNED_PLANNING_RESOURCE_ANCHORS:
        course = planning.normalize_text(context.get("course"))
        if not course:
            frappe.throw(_("This shared curriculum resource is missing its course."))
        user, roles = _assert_course_curriculum_access(
            course,
            ptype=ptype,
            action_label=_("this shared curriculum resource"),
        )
        context["can_manage_resources"] = int(planning.user_can_manage_course_curriculum(user, course, roles))
        return context

    student_group = planning.normalize_text(context.get("student_group"))
    if not student_group:
        frappe.throw(_("This resource context is missing its class."))
    _assert_staff_group_access(student_group)
    context["can_manage_resources"] = 1
    return context


def _assert_staff_group_access(student_group: str) -> None:
    user = _require_logged_in_user()
    roles = set(frappe.get_roles(user))
    if roles & TRIAGE_ROLES:
        return
    if student_group not in _instructor_group_names(user):
        frappe.throw(_("You do not have access to this class."), frappe.PermissionError)


def _assert_course_curriculum_access(
    course: str,
    *,
    ptype: str = "write",
    action_label: str | None = None,
) -> tuple[str, set[str]]:
    user = _require_logged_in_user()
    roles = set(frappe.get_roles(user))
    course_name = planning.normalize_text(course)
    if not course_name:
        frappe.throw(_("Course is required for this curriculum action."))

    if ptype == "write":
        planning.assert_can_manage_course_curriculum(user, course_name, roles, action_label=action_label)
    else:
        planning.assert_can_read_course_curriculum(user, course_name, roles, action_label=action_label)
    return user, roles


def _require_student_name() -> str:
    user = _require_logged_in_user()
    roles = set(frappe.get_roles(user))
    if "Student" not in roles:
        frappe.throw(_("Student access is required."), frappe.PermissionError)
    student_name = frappe.db.get_value("Student", {"student_email": user}, "name")
    if not student_name:
        frappe.throw(_("No student profile is linked to this login."), frappe.PermissionError)
    return student_name


def _assert_student_course_access(student_name: str, course_id: str) -> None:
    from ifitwala_ed.api import courses as courses_api

    scope = courses_api._build_student_course_scope(student_name)
    if course_id not in scope:
        frappe.throw(_("You do not have access to this course."), frappe.PermissionError)


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


def _serialize_course_plan_summary(
    row: dict, *, course_row: dict | None = None, can_manage_resources: int = 0
) -> dict[str, Any]:
    return {
        "course_plan": row.get("name"),
        "record_modified": _serialize_scalar(row.get("modified")),
        "title": row.get("title") or row.get("name"),
        "course": row.get("course"),
        "course_name": (course_row or {}).get("course_name") or row.get("course"),
        "course_group": (course_row or {}).get("course_group"),
        "school": row.get("school"),
        "academic_year": row.get("academic_year"),
        "cycle_label": row.get("cycle_label"),
        "plan_status": row.get("plan_status"),
        "summary": row.get("summary"),
        "can_manage_resources": can_manage_resources,
    }


def _serialize_class_teaching_plan_row(row: dict) -> dict[str, Any]:
    return {
        "class_teaching_plan": row.get("name"),
        "title": row.get("title") or row.get("name"),
        "course_plan": row.get("course_plan"),
        "planning_status": row.get("planning_status"),
    }


def _serialize_course_option(
    row: dict[str, Any], *, academic_year_options: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "course": row.get("name"),
        "course_name": row.get("course_name") or row.get("name"),
        "course_group": row.get("course_group"),
        "school": row.get("school"),
        "status": row.get("status"),
        "academic_year_options": academic_year_options or [],
    }


def _serialize_academic_year_option(row: dict[str, Any]) -> dict[str, Any]:
    name = planning.normalize_text(row.get("name"))
    return {
        "value": name,
        "label": name,
        "school": planning.normalize_text(row.get("school")) or None,
        "year_start_date": _serialize_scalar(row.get("year_start_date")),
        "year_end_date": _serialize_scalar(row.get("year_end_date")),
    }


def _serialize_program_option(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "value": row.get("name"),
        "label": row.get("program_name") or row.get("name"),
        "parent_program": row.get("parent_program"),
        "is_group": int(row.get("is_group") or 0),
        "archived": int(row.get("archive") or 0),
    }


def _academic_year_scope_for_school(school: str | None) -> list[str]:
    from ifitwala_ed.utilities.school_tree import get_school_scope_for_academic_year

    school_name = planning.normalize_text(school)
    if not school_name:
        return []

    scope = [
        planning.normalize_text(scope_school)
        for scope_school in (get_school_scope_for_academic_year(school_name) or [])
        if planning.normalize_text(scope_school)
    ]
    return scope or [school_name]


def _fetch_academic_year_options_for_schools(
    schools: list[str] | tuple[str, ...],
    *,
    pinned_years: dict[str, str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    normalized_schools = [
        school_name for school_name in {planning.normalize_text(school) for school in (schools or [])} if school_name
    ]
    if not normalized_schools:
        return {}

    scope_by_school = {school_name: _academic_year_scope_for_school(school_name) for school_name in normalized_schools}
    query_schools = sorted(
        {
            scope_school
            for scope in scope_by_school.values()
            for scope_school in scope
            if planning.normalize_text(scope_school)
        }
    )
    pinned_year_names = sorted(
        {
            planning.normalize_text(academic_year)
            for academic_year in (pinned_years or {}).values()
            if planning.normalize_text(academic_year)
        }
    )

    rows = frappe.get_all(
        "Academic Year",
        filters={"school": ["in", query_schools]} if query_schools else {"name": ["in", [""]]},
        fields=["name", "school", "year_start_date", "year_end_date"],
        order_by="year_start_date desc, name desc",
        limit=0,
    )
    if pinned_year_names:
        pinned_rows = frappe.get_all(
            "Academic Year",
            filters={"name": ["in", pinned_year_names]},
            fields=["name", "school", "year_start_date", "year_end_date"],
            order_by="year_start_date desc, name desc",
            limit=0,
        )
        rows_by_name = {planning.normalize_text(row.get("name")): row for row in rows or []}
        for row in pinned_rows or []:
            name = planning.normalize_text(row.get("name"))
            if name and name not in rows_by_name:
                rows.append(row)
                rows_by_name[name] = row

    rows_by_school: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows_by_name: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        school_name = planning.normalize_text(row.get("school"))
        record_name = planning.normalize_text(row.get("name"))
        if not record_name:
            continue
        if school_name:
            rows_by_school[school_name].append(row)
        rows_by_name[record_name] = row

    options_by_school: dict[str, list[dict[str, Any]]] = {}
    for school_name, scope in scope_by_school.items():
        seen: set[str] = set()
        options: list[dict[str, Any]] = []
        for scope_school in scope:
            for row in rows_by_school.get(scope_school, []):
                record_name = planning.normalize_text(row.get("name"))
                if not record_name or record_name in seen:
                    continue
                options.append(_serialize_academic_year_option(row))
                seen.add(record_name)

        pinned_name = planning.normalize_text((pinned_years or {}).get(school_name))
        pinned_row = rows_by_name.get(pinned_name)
        if pinned_name and pinned_row and pinned_name not in seen:
            options.append(_serialize_academic_year_option(pinned_row))

        options_by_school[school_name] = options

    return options_by_school


def _fetch_program_options_for_course(
    course: str | None,
    *,
    pinned_programs: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    course_name = planning.normalize_text(course)
    pinned_names = {
        planning.normalize_text(program_name)
        for program_name in (pinned_programs or [])
        if planning.normalize_text(program_name)
    }
    linked_program_names = (
        frappe.get_all(
            "Program Course",
            filters={"course": course_name},
            pluck="parent",
            distinct=True,
            limit=0,
        )
        if course_name
        else []
    )
    program_names = {
        planning.normalize_text(program_name)
        for program_name in linked_program_names
        if planning.normalize_text(program_name)
    }
    program_names.update(pinned_names)
    if not program_names:
        return []

    rows = frappe.get_all(
        "Program",
        filters={"name": ["in", sorted(program_names)]},
        fields=["name", "program_name", "parent_program", "is_group", "archive", "lft"],
        order_by="lft asc, name asc",
        limit=0,
    )
    payload: list[dict[str, Any]] = []
    for row in rows or []:
        name = planning.normalize_text(row.get("name"))
        if int(row.get("archive") or 0) and name not in pinned_names:
            continue
        payload.append(_serialize_program_option(row))
    return payload


def _validate_course_plan_academic_year(
    *,
    course_school: str | None,
    academic_year: str | None,
    previous_academic_year: str | None = None,
) -> None:
    academic_year_name = planning.normalize_text(academic_year)
    if not academic_year_name:
        return
    if academic_year_name == planning.normalize_text(previous_academic_year):
        return

    row = frappe.db.get_value("Academic Year", academic_year_name, ["name", "school"], as_dict=True)
    if not row:
        frappe.throw(
            _("Academic Year {academic_year} was not found.").format(academic_year=academic_year_name),
            frappe.ValidationError,
        )

    school_name = planning.normalize_text(course_school)
    if not school_name:
        return

    allowed_scope = set(_academic_year_scope_for_school(school_name))
    academic_year_school = planning.normalize_text(row.get("school"))
    if allowed_scope and academic_year_school not in allowed_scope:
        frappe.throw(
            _(
                "Academic Year {academic_year} is not available for school {school}. Choose an academic year from this course's school scope."
            ).format(academic_year=academic_year_name, school=school_name),
            frappe.ValidationError,
        )


def _validate_course_program_link(
    *,
    course: str | None,
    program: str | None,
    previous_program: str | None = None,
) -> None:
    program_name = planning.normalize_text(program)
    if not program_name:
        return
    if program_name == planning.normalize_text(previous_program):
        return

    if not frappe.db.exists("Program", program_name):
        frappe.throw(
            _("Program {program} was not found.").format(program=program_name),
            frappe.ValidationError,
        )

    course_name = planning.normalize_text(course)
    if course_name and not frappe.db.exists(
        "Program Course",
        {
            "parent": program_name,
            "parenttype": "Program",
            "parentfield": "courses",
            "course": course_name,
        },
    ):
        frappe.throw(
            _(
                "Program {program} is not linked to course {course}. Choose a program that already includes this course."
            ).format(
                program=program_name,
                course=course_name,
            ),
            frappe.ValidationError,
        )


def _quiz_question_bank_record_modified(bank_row: dict | None, question_rows: list[dict[str, Any]] | None) -> str:
    digest = hashlib.sha256()
    digest.update(planning.normalize_record_modified((bank_row or {}).get("modified")).encode("utf-8"))
    for row in sorted(
        question_rows or [],
        key=lambda item: (
            planning.normalize_text(item.get("name")),
            planning.normalize_record_modified(item.get("modified")),
        ),
    ):
        digest.update(b"|")
        digest.update(planning.normalize_text(row.get("name")).encode("utf-8"))
        digest.update(b":")
        digest.update(planning.normalize_record_modified(row.get("modified")).encode("utf-8"))
    return digest.hexdigest()


def _payload_size_bytes(payload: dict[str, Any] | None) -> int | None:
    if payload in (None, ""):
        return 0
    try:
        return len(
            json.dumps(
                payload,
                default=str,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    except Exception:
        return None


def _current_db_query_count() -> int | None:
    db = getattr(frappe, "db", None)
    for attr_name in ("query_count", "_query_count", "sql_count"):
        value = getattr(db, attr_name, None)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
    return None


def _db_query_delta(started_count: int | None) -> int | None:
    current_count = _current_db_query_count()
    if started_count is None or current_count is None:
        return None
    return max(current_count - started_count, 0)


def _log_planning_event(
    event: str,
    *,
    started_at: float | None = None,
    warning: bool = False,
    **context,
) -> None:
    logger_factory = getattr(frappe, "logger", None)
    if not callable(logger_factory):
        return

    payload = {
        "event": planning.normalize_text(event) or "course_plan_event",
    }
    if started_at is not None:
        payload["elapsed_ms"] = round((perf_counter() - started_at) * 1000, 2)
    for key, value in context.items():
        if value in (None, ""):
            continue
        payload[key] = value

    try:
        logger = logger_factory("ifitwala.curriculum")
        log_method = logger.warning if warning else logger.info
        log_method(payload)
    except Exception:
        return


def _list_creatable_course_rows(user: str, roles: set[str]) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {"status": ["!=", "Discontinued"]}
    if not planning.user_has_global_curriculum_access(user, roles):
        course_names = planning.get_curriculum_manageable_course_names(user, roles)
        if not course_names:
            return []
        filters["name"] = ["in", course_names]

    return frappe.get_all(
        "Course",
        filters=filters,
        fields=["name", "course_name", "course_group", "school", "status"],
        order_by="course_name asc, name asc",
        limit=0,
    )


def _build_course_plan_creation_access(user: str, roles: set[str]) -> dict[str, Any]:
    course_rows = _list_creatable_course_rows(user, roles)
    can_create = int(bool(course_rows))
    academic_year_options_by_school = _fetch_academic_year_options_for_schools(
        [
            planning.normalize_text(row.get("school"))
            for row in course_rows
            if planning.normalize_text(row.get("school"))
        ]
    )

    if not course_rows:
        reason = _(
            "You need an active teaching assignment or curriculum leadership access before you can start a shared course plan."
        )
    else:
        reason = None

    return {
        "can_create_course_plans": can_create,
        "create_block_reason": reason,
        "course_options": [
            _serialize_course_option(
                row,
                academic_year_options=academic_year_options_by_school.get(
                    planning.normalize_text(row.get("school")),
                    [],
                ),
            )
            for row in course_rows
        ],
    }


def _serialize_material_entry(entry: dict[str, Any]) -> dict[str, Any]:
    placement = (entry.get("placements") or [{}])[0]
    material_type = entry.get("material_type")
    if material_type == materials_domain.MATERIAL_TYPE_FILE:
        open_url = resolve_academic_file_open_url(
            file_name=entry.get("file"),
            file_url=entry.get("file_url"),
            context_doctype="Material Placement" if placement.get("placement") else "Supporting Material",
            context_name=placement.get("placement") or entry.get("material"),
        )
    else:
        open_url = entry.get("reference_url")

    return {
        "material": entry.get("material"),
        "title": entry.get("title"),
        "material_type": material_type,
        "modality": entry.get("modality"),
        "description": entry.get("description"),
        "reference_url": entry.get("reference_url"),
        "open_url": open_url,
        "file_name": entry.get("file_name"),
        "file_size": entry.get("file_size"),
        "placement": placement.get("placement"),
        "origin": placement.get("origin"),
        "usage_role": placement.get("usage_role"),
        "placement_note": placement.get("placement_note"),
        "placement_order": placement.get("placement_order"),
    }


def _fetch_course_quiz_question_banks(course: str | None) -> list[dict[str, Any]]:
    course_name = planning.normalize_text(course)
    if not course_name:
        return []

    rows = frappe.get_all(
        "Quiz Question Bank",
        filters={"course": course_name},
        fields=["name", "bank_title", "course", "is_published"],
        order_by="bank_title asc, creation asc",
        limit=0,
    )
    if not rows:
        return []

    counts = {
        row.get("question_bank"): row
        for row in frappe.db.sql(
            """
            SELECT
                question_bank,
                COUNT(name) AS question_count,
                SUM(CASE WHEN COALESCE(is_published, 0) = 1 THEN 1 ELSE 0 END) AS published_question_count
            FROM `tabQuiz Question`
            WHERE question_bank IN %(question_banks)s
            GROUP BY question_bank
            """,
            {"question_banks": tuple(row["name"] for row in rows)},
            as_dict=True,
        )
        or []
    }

    payload: list[dict[str, Any]] = []
    for row in rows:
        count_row = counts.get(row.get("name"), {})
        payload.append(
            {
                "quiz_question_bank": row.get("name"),
                "bank_title": row.get("bank_title") or row.get("name"),
                "course": row.get("course"),
                "is_published": int(row.get("is_published") or 0),
                "question_count": int(count_row.get("question_count") or 0),
                "published_question_count": int(count_row.get("published_question_count") or 0),
            }
        )
    return payload


def _fetch_selected_quiz_question_bank(
    question_bank: str | None,
    *,
    expected_course: str | None = None,
) -> dict[str, Any] | None:
    question_bank_name = planning.normalize_text(question_bank)
    if not question_bank_name:
        return None

    bank = frappe.db.get_value(
        "Quiz Question Bank",
        question_bank_name,
        ["name", "modified", "bank_title", "course", "is_published", "description"],
        as_dict=True,
    )
    if not bank:
        frappe.throw(_("Selected quiz question bank was not found."), frappe.DoesNotExistError)

    course_name = planning.normalize_text(expected_course)
    if course_name and planning.normalize_text(bank.get("course")) != course_name:
        frappe.throw(_("Selected quiz question bank does not belong to this course."), frappe.PermissionError)

    question_rows = frappe.get_all(
        "Quiz Question",
        filters={"question_bank": question_bank_name},
        fields=[
            "name",
            "modified",
            "question_bank",
            "title",
            "question_type",
            "is_published",
            "prompt",
            "accepted_answers",
            "explanation",
        ],
        order_by="modified asc, name asc",
        limit=0,
    )
    question_names = [row["name"] for row in question_rows if row.get("name")]
    option_rows = frappe.get_all(
        "Quiz Question Option",
        filters={
            "parent": ["in", question_names or [""]],
            "parenttype": "Quiz Question",
            "parentfield": "options",
        },
        fields=["parent", "option_text", "is_correct", "idx"],
        order_by="parent asc, idx asc",
        limit=0,
    )
    options_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in option_rows or []:
        parent = row.get("parent")
        if not parent:
            continue
        options_by_parent[parent].append(
            {
                "option_text": row.get("option_text"),
                "is_correct": int(row.get("is_correct") or 0),
            }
        )

    return {
        "quiz_question_bank": bank.get("name"),
        "record_modified": _quiz_question_bank_record_modified(bank, question_rows),
        "bank_title": bank.get("bank_title") or bank.get("name"),
        "course": bank.get("course"),
        "is_published": int(bank.get("is_published") or 0),
        "description": bank.get("description"),
        "questions": [
            {
                "quiz_question": row.get("name"),
                "title": row.get("title") or row.get("name"),
                "question_type": row.get("question_type"),
                "is_published": int(row.get("is_published") or 0),
                "prompt": row.get("prompt"),
                "accepted_answers": row.get("accepted_answers"),
                "explanation": row.get("explanation"),
                "options": options_by_parent.get(row.get("name"), []),
            }
            for row in question_rows
        ],
    }


def _reload_anchor_material(anchor_doctype: str, anchor_name: str, material_name: str) -> dict[str, Any]:
    rows = materials_domain.list_anchor_materials(anchor_doctype, anchor_name)
    created = next((row for row in rows if row.get("material") == material_name), None)
    if not created:
        frappe.throw(_("Material was created but could not be reloaded."))
    return _serialize_material_entry(created)


def _fetch_material_map(anchor_refs: list[tuple[str, str]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    material_map = materials_domain.list_materials_for_anchors(anchor_refs)
    return {anchor: [_serialize_material_entry(entry) for entry in entries] for anchor, entries in material_map.items()}


def _fetch_assigned_work(
    class_teaching_plan: str,
    *,
    audience: str = "staff",
    student_name: str | None = None,
) -> list[dict[str, Any]]:
    rows = frappe.db.sql(
        """
        SELECT
            td.name AS task_delivery,
            td.name AS delivery_name,
            td.task,
            td.class_session,
            td.delivery_mode,
            td.grading_mode,
            td.available_from,
            td.due_date,
            td.lock_date,
            td.quiz_question_bank,
            td.quiz_question_count,
            td.quiz_time_limit_minutes,
            td.quiz_max_attempts,
            td.quiz_pass_percentage,
            t.title,
            t.task_type,
            t.unit_plan
        FROM `tabTask Delivery` td
        INNER JOIN `tabTask` t ON t.name = td.task
        WHERE td.class_teaching_plan = %(class_teaching_plan)s
          AND td.docstatus = 1
        ORDER BY COALESCE(td.due_date, td.available_from, td.creation) ASC, td.creation ASC
        """,
        {"class_teaching_plan": class_teaching_plan},
        as_dict=True,
    )
    if not rows:
        return []

    task_materials = _fetch_material_map([("Task", row.get("task")) for row in rows if row.get("task")])
    outcomes_by_delivery: dict[str, dict[str, Any]] = {}
    quiz_state_by_delivery: dict[str, dict[str, Any]] = {}
    if audience == "student" and student_name:
        outcome_rows = frappe.get_all(
            "Task Outcome",
            filters={
                "student": student_name,
                "task_delivery": ["in", [row["task_delivery"] for row in rows if row.get("task_delivery")] or [""]],
            },
            fields=["task_delivery", "submission_status", "grading_status", "is_complete", "is_published"],
            limit=0,
        )
        outcomes_by_delivery = {row.get("task_delivery"): row for row in outcome_rows or [] if row.get("task_delivery")}
        deliveries_for_state = [
            {
                "name": row.get("task_delivery"),
                "task": row.get("task"),
                "delivery_mode": row.get("delivery_mode"),
                "quiz_question_bank": row.get("quiz_question_bank"),
                "quiz_question_count": row.get("quiz_question_count"),
                "quiz_time_limit_minutes": row.get("quiz_time_limit_minutes"),
                "quiz_max_attempts": row.get("quiz_max_attempts"),
                "quiz_pass_percentage": row.get("quiz_pass_percentage"),
            }
            for row in rows
            if row.get("task_delivery")
        ]
        tasks_by_name = {row.get("task"): {"task_type": row.get("task_type")} for row in rows if row.get("task")}
        quiz_state_by_delivery = quiz_service.get_student_delivery_state_map(
            student=student_name,
            deliveries=deliveries_for_state,
            tasks_by_name=tasks_by_name,
        )

    payload = []
    for row in rows:
        item = {
            "task_delivery": row.get("task_delivery"),
            "task": row.get("task"),
            "title": row.get("title") or row.get("task"),
            "task_type": row.get("task_type"),
            "unit_plan": row.get("unit_plan"),
            "class_session": row.get("class_session"),
            "delivery_mode": row.get("delivery_mode"),
            "grading_mode": row.get("grading_mode"),
            "available_from": _serialize_scalar(row.get("available_from")),
            "due_date": _serialize_scalar(row.get("due_date")),
            "lock_date": _serialize_scalar(row.get("lock_date")),
            "materials": task_materials.get(("Task", row.get("task")), []),
        }
        if audience == "student":
            outcome = outcomes_by_delivery.get(row.get("task_delivery"), {})
            item["submission_status"] = outcome.get("submission_status")
            item["grading_status"] = outcome.get("grading_status")
            item["is_complete"] = int(outcome.get("is_complete") or 0) if outcome else 0
            item["is_published"] = int(outcome.get("is_published") or 0) if outcome else 0
            item["quiz_state"] = quiz_state_by_delivery.get(row.get("task_delivery"))
        payload.append(item)
    return payload


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
            "resources": [],
            "assigned_work": [],
        }
        if audience == "staff":
            session_payload["teacher_note"] = session.get("teacher_note")
        payload.append(session_payload)
    return payload


def _serialize_standards_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "framework_name",
        "framework_version",
        "subject_area",
        "program",
        "strand",
        "substrand",
        "standard_code",
        "standard_description",
        "coverage_level",
        "alignment_strength",
        "alignment_type",
        "notes",
    )
    return [{fieldname: row.get(fieldname) for fieldname in fields} for row in rows or []]


def _serialize_reflection_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "academic_year",
        "school",
        "prior_to_the_unit",
        "during_the_unit",
        "what_work_well",
        "what_didnt_work_well",
        "changes_suggestions",
    )
    return [{fieldname: row.get(fieldname) for fieldname in fields} for row in rows or []]


def _has_reflection_content(row: dict[str, Any]) -> bool:
    return any(
        planning.normalize_text(row.get(fieldname))
        for fieldname in (
            "prior_to_the_unit",
            "during_the_unit",
            "what_work_well",
            "what_didnt_work_well",
            "changes_suggestions",
        )
    )


def _fetch_unit_child_rows(
    child_doctype: str,
    unit_names: list[str],
    *,
    parentfield: str,
    fields: list[str],
) -> dict[str, list[dict[str, Any]]]:
    if not unit_names:
        return {}

    rows = frappe.get_all(
        child_doctype,
        filters={
            "parent": ["in", unit_names],
            "parenttype": "Unit Plan",
            "parentfield": parentfield,
        },
        fields=["parent", *fields],
        order_by="parent asc, idx asc",
        limit=0,
    )
    rows_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows or []:
        parent = row.get("parent")
        if parent:
            rows_by_parent[parent].append(row)
    return rows_by_parent


def _build_unit_lookup(course_plan: str, audience: str = "staff") -> dict[str, dict[str, Any]]:
    unit_rows = planning.get_unit_plan_rows(course_plan)
    unit_names = [row["name"] for row in unit_rows if row.get("name")]
    if not unit_names:
        return {}

    standards_rows = _fetch_unit_child_rows(
        "Learning Unit Standard Alignment",
        unit_names,
        parentfield="standards",
        fields=[
            "framework_name",
            "framework_version",
            "subject_area",
            "program",
            "strand",
            "substrand",
            "standard_code",
            "standard_description",
            "coverage_level",
            "alignment_strength",
            "alignment_type",
            "notes",
        ],
    )
    reflection_rows = _fetch_unit_child_rows(
        "Curriculum Planning Reflection",
        unit_names,
        parentfield="reflections",
        fields=[
            "academic_year",
            "school",
            "prior_to_the_unit",
            "during_the_unit",
            "what_work_well",
            "what_didnt_work_well",
            "changes_suggestions",
        ],
    )

    class_reflections_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if audience == "staff":
        rows = frappe.db.sql(
            """
            SELECT
                cpu.unit_plan,
                ctp.name AS class_teaching_plan,
                ctp.title AS class_teaching_plan_title,
                ctp.student_group,
                ctp.academic_year,
                sg.student_group_name,
                sg.student_group_abbreviation,
                cpu.prior_to_the_unit,
                cpu.during_the_unit,
                cpu.what_work_well,
                cpu.what_didnt_work_well,
                cpu.changes_suggestions
            FROM `tabClass Teaching Plan Unit` cpu
            INNER JOIN `tabClass Teaching Plan` ctp ON ctp.name = cpu.parent
            LEFT JOIN `tabStudent Group` sg ON sg.name = ctp.student_group
            WHERE cpu.parenttype = 'Class Teaching Plan'
              AND cpu.parentfield = 'units'
              AND ctp.course_plan = %(course_plan)s
              AND cpu.unit_plan IN %(unit_plans)s
            ORDER BY cpu.unit_plan ASC, ctp.modified DESC, ctp.creation DESC
            """,
            {"course_plan": course_plan, "unit_plans": tuple(unit_names)},
            as_dict=True,
        )
        for row in rows or []:
            if not _has_reflection_content(row):
                continue
            unit_plan = row.get("unit_plan")
            if not unit_plan:
                continue
            class_reflections_by_unit[unit_plan].append(
                {
                    "class_teaching_plan": row.get("class_teaching_plan"),
                    "student_group": row.get("student_group"),
                    "class_label": row.get("student_group_name")
                    or row.get("student_group_abbreviation")
                    or row.get("class_teaching_plan_title")
                    or row.get("student_group"),
                    "academic_year": row.get("academic_year"),
                    "prior_to_the_unit": row.get("prior_to_the_unit"),
                    "during_the_unit": row.get("during_the_unit"),
                    "what_work_well": row.get("what_work_well"),
                    "what_didnt_work_well": row.get("what_didnt_work_well"),
                    "changes_suggestions": row.get("changes_suggestions"),
                }
            )

    lookup: dict[str, dict[str, Any]] = {}
    for row in unit_rows:
        unit_name = row.get("name")
        if not unit_name:
            continue
        lookup[unit_name] = {
            **row,
            "standards": _serialize_standards_rows(standards_rows.get(unit_name, [])),
            "shared_reflections": _serialize_reflection_rows(reflection_rows.get(unit_name, [])),
            "class_reflections": class_reflections_by_unit.get(unit_name, []),
        }
    return lookup


def _serialize_backbone_units(
    class_teaching_plan: str,
    unit_lookup: dict[str, dict[str, Any]],
    audience: str = "staff",
) -> list[dict[str, Any]]:
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
            "prior_to_the_unit",
            "during_the_unit",
            "what_work_well",
            "what_didnt_work_well",
            "changes_suggestions",
        ],
        order_by="unit_order asc, idx asc",
        limit=0,
    )
    payload = []
    for row in rows:
        unit_meta = unit_lookup.get(row.get("unit_plan"), {})
        unit_payload = {
            "unit_plan": row.get("unit_plan"),
            "title": unit_meta.get("title") or row.get("unit_title"),
            "unit_order": row.get("unit_order") or unit_meta.get("unit_order"),
            "program": unit_meta.get("program"),
            "unit_code": unit_meta.get("unit_code"),
            "unit_status": unit_meta.get("unit_status"),
            "version": unit_meta.get("version"),
            "duration": unit_meta.get("duration"),
            "estimated_duration": unit_meta.get("estimated_duration"),
            "overview": unit_meta.get("overview"),
            "essential_understanding": unit_meta.get("essential_understanding"),
            "content": unit_meta.get("content"),
            "skills": unit_meta.get("skills"),
            "concepts": unit_meta.get("concepts"),
            "standards": unit_meta.get("standards", []),
            "shared_resources": [],
            "assigned_work": [],
        }
        if audience == "staff":
            unit_payload["governed_required"] = int(row.get("governed_required") or 0)
            unit_payload["pacing_status"] = row.get("pacing_status")
            unit_payload["teacher_focus"] = row.get("teacher_focus")
            unit_payload["pacing_note"] = row.get("pacing_note")
            unit_payload["is_published"] = int(unit_meta.get("is_published") or 0)
            unit_payload["misconceptions"] = unit_meta.get("misconceptions")
            unit_payload["shared_reflections"] = unit_meta.get("shared_reflections", [])
            unit_payload["class_reflections"] = unit_meta.get("class_reflections", [])
            unit_payload["prior_to_the_unit"] = row.get("prior_to_the_unit")
            unit_payload["during_the_unit"] = row.get("during_the_unit")
            unit_payload["what_work_well"] = row.get("what_work_well")
            unit_payload["what_didnt_work_well"] = row.get("what_didnt_work_well")
            unit_payload["changes_suggestions"] = row.get("changes_suggestions")
        payload.append(unit_payload)
    return payload


def _serialize_governed_units(
    course_plan: str,
    unit_lookup: dict[str, dict[str, Any]],
    materials_by_anchor: dict[tuple[str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    unit_rows = planning.get_unit_plan_rows(course_plan)
    payload: list[dict[str, Any]] = []
    for row in unit_rows:
        unit_name = row.get("name")
        unit_meta = unit_lookup.get(unit_name, row)
        payload.append(
            {
                "unit_plan": unit_name,
                "record_modified": _serialize_scalar(unit_meta.get("modified")),
                "title": unit_meta.get("title") or unit_name,
                "unit_order": unit_meta.get("unit_order"),
                "program": unit_meta.get("program"),
                "unit_code": unit_meta.get("unit_code"),
                "unit_status": unit_meta.get("unit_status"),
                "version": unit_meta.get("version"),
                "duration": unit_meta.get("duration"),
                "estimated_duration": unit_meta.get("estimated_duration"),
                "is_published": int(unit_meta.get("is_published") or 0),
                "overview": unit_meta.get("overview"),
                "essential_understanding": unit_meta.get("essential_understanding"),
                "misconceptions": unit_meta.get("misconceptions"),
                "content": unit_meta.get("content"),
                "skills": unit_meta.get("skills"),
                "concepts": unit_meta.get("concepts"),
                "standards": unit_meta.get("standards", []),
                "shared_reflections": unit_meta.get("shared_reflections", []),
                "class_reflections": unit_meta.get("class_reflections", []),
                "shared_resources": materials_by_anchor.get(("Unit Plan", unit_name), []),
            }
        )
    return payload


def _index_sessions_by_name(units: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for unit in units:
        for session in unit.get("sessions") or []:
            if session.get("class_session"):
                lookup[session["class_session"]] = session
    return lookup


def _attach_resources_and_work(
    *,
    units: list[dict[str, Any]],
    course_plan: str | None = None,
    class_teaching_plan: str | None = None,
    assigned_work: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    anchor_refs: list[tuple[str, str]] = []
    if course_plan:
        anchor_refs.append(("Course Plan", course_plan))
    if class_teaching_plan:
        anchor_refs.append(("Class Teaching Plan", class_teaching_plan))

    for unit in units:
        unit_plan = unit.get("unit_plan")
        if unit_plan:
            anchor_refs.append(("Unit Plan", unit_plan))
        for session in unit.get("sessions") or []:
            if session.get("class_session"):
                anchor_refs.append(("Class Session", session["class_session"]))

    materials_by_anchor = _fetch_material_map(anchor_refs)
    session_lookup = _index_sessions_by_name(units)
    for unit in units:
        unit["shared_resources"] = materials_by_anchor.get(("Unit Plan", unit.get("unit_plan")), [])
        for session in unit.get("sessions") or []:
            session["resources"] = materials_by_anchor.get(("Class Session", session.get("class_session")), [])

    for item in assigned_work or []:
        resolved_unit_plan = planning.normalize_text(item.get("unit_plan"))
        if not resolved_unit_plan and item.get("class_session"):
            resolved_unit_plan = planning.normalize_text(
                (session_lookup.get(item.get("class_session")) or {}).get("unit_plan")
            )
            item["unit_plan"] = resolved_unit_plan or item.get("unit_plan")

        if resolved_unit_plan:
            for unit in units:
                if planning.normalize_text(unit.get("unit_plan")) == resolved_unit_plan:
                    unit.setdefault("assigned_work", []).append(item)
                    break
        if item.get("class_session") and item["class_session"] in session_lookup:
            session_lookup[item["class_session"]].setdefault("assigned_work", []).append(item)

    return {
        "shared_resources": materials_by_anchor.get(("Course Plan", course_plan), []) if course_plan else [],
        "class_resources": materials_by_anchor.get(("Class Teaching Plan", class_teaching_plan), [])
        if class_teaching_plan
        else [],
        "general_assigned_work": [
            item
            for item in (assigned_work or [])
            if not planning.normalize_text(item.get("unit_plan"))
            and not planning.normalize_text(item.get("class_session"))
        ],
    }


def _coerce_learning_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = get_datetime(value)
        if isinstance(parsed, datetime):
            return parsed
        if isinstance(parsed, str):
            return datetime.fromisoformat(parsed.replace("Z", "+00:00"))
        return None
    except Exception:
        return None


def _iter_learning_sessions(units: list[dict[str, Any]]):
    for unit in units or []:
        for session in unit.get("sessions") or []:
            yield unit, session


def _flatten_assigned_work(
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append_item(item: dict[str, Any] | None) -> None:
        if not isinstance(item, dict):
            return
        key = planning.normalize_text(item.get("task_delivery"))
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


def _resolve_student_learning_focus(units: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not units:
        return None, None

    today = now_datetime().date()
    in_progress: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []
    upcoming: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []
    undated: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
    previous: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []

    for unit_index, (unit, session) in enumerate(_iter_learning_sessions(units)):
        session_date = _coerce_learning_datetime(session.get("session_date"))
        session_status = planning.normalize_text(session.get("session_status")).lower()
        if session_status == "in progress":
            in_progress.append((session_date or now_datetime(), unit, session))
            continue
        if session_date and session_date.date() >= today:
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


def _build_student_focus_statement(unit: dict[str, Any] | None, session: dict[str, Any] | None) -> str | None:
    if session and planning.normalize_long_text(session.get("learning_goal")):
        return planning.normalize_long_text(session.get("learning_goal"))
    if unit and planning.normalize_long_text(unit.get("essential_understanding")):
        return planning.normalize_long_text(unit.get("essential_understanding"))
    if unit and planning.normalize_long_text(unit.get("overview")):
        return planning.normalize_long_text(unit.get("overview"))
    if unit and planning.normalize_text(unit.get("title")):
        return _("You are currently working through {unit_title}.").format(unit_title=unit.get("title"))
    return None


def _build_student_learning_focus(units: list[dict[str, Any]]) -> dict[str, Any]:
    unit, session = _resolve_student_learning_focus(units)
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
        "statement": _build_student_focus_statement(unit, session),
    }


def _build_student_unit_navigation(
    units: list[dict[str, Any]],
    current_unit_plan: str | None,
) -> list[dict[str, Any]]:
    current_unit_plan = planning.normalize_text(current_unit_plan)
    return [
        {
            "unit_plan": unit.get("unit_plan"),
            "title": unit.get("title"),
            "unit_order": unit.get("unit_order"),
            "session_count": len(unit.get("sessions") or []),
            "assigned_work_count": len(unit.get("assigned_work") or []),
            "is_current": int(planning.normalize_text(unit.get("unit_plan")) == current_unit_plan),
        }
        for unit in units or []
    ]


def _build_student_next_actions(
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    actions: list[tuple[int, datetime, dict[str, Any]]] = []
    fallback_date = datetime.max
    seen: set[tuple[str, str]] = set()

    for item in _flatten_assigned_work(units, general_assigned_work):
        task_delivery = planning.normalize_text(item.get("task_delivery"))
        quiz_state = item.get("quiz_state") or {}
        due_at = _coerce_learning_datetime(item.get("due_date")) or fallback_date
        title = planning.normalize_text(item.get("title")) or _("Assigned work")
        action: dict[str, Any]
        priority = 3
        if (item.get("task_type") or "").strip() == "Quiz" and quiz_state.get("can_continue"):
            priority = 0
            action = {
                "kind": "quiz",
                "label": _("Continue {title}").format(title=title),
                "supporting_text": quiz_state.get("status_label") or _("Your attempt is in progress."),
                "task_delivery": task_delivery,
                "class_session": item.get("class_session"),
                "unit_plan": item.get("unit_plan"),
            }
        elif (item.get("task_type") or "").strip() == "Quiz" and quiz_state.get("can_retry"):
            priority = 1
            action = {
                "kind": "quiz",
                "label": _("Retry {title}").format(title=title),
                "supporting_text": quiz_state.get("status_label") or _("You can start another attempt."),
                "task_delivery": task_delivery,
                "class_session": item.get("class_session"),
                "unit_plan": item.get("unit_plan"),
            }
        elif (item.get("task_type") or "").strip() == "Quiz" and quiz_state.get("can_start"):
            priority = 1
            action = {
                "kind": "quiz",
                "label": _("Start {title}").format(title=title),
                "supporting_text": _("Ready when you are."),
                "task_delivery": task_delivery,
                "class_session": item.get("class_session"),
                "unit_plan": item.get("unit_plan"),
            }
        else:
            action = {
                "kind": "assigned_work",
                "label": _("Complete {title}").format(title=title),
                "supporting_text": _("Due {due_date}").format(due_date=item.get("due_date"))
                if item.get("due_date")
                else _("Assigned for this course."),
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

    today = now_datetime().date()
    for unit, session in _iter_learning_sessions(units):
        session_id = planning.normalize_text(session.get("class_session"))
        if not session_id:
            continue
        session_date = _coerce_learning_datetime(session.get("session_date"))
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
                    "label": _("Get ready for {title}").format(
                        title=planning.normalize_text(session.get("title")) or _("your next class")
                    ),
                    "supporting_text": _("Session on {session_date}").format(session_date=session.get("session_date"))
                    if session.get("session_date")
                    else (session.get("learning_goal") or _("Your class will continue this unit soon.")),
                    "class_session": session_id,
                    "unit_plan": unit.get("unit_plan"),
                },
            )
        )

    actions.sort(key=lambda row: (row[0], row[1], row[2].get("label") or ""))
    return [row[2] for row in actions[:4]]


def _build_student_learning_sections(
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    focus = _build_student_learning_focus(units)
    current_unit_plan = planning.normalize_text((focus.get("current_unit") or {}).get("unit_plan"))
    current_session = focus.get("current_session") or {}
    return {
        "focus": focus,
        "next_actions": _build_student_next_actions(units, general_assigned_work),
        "selected_context": {
            "unit_plan": current_unit_plan or None,
            "class_session": planning.normalize_text(current_session.get("class_session")) or None,
        },
        "unit_navigation": _build_student_unit_navigation(units, current_unit_plan),
    }


def _build_student_learning_space_payload(
    student_name: str,
    course_id: str,
    student_group: str | None = None,
) -> dict[str, Any]:
    course_id = planning.normalize_text(course_id)
    if not course_id:
        frappe.throw(_("Course is required."), frappe.ValidationError)

    _assert_student_course_access(student_name, course_id)
    group_options = _resolve_student_group_options(student_name, course_id)

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
    resources_payload = {"shared_resources": [], "class_resources": [], "general_assigned_work": []}
    assigned_work_count = 0

    if class_plan_row:
        doc = frappe.get_doc("Class Teaching Plan", class_plan_row["name"])
        resolved_course_plan = doc.course_plan
        unit_lookup = _build_unit_lookup(doc.course_plan, audience="student")
        unit_rows = _serialize_backbone_units(doc.name, unit_lookup, audience="student")
        sessions = _fetch_class_sessions(doc.name, audience="student")
        assigned_work = _fetch_assigned_work(doc.name, audience="student", student_name=student_name)
        sessions_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for session in sessions:
            sessions_by_unit[session.get("unit_plan")].append(session)
        units_payload = [{**row, "sessions": sessions_by_unit.get(row.get("unit_plan"), [])} for row in unit_rows]
        resources_payload = _attach_resources_and_work(
            units=units_payload,
            course_plan=doc.course_plan,
            class_teaching_plan=doc.name,
            assigned_work=assigned_work,
        )
        assigned_work_count = len(assigned_work)
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
            unit_lookup = _build_unit_lookup(resolved_course_plan, audience="student")
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
            resources_payload = _attach_resources_and_work(
                units=units_payload,
                course_plan=resolved_course_plan,
            )
            if group_options:
                message = _("Your teacher has not published a class teaching plan yet. Showing the shared course plan.")
            else:
                message = _(
                    "Your class is not available yet. Showing the shared course plan while your class is being assigned."
                )
        else:
            if group_options:
                message = _(
                    "Your learning space is not available yet because the class teaching plan has not been published. Check with your teacher if this class should already be available."
                )
            else:
                message = _(
                    "Your learning space is not available yet because your class is still being assigned and no shared course plan is published yet. Check with your teacher or academic office if this course should already be available."
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
        "learning": _build_student_learning_sections(
            units_payload,
            resources_payload.get("general_assigned_work") or [],
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
        payload["resources"] = {"shared_resources": [], "class_resources": [], "general_assigned_work": []}
        payload["curriculum"] = {"units": [], "session_count": 0, "assigned_work_count": 0}
        return payload

    doc = frappe.get_doc("Class Teaching Plan", resolved_plan)
    unit_lookup = _build_unit_lookup(doc.course_plan, audience="staff")
    unit_rows = _serialize_backbone_units(doc.name, unit_lookup, audience="staff")
    sessions = _fetch_class_sessions(doc.name, audience="staff")
    assigned_work = _fetch_assigned_work(doc.name, audience="staff")
    sessions_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        sessions_by_unit[session.get("unit_plan")].append(session)

    decorated_units = [
        {
            **row,
            "sessions": sessions_by_unit.get(row.get("unit_plan"), []),
        }
        for row in unit_rows
    ]
    resource_bundle = _attach_resources_and_work(
        units=decorated_units,
        course_plan=doc.course_plan,
        class_teaching_plan=doc.name,
        assigned_work=assigned_work,
    )

    payload["teaching_plan"] = {
        "class_teaching_plan": doc.name,
        "title": doc.title,
        "course_plan": doc.course_plan,
        "planning_status": doc.planning_status,
        "team_note": doc.team_note,
    }
    payload["resolved"]["course_plan"] = doc.course_plan
    payload["resources"] = resource_bundle
    payload["curriculum"] = {
        "units": decorated_units,
        "session_count": len(sessions),
        "assigned_work_count": len(assigned_work),
    }
    return payload


def _build_staff_course_plan_bundle(
    course_plan: str,
    unit_plan: str | None = None,
    quiz_question_bank: str | None = None,
) -> dict[str, Any]:
    context = _resolve_planning_resource_anchor("Course Plan", course_plan, ptype="read")
    course_plan_row = planning.get_course_plan_row(context["anchor_name"])
    course_plan_doc = frappe.get_doc("Course Plan", context["anchor_name"])
    course_row = (
        frappe.db.get_value(
            "Course",
            course_plan_row.get("course"),
            ["course_name", "course_group"],
            as_dict=True,
        )
        or {}
    )
    unit_lookup = _build_unit_lookup(course_plan_doc.name, audience="staff")
    materials_by_anchor = _fetch_material_map(
        [("Course Plan", course_plan_doc.name), *[("Unit Plan", name) for name in unit_lookup.keys()]]
    )
    units = _serialize_governed_units(course_plan_doc.name, unit_lookup, materials_by_anchor)
    selected_unit = planning.normalize_text(unit_plan)
    if selected_unit and not any(row.get("unit_plan") == selected_unit for row in units):
        frappe.throw(_("Selected unit plan does not belong to this course plan."), frappe.PermissionError)
    if not selected_unit and units:
        selected_unit = units[0].get("unit_plan")
    selected_unit_row = next((row for row in units if row.get("unit_plan") == selected_unit), None)
    selected_programs = [
        planning.normalize_text(selected_unit_row.get("program")) if selected_unit_row else "",
        *[
            planning.normalize_text(row.get("program"))
            for row in (selected_unit_row or {}).get("standards", [])
            if planning.normalize_text(row.get("program"))
        ],
    ]

    quiz_question_banks = _fetch_course_quiz_question_banks(course_plan_row.get("course"))
    selected_quiz_question_bank = planning.normalize_text(quiz_question_bank)
    if selected_quiz_question_bank and not any(
        row.get("quiz_question_bank") == selected_quiz_question_bank for row in quiz_question_banks
    ):
        frappe.throw(_("Selected quiz question bank does not belong to this course."), frappe.PermissionError)
    if not selected_quiz_question_bank and quiz_question_banks:
        selected_quiz_question_bank = quiz_question_banks[0].get("quiz_question_bank")

    academic_year_options = _fetch_academic_year_options_for_schools(
        [course_plan_row.get("school")],
        pinned_years={course_plan_row.get("school"): course_plan_row.get("academic_year")}
        if planning.normalize_text(course_plan_row.get("school"))
        else None,
    ).get(planning.normalize_text(course_plan_row.get("school")), [])
    program_options = _fetch_program_options_for_course(
        course_plan_row.get("course"),
        pinned_programs=selected_programs,
    )

    return {
        "meta": {
            "generated_at": _serialize_scalar(now_datetime()),
            "course_plan": course_plan_doc.name,
        },
        "course_plan": _serialize_course_plan_summary(
            {
                **course_plan_row,
                "modified": course_plan_doc.modified,
                "summary": course_plan_doc.summary,
            },
            course_row=course_row,
            can_manage_resources=int(context.get("can_manage_resources") or 0),
        ),
        "resolved": {
            "unit_plan": selected_unit or None,
            "quiz_question_bank": selected_quiz_question_bank or None,
        },
        "resources": {
            "course_plan_resources": materials_by_anchor.get(("Course Plan", course_plan_doc.name), []),
        },
        "field_options": {
            "academic_years": academic_year_options,
            "programs": program_options,
        },
        "curriculum": {
            "units": units,
            "unit_count": len(units),
        },
        "assessment": {
            "quiz_question_banks": quiz_question_banks,
            "selected_quiz_question_bank": _fetch_selected_quiz_question_bank(
                selected_quiz_question_bank,
                expected_course=course_plan_row.get("course"),
            ),
        },
    }


@frappe.whitelist()
def get_staff_class_planning_surface(student_group: str, class_teaching_plan: str | None = None) -> dict[str, Any]:
    _assert_staff_group_access(student_group)
    return _build_staff_bundle(student_group, class_teaching_plan=class_teaching_plan)


@frappe.whitelist()
def get_staff_course_plan_surface(
    course_plan: str,
    unit_plan: str | None = None,
    quiz_question_bank: str | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()
    status = "success"
    try:
        return _build_staff_course_plan_bundle(
            course_plan,
            unit_plan=unit_plan,
            quiz_question_bank=quiz_question_bank,
        )
    except Exception:
        status = "error"
        raise
    finally:
        _log_planning_event(
            "course_plan_surface_load",
            started_at=started_at,
            status=status,
            course_plan=planning.normalize_text(course_plan),
            unit_plan=planning.normalize_text(unit_plan),
            quiz_question_bank=planning.normalize_text(quiz_question_bank),
        )


@frappe.whitelist()
def list_staff_course_plans() -> dict[str, Any]:
    started_at = perf_counter()
    status = "success"
    course_plan_count = 0
    course_option_count = 0
    try:
        user = _require_logged_in_user()
        roles = set(frappe.get_roles(user))
        creation_access = _build_course_plan_creation_access(user, roles)
        filters: dict[str, Any] = {"plan_status": ["!=", "Archived"]}
        if planning.user_has_global_curriculum_access(user, roles):
            rows = frappe.get_list(
                "Course Plan",
                filters=filters,
                fields=[
                    "name",
                    "modified",
                    "title",
                    "course",
                    "school",
                    "academic_year",
                    "cycle_label",
                    "plan_status",
                ],
                order_by="modified desc, creation desc",
                limit=0,
            )
        else:
            managed_courses = planning.get_curriculum_manageable_course_names(user, roles)
            if managed_courses:
                filters["course"] = ["in", managed_courses]
                rows = frappe.get_list(
                    "Course Plan",
                    filters=filters,
                    fields=[
                        "name",
                        "modified",
                        "title",
                        "course",
                        "school",
                        "academic_year",
                        "cycle_label",
                        "plan_status",
                    ],
                    order_by="modified desc, creation desc",
                    limit=0,
                )
            else:
                rows = []
        course_names = sorted({row.get("course") for row in rows if row.get("course")})
        course_map = {
            row.get("name"): row
            for row in frappe.get_all(
                "Course",
                filters={"name": ["in", course_names]} if course_names else {"name": ["in", [""]]},
                fields=["name", "course_name", "course_group"],
                limit=0,
            )
        }
        payload = []
        for row in rows or []:
            payload.append(
                _serialize_course_plan_summary(
                    row,
                    course_row=course_map.get(row.get("course")),
                    can_manage_resources=int(
                        planning.user_can_manage_course_curriculum(user, row.get("course"), roles)
                    ),
                )
            )
        course_plan_count = len(payload)
        course_option_count = len(creation_access.get("course_options") or [])
        return {
            "meta": {
                "generated_at": _serialize_scalar(now_datetime()),
            },
            "access": {
                "can_create_course_plans": creation_access["can_create_course_plans"],
                "create_block_reason": creation_access["create_block_reason"],
            },
            "course_options": creation_access["course_options"],
            "course_plans": payload,
        }
    except Exception:
        status = "error"
        raise
    finally:
        _log_planning_event(
            "course_plan_index_load",
            started_at=started_at,
            status=status,
            course_plan_count=course_plan_count,
            course_option_count=course_option_count,
        )


@frappe.whitelist()
def create_course_plan(payload=None, **kwargs) -> dict[str, Any]:
    started_at = perf_counter()
    status = "success"
    course_name = ""
    created_name = ""
    try:
        user = _require_logged_in_user()
        roles = set(frappe.get_roles(user))
        data = _normalize_payload(payload if payload is not None else kwargs)
        course_name = planning.normalize_text(data.get("course"))
        if not course_name:
            frappe.throw(_("Course is required."))

        allowed_courses = {row.get("name"): row for row in _list_creatable_course_rows(user, roles) if row.get("name")}
        if not allowed_courses:
            frappe.throw(
                _(
                    "You need an active teaching assignment or curriculum leadership access before you can start a shared course plan."
                ),
                frappe.PermissionError,
            )
        course_row = allowed_courses.get(course_name)
        if not course_row:
            frappe.throw(_("You cannot create a shared course plan for this course."), frappe.PermissionError)

        doc = frappe.new_doc("Course Plan")
        doc.course = course_name
        doc.title = planning.normalize_text(data.get("title")) or _("{course_name} Plan").format(
            course_name=course_row.get("course_name") or course_name
        )
        doc.academic_year = planning.normalize_text(data.get("academic_year")) or None
        _validate_course_plan_academic_year(
            course_school=course_row.get("school"),
            academic_year=doc.academic_year,
        )
        doc.cycle_label = planning.normalize_text(data.get("cycle_label")) or None
        if data.get("plan_status") not in (None, ""):
            doc.plan_status = data.get("plan_status")
        doc.summary = planning.normalize_rich_text(data.get("summary"))

        doc.insert(ignore_permissions=True)
        created_name = planning.normalize_text(getattr(doc, "name", None))
        return {
            "course_plan": doc.name,
            "course": doc.course,
            "title": doc.title,
            "plan_status": doc.plan_status,
        }
    except Exception:
        status = "error"
        raise
    finally:
        _log_planning_event(
            "course_plan_create",
            started_at=started_at,
            status=status,
            course_plan=created_name,
            course=course_name,
        )


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
    doc.team_note = planning.normalize_rich_text(team_note)
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
    prior_to_the_unit: str | None = None,
    during_the_unit: str | None = None,
    what_work_well: str | None = None,
    what_didnt_work_well: str | None = None,
    changes_suggestions: str | None = None,
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
    matched.prior_to_the_unit = planning.normalize_rich_text(prior_to_the_unit)
    matched.during_the_unit = planning.normalize_rich_text(during_the_unit)
    matched.what_work_well = planning.normalize_rich_text(what_work_well)
    matched.what_didnt_work_well = planning.normalize_rich_text(what_didnt_work_well)
    matched.changes_suggestions = planning.normalize_rich_text(changes_suggestions)
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
    doc.learning_goal = planning.normalize_long_text(learning_goal)
    doc.teacher_note = planning.normalize_rich_text(teacher_note)

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


@frappe.whitelist()
def save_course_plan(payload=None, **kwargs) -> dict[str, Any]:
    started_at = perf_counter()
    status = "success"
    course_plan = ""
    course = ""
    try:
        data = _normalize_payload(payload if payload is not None else kwargs)
        course_plan = planning.normalize_text(data.get("course_plan"))
        if not course_plan:
            frappe.throw(_("Course Plan is required."))

        doc = frappe.get_doc("Course Plan", course_plan)
        course = planning.normalize_text(getattr(doc, "course", None))
        _assert_course_curriculum_access(
            doc.course,
            ptype="write",
            action_label=_("update this shared course plan"),
        )
        planning.assert_record_modified_matches(
            expected_modified=data.get("expected_modified"),
            current_modified=getattr(doc, "modified", None),
            section_label=_("Shared course plan"),
        )

        doc.title = planning.normalize_text(data.get("title")) or None
        doc.academic_year = planning.normalize_text(data.get("academic_year")) or None
        _validate_course_plan_academic_year(
            course_school=getattr(doc, "school", None),
            academic_year=doc.academic_year,
            previous_academic_year=doc.get_db_value("academic_year") if hasattr(doc, "get_db_value") else None,
        )
        doc.cycle_label = planning.normalize_text(data.get("cycle_label")) or None
        doc.plan_status = planning.normalize_text(data.get("plan_status")) or None
        doc.summary = planning.normalize_rich_text(data.get("summary"))

        doc.save(ignore_permissions=True)
        return {
            "course_plan": doc.name,
            "plan_status": doc.plan_status,
        }
    except Exception:
        status = "error"
        raise
    finally:
        _log_planning_event(
            "course_plan_save",
            started_at=started_at,
            status=status,
            course_plan=course_plan,
            course=course,
        )


@frappe.whitelist()
def save_unit_plan(
    payload=None,
    *,
    course_plan: str | None = None,
    unit_plan: str | None = None,
    title: str | None = None,
    program: str | None = None,
    unit_code: str | None = None,
    unit_order: int | None = None,
    unit_status: str | None = None,
    version: str | None = None,
    duration: str | None = None,
    estimated_duration: str | None = None,
    is_published: int | None = None,
    expected_modified: str | None = None,
    overview: str | None = None,
    essential_understanding: str | None = None,
    misconceptions: str | None = None,
    content: str | None = None,
    skills: str | None = None,
    concepts: str | None = None,
    standards_json: str | None = None,
    reflections_json: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    started_at = perf_counter()
    status = "success"
    course_plan_name = planning.normalize_text(course_plan)
    unit_plan_name = planning.normalize_text(unit_plan)
    course_name = ""
    doc = None
    try:
        data = _normalize_payload(payload if payload is not None else kwargs)
        course_plan_name = planning.normalize_text(course_plan or data.get("course_plan"))
        unit_plan_name = planning.normalize_text(unit_plan or data.get("unit_plan"))
        title = title if title is not None else data.get("title")
        program = program if program is not None else data.get("program")
        unit_code = unit_code if unit_code is not None else data.get("unit_code")
        unit_order = unit_order if unit_order is not None else data.get("unit_order")
        unit_status = unit_status if unit_status is not None else data.get("unit_status")
        version = version if version is not None else data.get("version")
        duration = duration if duration is not None else data.get("duration")
        estimated_duration = estimated_duration if estimated_duration is not None else data.get("estimated_duration")
        is_published = is_published if is_published is not None else data.get("is_published")
        overview = overview if overview is not None else data.get("overview")
        essential_understanding = (
            essential_understanding if essential_understanding is not None else data.get("essential_understanding")
        )
        misconceptions = misconceptions if misconceptions is not None else data.get("misconceptions")
        content = content if content is not None else data.get("content")
        skills = skills if skills is not None else data.get("skills")
        concepts = concepts if concepts is not None else data.get("concepts")
        standards_json = standards_json if standards_json is not None else data.get("standards_json")
        reflections_json = reflections_json if reflections_json is not None else data.get("reflections_json")
        expected_modified = expected_modified if expected_modified is not None else data.get("expected_modified")

        if unit_plan_name:
            doc = frappe.get_doc("Unit Plan", unit_plan_name)
            course_plan_row = planning.get_course_plan_row(doc.course_plan)
            course_name = planning.normalize_text(course_plan_row.get("course"))
            _assert_course_curriculum_access(
                course_plan_row.get("course"),
                ptype="write",
                action_label=_("update this unit plan"),
            )
            planning.assert_record_modified_matches(
                expected_modified=expected_modified,
                current_modified=getattr(doc, "modified", None),
                section_label=_("Unit plan"),
            )
        else:
            if not course_plan_name:
                frappe.throw(_("Course Plan is required."))
            course_plan_row = planning.get_course_plan_row(course_plan_name)
            course_name = planning.normalize_text(course_plan_row.get("course"))
            _assert_course_curriculum_access(
                course_plan_row.get("course"),
                ptype="write",
                action_label=_("create a unit plan for this course"),
            )
            doc = frappe.new_doc("Unit Plan")
            doc.course_plan = course_plan_name

        doc.title = planning.normalize_text(title) or None
        doc.program = planning.normalize_text(program) or None
        _validate_course_program_link(
            course=course_plan_row.get("course"),
            program=doc.program,
            previous_program=doc.get_db_value("program") if hasattr(doc, "get_db_value") else None,
        )
        doc.unit_code = planning.normalize_text(unit_code) or None
        doc.unit_order = int(unit_order) if unit_order not in (None, "") else None
        if unit_status not in (None, ""):
            doc.unit_status = planning.normalize_text(unit_status) or None
        doc.version = planning.normalize_text(version) or None
        doc.duration = planning.normalize_text(duration) or None
        doc.estimated_duration = planning.normalize_text(estimated_duration) or None
        doc.is_published = planning.normalize_flag(is_published)
        doc.overview = planning.normalize_rich_text(overview)
        doc.essential_understanding = planning.normalize_rich_text(essential_understanding)
        doc.misconceptions = planning.normalize_rich_text(misconceptions)
        doc.content = planning.normalize_rich_text(content)
        doc.skills = planning.normalize_rich_text(skills)
        doc.concepts = planning.normalize_rich_text(concepts)

        planning.replace_unit_plan_standards(
            doc,
            _normalize_rows_payload(standards_json, label=_("Standards")),
        )
        planning.replace_unit_plan_reflections(
            doc,
            _normalize_rows_payload(reflections_json, label=_("Reflections")),
            course_plan_row=course_plan_row,
        )
        if doc.is_new():
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)

        return {
            "course_plan": doc.course_plan,
            "unit_plan": doc.name,
            "unit_order": doc.unit_order,
        }
    except Exception:
        status = "error"
        raise
    finally:
        _log_planning_event(
            "unit_plan_save",
            started_at=started_at,
            status=status,
            course_plan=planning.normalize_text(getattr(doc, "course_plan", None)),
            unit_plan=planning.normalize_text(getattr(doc, "name", None)),
            course=course_name,
        )


@frappe.whitelist()
def create_planning_reference_material(payload=None, **kwargs) -> dict[str, Any]:
    data = _normalize_payload(payload if payload is not None else kwargs)
    context = _resolve_planning_resource_anchor(data.get("anchor_doctype"), data.get("anchor_name"), ptype="write")
    title = planning.normalize_text(data.get("title"))
    if not title:
        frappe.throw(_("Title is required."))

    material, placement = materials_domain.create_reference_material(
        anchor_doctype=context["anchor_doctype"],
        anchor_name=context["anchor_name"],
        title=title,
        reference_url=data.get("reference_url"),
        description=data.get("description"),
        modality=data.get("modality"),
        usage_role=data.get("usage_role"),
        placement_note=data.get("placement_note"),
        origin=materials_domain.resolve_material_origin(context["anchor_doctype"]),
    )
    return {
        "anchor_doctype": context["anchor_doctype"],
        "anchor_name": context["anchor_name"],
        "placement": placement.name,
        "resource": _reload_anchor_material(context["anchor_doctype"], context["anchor_name"], material.name),
    }


@frappe.whitelist()
def upload_planning_material_file(
    anchor_doctype: str | None = None,
    anchor_name: str | None = None,
    title: str | None = None,
    description: str | None = None,
    modality: str | None = None,
    usage_role: str | None = None,
    placement_note: str | None = None,
) -> dict[str, Any]:
    anchor_doctype = anchor_doctype or frappe.form_dict.get("anchor_doctype")
    anchor_name = anchor_name or frappe.form_dict.get("anchor_name")
    title = title or frappe.form_dict.get("title")
    description = description if description is not None else frappe.form_dict.get("description")
    modality = modality if modality is not None else frappe.form_dict.get("modality")
    usage_role = usage_role if usage_role is not None else frappe.form_dict.get("usage_role")
    placement_note = placement_note if placement_note is not None else frappe.form_dict.get("placement_note")

    context = _resolve_planning_resource_anchor(anchor_doctype, anchor_name, ptype="write")
    title = planning.normalize_text(title)
    if not title:
        frappe.throw(_("Title is required."))

    frappe.db.savepoint("upload_planning_material_file")
    try:
        material = materials_domain.create_file_material_record(
            anchor_doctype=context["anchor_doctype"],
            anchor_name=context["anchor_name"],
            title=title,
            description=description,
            modality=modality,
        )
        governed_uploads.upload_supporting_material_file(material=material.name)
        placement = materials_domain.create_material_placement(
            supporting_material=material.name,
            anchor_doctype=context["anchor_doctype"],
            anchor_name=context["anchor_name"],
            usage_role=usage_role,
            placement_note=placement_note,
            origin=materials_domain.resolve_material_origin(context["anchor_doctype"]),
        )
    except Exception:
        frappe.db.rollback(save_point="upload_planning_material_file")
        raise

    return {
        "anchor_doctype": context["anchor_doctype"],
        "anchor_name": context["anchor_name"],
        "placement": placement.name,
        "resource": _reload_anchor_material(context["anchor_doctype"], context["anchor_name"], material.name),
    }


@frappe.whitelist()
def remove_planning_material(payload=None, **kwargs) -> dict[str, Any]:
    data = _normalize_payload(payload if payload is not None else kwargs)
    context = _resolve_planning_resource_anchor(data.get("anchor_doctype"), data.get("anchor_name"), ptype="write")
    placement = planning.normalize_text(data.get("placement"))
    if not placement:
        frappe.throw(_("Placement is required."))

    materials_domain.delete_anchor_material_placement(
        placement,
        anchor_doctype=context["anchor_doctype"],
        anchor_name=context["anchor_name"],
    )
    return {
        "anchor_doctype": context["anchor_doctype"],
        "anchor_name": context["anchor_name"],
        "placement": placement,
        "removed": 1,
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

    return selected_group or None, class_plan_row


@frappe.whitelist()
def get_student_learning_space(course_id: str, student_group: str | None = None) -> dict[str, Any]:
    started_at = perf_counter()
    started_query_count = _current_db_query_count()
    status = "success"
    payload = None
    try:
        student_name = _require_student_name()
        payload = _build_student_learning_space_payload(
            student_name,
            course_id,
            student_group=student_group,
        )
        return payload
    except Exception:
        status = "error"
        raise
    finally:
        payload_bytes = _payload_size_bytes(payload)
        query_count = _db_query_delta(started_query_count)
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        should_warn = bool(
            status == "success"
            and (
                elapsed_ms > STUDENT_LEARNING_SPACE_WARN_ELAPSED_MS
                or (payload_bytes is not None and payload_bytes > STUDENT_LEARNING_SPACE_WARN_PAYLOAD_BYTES)
            )
        )
        _log_planning_event(
            "student_learning_space_load",
            started_at=started_at,
            warning=should_warn,
            status=status,
            course_id=planning.normalize_text(course_id),
            student_group=planning.normalize_text((payload or {}).get("access", {}).get("resolved_student_group"))
            or planning.normalize_text(student_group),
            source=(payload or {}).get("teaching_plan", {}).get("source"),
            unit_count=(payload or {}).get("curriculum", {}).get("counts", {}).get("units"),
            session_count=(payload or {}).get("curriculum", {}).get("counts", {}).get("sessions"),
            assigned_work_count=(payload or {}).get("curriculum", {}).get("counts", {}).get("assigned_work"),
            payload_bytes=payload_bytes,
            db_query_count=query_count,
        )
