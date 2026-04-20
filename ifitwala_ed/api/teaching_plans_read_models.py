from __future__ import annotations

from typing import Any

from ifitwala_ed.api.attachment_previews import build_attachment_preview_item, extract_file_extension
from ifitwala_ed.utilities.html_sanitizer import sanitize_html


def _material_thumbnail_ready_map(api, entries: list[dict[str, Any]]) -> dict[str, bool]:
    file_names = [
        str(entry.get("file") or "").strip()
        for entry in entries or []
        if entry.get("material_type") == api.materials_domain.MATERIAL_TYPE_FILE
        and str(entry.get("file") or "").strip()
    ]
    return api.get_academic_file_thumbnail_ready_map(file_names)


def serialize_material_entry(
    api,
    entry: dict[str, Any],
    *,
    thumbnail_ready_map: dict[str, bool] | None = None,
) -> dict[str, Any]:
    placement = (entry.get("placements") or [{}])[0]
    material_type = entry.get("material_type")
    owner_doctype = "Material Placement" if placement.get("placement") else "Supporting Material"
    owner_name = placement.get("placement") or entry.get("material")
    if material_type == api.materials_domain.MATERIAL_TYPE_FILE:
        resolved_file_id = entry.get("file")
        resolved_file_name = str(entry.get("file") or "").strip()
        thumbnail_url = api.resolve_academic_file_thumbnail_url(
            file_name=entry.get("file"),
            file_url=entry.get("file_url"),
            context_doctype="Material Placement" if placement.get("placement") else "Supporting Material",
            context_name=placement.get("placement") or entry.get("material"),
            thumbnail_ready=(
                thumbnail_ready_map.get(resolved_file_name)
                if thumbnail_ready_map is not None and resolved_file_name
                else None
            ),
        )
        preview_url = api.resolve_academic_file_preview_url(
            file_name=entry.get("file"),
            file_url=entry.get("file_url"),
            context_doctype="Material Placement" if placement.get("placement") else "Supporting Material",
            context_name=placement.get("placement") or entry.get("material"),
        )
        open_url = api.resolve_academic_file_open_url(
            file_name=entry.get("file"),
            file_url=entry.get("file_url"),
            context_doctype="Material Placement" if placement.get("placement") else "Supporting Material",
            context_name=placement.get("placement") or entry.get("material"),
        )
        attachment_preview = build_attachment_preview_item(
            item_id=owner_name,
            owner_doctype=owner_doctype,
            owner_name=owner_name,
            file_id=resolved_file_id,
            display_name=entry.get("title"),
            description=entry.get("description"),
            extension=extract_file_extension(file_name=entry.get("file_name"), file_url=entry.get("file_url")),
            size_bytes=entry.get("file_size"),
            thumbnail_url=thumbnail_url,
            preview_url=preview_url,
            open_url=open_url,
            download_url=open_url,
        )
    else:
        thumbnail_url = None
        preview_url = None
        open_url = entry.get("reference_url")
        attachment_preview = build_attachment_preview_item(
            item_id=owner_name,
            owner_doctype=owner_doctype,
            owner_name=owner_name,
            link_url=entry.get("reference_url"),
            display_name=entry.get("title"),
            description=entry.get("description"),
            open_url=open_url,
        )

    return {
        "material": entry.get("material"),
        "title": entry.get("title"),
        "material_type": material_type,
        "modality": entry.get("modality"),
        "description": entry.get("description"),
        "reference_url": entry.get("reference_url"),
        "thumbnail_url": thumbnail_url,
        "preview_url": preview_url,
        "open_url": open_url,
        "file_name": entry.get("file_name"),
        "file_size": entry.get("file_size"),
        "placement": placement.get("placement"),
        "origin": placement.get("origin"),
        "usage_role": placement.get("usage_role"),
        "placement_note": placement.get("placement_note"),
        "placement_order": placement.get("placement_order"),
        "attachment_preview": attachment_preview,
    }


