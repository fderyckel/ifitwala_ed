from __future__ import annotations

import re
from collections.abc import Iterable

import frappe
from frappe import _

from ifitwala_ed.api import student_groups as student_groups_api
from ifitwala_ed.utilities.html_sanitizer import sanitize_html

ORDER_STEP = 10
CURRICULUM_GLOBAL_MANAGER_ROLES = {"System Manager", "Academic Admin", "Administrator"}
_RICH_TEXT_TAG_RE = re.compile(r"<[^>]*>")
_RICH_TEXT_MEDIA_RE = re.compile(r"<(audio|hr|iframe|img|table|video)\b", re.IGNORECASE)
_RICH_TEXT_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[\s\S]*?</\1>", re.IGNORECASE)
_RICH_TEXT_NBSP_RE = re.compile(r"&nbsp;|&#160;", re.IGNORECASE)
LEARNING_STANDARD_CATALOG_FIELDS = (
    "framework_name",
    "framework_version",
    "subject_area",
    "program",
    "strand",
    "substrand",
    "standard_code",
    "standard_description",
    "alignment_type",
)


def normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def normalize_long_text(value: str | None) -> str | None:
    text = normalize_text(value)
    return text or None


def normalize_rich_text(value: str | None, *, allow_headings_from: str = "h2") -> str | None:
    text = normalize_text(value)
    if not text:
        return None

    cleaned = normalize_text(sanitize_html(text, allow_headings_from=allow_headings_from))
    if not cleaned:
        return None

    visible_text = _RICH_TEXT_NBSP_RE.sub(
        " ",
        _RICH_TEXT_TAG_RE.sub(
            " ",
            _RICH_TEXT_SCRIPT_STYLE_RE.sub(" ", cleaned),
        ),
    ).strip()
    return cleaned if visible_text or _RICH_TEXT_MEDIA_RE.search(cleaned) else None


def normalize_flag(value) -> int:
    if isinstance(value, bool):
        return int(value)
    text = normalize_text(value)
    if not text:
        return 0
    return 1 if text in {"1", "true", "True", "yes", "Yes"} else 0


def normalize_record_modified(value) -> str:
    return normalize_text(value)


def assert_record_modified_matches(*, expected_modified, current_modified, section_label: str) -> None:
    if expected_modified is None:
        return

    expected = normalize_record_modified(expected_modified)
    current = normalize_record_modified(current_modified)
    if expected == current:
        return

    frappe.throw(
        _("{section_label} was updated by another user. Reload this page before saving again.").format(
            section_label=section_label,
        ),
        frappe.ValidationError,
    )


def user_has_global_curriculum_access(user: str, roles: Iterable[str] | None = None) -> bool:
    user = normalize_text(user)
    if not user or user == "Guest":
        return False
    role_set = set(roles or frappe.get_roles(user) or [])
    return user == "Administrator" or bool(role_set & CURRICULUM_GLOBAL_MANAGER_ROLES)


def get_instructor_course_names(user: str) -> list[str]:
    user = normalize_text(user)
    if not user or user == "Guest":
        return []

    group_names = list(student_groups_api._instructor_group_names(user) or [])
    if not group_names:
        return []

    return sorted(
        {
            normalize_text(course)
            for course in (
                frappe.get_all(
                    "Student Group",
                    filters={"name": ["in", group_names]},
                    pluck="course",
                    limit=0,
                )
                or []
            )
            if normalize_text(course)
        }
    )


def get_coordinator_course_names(user: str) -> list[str]:
    user = normalize_text(user)
    if not user or user == "Guest":
        return []

    employee = normalize_text(frappe.db.get_value("Employee", {"user_id": user, "employment_status": "Active"}, "name"))
    if not employee:
        return []

    rows = frappe.db.sql(
        """
        SELECT DISTINCT pcr.course
        FROM `tabProgram Coordinator` pc
        JOIN `tabProgram Course` pcr ON pcr.parent = pc.parent
        WHERE pc.parenttype = 'Program'
          AND pc.parentfield = 'program_coordinators'
          AND pcr.parenttype = 'Program'
          AND pcr.parentfield = 'courses'
          AND pc.coordinator = %(employee)s
        """,
        {"employee": employee},
        as_dict=True,
    )
    return sorted({normalize_text(row.get("course")) for row in rows or [] if normalize_text(row.get("course"))})


