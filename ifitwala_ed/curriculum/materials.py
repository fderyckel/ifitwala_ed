from __future__ import annotations

from collections import OrderedDict
from urllib.parse import urlparse

import frappe
from frappe import _

from ifitwala_ed.api import student_groups as student_groups_api

MATERIAL_TYPE_FILE = "File"
MATERIAL_TYPE_REFERENCE_LINK = "Reference Link"
MATERIAL_MODALITIES = {"Read", "Watch", "Listen", "Use"}
MATERIAL_USAGE_ROLES = {"Required", "Reference", "Template", "Example"}
MATERIAL_ORIGINS = {"curriculum", "task", "shared_in_class"}
MATERIAL_ALLOWED_ANCHORS = {
    "Course Plan",
    "Unit Plan",
    "Class Teaching Plan",
    "Class Session",
    "Task",
}
MATERIAL_SHARED_ANCHORS = {"Course Plan", "Unit Plan", "Task"}
MATERIAL_CLASS_OWNED_ANCHORS = {"Class Teaching Plan", "Class Session"}
MATERIAL_FILE_SLOT = "material_file"
MATERIAL_BINDING_ROLE = "general_reference"
MATERIAL_DATA_CLASS = "academic"
MATERIAL_PURPOSE = "general_reference"
MATERIAL_RETENTION_POLICY = "until_program_end_plus_1y"

_ADMIN_ROLES = {"Administrator", "System Manager", "Academic Admin"}
_GROUP_WIDE_STAFF_ROLES = {"Academic Staff", "Academic Assistant", "Counselor"}


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def _ensure_known_doctype(doctype: str, name: str):
    if not frappe.db.exists(doctype, name):
        frappe.throw(_("{doctype} does not exist: {name}").format(doctype=doctype, name=name))
    return frappe.get_doc(doctype, name)


def _anchor_exists(anchor_doctype: str, anchor_name: str) -> None:
    if not frappe.db.exists(anchor_doctype, anchor_name):
        frappe.throw(
            _("Anchor document does not exist: {doctype} {name}").format(doctype=anchor_doctype, name=anchor_name)
        )


def resolve_anchor_context(anchor_doctype: str, anchor_name: str) -> dict[str, str | None]:
    anchor_doctype = _normalize_text(anchor_doctype)
    anchor_name = _normalize_text(anchor_name)
    if anchor_doctype not in MATERIAL_ALLOWED_ANCHORS:
        frappe.throw(_("Unsupported material anchor type: {0}").format(anchor_doctype))
    if not anchor_name:
        frappe.throw(_("Anchor Name is required."))

    fields_by_doctype = {
        "Course Plan": ["name", "course"],
        "Unit Plan": ["name", "course", "course_plan"],
        "Class Teaching Plan": ["name", "student_group", "course_plan", "course", "academic_year"],
        "Class Session": [
            "name",
            "class_teaching_plan",
            "student_group",
            "course_plan",
            "course",
            "academic_year",
            "unit_plan",
        ],
        "Task": ["name", "default_course", "unit_plan", "lesson"],
    }
    row = frappe.db.get_value(anchor_doctype, anchor_name, fields_by_doctype[anchor_doctype], as_dict=True) or {}
    if not row:
        frappe.throw(
            _("Anchor document does not exist: {doctype} {name}").format(doctype=anchor_doctype, name=anchor_name)
        )

    context = {key: _normalize_text(value) or None for key, value in row.items()}
    context["anchor_doctype"] = anchor_doctype
    context["anchor_name"] = anchor_name

    course = None
    if anchor_doctype == "Course Plan":
        course = context.get("course")
        context["course_plan"] = anchor_name
    elif anchor_doctype == "Unit Plan":
        course = context.get("course")
        context["unit_plan"] = anchor_name
    elif anchor_doctype == "Class Teaching Plan":
        course = context.get("course")
        context["class_teaching_plan"] = anchor_name
    elif anchor_doctype == "Class Session":
        course = context.get("course")
        context["class_session"] = anchor_name
    elif anchor_doctype == "Task":
        course = context.get("default_course")
        context["course"] = course
        if context.get("lesson") and not context.get("unit_plan"):
            context["unit_plan"] = (
                _normalize_text(frappe.db.get_value("Lesson", context.get("lesson"), "unit_plan")) or None
            )
        if context.get("unit_plan"):
            context["course_plan"] = (
                _normalize_text(frappe.db.get_value("Unit Plan", context.get("unit_plan"), "course_plan")) or None
            )

    context["course"] = course
    if not context.get("course"):
        frappe.throw(
            _("Could not resolve the authoritative Course for {doctype} {name}.").format(
                doctype=anchor_doctype, name=anchor_name
            )
        )
    return context


