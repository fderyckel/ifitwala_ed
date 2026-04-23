from __future__ import annotations

from typing import Any


def serialize_scalar(api, value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, api.datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, api.date):
        return value.isoformat()
    return value


def normalize_payload(api, value) -> dict[str, Any]:
    if isinstance(value, str):
        value = api.frappe.parse_json(value)
    if not isinstance(value, dict):
        api.frappe.throw(api._("Payload must be a dict."))
    return value


def normalize_rows_payload(api, value, *, label: str) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    rows = api.frappe.parse_json(value) if isinstance(value, str) else value
    if not isinstance(rows, list):
        api.frappe.throw(api._("{label} must be a list.").format(label=label))
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            api.frappe.throw(api._("{label} rows must be objects.").format(label=label))
        normalized.append(row)
    return normalized


def require_logged_in_user(api) -> str:
    user = api.frappe.session.user
    if not user or user == "Guest":
        api.frappe.throw(api._("You need to sign in to continue."), api.frappe.AuthenticationError)
    return user


def resolve_planning_resource_anchor(
    api, anchor_doctype: str, anchor_name: str, *, ptype: str = "write"
) -> dict[str, Any]:
    anchor_doctype = api.planning.normalize_text(anchor_doctype)
    anchor_name = api.planning.normalize_text(anchor_name)
    if anchor_doctype not in api.PLANNING_RESOURCE_ANCHORS:
        api.frappe.throw(
            api._("Planning resources must be attached to a course plan, unit plan, class plan, or class session.")
        )
    context = api.materials_domain.resolve_anchor_context(anchor_doctype, anchor_name)
    if anchor_doctype in api.GOVERNED_PLANNING_RESOURCE_ANCHORS:
        course = api.planning.normalize_text(context.get("course"))
        if not course:
            api.frappe.throw(api._("This shared curriculum resource is missing its course."))
        user, roles = api._assert_course_curriculum_access(
            course,
            ptype=ptype,
            action_label=api._("this shared curriculum resource"),
        )
        context["can_manage_resources"] = int(api.planning.user_can_manage_course_curriculum(user, course, roles))
        return context

    student_group = api.planning.normalize_text(context.get("student_group"))
    if not student_group:
        api.frappe.throw(api._("This resource context is missing its class."))
    api._assert_staff_group_access(student_group)
    context["can_manage_resources"] = 1
    return context


def assert_staff_group_access(api, student_group: str) -> None:
    user = api._require_logged_in_user()
    roles = set(api.frappe.get_roles(user))
    if roles & api.TRIAGE_ROLES:
        return
    if student_group not in api._instructor_group_names(user):
        api.frappe.throw(api._("You do not have access to this class."), api.frappe.PermissionError)


def assert_course_curriculum_access(
    api,
    course: str,
    *,
    ptype: str = "write",
    action_label: str | None = None,
) -> tuple[str, set[str]]:
    user = api._require_logged_in_user()
    roles = set(api.frappe.get_roles(user))
    course_name = api.planning.normalize_text(course)
    if not course_name:
        api.frappe.throw(api._("Course is required for this curriculum action."))

    if ptype == "write":
        api.planning.assert_can_manage_course_curriculum(user, course_name, roles, action_label=action_label)
    else:
        api.planning.assert_can_read_course_curriculum(user, course_name, roles, action_label=action_label)
    return user, roles


def require_student_name(api) -> str:
    user = api._require_logged_in_user()
    roles = set(api.frappe.get_roles(user))
    if "Student" not in roles:
        api.frappe.throw(api._("Student access is required."), api.frappe.PermissionError)
    student_name = api.frappe.db.get_value("Student", {"student_email": user}, "name")
    if not student_name:
        api.frappe.throw(api._("No student profile is linked to this login."), api.frappe.PermissionError)
    return student_name


def assert_student_course_access(api, student_name: str, course_id: str) -> None:
    from ifitwala_ed.api import courses as courses_api

    scope = courses_api._build_student_course_scope(student_name)
    if course_id not in scope:
        api.frappe.throw(api._("You do not have access to this course."), api.frappe.PermissionError)