def get_curriculum_manageable_course_names(user: str, roles: Iterable[str] | None = None) -> list[str]:
    user = normalize_text(user)
    if not user or user == "Guest":
        return []

    role_set = set(roles or frappe.get_roles(user) or [])
    courses = set(get_instructor_course_names(user))
    if "Curriculum Coordinator" in role_set or user_has_global_curriculum_access(user, role_set):
        courses.update(get_coordinator_course_names(user))
    return sorted(course for course in courses if course)


def user_can_read_course_curriculum(user: str, course: str, roles: Iterable[str] | None = None) -> bool:
    user = normalize_text(user)
    course = normalize_text(course)
    if not user or user == "Guest" or not course:
        return False

    role_set = set(roles or frappe.get_roles(user) or [])
    if user_has_global_curriculum_access(user, role_set):
        return True

    return course in set(get_curriculum_manageable_course_names(user, role_set))


def user_can_manage_course_curriculum(user: str, course: str, roles: Iterable[str] | None = None) -> bool:
    return user_can_read_course_curriculum(user, course, roles)


def assert_can_read_course_curriculum(
    user: str,
    course: str,
    roles: Iterable[str] | None = None,
    *,
    action_label: str | None = None,
) -> None:
    if user_can_read_course_curriculum(user, course, roles):
        return

    if action_label:
        frappe.throw(
            _("You do not have access to {0}.").format(action_label),
            frappe.PermissionError,
        )
    frappe.throw(_("You do not have access to this course curriculum."), frappe.PermissionError)


def assert_can_manage_course_curriculum(
    user: str,
    course: str,
    roles: Iterable[str] | None = None,
    *,
    action_label: str | None = None,
) -> None:
    if user_can_manage_course_curriculum(user, course, roles):
        return

    if action_label:
        frappe.throw(
            _("You do not have access to {0}.").format(action_label),
            frappe.PermissionError,
        )
    frappe.throw(_("You do not have access to manage this course curriculum."), frappe.PermissionError)