def validate_reference_url(value: str) -> str:
    reference_url = _normalize_text(value)
    if not reference_url:
        frappe.throw(_("Reference URL is required."))

    parsed = urlparse(reference_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        frappe.throw(_("Reference URL must be a valid http or https URL."))
    return reference_url


def resolve_anchor_course(anchor_doctype: str, anchor_name: str) -> str:
    return _normalize_text(resolve_anchor_context(anchor_doctype, anchor_name).get("course"))


def resolve_material_origin(anchor_doctype: str) -> str:
    anchor_doctype = _normalize_text(anchor_doctype)
    if anchor_doctype == "Task":
        return "task"
    if anchor_doctype in MATERIAL_CLASS_OWNED_ANCHORS:
        return "shared_in_class"
    return "curriculum"


def normalize_material_modality(value: str | None) -> str:
    modality = _normalize_text(value) or "Read"
    if modality not in MATERIAL_MODALITIES:
        frappe.throw(_("Unsupported material modality: {0}").format(modality))
    return modality


def normalize_material_usage_role(value: str | None) -> str:
    usage_role = _normalize_text(value) or "Reference"
    if usage_role not in MATERIAL_USAGE_ROLES:
        frappe.throw(_("Unsupported material usage role: {0}").format(usage_role))
    return usage_role


def normalize_material_origin(value: str | None, *, anchor_doctype: str | None = None) -> str:
    origin = _normalize_text(value)
    if not origin and anchor_doctype:
        origin = resolve_material_origin(anchor_doctype)
    if origin not in MATERIAL_ORIGINS:
        frappe.throw(_("Unsupported material origin: {0}").format(origin))
    return origin


def get_course_school_context(course: str) -> tuple[str, str]:
    school = _normalize_text(frappe.db.get_value("Course", course, "school"))
    if not school:
        frappe.throw(_("Course is missing its school context."))
    organization = _normalize_text(frappe.db.get_value("School", school, "organization"))
    if not organization:
        frappe.throw(_("Course school is missing its organization context."))
    return school, organization


def create_file_material_record(
    *,
    anchor_doctype: str,
    anchor_name: str,
    title: str,
    description: str | None = None,
    modality: str | None = None,
) -> frappe.model.document.Document:
    assert_can_manage_material_anchor(anchor_doctype, anchor_name)

    material = frappe.new_doc("Supporting Material")
    material.title = _normalize_text(title)
    material.course = resolve_anchor_course(anchor_doctype, anchor_name)
    material.material_type = MATERIAL_TYPE_FILE
    material.description = _normalize_text(description) or None
    material.modality = normalize_material_modality(modality)
    material.flags.allow_missing_file = True
    material.insert()
    return material


def create_reference_material(
    *,
    anchor_doctype: str,
    anchor_name: str,
    title: str,
    reference_url: str,
    description: str | None = None,
    modality: str | None = None,
    usage_role: str | None = None,
    placement_note: str | None = None,
    origin: str | None = None,
    placement_order: int | None = None,
) -> tuple[frappe.model.document.Document, frappe.model.document.Document]:
    assert_can_manage_material_anchor(anchor_doctype, anchor_name)

    material = frappe.new_doc("Supporting Material")
    material.title = _normalize_text(title)
    material.course = resolve_anchor_course(anchor_doctype, anchor_name)
    material.material_type = MATERIAL_TYPE_REFERENCE_LINK
    material.reference_url = validate_reference_url(reference_url)
    material.description = _normalize_text(description) or None
    material.modality = normalize_material_modality(modality)
    material.insert()

    placement = create_material_placement(
        supporting_material=material.name,
        anchor_doctype=anchor_doctype,
        anchor_name=anchor_name,
        usage_role=usage_role,
        placement_note=placement_note,
        origin=origin,
        placement_order=placement_order,
    )
    return material, placement


def create_material_placement(
    *,
    supporting_material: str,
    anchor_doctype: str,
    anchor_name: str,
    usage_role: str | None = None,
    placement_note: str | None = None,
    origin: str | None = None,
    placement_order: int | None = None,
) -> frappe.model.document.Document:
    assert_can_manage_material_anchor(anchor_doctype, anchor_name)

    material_doc = _ensure_known_doctype("Supporting Material", supporting_material)

    placement = frappe.new_doc("Material Placement")
    placement.supporting_material = material_doc.name
    placement.course = material_doc.course
    placement.anchor_doctype = _normalize_text(anchor_doctype)
    placement.anchor_name = _normalize_text(anchor_name)
    placement.usage_role = normalize_material_usage_role(usage_role)
    placement.origin = normalize_material_origin(origin, anchor_doctype=anchor_doctype)
    placement.placement_note = _normalize_text(placement_note) or None
    placement.placement_order = placement_order
    placement.insert()
    return placement


def delete_task_material_placement(placement_name: str, *, task: str) -> None:
    placement = _ensure_known_doctype("Material Placement", placement_name)
    if placement.anchor_doctype != "Task" or placement.anchor_name != task:
        frappe.throw(_("Material placement does not belong to this task."), frappe.PermissionError)
    task_doc = _ensure_known_doctype("Task", task)
    task_doc.check_permission("write")
    frappe.delete_doc("Material Placement", placement_name, ignore_permissions=True)


def delete_anchor_material_placement(placement_name: str, *, anchor_doctype: str, anchor_name: str) -> None:
    placement = _ensure_known_doctype("Material Placement", placement_name)
    if placement.anchor_doctype != anchor_doctype or placement.anchor_name != anchor_name:
        frappe.throw(_("Material placement does not belong to this context."), frappe.PermissionError)
    assert_can_manage_material_anchor(anchor_doctype, anchor_name)
    frappe.delete_doc("Material Placement", placement_name, ignore_permissions=True)


def _fetch_material_rows(where_sql: str, params: dict[str, object]) -> list[dict]:
    rows = frappe.db.sql(
        f"""
        SELECT
            mp.name AS placement,
            mp.supporting_material,
            mp.course AS placement_course,
            mp.anchor_doctype,
            mp.anchor_name,
            mp.origin,
            mp.usage_role,
            mp.placement_note,
            mp.placement_order,
            sm.name AS material,
            sm.course,
            sm.title,
            sm.material_type,
            sm.modality,
            sm.description,
            sm.reference_url,
            sm.file,
            sm.file_name,
            sm.file_size,
            sm.is_archived,
            f.file_url
        FROM `tabMaterial Placement` mp
        INNER JOIN `tabSupporting Material` sm ON sm.name = mp.supporting_material
        LEFT JOIN `tabFile` f ON f.name = sm.file
        WHERE {where_sql}
        ORDER BY
            sm.title ASC,
            mp.anchor_doctype ASC,
            COALESCE(mp.placement_order, 2147483647) ASC,
            mp.name ASC
        """,
        params,
        as_dict=True,
    )
    return rows or []


def _material_row_is_ready(row: dict) -> bool:
    if int(row.get("is_archived") or 0):
        return False
    material_type = _normalize_text(row.get("material_type"))
    if material_type == MATERIAL_TYPE_FILE:
        return bool(_normalize_text(row.get("file")))
    if material_type == MATERIAL_TYPE_REFERENCE_LINK:
        return bool(_normalize_text(row.get("reference_url")))
    return False


def _aggregate_material_rows(rows: list[dict]) -> list[dict]:
    material_map: OrderedDict[str, dict] = OrderedDict()

    for row in rows:
        if not _material_row_is_ready(row):
            continue

        material_name = _normalize_text(row.get("material"))
        if not material_name:
            continue

        entry = material_map.setdefault(
            material_name,
            {
                "material": material_name,
                "course": _normalize_text(row.get("course")),
                "title": row.get("title"),
                "material_type": row.get("material_type"),
                "modality": row.get("modality"),
                "description": row.get("description"),
                "reference_url": row.get("reference_url"),
                "file": row.get("file"),
                "file_name": row.get("file_name"),
                "file_size": row.get("file_size"),
                "file_url": row.get("file_url"),
                "placements": [],
            },
        )

        entry["placements"].append(
            {
                "placement": row.get("placement"),
                "anchor_doctype": row.get("anchor_doctype"),
                "anchor_name": row.get("anchor_name"),
                "origin": row.get("origin"),
                "usage_role": row.get("usage_role"),
                "placement_note": row.get("placement_note"),
                "placement_order": row.get("placement_order"),
            }
        )

    return list(material_map.values())


def list_materials_for_anchors(anchor_refs: list[tuple[str, str]]) -> dict[tuple[str, str], list[dict]]:
    cleaned = []
    for anchor_doctype, anchor_name in anchor_refs or []:
        doctype = _normalize_text(anchor_doctype)
        name = _normalize_text(anchor_name)
        if doctype and name:
            cleaned.append((doctype, name))
    if not cleaned:
        return {}

    conditions = []
    params: dict[str, object] = {}
    for idx, (anchor_doctype, anchor_name) in enumerate(cleaned):
        doctype_key = f"anchor_doctype_{idx}"
        name_key = f"anchor_name_{idx}"
        params[doctype_key] = anchor_doctype
        params[name_key] = anchor_name
        conditions.append(f"(mp.anchor_doctype = %({doctype_key})s AND mp.anchor_name = %({name_key})s)")

    rows = _fetch_material_rows(" OR ".join(conditions), params)
    grouped: dict[tuple[str, str], OrderedDict[str, dict]] = {}
    for row in rows:
        if not _material_row_is_ready(row):
            continue

        anchor_key = (_normalize_text(row.get("anchor_doctype")), _normalize_text(row.get("anchor_name")))
        material_name = _normalize_text(row.get("material"))
        if not anchor_key[0] or not anchor_key[1] or not material_name:
            continue

        material_map = grouped.setdefault(anchor_key, OrderedDict())
        entry = material_map.setdefault(
            material_name,
            {
                "material": material_name,
                "course": _normalize_text(row.get("course")),
                "title": row.get("title"),
                "material_type": row.get("material_type"),
                "modality": row.get("modality"),
                "description": row.get("description"),
                "reference_url": row.get("reference_url"),
                "file": row.get("file"),
                "file_name": row.get("file_name"),
                "file_size": row.get("file_size"),
                "file_url": row.get("file_url"),
                "placements": [],
            },
        )
        entry["placements"].append(
            {
                "placement": row.get("placement"),
                "anchor_doctype": row.get("anchor_doctype"),
                "anchor_name": row.get("anchor_name"),
                "origin": row.get("origin"),
                "usage_role": row.get("usage_role"),
                "placement_note": row.get("placement_note"),
                "placement_order": row.get("placement_order"),
            }
        )

    return {key: list(value.values()) for key, value in grouped.items()}


def list_course_materials(course: str) -> list[dict]:
    return _aggregate_material_rows(_fetch_material_rows("mp.course = %(course)s", {"course": course}))


def list_anchor_materials(anchor_doctype: str, anchor_name: str) -> list[dict]:
    return _aggregate_material_rows(
        _fetch_material_rows(
            "mp.anchor_doctype = %(anchor_doctype)s AND mp.anchor_name = %(anchor_name)s",
            {"anchor_doctype": anchor_doctype, "anchor_name": anchor_name},
        )
    )


def material_has_any_placement(material_name: str) -> bool:
    return bool(frappe.db.exists("Material Placement", {"supporting_material": material_name}))


def _student_name_for_user(user: str) -> str | None:
    return _normalize_text(frappe.db.get_value("Student", {"student_email": user}, "name")) or None


def _student_group_names_for_student(student: str) -> list[str]:
    if not student:
        return []
    return sorted(
        {
            group
            for group in (
                frappe.get_all(
                    "Student Group Student",
                    filters={"student": student, "active": 1},
                    pluck="parent",
                    limit=0,
                )
                or []
            )
            if group
        }
    )


def _coordinator_course_names(user: str) -> list[str]:
    employee = _normalize_text(
        frappe.db.get_value("Employee", {"user_id": user, "employment_status": "Active"}, "name")
    )
    if not employee:
        return []

    rows = frappe.db.sql(
        """
        SELECT course
        FROM `tabProgram Coordinator`
        WHERE employee = %(employee)s
          AND COALESCE(status, 'Active') = 'Active'
        """,
        {"employee": employee},
        as_dict=True,
    )
    return sorted({_normalize_text(row.get("course")) for row in rows or [] if _normalize_text(row.get("course"))})


def _student_course_names(user: str) -> list[str]:
    student = _student_name_for_user(user)
    if not student:
        return []
    courses = set()

    rows = frappe.db.sql(
        """
        SELECT pec.course
        FROM `tabProgram Enrollment Course` pec
        JOIN `tabProgram Enrollment` pe ON pe.name = pec.parent
        WHERE pe.student = %(student)s
          AND COALESCE(pec.status, 'Enrolled') <> 'Dropped'
        """,
        {"student": student},
        as_dict=True,
    )
    for row in rows or []:
        if _normalize_text(row.get("course")):
            courses.add(_normalize_text(row.get("course")))

    group_names = _student_group_names_for_student(student)
    if group_names:
        for course in (
            frappe.get_all("Student Group", filters={"name": ["in", group_names]}, pluck="course", limit=0) or []
        ):
            if _normalize_text(course):
                courses.add(_normalize_text(course))

    return sorted(courses)


def _visibility_scope(user: str, *, manage_only: bool = False) -> dict[str, object]:
    user = _normalize_text(user)
    roles = set(frappe.get_roles(user) or [])
    if roles & _ADMIN_ROLES or roles & _GROUP_WIDE_STAFF_ROLES:
        return {"all": True, "shared_courses": [], "class_groups": [], "class_courses": []}

    shared_courses: set[str] = set()
    class_groups: set[str] = set()
    class_courses: set[str] = set()

    instructor_groups = set(student_groups_api._instructor_group_names(user) or [])
    if instructor_groups:
        class_groups.update(group for group in instructor_groups if group)
        for course in (
            frappe.get_all("Student Group", filters={"name": ["in", list(instructor_groups)]}, pluck="course", limit=0)
            or []
        ):
            if _normalize_text(course):
                shared_courses.add(_normalize_text(course))

    if not manage_only and "Curriculum Coordinator" in roles:
        coordinator_courses = _coordinator_course_names(user)
        shared_courses.update(coordinator_courses)
        class_courses.update(coordinator_courses)

    if not manage_only:
        student_courses = _student_course_names(user)
        shared_courses.update(student_courses)
        student_name = _student_name_for_user(user)
        if student_name:
            class_groups.update(_student_group_names_for_student(student_name))

    return {
        "all": False,
        "shared_courses": sorted(course for course in shared_courses if course),
        "class_groups": sorted(group for group in class_groups if group),
        "class_courses": sorted(course for course in class_courses if course),
    }


def _sql_in_list(values: list[str]) -> str:
    return ", ".join(frappe.db.escape(value) for value in values if value)


def _material_placement_scope_sql(
    table_alias: str, *, user: str | None = None, manage_only: bool = False
) -> str | None:
    scope = _visibility_scope(_normalize_text(user or frappe.session.user), manage_only=manage_only)
    if scope.get("all"):
        return None

    conditions = []
    shared_courses = scope.get("shared_courses") or []
    class_groups = scope.get("class_groups") or []
    class_courses = scope.get("class_courses") or []

    if shared_courses:
        conditions.append(
            f"({table_alias}.anchor_doctype in ('Course Plan', 'Unit Plan', 'Task') AND {table_alias}.course in ({_sql_in_list(shared_courses)}))"
        )
    if class_groups:
        group_list = _sql_in_list(class_groups)
        conditions.append(
            f"({table_alias}.anchor_doctype = 'Class Teaching Plan' AND {table_alias}.anchor_name in (SELECT name FROM `tabClass Teaching Plan` WHERE student_group in ({group_list})))"
        )
        conditions.append(
            f"({table_alias}.anchor_doctype = 'Class Session' AND {table_alias}.anchor_name in (SELECT name FROM `tabClass Session` WHERE student_group in ({group_list})))"
        )
    if class_courses:
        course_list = _sql_in_list(class_courses)
        conditions.append(
            f"({table_alias}.anchor_doctype = 'Class Teaching Plan' AND {table_alias}.anchor_name in (SELECT name FROM `tabClass Teaching Plan` WHERE course in ({course_list})))"
        )
        conditions.append(
            f"({table_alias}.anchor_doctype = 'Class Session' AND {table_alias}.anchor_name in (SELECT name FROM `tabClass Session` WHERE course in ({course_list})))"
        )

    if not conditions:
        return "1=0"
    return "(" + " OR ".join(conditions) + ")"


def user_can_read_material_anchor(user: str, anchor_doctype: str, anchor_name: str) -> bool:
    user = _normalize_text(user)
    if not user or user == "Guest":
        return False

    scope = _visibility_scope(user, manage_only=False)
    if scope.get("all"):
        return True

    context = resolve_anchor_context(anchor_doctype, anchor_name)
    doctype = context.get("anchor_doctype")
    course = context.get("course")
    student_group = context.get("student_group")

    if doctype in MATERIAL_SHARED_ANCHORS:
        return course in set(scope.get("shared_courses") or [])
    if doctype in MATERIAL_CLASS_OWNED_ANCHORS:
        return student_group in set(scope.get("class_groups") or []) or course in set(scope.get("class_courses") or [])
    return False


def user_can_manage_material_anchor(user: str, anchor_doctype: str, anchor_name: str) -> bool:
    user = _normalize_text(user)
    if not user or user == "Guest":
        return False

    scope = _visibility_scope(user, manage_only=True)
    if scope.get("all"):
        return True

    context = resolve_anchor_context(anchor_doctype, anchor_name)
    doctype = context.get("anchor_doctype")
    course = context.get("course")
    student_group = context.get("student_group")

    if doctype in MATERIAL_SHARED_ANCHORS:
        return course in set(scope.get("shared_courses") or [])
    if doctype in MATERIAL_CLASS_OWNED_ANCHORS:
        return student_group in set(scope.get("class_groups") or [])
    return False


def assert_can_manage_material_anchor(anchor_doctype: str, anchor_name: str, *, user: str | None = None) -> None:
    resolved_user = _normalize_text(user or frappe.session.user)
    _anchor_exists(anchor_doctype, anchor_name)
    if not user_can_manage_material_anchor(resolved_user, anchor_doctype, anchor_name):
        frappe.throw(_("You do not have permission to manage materials in this context."), frappe.PermissionError)


def user_can_read_supporting_material(user: str, material_name: str, *, course: str | None = None) -> bool:
    user = _normalize_text(user)
    material_name = _normalize_text(material_name)
    if not user or user == "Guest" or not material_name:
        return False

    placements = frappe.get_all(
        "Material Placement",
        filters={"supporting_material": material_name},
        fields=["anchor_doctype", "anchor_name"],
        limit=0,
    )
    if placements:
        return any(
            user_can_read_material_anchor(user, row.get("anchor_doctype"), row.get("anchor_name"))
            for row in placements
            if row.get("anchor_doctype") and row.get("anchor_name")
        )
    return user_can_read_course_material(
        user, course or frappe.db.get_value("Supporting Material", material_name, "course")
    )


def user_can_manage_supporting_material(user: str, material_name: str, *, course: str | None = None) -> bool:
    user = _normalize_text(user)
    material_name = _normalize_text(material_name)
    if not user or user == "Guest" or not material_name:
        return False

    placements = frappe.get_all(
        "Material Placement",
        filters={"supporting_material": material_name},
        fields=["anchor_doctype", "anchor_name"],
        limit=0,
    )
    if placements:
        return any(
            user_can_manage_material_anchor(user, row.get("anchor_doctype"), row.get("anchor_name"))
            for row in placements
            if row.get("anchor_doctype") and row.get("anchor_name")
        )
    return user_can_manage_course_material(
        user, course or frappe.db.get_value("Supporting Material", material_name, "course")
    )


def user_can_read_course_material(user: str, course: str) -> bool:
    user = _normalize_text(user)
    course = _normalize_text(course)
    if not user or user == "Guest" or not course:
        return False

    roles = set(frappe.get_roles(user) or [])
    if roles & _ADMIN_ROLES:
        return True

    if _student_has_course_access(user, course):
        return True

    if _staff_has_course_access(user, course, roles):
        return True

    return False


def user_can_manage_course_material(user: str, course: str) -> bool:
    user = _normalize_text(user)
    course = _normalize_text(course)
    if not user or user == "Guest" or not course:
        return False

    roles = set(frappe.get_roles(user) or [])
    if roles & _ADMIN_ROLES:
        return True

    return _staff_can_manage_course(user, course, roles)


def get_material_permission_query_conditions(
    *, user: str | None = None, table_alias: str, manage_only: bool = False
) -> str | None:
    user = _normalize_text(user or frappe.session.user)
    if not user or user == "Guest":
        return "1=0"

    if table_alias == "`tabMaterial Placement`":
        return _material_placement_scope_sql(table_alias, user=user, manage_only=manage_only)

    placement_scope_sql = _material_placement_scope_sql("mp", user=user, manage_only=manage_only)
    if placement_scope_sql is None:
        return None

    scope = _visibility_scope(user, manage_only=manage_only)
    shared_courses = scope.get("shared_courses") or []
    fallback_course_sql = f"{table_alias}.course in ({_sql_in_list(shared_courses)})" if shared_courses else "1=0"
    return f"""(
        EXISTS (
            SELECT 1
            FROM `tabMaterial Placement` mp
            WHERE mp.supporting_material = {table_alias}.name
              AND {placement_scope_sql}
        )
        OR (
            NOT EXISTS (
                SELECT 1
                FROM `tabMaterial Placement` mp_unplaced
                WHERE mp_unplaced.supporting_material = {table_alias}.name
            )
            AND {fallback_course_sql}
        )
    )"""


def _student_has_course_access(user: str, course: str) -> bool:
    student = _normalize_text(frappe.db.get_value("Student", {"student_email": user}, "name"))
    if not student:
        return False

    if frappe.db.sql(
        """
        SELECT 1
        FROM `tabProgram Enrollment Course` pec
        JOIN `tabProgram Enrollment` pe ON pe.name = pec.parent
        WHERE pe.student = %(student)s
          AND pec.course = %(course)s
          AND COALESCE(pec.status, 'Enrolled') <> 'Dropped'
        LIMIT 1
        """,
        {"student": student, "course": course},
    ):
        return True

    return bool(
        frappe.db.exists(
            "Student Group",
            {
                "course": course,
                "status": "Active",
                "name": [
                    "in",
                    frappe.get_all(
                        "Student Group Student",
                        filters={"student": student, "active": 1},
                        pluck="parent",
                    )
                    or [""],
                ],
            },
        )
    )


def _staff_has_course_access(user: str, course: str, roles: set[str]) -> bool:
    if _staff_can_manage_course(user, course, roles):
        return True

    if "Curriculum Coordinator" not in roles:
        return False

    return course in set(_get_coordinator_course_names(user))


def _staff_can_manage_course(user: str, course: str, roles: set[str]) -> bool:
    group_names = list(student_groups_api._instructor_group_names(user) or [])
    if group_names and frappe.db.exists("Student Group", {"name": ["in", group_names], "course": course}):
        return True

    return False


def _get_material_readable_courses(user: str, roles: set[str]) -> list[str]:
    courses = set(_get_material_manageable_courses(user, roles))
    if "Curriculum Coordinator" in roles:
        courses.update(_get_coordinator_course_names(user))
    return sorted(course for course in courses if course)


def _get_material_manageable_courses(user: str, roles: set[str]) -> list[str]:
    if roles & _ADMIN_ROLES:
        return []
    return sorted(course for course in _get_instructor_course_names(user) if course)


def _get_instructor_course_names(user: str) -> list[str]:
    group_names = list(student_groups_api._instructor_group_names(user) or [])
    if not group_names:
        return []

    return (
        frappe.get_all(
            "Student Group",
            filters={"name": ["in", group_names]},
            pluck="course",
        )
        or []
    )


def _get_coordinator_course_names(user: str) -> list[str]:
    employee = _normalize_text(
        frappe.db.get_value("Employee", {"user_id": user, "employment_status": "Active"}, "name")
    )
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
    return [_normalize_text(row.get("course")) for row in rows or [] if _normalize_text(row.get("course"))]
