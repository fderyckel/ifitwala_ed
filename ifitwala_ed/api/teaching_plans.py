from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from time import perf_counter
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime, strip_html

from ifitwala_ed.api import teaching_plans_mutations as _mutations_impl
from ifitwala_ed.api import teaching_plans_read_models as _read_models_impl
from ifitwala_ed.api import teaching_plans_shared as _shared_impl
from ifitwala_ed.api import teaching_plans_staff as _staff_impl
from ifitwala_ed.api import teaching_plans_student as _student_impl
from ifitwala_ed.api import teaching_plans_timeline as _timeline_impl
from ifitwala_ed.api.file_access import (
    get_academic_file_thumbnail_ready_map,
    resolve_academic_file_open_url,
    resolve_academic_file_preview_url,
    resolve_academic_file_thumbnail_url,
)
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

_COMPAT_EXPORTS = (
    _,
    TRIAGE_ROLES,
    _instructor_group_names,
    defaultdict,
    get_datetime,
    getdate,
    now_datetime,
    strip_html,
    get_academic_file_thumbnail_ready_map,
    resolve_academic_file_open_url,
    resolve_academic_file_preview_url,
    resolve_academic_file_thumbnail_url,
    quiz_service,
    materials_domain,
    governed_uploads,
    hashlib,
    json,
)


def _module():
    return sys.modules[__name__]


def _serialize_scalar(value: Any) -> Any:
    return _shared_impl.serialize_scalar(_module(), value)


def _normalize_payload(value) -> dict[str, Any]:
    return _shared_impl.normalize_payload(_module(), value)


def _normalize_rows_payload(value, *, label: str) -> list[dict[str, Any]]:
    return _shared_impl.normalize_rows_payload(_module(), value, label=label)


def _require_logged_in_user() -> str:
    return _shared_impl.require_logged_in_user(_module())


def _resolve_planning_resource_anchor(anchor_doctype: str, anchor_name: str, *, ptype: str = "write") -> dict[str, Any]:
    return _shared_impl.resolve_planning_resource_anchor(_module(), anchor_doctype, anchor_name, ptype=ptype)


def _assert_staff_group_access(student_group: str) -> None:
    _shared_impl.assert_staff_group_access(_module(), student_group)


def _assert_course_curriculum_access(
    course: str,
    *,
    ptype: str = "write",
    action_label: str | None = None,
) -> tuple[str, set[str]]:
    return _shared_impl.assert_course_curriculum_access(
        _module(),
        course,
        ptype=ptype,
        action_label=action_label,
    )


def _require_student_name() -> str:
    return _shared_impl.require_student_name(_module())


def _assert_student_course_access(student_name: str, course_id: str) -> None:
    _shared_impl.assert_student_course_access(_module(), student_name, course_id)


def _assert_student_group_membership(student_name: str, student_group: str) -> None:
    _shared_impl.assert_student_group_membership(_module(), student_name, student_group)


def _group_context(student_group: str) -> dict:
    return _shared_impl.group_context(_module(), student_group)


def _serialize_course_plan(row: dict) -> dict[str, Any]:
    return _shared_impl.serialize_course_plan(_module(), row)


def _serialize_course_plan_summary(
    row: dict, *, course_row: dict | None = None, can_manage_resources: int = 0
) -> dict[str, Any]:
    return _shared_impl.serialize_course_plan_summary(
        _module(),
        row,
        course_row=course_row,
        can_manage_resources=can_manage_resources,
    )


def _timeline_blocked(reason: str, message: str) -> dict[str, Any]:
    return _timeline_impl.timeline_blocked(_module(), reason, message)


def _timeline_weekday_js(value: date) -> int:
    return _timeline_impl.timeline_weekday_js(_module(), value)


def _timeline_duration_weeks(value: str | None) -> int | None:
    return _timeline_impl.timeline_duration_weeks(_module(), value)


def _coerce_curriculum_anchor_date(value: Any | None = None) -> date:
    return _timeline_impl.coerce_curriculum_anchor_date(_module(), value)


def _resolve_course_plan_timeline_scope(
    course_plan_row: dict[str, Any],
    *,
    student_group: str | None = None,
) -> dict[str, Any]:
    return _timeline_impl.resolve_course_plan_timeline_scope(
        _module(),
        course_plan_row,
        student_group=student_group,
    )


