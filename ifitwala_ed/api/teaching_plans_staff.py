from __future__ import annotations

from collections import defaultdict
from typing import Any


def _ordered_unit_plans(api, units: list[dict[str, Any]]) -> list[str]:
    ranked = sorted(
        [unit for unit in units or [] if api.planning.normalize_text(unit.get("unit_plan"))],
        key=lambda unit: (
            int(unit.get("unit_order") or 0) <= 0,
            int(unit.get("unit_order") or 0),
            api.planning.normalize_text(unit.get("unit_plan")),
        ),
    )
    return [api.planning.normalize_text(unit.get("unit_plan")) for unit in ranked]


def _decorate_resolved_pacing_statuses(
    api,
    units: list[dict[str, Any]],
    current_unit_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    current_unit_plan = api.planning.normalize_text((current_unit_payload or {}).get("unit_plan"))
    ordered_unit_plans = _ordered_unit_plans(api, units)
    unit_rank = {unit_plan: index for index, unit_plan in enumerate(ordered_unit_plans)}
    current_index = unit_rank.get(current_unit_plan, -1)

    decorated: list[dict[str, Any]] = []
    for unit in units or []:
        unit_plan = api.planning.normalize_text(unit.get("unit_plan"))
        stored_status = api.planning.normalize_text(unit.get("pacing_status"))
        resolved_status = stored_status or "Not Started"

        if stored_status == "Hold":
            resolved_status = "Hold"
        elif current_index >= 0 and unit_plan in unit_rank:
            unit_index = unit_rank[unit_plan]
            if unit_index < current_index:
                resolved_status = "Completed"
            elif unit_index == current_index:
                resolved_status = "In Progress"
            else:
                resolved_status = "Not Started"

        decorated.append(
            {
                **unit,
                "resolved_pacing_status": resolved_status,
            }
        )

    return decorated


def resolve_staff_plan(
    api,
    student_group: str,
    requested_plan: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str | None]:
    group = api._group_context(student_group)
    course_plans = api.frappe.get_all(
        "Course Plan",
        filters={"course": group["course"], "plan_status": "Active"},
        fields=["name", "title", "academic_year", "cycle_label", "plan_status"],
        order_by="modified desc, creation desc",
        limit=50,
    )
    class_plans = api.frappe.get_all(
        "Class Teaching Plan",
        filters={"student_group": student_group},
        fields=["name", "title", "course_plan", "planning_status"],
        order_by="modified desc, creation desc",
        limit=50,
    )

    selected = api.planning.normalize_text(requested_plan)
    if selected and not any(row.get("name") == selected for row in class_plans):
        api.frappe.throw(
            api._("Selected class teaching plan does not belong to this class."), api.frappe.PermissionError
        )
    if not selected and len(class_plans) == 1:
        selected = class_plans[0]["name"]
    return group, course_plans, class_plans, selected or None


def build_staff_bundle(
    api,
    student_group: str,
    class_teaching_plan: str | None = None,
) -> dict[str, Any]:
    group, course_plans, class_plans, resolved_plan = api._resolve_staff_plan(student_group, class_teaching_plan)

    payload: dict[str, Any] = {
        "meta": {
            "generated_at": api._serialize_scalar(api.now_datetime()),
            "student_group": student_group,
        },
        "group": {
            "student_group": group.get("name"),
            "title": group.get("student_group_name") or group.get("student_group_abbreviation") or group.get("name"),
            "course": group.get("course"),
            "academic_year": group.get("academic_year"),
        },
        "course_plans": [api._serialize_course_plan(row) for row in course_plans],
        "class_teaching_plans": [api._serialize_class_teaching_plan_row(row) for row in class_plans],
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

    doc = api.frappe.get_doc("Class Teaching Plan", resolved_plan)
    unit_lookup = api._build_unit_lookup(doc.course_plan, audience="staff")
    unit_rows = api._serialize_backbone_units(doc.name, unit_lookup, audience="staff")
    sessions = api._fetch_class_sessions(doc.name, audience="staff")
    assigned_work = api._fetch_assigned_work(doc.name, audience="staff")
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
    resource_bundle = api._attach_resources_and_work(
        units=decorated_units,
        course_plan=doc.course_plan,
        class_teaching_plan=doc.name,
        assigned_work=assigned_work,
        attachment_surface=api.PLANNING_ATTACHMENT_SURFACE,
    )
    course_plan_row = api.planning.get_course_plan_row(doc.course_plan)
    current_unit = api._resolve_current_curriculum_unit(
        decorated_units,
        course_plan_row=course_plan_row,
        student_group=student_group,
        class_unit_rows=doc.get("units") or [],
        anchor_date=api.now_datetime(),
    )
    decorated_units = api._decorate_resolved_pacing_statuses(decorated_units, current_unit)

    payload["teaching_plan"] = {
        "class_teaching_plan": doc.name,
        "title": doc.title,
        "course_plan": doc.course_plan,
        "planning_status": doc.planning_status,
        "team_note": doc.team_note,
    }
    payload["resolved"]["course_plan"] = doc.course_plan
    payload["resolved"]["unit_plan"] = current_unit.get("unit_plan")
    payload["resources"] = resource_bundle
    payload["curriculum"] = {
        "units": decorated_units,
        "session_count": len(sessions),
        "assigned_work_count": len(assigned_work),
    }
    return payload


def build_staff_course_plan_bundle(
    api,
    course_plan: str,
    unit_plan: str | None = None,
    quiz_question_bank: str | None = None,
    student_group: str | None = None,
) -> dict[str, Any]:
    context = api._resolve_planning_resource_anchor("Course Plan", course_plan, ptype="read")
    course_plan_row = api.planning.get_course_plan_row(context["anchor_name"])
    course_plan_doc = api.frappe.get_doc("Course Plan", context["anchor_name"])
    course_row = (
        api.frappe.db.get_value(
            "Course",
            course_plan_row.get("course"),
            ["course_name", "course_group"],
            as_dict=True,
        )
        or {}
    )
    unit_lookup = api._build_unit_lookup(course_plan_doc.name, audience="staff")
    materials_by_anchor = api._fetch_material_map(
        [("Course Plan", course_plan_doc.name), *[("Unit Plan", name) for name in unit_lookup.keys()]],
        attachment_surface=api.PLANNING_ATTACHMENT_SURFACE,
    )
    unit_rows = list(unit_lookup.values())
    if not all(
        api.planning.normalize_text((row or {}).get("name") or (row or {}).get("unit_plan")) for row in unit_rows
    ):
        unit_rows = None
    units = api._serialize_governed_units(
        course_plan_doc.name,
        unit_lookup,
        materials_by_anchor,
        unit_rows=unit_rows,
    )
    timeline = api._build_course_plan_timeline(
        course_plan_row,
        units,
        student_group=api.planning.normalize_text(student_group) or None,
    )
    timeline_current_unit = next(
        (row for row in (timeline.get("units") or []) if int(row.get("is_current") or 0) == 1),
        None,
    )
    selected_unit = api.planning.normalize_text(unit_plan)
    if selected_unit and not any(row.get("unit_plan") == selected_unit for row in units):
        api.frappe.throw(api._("Selected unit plan does not belong to this course plan."), api.frappe.PermissionError)
    if not selected_unit and units:
        selected_unit = api.planning.normalize_text((timeline_current_unit or {}).get("unit_plan")) or units[0].get(
            "unit_plan"
        )
    quiz_question_banks = api._fetch_course_quiz_question_banks(course_plan_row.get("course"))
    selected_quiz_question_bank = api.planning.normalize_text(quiz_question_bank)
    if selected_quiz_question_bank and not any(
        row.get("quiz_question_bank") == selected_quiz_question_bank for row in quiz_question_banks
    ):
        api.frappe.throw(
            api._("Selected quiz question bank does not belong to this course."),
            api.frappe.PermissionError,
        )
    if not selected_quiz_question_bank and quiz_question_banks:
        selected_quiz_question_bank = quiz_question_banks[0].get("quiz_question_bank")

    academic_year_options = api._fetch_academic_year_options_for_schools([course_plan_row.get("school")]).get(
        api.planning.normalize_text(course_plan_row.get("school")), []
    )
    program_options = api._fetch_program_options_for_course(course_plan_row.get("course"))

    return {
        "meta": {
            "generated_at": api._serialize_scalar(api.now_datetime()),
            "course_plan": course_plan_doc.name,
        },
        "course_plan": api._serialize_course_plan_summary(
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
            "timeline": timeline,
        },
        "assessment": {
            "quiz_question_banks": quiz_question_banks,
            "selected_quiz_question_bank": api._fetch_selected_quiz_question_bank(
                selected_quiz_question_bank,
                expected_course=course_plan_row.get("course"),
            ),
        },
    }


def list_staff_course_plans_payload(api) -> dict[str, Any]:
    user = api._require_logged_in_user()
    roles = set(api.frappe.get_roles(user))
    creation_access = api._build_course_plan_creation_access(user, roles)
    filters: dict[str, Any] = {"plan_status": ["!=", "Archived"]}
    if api.planning.user_has_global_curriculum_access(user, roles):
        rows = api.frappe.get_list(
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
                "rollover_source_course_plan",
            ],
            order_by="modified desc, creation desc",
            limit=0,
        )
    else:
        managed_courses = api.planning.get_curriculum_manageable_course_names(user, roles)
        if managed_courses:
            filters["course"] = ["in", managed_courses]
            rows = api.frappe.get_list(
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
                    "rollover_source_course_plan",
                ],
                order_by="modified desc, creation desc",
                limit=0,
            )
        else:
            rows = []
    if "Curriculum Coordinator" not in roles:
        rows = [
            row
            for row in rows or []
            if not (
                api.planning.normalize_text(row.get("plan_status")) == "Draft"
                and api.planning.normalize_text(row.get("rollover_source_course_plan"))
            )
        ]
    course_names = sorted({row.get("course") for row in rows if row.get("course")})
    course_map = {
        row.get("name"): row
        for row in api.frappe.get_all(
            "Course",
            filters={"name": ["in", course_names]} if course_names else {"name": ["in", [""]]},
            fields=["name", "course_name", "course_group"],
            limit=0,
        )
    }
    payload = []
    for row in rows or []:
        payload.append(
            api._serialize_course_plan_summary(
                row,
                course_row=course_map.get(row.get("course")),
                can_manage_resources=int(
                    api.planning.user_can_manage_course_curriculum(user, row.get("course"), roles)
                ),
            )
        )
    return {
        "meta": {
            "generated_at": api._serialize_scalar(api.now_datetime()),
        },
        "access": {
            "can_create_course_plans": creation_access["can_create_course_plans"],
            "create_block_reason": creation_access["create_block_reason"],
        },
        "course_options": creation_access["course_options"],
        "course_plans": payload,
    }
