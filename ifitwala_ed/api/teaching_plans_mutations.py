from __future__ import annotations

from typing import Any


def create_course_plan_impl(api, payload=None, **kwargs) -> dict[str, Any]:
    user = api._require_logged_in_user()
    roles = set(api.frappe.get_roles(user))
    data = api._normalize_payload(payload if payload is not None else kwargs)
    course_name = api.planning.normalize_text(data.get("course"))
    if not course_name:
        api.frappe.throw(api._("Course is required."))

    allowed_courses = {row.get("name"): row for row in api._list_creatable_course_rows(user, roles) if row.get("name")}
    if not allowed_courses:
        api.frappe.throw(
            api._(
                "You need an active teaching assignment or curriculum leadership access before you can start a shared course plan."
            ),
            api.frappe.PermissionError,
        )
    course_row = allowed_courses.get(course_name)
    if not course_row:
        api.frappe.throw(api._("You cannot create a shared course plan for this course."), api.frappe.PermissionError)

    doc = api.frappe.new_doc("Course Plan")
    doc.course = course_name
    doc.title = api.planning.normalize_text(data.get("title")) or api._("{course_name} Plan").format(
        course_name=course_row.get("course_name") or course_name
    )
    doc.academic_year = api.planning.normalize_text(data.get("academic_year")) or None
    api._validate_course_plan_academic_year(
        course_school=course_row.get("school"),
        academic_year=doc.academic_year,
    )
    doc.cycle_label = api.planning.normalize_text(data.get("cycle_label")) or None
    if data.get("plan_status") not in (None, ""):
        doc.plan_status = data.get("plan_status")
    doc.summary = api.planning.normalize_rich_text(data.get("summary"))

    doc.insert(ignore_permissions=True)
    return {
        "course_plan": doc.name,
        "course": doc.course,
        "title": doc.title,
        "plan_status": doc.plan_status,
    }


def create_class_teaching_plan_impl(api, student_group: str, course_plan: str) -> dict[str, Any]:
    api._assert_staff_group_access(student_group)
    group = api._group_context(student_group)
    course_plan_row = api.planning.get_course_plan_row(course_plan)
    if api.planning.normalize_text(course_plan_row.get("course")) != api.planning.normalize_text(group.get("course")):
        api.frappe.throw(
            api._("The selected course plan does not belong to this class course."),
            api.frappe.ValidationError,
        )

    doc = api.frappe.new_doc("Class Teaching Plan")
    doc.course_plan = course_plan
    doc.student_group = student_group
    doc.insert(ignore_permissions=True)
    return {
        "class_teaching_plan": doc.name,
        "student_group": student_group,
    }


def save_class_teaching_plan_impl(
    api,
    class_teaching_plan: str,
    planning_status: str | None = None,
    team_note: str | None = None,
) -> dict[str, Any]:
    doc = api.frappe.get_doc("Class Teaching Plan", api.planning.normalize_text(class_teaching_plan))
    api._assert_staff_group_access(doc.student_group)

    if planning_status not in (None, ""):
        doc.planning_status = planning_status
    doc.team_note = api.planning.normalize_rich_text(team_note)
    doc.save(ignore_permissions=True)
    return {
        "class_teaching_plan": doc.name,
        "planning_status": doc.planning_status,
    }