def _fetch_timeline_calendar_terms(
    school_calendar: str,
    *,
    window_start: date,
    window_end: date,
) -> list[dict[str, Any]]:
    return _timeline_impl.fetch_timeline_calendar_terms(
        _module(),
        school_calendar,
        window_start=window_start,
        window_end=window_end,
    )


def _fetch_timeline_holiday_spans(
    school_calendar: str,
    *,
    window_start: date,
    window_end: date,
    weekend_days: list[int] | tuple[int, ...] | set[int] | None = None,
) -> list[dict[str, Any]]:
    return _timeline_impl.fetch_timeline_holiday_spans(
        _module(),
        school_calendar,
        window_start=window_start,
        window_end=window_end,
        weekend_days=weekend_days,
    )


def _build_course_plan_timeline(
    course_plan_row: dict[str, Any],
    units: list[dict[str, Any]],
    *,
    student_group: str | None = None,
) -> dict[str, Any]:
    return _timeline_impl.build_course_plan_timeline(
        _module(),
        course_plan_row,
        units,
        student_group=student_group,
    )


def _resolve_timeline_current_unit(
    timeline: dict[str, Any],
    *,
    anchor_date: Any | None = None,
) -> dict[str, Any] | None:
    return _timeline_impl.resolve_timeline_current_unit(
        _module(),
        timeline,
        anchor_date=anchor_date,
    )


def _resolve_current_curriculum_unit(
    units: list[dict[str, Any]],
    *,
    course_plan_row: dict[str, Any] | None = None,
    student_group: str | None = None,
    class_unit_rows: list[Any] | None = None,
    anchor_date: Any | None = None,
    allow_live_session: bool = True,
) -> dict[str, Any]:
    return _timeline_impl.resolve_current_curriculum_unit(
        _module(),
        units,
        course_plan_row=course_plan_row,
        student_group=student_group,
        class_unit_rows=class_unit_rows,
        anchor_date=anchor_date,
        allow_live_session=allow_live_session,
    )


def _serialize_class_teaching_plan_row(row: dict) -> dict[str, Any]:
    return _shared_impl.serialize_class_teaching_plan_row(_module(), row)