def assert_student_group_membership(api, student_name: str, student_group: str) -> None:
    allowed = api.frappe.db.exists(
        "Student Group Student",
        {
            "parent": student_group,
            "parenttype": "Student Group",
            "student": student_name,
            "active": 1,
        },
    )
    if not allowed:
        api.frappe.throw(api._("You do not have access to this class."), api.frappe.PermissionError)


def group_context(api, student_group: str) -> dict[str, Any]:
    group = api.planning.get_student_group_row(student_group)
    if not api.planning.normalize_text(group.get("course")):
        api.frappe.throw(api._("This class is not linked to a course."), api.frappe.ValidationError)
    return group


def serialize_course_plan(api, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "course_plan": row.get("name"),
        "title": row.get("title") or row.get("name"),
        "academic_year": row.get("academic_year"),
        "cycle_label": row.get("cycle_label"),
        "plan_status": row.get("plan_status"),
    }


def serialize_course_plan_summary(
    api,
    row: dict[str, Any],
    *,
    course_row: dict[str, Any] | None = None,
    can_manage_resources: int = 0,
) -> dict[str, Any]:
    return {
        "name": row.get("name"),
        "course_plan": row.get("name"),
        "record_modified": api._serialize_scalar(row.get("modified")),
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


def serialize_class_teaching_plan_row(api, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "class_teaching_plan": row.get("name"),
        "title": row.get("title") or row.get("name"),
        "course_plan": row.get("course_plan"),
        "planning_status": row.get("planning_status"),
    }


def serialize_course_option(
    api,
    row: dict[str, Any],
    *,
    academic_year_options: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "course": row.get("name"),
        "course_name": row.get("course_name") or row.get("name"),
        "course_group": row.get("course_group"),
        "school": row.get("school"),
        "status": row.get("status"),
        "academic_year_options": academic_year_options or [],
    }


def serialize_academic_year_option(api, row: dict[str, Any]) -> dict[str, Any]:
    name = api.planning.normalize_text(row.get("name"))
    return {
        "value": name,
        "label": name,
        "school": api.planning.normalize_text(row.get("school")) or None,
        "year_start_date": api._serialize_scalar(row.get("year_start_date")),
        "year_end_date": api._serialize_scalar(row.get("year_end_date")),
    }


def serialize_program_option(api, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "value": row.get("name"),
        "label": row.get("program_name") or row.get("name"),
        "parent_program": row.get("parent_program"),
        "is_group": int(row.get("is_group") or 0),
        "archived": int(row.get("archive") or 0),
    }


def academic_year_scope_for_school(api, school: str | None) -> list[str]:
    from ifitwala_ed.utilities.school_tree import get_school_scope_for_academic_year

    school_name = api.planning.normalize_text(school)
    if not school_name:
        return []

    scope = [
        api.planning.normalize_text(scope_school)
        for scope_school in (get_school_scope_for_academic_year(school_name) or [])
        if api.planning.normalize_text(scope_school)
    ]
    return scope or [school_name]


def fetch_academic_year_options_for_schools(
    api,
    schools: list[str] | tuple[str, ...],
    *,
    pinned_years: dict[str, str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    normalized_schools = [
        school_name
        for school_name in {api.planning.normalize_text(school) for school in (schools or [])}
        if school_name
    ]
    if not normalized_schools:
        return {}

    scope_by_school = {
        school_name: api._academic_year_scope_for_school(school_name) for school_name in normalized_schools
    }
    query_schools = sorted(
        {
            scope_school
            for scope in scope_by_school.values()
            for scope_school in scope
            if api.planning.normalize_text(scope_school)
        }
    )
    pinned_year_names = sorted(
        {
            api.planning.normalize_text(academic_year)
            for academic_year in (pinned_years or {}).values()
            if api.planning.normalize_text(academic_year)
        }
    )

    rows = api.frappe.get_all(
        "Academic Year",
        filters={"school": ["in", query_schools]} if query_schools else {"name": ["in", [""]]},
        fields=["name", "school", "year_start_date", "year_end_date"],
        order_by="year_start_date desc, name desc",
        limit=0,
    )
    if pinned_year_names:
        pinned_rows = api.frappe.get_all(
            "Academic Year",
            filters={"name": ["in", pinned_year_names]},
            fields=["name", "school", "year_start_date", "year_end_date"],
            order_by="year_start_date desc, name desc",
            limit=0,
        )
        rows_by_name = {api.planning.normalize_text(row.get("name")): row for row in rows or []}
        for row in pinned_rows or []:
            name = api.planning.normalize_text(row.get("name"))
            if name and name not in rows_by_name:
                rows.append(row)
                rows_by_name[name] = row

    rows_by_school: dict[str, list[dict[str, Any]]] = api.defaultdict(list)
    rows_by_name: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        school_name = api.planning.normalize_text(row.get("school"))
        record_name = api.planning.normalize_text(row.get("name"))
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
                record_name = api.planning.normalize_text(row.get("name"))
                if not record_name or record_name in seen:
                    continue
                options.append(api._serialize_academic_year_option(row))
                seen.add(record_name)

        pinned_name = api.planning.normalize_text((pinned_years or {}).get(school_name))
        pinned_row = rows_by_name.get(pinned_name)
        if pinned_name and pinned_row and pinned_name not in seen:
            options.append(api._serialize_academic_year_option(pinned_row))

        options_by_school[school_name] = options

    return options_by_school


def fetch_program_options_for_course(
    api,
    course: str | None,
    *,
    pinned_programs: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    course_name = api.planning.normalize_text(course)
    pinned_names = {
        api.planning.normalize_text(program_name)
        for program_name in (pinned_programs or [])
        if api.planning.normalize_text(program_name)
    }
    linked_program_names = (
        api.frappe.get_all(
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
        api.planning.normalize_text(program_name)
        for program_name in linked_program_names
        if api.planning.normalize_text(program_name)
    }
    program_names.update(pinned_names)
    if not program_names:
        return []

    rows = api.frappe.get_all(
        "Program",
        filters={"name": ["in", sorted(program_names)]},
        fields=["name", "program_name", "parent_program", "is_group", "archive", "lft"],
        order_by="lft asc, name asc",
        limit=0,
    )
    payload: list[dict[str, Any]] = []
    for row in rows or []:
        name = api.planning.normalize_text(row.get("name"))
        if int(row.get("archive") or 0) and name not in pinned_names:
            continue
        payload.append(api._serialize_program_option(row))
    return payload


def validate_course_plan_academic_year(
    api,
    *,
    course_school: str | None,
    academic_year: str | None,
    previous_academic_year: str | None = None,
) -> None:
    academic_year_name = api.planning.normalize_text(academic_year)
    if not academic_year_name:
        return
    if academic_year_name == api.planning.normalize_text(previous_academic_year):
        return

    row = api.frappe.db.get_value("Academic Year", academic_year_name, ["name", "school"], as_dict=True)
    if not row:
        api.frappe.throw(
            api._("Academic Year {academic_year} was not found.").format(academic_year=academic_year_name),
            api.frappe.ValidationError,
        )

    school_name = api.planning.normalize_text(course_school)
    if not school_name:
        return

    allowed_scope = set(api._academic_year_scope_for_school(school_name))
    academic_year_school = api.planning.normalize_text(row.get("school"))
    if allowed_scope and academic_year_school not in allowed_scope:
        api.frappe.throw(
            api._(
                "Academic Year {academic_year} is not available for school {school}. Choose an academic year from this course's school scope."
            ).format(academic_year=academic_year_name, school=school_name),
            api.frappe.ValidationError,
        )


def validate_course_program_link(
    api,
    *,
    course: str | None,
    program: str | None,
    previous_program: str | None = None,
) -> None:
    program_name = api.planning.normalize_text(program)
    if not program_name:
        return
    if program_name == api.planning.normalize_text(previous_program):
        return

    if not api.frappe.db.exists("Program", program_name):
        api.frappe.throw(
            api._("Program {program} was not found.").format(program=program_name),
            api.frappe.ValidationError,
        )

    course_name = api.planning.normalize_text(course)
    if course_name and not api.frappe.db.exists(
        "Program Course",
        {
            "parent": program_name,
            "parenttype": "Program",
            "parentfield": "courses",
            "course": course_name,
        },
    ):
        api.frappe.throw(
            api._(
                "Program {program} is not linked to course {course}. Choose a program that already includes this course."
            ).format(program=program_name, course=course_name),
            api.frappe.ValidationError,
        )


def quiz_question_bank_record_modified(
    api,
    bank_row: dict[str, Any] | None,
    question_rows: list[dict[str, Any]] | None,
) -> str:
    digest = api.hashlib.sha256()
    digest.update(api.planning.normalize_record_modified((bank_row or {}).get("modified")).encode("utf-8"))
    for row in sorted(
        question_rows or [],
        key=lambda item: (
            api.planning.normalize_text(item.get("name")),
            api.planning.normalize_record_modified(item.get("modified")),
        ),
    ):
        digest.update(b"|")
        digest.update(api.planning.normalize_text(row.get("name")).encode("utf-8"))
        digest.update(b":")
        digest.update(api.planning.normalize_record_modified(row.get("modified")).encode("utf-8"))
    return digest.hexdigest()


def payload_size_bytes(api, payload: dict[str, Any] | None) -> int | None:
    if payload in (None, ""):
        return 0
    try:
        return len(
            api.json.dumps(
                payload,
                default=str,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    except Exception:
        return None


def current_db_query_count(api) -> int | None:
    db = getattr(api.frappe, "db", None)
    for attr_name in ("query_count", "_query_count", "sql_count"):
        value = getattr(db, attr_name, None)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
    return None


def db_query_delta(api, started_count: int | None) -> int | None:
    current_count = api._current_db_query_count()
    if started_count is None or current_count is None:
        return None
    return max(current_count - started_count, 0)


def log_planning_event(
    api,
    event: str,
    *,
    started_at: float | None = None,
    warning: bool = False,
    **context,
) -> None:
    logger_factory = getattr(api.frappe, "logger", None)
    if not callable(logger_factory):
        return

    payload = {
        "event": api.planning.normalize_text(event) or "course_plan_event",
    }
    if started_at is not None:
        payload["elapsed_ms"] = round((api.perf_counter() - started_at) * 1000, 2)
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


def list_creatable_course_rows(api, user: str, roles: set[str]) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {"status": ["!=", "Discontinued"]}
    if not api.planning.user_has_global_curriculum_access(user, roles):
        course_names = api.planning.get_curriculum_manageable_course_names(user, roles)
        if not course_names:
            return []
        filters["name"] = ["in", course_names]

    return api.frappe.get_all(
        "Course",
        filters=filters,
        fields=["name", "course_name", "course_group", "school", "status"],
        order_by="course_name asc, name asc",
        limit=0,
    )


def build_course_plan_creation_access(api, user: str, roles: set[str]) -> dict[str, Any]:
    course_rows = api._list_creatable_course_rows(user, roles)
    can_create = int(bool(course_rows))
    academic_year_options_by_school = api._fetch_academic_year_options_for_schools(
        [
            api.planning.normalize_text(row.get("school"))
            for row in course_rows
            if api.planning.normalize_text(row.get("school"))
        ]
    )

    if not course_rows:
        reason = api._(
            "You need an active teaching assignment or curriculum leadership access before you can start a shared course plan."
        )
    else:
        reason = None

    return {
        "can_create_course_plans": can_create,
        "create_block_reason": reason,
        "course_options": [
            api._serialize_course_option(
                row,
                academic_year_options=academic_year_options_by_school.get(
                    api.planning.normalize_text(row.get("school")),
                    [],
                ),
            )
            for row in course_rows
        ],
    }