def get_course_plan_row(course_plan: str) -> dict:
    row = frappe.db.get_value(
        "Course Plan",
        course_plan,
        ["name", "title", "course", "school", "academic_year", "cycle_label", "plan_status"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Course Plan not found."))
    return row


def get_student_group_row(student_group: str) -> dict:
    row = frappe.db.get_value(
        "Student Group",
        student_group,
        ["name", "student_group_name", "student_group_abbreviation", "course", "academic_year", "school", "term"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Student Group not found."))
    return row


def resolve_active_class_teaching_plan(student_group: str) -> dict[str, object]:
    student_group = normalize_text(student_group)
    if not student_group:
        return {
            "status": "missing_active_plan",
            "class_teaching_plan": None,
            "active_plan_count": 0,
        }

    active_rows = frappe.get_all(
        "Class Teaching Plan",
        filters={"student_group": student_group, "planning_status": "Active"},
        fields=["name", "title", "course_plan", "planning_status"],
        order_by="modified desc, creation desc",
        limit=2,
        ignore_permissions=True,
    )

    if not active_rows:
        return {
            "status": "missing_active_plan",
            "class_teaching_plan": None,
            "active_plan_count": 0,
        }

    if len(active_rows) > 1:
        return {
            "status": "multiple_active_plans",
            "class_teaching_plan": None,
            "active_plan_count": len(active_rows),
        }

    return {
        "status": "ready",
        "class_teaching_plan": normalize_text(active_rows[0].get("name")) or None,
        "active_plan_count": 1,
    }


def get_unit_plan_rows(course_plan: str) -> list[dict]:
    return frappe.get_all(
        "Unit Plan",
        filters={"course_plan": course_plan, "unit_status": ["!=", "Archived"]},
        fields=[
            "name",
            "title",
            "course_plan",
            "course",
            "modified",
            "program",
            "unit_code",
            "unit_order",
            "unit_status",
            "version",
            "duration",
            "estimated_duration",
            "is_published",
            "overview",
            "essential_understanding",
            "misconceptions",
            "content",
            "skills",
            "concepts",
        ],
        order_by="unit_order asc, creation asc",
        limit=0,
    )


def next_unit_order(course_plan: str) -> int:
    current = frappe.db.sql(
        """
        SELECT COALESCE(MAX(unit_order), 0)
        FROM `tabUnit Plan`
        WHERE course_plan = %s
        """,
        (course_plan,),
        as_list=True,
    )[0][0]
    return int(current or 0) + ORDER_STEP


def next_session_sequence(class_teaching_plan: str, unit_plan: str | None = None) -> int:
    filters = {"class_teaching_plan": class_teaching_plan}
    if unit_plan:
        filters["unit_plan"] = unit_plan
    current = frappe.db.get_value("Class Session", filters, "MAX(sequence_index)")
    return int(current or 0) + ORDER_STEP


def build_class_teaching_plan_title(group_row: dict, course_plan_row: dict) -> str:
    label = normalize_text(group_row.get("student_group_name")) or normalize_text(group_row.get("name"))
    plan_title = normalize_text(course_plan_row.get("title")) or normalize_text(course_plan_row.get("name"))
    return f"{label} · {plan_title}"


def sync_class_teaching_plan_units(doc) -> None:
    unit_rows = get_unit_plan_rows(doc.course_plan)
    if not unit_rows:
        doc.set("units", [])
        return

    existing = {
        normalize_text(row.unit_plan): row
        for row in (doc.get("units") or [])
        if normalize_text(getattr(row, "unit_plan", None))
    }

    refreshed = []
    for unit in unit_rows:
        cached = existing.get(unit["name"])
        refreshed.append(
            {
                "unit_plan": unit["name"],
                "unit_title": unit.get("title"),
                "unit_order": unit.get("unit_order"),
                "governed_required": 1,
                "pacing_status": getattr(cached, "pacing_status", None) or "Not Started",
                "teacher_focus": getattr(cached, "teacher_focus", None),
                "pacing_note": getattr(cached, "pacing_note", None),
                "prior_to_the_unit": getattr(cached, "prior_to_the_unit", None),
                "during_the_unit": getattr(cached, "during_the_unit", None),
                "what_work_well": getattr(cached, "what_work_well", None),
                "what_didnt_work_well": getattr(cached, "what_didnt_work_well", None),
                "changes_suggestions": getattr(cached, "changes_suggestions", None),
            }
        )

    doc.set("units", refreshed)


def sync_all_class_teaching_plans(course_plan: str) -> None:
    course_plan_name = normalize_text(course_plan)
    if not course_plan_name:
        return

    plan_names = frappe.get_all(
        "Class Teaching Plan",
        filters={"course_plan": course_plan_name},
        pluck="name",
        limit=0,
    )
    for plan_name in plan_names or []:
        doc = frappe.get_doc("Class Teaching Plan", plan_name)
        sync_class_teaching_plan_units(doc)
        doc.save(ignore_permissions=True)


def _log_class_teaching_plan_bootstrap(payload: dict) -> None:
    logger_factory = getattr(frappe, "logger", None)
    if not callable(logger_factory):
        return
    logger_factory("ifitwala.curriculum").info(payload)


def _resolve_bootstrap_course_plan_for_group(course: str, academic_year: str | None) -> dict[str, str | None]:
    course = normalize_text(course)
    academic_year = normalize_text(academic_year)
    if not course:
        return {"course_plan": None, "reason": "missing_course"}

    base_filters = {
        "course": course,
        "plan_status": "Active",
    }
    if academic_year:
        exact_year_rows = frappe.get_all(
            "Course Plan",
            filters={**base_filters, "academic_year": academic_year},
            fields=["name"],
            order_by="modified desc, creation desc",
            limit=2,
        )
        if len(exact_year_rows) == 1:
            return {
                "course_plan": normalize_text(exact_year_rows[0].get("name")) or None,
                "reason": None,
            }
        if len(exact_year_rows) > 1:
            return {
                "course_plan": None,
                "reason": "multiple_course_plans_for_academic_year",
            }

    fallback_rows = frappe.get_all(
        "Course Plan",
        filters=base_filters,
        fields=["name"],
        order_by="modified desc, creation desc",
        limit=2,
    )
    if len(fallback_rows) == 1:
        return {
            "course_plan": normalize_text(fallback_rows[0].get("name")) or None,
            "reason": None,
        }
    if len(fallback_rows) > 1:
        return {"course_plan": None, "reason": "multiple_course_plans"}
    return {"course_plan": None, "reason": "missing_course_plan"}


def bootstrap_student_group_class_teaching_plan(student_group_doc) -> dict[str, str | None]:
    student_group = normalize_text(getattr(student_group_doc, "name", None))
    group_based_on = normalize_text(getattr(student_group_doc, "group_based_on", None))
    status = normalize_text(getattr(student_group_doc, "status", None)) or "Active"
    course = normalize_text(getattr(student_group_doc, "course", None))
    academic_year = normalize_text(getattr(student_group_doc, "academic_year", None)) or None

    if group_based_on != "Course":
        return {
            "status": "skipped",
            "reason": "non_course_group",
            "student_group": student_group or None,
            "course_plan": None,
            "class_teaching_plan": None,
        }
    if status != "Active":
        return {
            "status": "skipped",
            "reason": "inactive_student_group",
            "student_group": student_group or None,
            "course_plan": None,
            "class_teaching_plan": None,
        }
    if not student_group or not course:
        result = {
            "status": "skipped",
            "reason": "missing_student_group_or_course",
            "student_group": student_group or None,
            "course_plan": None,
            "class_teaching_plan": None,
        }
        _log_class_teaching_plan_bootstrap(
            {
                "event": "class_teaching_plan_bootstrap_skipped",
                "result": result,
                "academic_year": academic_year,
            }
        )
        return result

    resolved = _resolve_bootstrap_course_plan_for_group(course, academic_year)
    course_plan = normalize_text(resolved.get("course_plan")) or None
    if not course_plan:
        result = {
            "status": "skipped",
            "reason": resolved.get("reason") or "unresolved_course_plan",
            "student_group": student_group,
            "course_plan": None,
            "class_teaching_plan": None,
        }
        _log_class_teaching_plan_bootstrap(
            {
                "event": "class_teaching_plan_bootstrap_skipped",
                "result": result,
                "course": course,
                "academic_year": academic_year,
            }
        )
        return result

    existing_plan = normalize_text(
        frappe.db.get_value(
            "Class Teaching Plan",
            {
                "student_group": student_group,
                "course_plan": course_plan,
            },
            "name",
        )
    )
    if existing_plan:
        return {
            "status": "existing",
            "reason": None,
            "student_group": student_group,
            "course_plan": course_plan,
            "class_teaching_plan": existing_plan,
        }

    doc = frappe.new_doc("Class Teaching Plan")
    doc.student_group = student_group
    doc.course_plan = course_plan
    doc.planning_status = "Active"
    try:
        doc.insert(ignore_permissions=True)
    except frappe.ValidationError:
        existing_plan = normalize_text(
            frappe.db.get_value(
                "Class Teaching Plan",
                {
                    "student_group": student_group,
                    "course_plan": course_plan,
                },
                "name",
            )
        )
        if existing_plan:
            return {
                "status": "existing",
                "reason": None,
                "student_group": student_group,
                "course_plan": course_plan,
                "class_teaching_plan": existing_plan,
            }
        raise

    result = {
        "status": "created",
        "reason": None,
        "student_group": student_group,
        "course_plan": course_plan,
        "class_teaching_plan": doc.name,
    }
    _log_class_teaching_plan_bootstrap(
        {
            "event": "class_teaching_plan_bootstrap_created",
            "result": result,
            "course": course,
            "academic_year": academic_year,
        }
    )
    return result


def replace_session_activities(doc, rows: Iterable[dict] | None) -> None:
    sanitized: list[dict] = []
    for idx, row in enumerate(rows or [], start=1):
        title = normalize_text((row or {}).get("title"))
        if not title:
            continue
        sequence_index = (row or {}).get("sequence_index")
        sanitized.append(
            {
                "title": title,
                "activity_type": normalize_text((row or {}).get("activity_type")) or "Other",
                "estimated_minutes": (row or {}).get("estimated_minutes"),
                "sequence_index": int(sequence_index) if sequence_index not in (None, "") else idx * ORDER_STEP,
                "student_direction": normalize_long_text((row or {}).get("student_direction")),
                "teacher_prompt": normalize_long_text((row or {}).get("teacher_prompt")),
                "resource_note": normalize_long_text((row or {}).get("resource_note")),
            }
        )
    doc.set("activities", sanitized)


def replace_unit_plan_standards(doc, rows: Iterable[dict] | None) -> None:
    sanitized: list[dict] = []
    for row in rows or []:
        payload = {
            "learning_standard": normalize_text((row or {}).get("learning_standard")) or None,
            "framework_name": normalize_text((row or {}).get("framework_name")) or None,
            "framework_version": normalize_text((row or {}).get("framework_version")) or None,
            "subject_area": normalize_text((row or {}).get("subject_area")) or None,
            "program": normalize_text((row or {}).get("program")) or None,
            "strand": normalize_text((row or {}).get("strand")) or None,
            "substrand": normalize_text((row or {}).get("substrand")) or None,
            "standard_code": normalize_text((row or {}).get("standard_code")) or None,
            "standard_description": normalize_long_text((row or {}).get("standard_description")),
            "coverage_level": normalize_text((row or {}).get("coverage_level")) or None,
            "alignment_strength": normalize_text((row or {}).get("alignment_strength")) or None,
            "alignment_type": normalize_text((row or {}).get("alignment_type")) or None,
            "notes": normalize_long_text((row or {}).get("notes")),
        }
        if not any(payload.values()):
            continue
        sanitized.append(payload)
    doc.set("standards", sanitized)


def _normalize_learning_standard_catalog_row(row: dict | None) -> dict[str, str | None]:
    payload = {
        fieldname: normalize_long_text((row or {}).get(fieldname))
        if fieldname == "standard_description"
        else normalize_text((row or {}).get(fieldname)) or None
        for fieldname in LEARNING_STANDARD_CATALOG_FIELDS
    }
    payload["learning_standard"] = (
        normalize_text((row or {}).get("name") or (row or {}).get("learning_standard")) or None
    )
    return payload


def _catalog_rows_match(candidate: dict[str, str | None], row: dict[str, str | None]) -> bool:
    for fieldname in LEARNING_STANDARD_CATALOG_FIELDS:
        expected = row.get(fieldname)
        if expected in (None, ""):
            continue
        if candidate.get(fieldname) != expected:
            return False
    return True


def _resolve_learning_standard_candidates(code: str) -> list[dict[str, str | None]]:
    if not code:
        return []
    return [
        _normalize_learning_standard_catalog_row(row)
        for row in (
            frappe.get_all(
                "Learning Standards",
                filters={"standard_code": code},
                fields=["name", *LEARNING_STANDARD_CATALOG_FIELDS],
                limit=0,
            )
            or []
        )
    ]


def _resolve_learning_standard_identifier(
    identifier: str,
    row: dict[str, str | None],
) -> dict[str, str | None] | None:
    identifier = normalize_text(identifier)
    if not identifier:
        return None

    direct_match = frappe.db.get_value(
        "Learning Standards",
        identifier,
        ["name", *LEARNING_STANDARD_CATALOG_FIELDS],
        as_dict=True,
    )
    if direct_match:
        return _normalize_learning_standard_catalog_row(direct_match)

    code_matches = _resolve_learning_standard_candidates(identifier)
    if not code_matches:
        return None
    if len(code_matches) == 1:
        return code_matches[0]

    narrowed = [candidate for candidate in code_matches if _catalog_rows_match(candidate, row)]
    if len(narrowed) == 1:
        return narrowed[0]

    frappe.throw(
        _("Learning Standard {0} matches multiple catalog rows. Select the exact record again.").format(
            identifier,
        ),
        frappe.ValidationError,
    )


def _resolve_unit_standard_catalog_row(
    row: dict | None,
    linked_rows: dict[str, dict[str, str | None]],
) -> dict[str, str | None]:
    normalized = _normalize_learning_standard_catalog_row(row)
    linked_name = normalized.get("learning_standard")
    if linked_name:
        linked_row = linked_rows.get(linked_name) or _resolve_learning_standard_identifier(
            linked_name,
            normalized,
        )
        if linked_row:
            return linked_row

    code = normalized.get("standard_code")
    if not code:
        if linked_name:
            frappe.throw(
                _("Learning Standard {0} does not exist.").format(linked_name),
                frappe.ValidationError,
            )
        frappe.throw(
            _("Each standards alignment row must select an existing Learning Standard."),
            frappe.ValidationError,
        )

    matches = [
        candidate
        for candidate in _resolve_learning_standard_candidates(code)
        if _catalog_rows_match(candidate, normalized)
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        if linked_name:
            frappe.throw(
                _("Learning Standard {0} could not be resolved from the catalog. Re-select it from the picker.").format(
                    linked_name
                ),
                frappe.ValidationError,
            )
        frappe.throw(
            _("Standard {0} must match an existing Learning Standard.").format(code),
            frappe.ValidationError,
        )
    frappe.throw(
        _("Standard {0} matches multiple Learning Standards. Select the exact standard from the catalog.").format(
            code,
        ),
        frappe.ValidationError,
    )


def ensure_linked_unit_plan_standards(doc) -> None:
    rows = list(doc.get("standards") or [])
    linked_names = sorted(
        {
            normalize_text((row or {}).get("learning_standard"))
            for row in rows
            if normalize_text((row or {}).get("learning_standard"))
        }
    )
    linked_rows = {}
    if linked_names:
        linked_rows = {
            row["learning_standard"]: row
            for row in (
                _normalize_learning_standard_catalog_row(raw_row)
                for raw_row in (
                    frappe.get_all(
                        "Learning Standards",
                        filters={"name": ["in", linked_names]},
                        fields=["name", *LEARNING_STANDARD_CATALOG_FIELDS],
                        limit=0,
                    )
                    or []
                )
            )
            if row.get("learning_standard")
        }

    seen: set[str] = set()
    resolved_rows: list[dict[str, str | None]] = []
    for row in rows:
        normalized_row = {
            "coverage_level": normalize_text((row or {}).get("coverage_level")) or None,
            "alignment_strength": normalize_text((row or {}).get("alignment_strength")) or None,
            "notes": normalize_long_text((row or {}).get("notes")),
        }
        if not any(normalized_row.values()) and not any(
            normalize_text((row or {}).get(fieldname))
            or (normalize_long_text((row or {}).get(fieldname)) if fieldname == "standard_description" else None)
            for fieldname in ("learning_standard", *LEARNING_STANDARD_CATALOG_FIELDS)
        ):
            continue

        catalog_row = _resolve_unit_standard_catalog_row(row, linked_rows)
        learning_standard = catalog_row.get("learning_standard")
        if not learning_standard:
            frappe.throw(_("Each standards alignment row must select an existing Learning Standard."))
        if learning_standard in seen:
            frappe.throw(
                _("Learning Standard {0} is already aligned to this unit.").format(
                    catalog_row.get("standard_code") or learning_standard,
                ),
                frappe.ValidationError,
            )
        seen.add(learning_standard)
        resolved_rows.append(
            {
                "learning_standard": learning_standard,
                **{fieldname: catalog_row.get(fieldname) for fieldname in LEARNING_STANDARD_CATALOG_FIELDS},
                **normalized_row,
            }
        )

    doc.set("standards", resolved_rows)


def replace_unit_plan_reflections(doc, rows: Iterable[dict] | None, *, course_plan_row: dict | None = None) -> None:
    defaults = course_plan_row or {}
    default_year = normalize_text(defaults.get("academic_year")) or None
    default_school = normalize_text(defaults.get("school")) or None

    sanitized: list[dict] = []
    for row in rows or []:
        payload = {
            "academic_year": normalize_text((row or {}).get("academic_year")) or default_year,
            "school": normalize_text((row or {}).get("school")) or default_school,
            "prior_to_the_unit": normalize_rich_text((row or {}).get("prior_to_the_unit")),
            "during_the_unit": normalize_rich_text((row or {}).get("during_the_unit")),
            "what_work_well": normalize_rich_text((row or {}).get("what_work_well")),
            "what_didnt_work_well": normalize_rich_text((row or {}).get("what_didnt_work_well")),
            "changes_suggestions": normalize_rich_text((row or {}).get("changes_suggestions")),
        }
        if not any(
            payload.get(fieldname)
            for fieldname in (
                "academic_year",
                "school",
                "prior_to_the_unit",
                "during_the_unit",
                "what_work_well",
                "what_didnt_work_well",
                "changes_suggestions",
            )
        ):
            continue
        sanitized.append(payload)
    doc.set("reflections", sanitized)