def _serialize_course_option(
    row: dict[str, Any], *, academic_year_options: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return _shared_impl.serialize_course_option(_module(), row, academic_year_options=academic_year_options)


def _serialize_academic_year_option(row: dict[str, Any]) -> dict[str, Any]:
    return _shared_impl.serialize_academic_year_option(_module(), row)


def _serialize_program_option(row: dict[str, Any]) -> dict[str, Any]:
    return _shared_impl.serialize_program_option(_module(), row)


def _academic_year_scope_for_school(school: str | None) -> list[str]:
    return _shared_impl.academic_year_scope_for_school(_module(), school)


def _fetch_academic_year_options_for_schools(
    schools: list[str] | tuple[str, ...],
    *,
    pinned_years: dict[str, str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    return _shared_impl.fetch_academic_year_options_for_schools(
        _module(),
        schools,
        pinned_years=pinned_years,
    )


def _fetch_program_options_for_course(
    course: str | None,
    *,
    pinned_programs: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    return _shared_impl.fetch_program_options_for_course(
        _module(),
        course,
        pinned_programs=pinned_programs,
    )


def _validate_course_plan_academic_year(
    *,
    course_school: str | None,
    academic_year: str | None,
    previous_academic_year: str | None = None,
) -> None:
    _shared_impl.validate_course_plan_academic_year(
        _module(),
        course_school=course_school,
        academic_year=academic_year,
        previous_academic_year=previous_academic_year,
    )


def _validate_course_program_link(
    *,
    course: str | None,
    program: str | None,
    previous_program: str | None = None,
) -> None:
    _shared_impl.validate_course_program_link(
        _module(),
        course=course,
        program=program,
        previous_program=previous_program,
    )


def _quiz_question_bank_record_modified(bank_row: dict | None, question_rows: list[dict[str, Any]] | None) -> str:
    return _shared_impl.quiz_question_bank_record_modified(_module(), bank_row, question_rows)


def _payload_size_bytes(payload: dict[str, Any] | None) -> int | None:
    return _shared_impl.payload_size_bytes(_module(), payload)


def _current_db_query_count() -> int | None:
    return _shared_impl.current_db_query_count(_module())


def _db_query_delta(started_count: int | None) -> int | None:
    return _shared_impl.db_query_delta(_module(), started_count)


def _log_planning_event(
    event: str,
    *,
    started_at: float | None = None,
    warning: bool = False,
    **context,
) -> None:
    _shared_impl.log_planning_event(
        _module(),
        event,
        started_at=started_at,
        warning=warning,
        **context,
    )


def _list_creatable_course_rows(user: str, roles: set[str]) -> list[dict[str, Any]]:
    return _shared_impl.list_creatable_course_rows(_module(), user, roles)


def _build_course_plan_creation_access(user: str, roles: set[str]) -> dict[str, Any]:
    return _shared_impl.build_course_plan_creation_access(_module(), user, roles)


def _serialize_material_entry(
    entry: dict[str, Any], *, thumbnail_ready_map: dict[str, bool] | None = None
) -> dict[str, Any]:
    return _read_models_impl.serialize_material_entry(_module(), entry, thumbnail_ready_map=thumbnail_ready_map)


def _fetch_course_quiz_question_banks(course: str | None) -> list[dict[str, Any]]:
    return _read_models_impl.fetch_course_quiz_question_banks(_module(), course)


def _fetch_selected_quiz_question_bank(
    question_bank: str | None,
    *,
    expected_course: str | None = None,
) -> dict[str, Any] | None:
    return _read_models_impl.fetch_selected_quiz_question_bank(
        _module(),
        question_bank,
        expected_course=expected_course,
    )


def _reload_anchor_material(anchor_doctype: str, anchor_name: str, material_name: str) -> dict[str, Any]:
    return _read_models_impl.reload_anchor_material(_module(), anchor_doctype, anchor_name, material_name)


def _fetch_material_map(anchor_refs: list[tuple[str, str]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    return _read_models_impl.fetch_material_map(_module(), anchor_refs)


def _fetch_assigned_work(
    class_teaching_plan: str,
    *,
    audience: str = "staff",
    student_name: str | None = None,
) -> list[dict[str, Any]]:
    return _read_models_impl.fetch_assigned_work(
        _module(),
        class_teaching_plan,
        audience=audience,
        student_name=student_name,
    )


def _fetch_class_sessions(class_teaching_plan: str, audience: str = "staff") -> list[dict[str, Any]]:
    return _read_models_impl.fetch_class_sessions(_module(), class_teaching_plan, audience=audience)


def _serialize_standards_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _read_models_impl.serialize_standards_rows(_module(), rows)


def _serialize_reflection_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _read_models_impl.serialize_reflection_rows(_module(), rows)


def _has_reflection_content(row: dict[str, Any]) -> bool:
    return _read_models_impl.has_reflection_content(_module(), row)


def _fetch_unit_child_rows(
    child_doctype: str,
    unit_names: list[str],
    *,
    parentfield: str,
    fields: list[str],
) -> dict[str, list[dict[str, Any]]]:
    return _read_models_impl.fetch_unit_child_rows(
        _module(),
        child_doctype,
        unit_names,
        parentfield=parentfield,
        fields=fields,
    )


def _build_unit_lookup(course_plan: str, audience: str = "staff") -> dict[str, dict[str, Any]]:
    return _read_models_impl.build_unit_lookup(_module(), course_plan, audience=audience)


def _serialize_backbone_units(
    class_teaching_plan: str,
    unit_lookup: dict[str, dict[str, Any]],
    audience: str = "staff",
) -> list[dict[str, Any]]:
    return _read_models_impl.serialize_backbone_units(
        _module(),
        class_teaching_plan,
        unit_lookup,
        audience=audience,
    )


def _serialize_governed_units(
    course_plan: str,
    unit_lookup: dict[str, dict[str, Any]],
    materials_by_anchor: dict[tuple[str, str], list[dict[str, Any]]],
    *,
    unit_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    return _read_models_impl.serialize_governed_units(
        _module(),
        course_plan,
        unit_lookup,
        materials_by_anchor,
        unit_rows=unit_rows,
    )


def _index_sessions_by_name(units: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return _read_models_impl.index_sessions_by_name(_module(), units)


def _attach_resources_and_work(
    *,
    units: list[dict[str, Any]],
    course_plan: str | None = None,
    class_teaching_plan: str | None = None,
    assigned_work: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    return _read_models_impl.attach_resources_and_work(
        _module(),
        units=units,
        course_plan=course_plan,
        class_teaching_plan=class_teaching_plan,
        assigned_work=assigned_work,
    )


def _coerce_learning_datetime(value: Any) -> datetime | None:
    return _student_impl.coerce_learning_datetime(_module(), value)


def _iter_learning_sessions(units: list[dict[str, Any]]):
    return _student_impl.iter_learning_sessions(_module(), units)


def _flatten_assigned_work(
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    return _student_impl.flatten_assigned_work(_module(), units, general_assigned_work)


def _resolve_student_learning_focus(
    units: list[dict[str, Any]],
    preferred_unit_plan: str | None = None,
    *,
    anchor_date: Any | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    return _student_impl.resolve_student_learning_focus(
        _module(),
        units,
        preferred_unit_plan,
        anchor_date=anchor_date,
    )


def _build_student_focus_statement(unit: dict[str, Any] | None, session: dict[str, Any] | None) -> str | None:
    return _student_impl.build_student_focus_statement(_module(), unit, session)


def _build_student_learning_focus(
    units: list[dict[str, Any]],
    current_unit_plan: str | None = None,
    *,
    anchor_date: Any | None = None,
) -> dict[str, Any]:
    return _student_impl.build_student_learning_focus(
        _module(),
        units,
        current_unit_plan,
        anchor_date=anchor_date,
    )


def _build_student_unit_navigation(
    units: list[dict[str, Any]],
    current_unit_plan: str | None,
) -> list[dict[str, Any]]:
    return _student_impl.build_student_unit_navigation(_module(), units, current_unit_plan)


def _build_student_next_actions(
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    return _student_impl.build_student_next_actions(_module(), units, general_assigned_work)


def _build_student_learning_sections(
    units: list[dict[str, Any]],
    general_assigned_work: list[dict[str, Any]] | None,
    reflection_entries: list[dict[str, Any]] | None = None,
    current_unit_plan: str | None = None,
    *,
    anchor_date: Any | None = None,
) -> dict[str, Any]:
    return _student_impl.build_student_learning_sections(
        _module(),
        units,
        general_assigned_work,
        reflection_entries,
        current_unit_plan,
        anchor_date=anchor_date,
    )


def _fetch_student_learning_reflections(
    student_name: str,
    *,
    course_id: str,
    student_group: str | None = None,
    academic_year: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    return _student_impl.fetch_student_learning_reflections(
        _module(),
        student_name,
        course_id=course_id,
        student_group=student_group,
        academic_year=academic_year,
        limit=limit,
    )


def _build_student_learning_space_payload(
    student_name: str,
    course_id: str,
    student_group: str | None = None,
) -> dict[str, Any]:
    return _student_impl.build_student_learning_space_payload(
        _module(),
        student_name,
        course_id,
        student_group=student_group,
    )


def _resolve_staff_plan(
    student_group: str,
    requested_plan: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str | None]:
    return _staff_impl.resolve_staff_plan(_module(), student_group, requested_plan)


def _build_staff_bundle(student_group: str, class_teaching_plan: str | None = None) -> dict[str, Any]:
    return _staff_impl.build_staff_bundle(_module(), student_group, class_teaching_plan=class_teaching_plan)


def _build_staff_course_plan_bundle(
    course_plan: str,
    unit_plan: str | None = None,
    quiz_question_bank: str | None = None,
    student_group: str | None = None,
) -> dict[str, Any]:
    return _staff_impl.build_staff_course_plan_bundle(
        _module(),
        course_plan,
        unit_plan=unit_plan,
        quiz_question_bank=quiz_question_bank,
        student_group=student_group,
    )


@frappe.whitelist()
def get_staff_class_planning_surface(student_group: str, class_teaching_plan: str | None = None) -> dict[str, Any]:
    _assert_staff_group_access(student_group)
    return _build_staff_bundle(student_group, class_teaching_plan=class_teaching_plan)


@frappe.whitelist()
def get_staff_course_plan_surface(
    course_plan: str,
    unit_plan: str | None = None,
    quiz_question_bank: str | None = None,
    student_group: str | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()
    status = "success"
    try:
        return _build_staff_course_plan_bundle(
            course_plan,
            unit_plan=unit_plan,
            quiz_question_bank=quiz_question_bank,
            student_group=student_group,
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
            student_group=planning.normalize_text(student_group),
        )


@frappe.whitelist()
def list_staff_course_plans() -> dict[str, Any]:
    started_at = perf_counter()
    status = "success"
    course_plan_count = 0
    course_option_count = 0
    try:
        payload = _staff_impl.list_staff_course_plans_payload(_module())
        course_plan_count = len(payload.get("course_plans") or [])
        course_option_count = len(payload.get("course_options") or [])
        return payload
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
        created = _mutations_impl.create_course_plan_impl(_module(), payload, **kwargs)
        course_name = planning.normalize_text(created.get("course"))
        created_name = planning.normalize_text(created.get("course_plan"))
        return created
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
    return _mutations_impl.create_class_teaching_plan_impl(_module(), student_group, course_plan)


@frappe.whitelist()
def save_class_teaching_plan(
    class_teaching_plan: str,
    planning_status: str | None = None,
    team_note: str | None = None,
) -> dict[str, Any]:
    return _mutations_impl.save_class_teaching_plan_impl(
        _module(),
        class_teaching_plan,
        planning_status=planning_status,
        team_note=team_note,
    )


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
    return _mutations_impl.save_class_teaching_plan_unit_impl(
        _module(),
        class_teaching_plan,
        unit_plan,
        pacing_status=pacing_status,
        teacher_focus=teacher_focus,
        pacing_note=pacing_note,
        prior_to_the_unit=prior_to_the_unit,
        during_the_unit=during_the_unit,
        what_work_well=what_work_well,
        what_didnt_work_well=what_didnt_work_well,
        changes_suggestions=changes_suggestions,
    )


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
    return _mutations_impl.save_class_session_impl(
        _module(),
        class_teaching_plan,
        unit_plan,
        title,
        session_status=session_status,
        session_date=session_date,
        sequence_index=sequence_index,
        learning_goal=learning_goal,
        teacher_note=teacher_note,
        activities_json=activities_json,
        class_session=class_session,
    )


@frappe.whitelist()
def save_course_plan(payload=None, **kwargs) -> dict[str, Any]:
    started_at = perf_counter()
    status = "success"
    course_plan_name = ""
    try:
        if payload is not None or kwargs:
            data = _normalize_payload(payload if payload is not None else kwargs)
            course_plan_name = planning.normalize_text(data.get("course_plan"))
        return _mutations_impl.save_course_plan_impl(_module(), payload, **kwargs)
    except Exception:
        status = "error"
        raise
    finally:
        _log_planning_event(
            "course_plan_save",
            started_at=started_at,
            status=status,
            course_plan=course_plan_name,
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
    result = None
    try:
        result = _mutations_impl.save_unit_plan_impl(
            _module(),
            payload,
            course_plan=course_plan,
            unit_plan=unit_plan,
            title=title,
            program=program,
            unit_code=unit_code,
            unit_order=unit_order,
            unit_status=unit_status,
            version=version,
            duration=duration,
            estimated_duration=estimated_duration,
            is_published=is_published,
            expected_modified=expected_modified,
            overview=overview,
            essential_understanding=essential_understanding,
            misconceptions=misconceptions,
            content=content,
            skills=skills,
            concepts=concepts,
            standards_json=standards_json,
            reflections_json=reflections_json,
            **kwargs,
        )
        return result
    except Exception:
        status = "error"
        raise
    finally:
        _log_planning_event(
            "unit_plan_save",
            started_at=started_at,
            status=status,
            course_plan=planning.normalize_text((result or {}).get("course_plan")),
            unit_plan=planning.normalize_text((result or {}).get("unit_plan")),
        )


@frappe.whitelist()
def create_planning_reference_material(payload=None, **kwargs) -> dict[str, Any]:
    return _mutations_impl.create_planning_reference_material_impl(_module(), payload, **kwargs)


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
    return _mutations_impl.upload_planning_material_file_impl(
        _module(),
        anchor_doctype=anchor_doctype,
        anchor_name=anchor_name,
        title=title,
        description=description,
        modality=modality,
        usage_role=usage_role,
        placement_note=placement_note,
    )


@frappe.whitelist()
def remove_planning_material(payload=None, **kwargs) -> dict[str, Any]:
    return _mutations_impl.remove_planning_material_impl(_module(), payload, **kwargs)


def _resolve_student_group_options(student_name: str, course_id: str) -> list[dict[str, Any]]:
    return _student_impl.resolve_student_group_options(_module(), student_name, course_id)


def _resolve_student_plan(course_id: str, student_groups: list[dict[str, Any]], requested_group: str | None):
    return _student_impl.resolve_student_plan(_module(), course_id, student_groups, requested_group)


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