def fetch_course_quiz_question_banks(api, course: str | None) -> list[dict[str, Any]]:
    course_name = api.planning.normalize_text(course)
    if not course_name:
        return []

    rows = api.frappe.get_all(
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
        for row in api.frappe.db.sql(
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


def fetch_selected_quiz_question_bank(
    api,
    question_bank: str | None,
    *,
    expected_course: str | None = None,
) -> dict[str, Any] | None:
    question_bank_name = api.planning.normalize_text(question_bank)
    if not question_bank_name:
        return None

    bank = api.frappe.db.get_value(
        "Quiz Question Bank",
        question_bank_name,
        ["name", "modified", "bank_title", "course", "is_published", "description"],
        as_dict=True,
    )
    if not bank:
        api.frappe.throw(api._("Selected quiz question bank was not found."), api.frappe.DoesNotExistError)

    course_name = api.planning.normalize_text(expected_course)
    if course_name and api.planning.normalize_text(bank.get("course")) != course_name:
        api.frappe.throw(
            api._("Selected quiz question bank does not belong to this course."), api.frappe.PermissionError
        )

    question_rows = api.frappe.get_all(
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
    option_rows = api.frappe.get_all(
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
    options_by_parent: dict[str, list[dict[str, Any]]] = api.defaultdict(list)
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
        "record_modified": api._quiz_question_bank_record_modified(bank, question_rows),
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


def reload_anchor_material(api, anchor_doctype: str, anchor_name: str, material_name: str) -> dict[str, Any]:
    rows = api.materials_domain.list_anchor_materials(anchor_doctype, anchor_name)
    created = next((row for row in rows if row.get("material") == material_name), None)
    if not created:
        api.frappe.throw(api._("Material was created but could not be reloaded."))
    thumbnail_ready_map = _material_thumbnail_ready_map(api, rows)
    return api._serialize_material_entry(created, thumbnail_ready_map=thumbnail_ready_map)


def fetch_material_map(
    api,
    anchor_refs: list[tuple[str, str]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    material_map = api.materials_domain.list_materials_for_anchors(anchor_refs)
    thumbnail_ready_map = _material_thumbnail_ready_map(
        api,
        [entry for entries in material_map.values() for entry in (entries or [])],
    )
    return {
        anchor: [api._serialize_material_entry(entry, thumbnail_ready_map=thumbnail_ready_map) for entry in entries]
        for anchor, entries in material_map.items()
    }


def fetch_assigned_work(
    api,
    class_teaching_plan: str,
    *,
    audience: str = "staff",
    student_name: str | None = None,
) -> list[dict[str, Any]]:
    rows = api.frappe.db.sql(
        """
        SELECT
            td.name AS task_delivery,
            td.name AS delivery_name,
            td.task,
            td.class_session,
            td.delivery_mode,
            td.grading_mode,
            td.requires_submission,
            td.allow_late_submission,
            td.available_from,
            td.due_date,
            td.lock_date,
            td.quiz_question_bank,
            td.quiz_question_count,
            td.quiz_time_limit_minutes,
            td.quiz_max_attempts,
            td.quiz_pass_percentage,
            t.title,
            t.instructions,
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

    task_materials = api._fetch_material_map([("Task", row.get("task")) for row in rows if row.get("task")])
    outcomes_by_delivery: dict[str, dict[str, Any]] = {}
    quiz_state_by_delivery: dict[str, dict[str, Any]] = {}
    if audience == "student" and student_name:
        outcome_rows = api.frappe.get_all(
            "Task Outcome",
            filters={
                "student": student_name,
                "task_delivery": ["in", [row["task_delivery"] for row in rows if row.get("task_delivery")] or [""]],
            },
            fields=["name", "task_delivery", "submission_status", "grading_status", "is_complete", "is_published"],
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
        quiz_state_by_delivery = api.quiz_service.get_student_delivery_state_map(
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
            "instructions_html": sanitize_html(row.get("instructions") or "", allow_headings_from="h3"),
            "task_type": row.get("task_type"),
            "unit_plan": row.get("unit_plan"),
            "class_session": row.get("class_session"),
            "delivery_mode": row.get("delivery_mode"),
            "grading_mode": row.get("grading_mode"),
            "requires_submission": int(row.get("requires_submission") or 0),
            "allow_late_submission": int(row.get("allow_late_submission") or 0),
            "available_from": api._serialize_scalar(row.get("available_from")),
            "due_date": api._serialize_scalar(row.get("due_date")),
            "lock_date": api._serialize_scalar(row.get("lock_date")),
            "materials": task_materials.get(("Task", row.get("task")), []),
        }
        if audience == "student":
            outcome = outcomes_by_delivery.get(row.get("task_delivery"), {})
            item["task_outcome"] = outcome.get("name")
            item["submission_status"] = outcome.get("submission_status")
            item["grading_status"] = outcome.get("grading_status")
            item["is_complete"] = int(outcome.get("is_complete") or 0) if outcome else 0
            item["is_published"] = int(outcome.get("is_published") or 0) if outcome else 0
            item["quiz_state"] = quiz_state_by_delivery.get(row.get("task_delivery"))
        payload.append(item)
    return payload


def fetch_class_sessions(api, class_teaching_plan: str, audience: str = "staff") -> list[dict[str, Any]]:
    filters: dict[str, Any] = {"class_teaching_plan": class_teaching_plan}
    if audience == "student":
        filters["session_status"] = ["not in", ["Draft", "Canceled"]]

    sessions = api.frappe.get_all(
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
    activity_rows = api.frappe.db.sql(
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
    activities_by_parent: dict[str, list[dict[str, Any]]] = api.defaultdict(list)
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
            "session_date": api._serialize_scalar(session.get("session_date")),
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


def serialize_standards_rows(api, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "learning_standard",
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


def serialize_reflection_rows(api, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def has_reflection_content(api, row: dict[str, Any]) -> bool:
    return any(
        api.planning.normalize_text(row.get(fieldname))
        for fieldname in (
            "prior_to_the_unit",
            "during_the_unit",
            "what_work_well",
            "what_didnt_work_well",
            "changes_suggestions",
        )
    )


def fetch_unit_child_rows(
    api,
    child_doctype: str,
    unit_names: list[str],
    *,
    parentfield: str,
    fields: list[str],
) -> dict[str, list[dict[str, Any]]]:
    if not unit_names:
        return {}

    rows = api.frappe.get_all(
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
    rows_by_parent: dict[str, list[dict[str, Any]]] = api.defaultdict(list)
    for row in rows or []:
        parent = row.get("parent")
        if parent:
            rows_by_parent[parent].append(row)
    return rows_by_parent


def build_unit_lookup(api, course_plan: str, audience: str = "staff") -> dict[str, dict[str, Any]]:
    unit_rows = api.planning.get_unit_plan_rows(course_plan)
    unit_names = [row["name"] for row in unit_rows if row.get("name")]
    if not unit_names:
        return {}

    standards_rows = api._fetch_unit_child_rows(
        "Learning Unit Standard Alignment",
        unit_names,
        parentfield="standards",
        fields=[
            "learning_standard",
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
    reflection_rows = api._fetch_unit_child_rows(
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

    class_reflections_by_unit: dict[str, list[dict[str, Any]]] = api.defaultdict(list)
    if audience == "staff":
        rows = api.frappe.db.sql(
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
            if not api._has_reflection_content(row):
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
            "standards": api._serialize_standards_rows(standards_rows.get(unit_name, [])),
            "shared_reflections": api._serialize_reflection_rows(reflection_rows.get(unit_name, [])),
            "class_reflections": class_reflections_by_unit.get(unit_name, []),
        }
    return lookup


def serialize_backbone_units(
    api,
    class_teaching_plan: str,
    unit_lookup: dict[str, dict[str, Any]],
    audience: str = "staff",
) -> list[dict[str, Any]]:
    rows = api.frappe.get_all(
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


def serialize_governed_units(
    api,
    course_plan: str,
    unit_lookup: dict[str, dict[str, Any]],
    materials_by_anchor: dict[tuple[str, str], list[dict[str, Any]]],
    *,
    unit_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = unit_rows if unit_rows is not None else api.planning.get_unit_plan_rows(course_plan)
    payload: list[dict[str, Any]] = []
    for row in rows:
        unit_name = row.get("name") or row.get("unit_plan")
        unit_meta = unit_lookup.get(unit_name, row)
        payload.append(
            {
                "unit_plan": unit_name,
                "record_modified": api._serialize_scalar(unit_meta.get("modified")),
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


def index_sessions_by_name(api, units: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for unit in units:
        for session in unit.get("sessions") or []:
            if session.get("class_session"):
                lookup[session["class_session"]] = session
    return lookup


def attach_resources_and_work(
    api,
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

    materials_by_anchor = api._fetch_material_map(anchor_refs)
    session_lookup = api._index_sessions_by_name(units)
    for unit in units:
        unit["shared_resources"] = materials_by_anchor.get(("Unit Plan", unit.get("unit_plan")), [])
        for session in unit.get("sessions") or []:
            session["resources"] = materials_by_anchor.get(("Class Session", session.get("class_session")), [])

    for item in assigned_work or []:
        resolved_unit_plan = api.planning.normalize_text(item.get("unit_plan"))
        if not resolved_unit_plan and item.get("class_session"):
            resolved_unit_plan = api.planning.normalize_text(
                (session_lookup.get(item.get("class_session")) or {}).get("unit_plan")
            )
            item["unit_plan"] = resolved_unit_plan or item.get("unit_plan")

        if resolved_unit_plan:
            for unit in units:
                if api.planning.normalize_text(unit.get("unit_plan")) == resolved_unit_plan:
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
            if not api.planning.normalize_text(item.get("unit_plan"))
            and not api.planning.normalize_text(item.get("class_session"))
        ],
    }