def save_class_teaching_plan_unit_impl(
    api,
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
    plan_name = api.planning.normalize_text(class_teaching_plan)
    doc = api.frappe.get_doc("Class Teaching Plan", plan_name)
    api._assert_staff_group_access(doc.student_group)

    matched = None
    for row in doc.get("units") or []:
        if api.planning.normalize_text(row.unit_plan) == api.planning.normalize_text(unit_plan):
            matched = row
            break
    if not matched:
        api.frappe.throw(api._("Unit Plan is not part of this class teaching plan."), api.frappe.ValidationError)

    if pacing_status not in (None, ""):
        matched.pacing_status = pacing_status
    matched.teacher_focus = api.planning.normalize_long_text(teacher_focus)
    matched.pacing_note = api.planning.normalize_long_text(pacing_note)
    matched.prior_to_the_unit = api.planning.normalize_rich_text(prior_to_the_unit)
    matched.during_the_unit = api.planning.normalize_rich_text(during_the_unit)
    matched.what_work_well = api.planning.normalize_rich_text(what_work_well)
    matched.what_didnt_work_well = api.planning.normalize_rich_text(what_didnt_work_well)
    matched.changes_suggestions = api.planning.normalize_rich_text(changes_suggestions)
    doc.save(ignore_permissions=True)
    return {
        "class_teaching_plan": doc.name,
        "unit_plan": matched.unit_plan,
        "pacing_status": matched.pacing_status,
    }


def save_class_session_impl(
    api,
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
    plan_doc = api.frappe.get_doc("Class Teaching Plan", class_teaching_plan)
    api._assert_staff_group_access(plan_doc.student_group)

    if class_session:
        doc = api.frappe.get_doc("Class Session", class_session)
        if api.planning.normalize_text(doc.class_teaching_plan) != api.planning.normalize_text(class_teaching_plan):
            api.frappe.throw(
                api._("Class Session does not belong to this class teaching plan."),
                api.frappe.PermissionError,
            )
    else:
        doc = api.frappe.new_doc("Class Session")
        doc.class_teaching_plan = class_teaching_plan

    doc.unit_plan = unit_plan
    doc.title = title
    if session_status not in (None, ""):
        doc.session_status = session_status
    doc.session_date = session_date or None
    doc.sequence_index = int(sequence_index) if sequence_index not in (None, "") else None
    doc.learning_goal = api.planning.normalize_long_text(learning_goal)
    doc.teacher_note = api.planning.normalize_rich_text(teacher_note)

    parsed_activities = api.frappe.parse_json(activities_json) if activities_json else []
    api.planning.replace_session_activities(doc, parsed_activities)

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    return {
        "class_session": doc.name,
        "class_teaching_plan": class_teaching_plan,
        "session_status": doc.session_status,
    }


def save_course_plan_impl(api, payload=None, **kwargs) -> dict[str, Any]:
    data = api._normalize_payload(payload if payload is not None else kwargs)
    course_plan = api.planning.normalize_text(data.get("course_plan"))
    if not course_plan:
        api.frappe.throw(api._("Course Plan is required."))

    doc = api.frappe.get_doc("Course Plan", course_plan)
    api._assert_course_curriculum_access(
        doc.course,
        ptype="write",
        action_label=api._("update this shared course plan"),
    )
    api.planning.assert_record_modified_matches(
        expected_modified=data.get("expected_modified"),
        current_modified=getattr(doc, "modified", None),
        section_label=api._("Shared course plan"),
    )

    doc.title = api.planning.normalize_text(data.get("title")) or None
    doc.academic_year = api.planning.normalize_text(data.get("academic_year")) or None
    api._validate_course_plan_academic_year(
        course_school=getattr(doc, "school", None),
        academic_year=doc.academic_year,
        previous_academic_year=doc.get_db_value("academic_year") if hasattr(doc, "get_db_value") else None,
    )
    doc.cycle_label = api.planning.normalize_text(data.get("cycle_label")) or None
    doc.plan_status = api.planning.normalize_text(data.get("plan_status")) or None
    doc.summary = api.planning.normalize_rich_text(data.get("summary"))

    doc.save(ignore_permissions=True)
    return {
        "course_plan": doc.name,
        "plan_status": doc.plan_status,
    }


def save_unit_plan_impl(
    api,
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
    data = api._normalize_payload(payload if payload is not None else kwargs)
    course_plan_name = api.planning.normalize_text(course_plan or data.get("course_plan"))
    unit_plan_name = api.planning.normalize_text(unit_plan or data.get("unit_plan"))
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
        doc = api.frappe.get_doc("Unit Plan", unit_plan_name)
        course_plan_row = api.planning.get_course_plan_row(doc.course_plan)
        api._assert_course_curriculum_access(
            course_plan_row.get("course"),
            ptype="write",
            action_label=api._("update this unit plan"),
        )
        api.planning.assert_record_modified_matches(
            expected_modified=expected_modified,
            current_modified=getattr(doc, "modified", None),
            section_label=api._("Unit plan"),
        )
    else:
        if not course_plan_name:
            api.frappe.throw(api._("Course Plan is required."))
        course_plan_row = api.planning.get_course_plan_row(course_plan_name)
        api._assert_course_curriculum_access(
            course_plan_row.get("course"),
            ptype="write",
            action_label=api._("create a unit plan for this course"),
        )
        doc = api.frappe.new_doc("Unit Plan")
        doc.course_plan = course_plan_name

    doc.title = api.planning.normalize_text(title) or None
    doc.program = api.planning.normalize_text(program) or None
    api._validate_course_program_link(
        course=course_plan_row.get("course"),
        program=doc.program,
        previous_program=doc.get_db_value("program") if hasattr(doc, "get_db_value") else None,
    )
    doc.unit_code = api.planning.normalize_text(unit_code) or None
    doc.unit_order = int(unit_order) if unit_order not in (None, "") else None
    if unit_status not in (None, ""):
        doc.unit_status = api.planning.normalize_text(unit_status) or None
    doc.version = api.planning.normalize_text(version) or None
    doc.duration = api.planning.normalize_text(duration) or None
    doc.estimated_duration = api.planning.normalize_text(estimated_duration) or None
    doc.is_published = api.planning.normalize_flag(is_published)
    doc.overview = api.planning.normalize_rich_text(overview)
    doc.essential_understanding = api.planning.normalize_rich_text(essential_understanding)
    doc.misconceptions = api.planning.normalize_rich_text(misconceptions)
    doc.content = api.planning.normalize_rich_text(content)
    doc.skills = api.planning.normalize_rich_text(skills)
    doc.concepts = api.planning.normalize_rich_text(concepts)

    api.planning.replace_unit_plan_standards(
        doc,
        api._normalize_rows_payload(standards_json, label=api._("Standards")),
    )
    api.planning.ensure_linked_unit_plan_standards(doc)
    api.planning.replace_unit_plan_reflections(
        doc,
        api._normalize_rows_payload(reflections_json, label=api._("Reflections")),
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


def create_planning_reference_material_impl(api, payload=None, **kwargs) -> dict[str, Any]:
    data = api._normalize_payload(payload if payload is not None else kwargs)
    context = api._resolve_planning_resource_anchor(data.get("anchor_doctype"), data.get("anchor_name"), ptype="write")
    title = api.planning.normalize_text(data.get("title"))
    if not title:
        api.frappe.throw(api._("Title is required."))

    material, placement = api.materials_domain.create_reference_material(
        anchor_doctype=context["anchor_doctype"],
        anchor_name=context["anchor_name"],
        title=title,
        reference_url=data.get("reference_url"),
        description=data.get("description"),
        modality=data.get("modality"),
        usage_role=data.get("usage_role"),
        placement_note=data.get("placement_note"),
        origin=api.materials_domain.resolve_material_origin(context["anchor_doctype"]),
    )
    return {
        "anchor_doctype": context["anchor_doctype"],
        "anchor_name": context["anchor_name"],
        "placement": placement.name,
        "resource": api._reload_anchor_material(context["anchor_doctype"], context["anchor_name"], material.name),
    }


def upload_planning_material_file_impl(
    api,
    anchor_doctype: str | None = None,
    anchor_name: str | None = None,
    title: str | None = None,
    description: str | None = None,
    modality: str | None = None,
    usage_role: str | None = None,
    placement_note: str | None = None,
) -> dict[str, Any]:
    anchor_doctype = anchor_doctype or api.frappe.form_dict.get("anchor_doctype")
    anchor_name = anchor_name or api.frappe.form_dict.get("anchor_name")
    title = title or api.frappe.form_dict.get("title")
    description = description if description is not None else api.frappe.form_dict.get("description")
    modality = modality if modality is not None else api.frappe.form_dict.get("modality")
    usage_role = usage_role if usage_role is not None else api.frappe.form_dict.get("usage_role")
    placement_note = placement_note if placement_note is not None else api.frappe.form_dict.get("placement_note")

    context = api._resolve_planning_resource_anchor(anchor_doctype, anchor_name, ptype="write")
    title = api.planning.normalize_text(title)
    if not title:
        api.frappe.throw(api._("Title is required."))

    api.frappe.db.savepoint("upload_planning_material_file")
    try:
        material = api.materials_domain.create_file_material_record(
            anchor_doctype=context["anchor_doctype"],
            anchor_name=context["anchor_name"],
            title=title,
            description=description,
            modality=modality,
        )
        api.governed_uploads.upload_supporting_material_file(material=material.name)
        placement = api.materials_domain.create_material_placement(
            supporting_material=material.name,
            anchor_doctype=context["anchor_doctype"],
            anchor_name=context["anchor_name"],
            usage_role=usage_role,
            placement_note=placement_note,
            origin=api.materials_domain.resolve_material_origin(context["anchor_doctype"]),
        )
    except Exception:
        api.frappe.db.rollback(save_point="upload_planning_material_file")
        raise

    return {
        "anchor_doctype": context["anchor_doctype"],
        "anchor_name": context["anchor_name"],
        "placement": placement.name,
        "resource": api._reload_anchor_material(context["anchor_doctype"], context["anchor_name"], material.name),
    }


def remove_planning_material_impl(api, payload=None, **kwargs) -> dict[str, Any]:
    data = api._normalize_payload(payload if payload is not None else kwargs)
    context = api._resolve_planning_resource_anchor(data.get("anchor_doctype"), data.get("anchor_name"), ptype="write")
    placement = api.planning.normalize_text(data.get("placement"))
    if not placement:
        api.frappe.throw(api._("Placement is required."))

    api.materials_domain.delete_anchor_material_placement(
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
