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
MATERIAL_ALLOWED_ANCHORS = {"Course", "Learning Unit", "Lesson", "Task"}
MATERIAL_FILE_SLOT = "material_file"
MATERIAL_BINDING_ROLE = "general_reference"
MATERIAL_DATA_CLASS = "academic"
MATERIAL_PURPOSE = "general_reference"
MATERIAL_RETENTION_POLICY = "until_program_end_plus_1y"

_ADMIN_ROLES = {"Administrator", "System Manager", "Academic Admin"}


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


def validate_reference_url(value: str) -> str:
    reference_url = _normalize_text(value)
    if not reference_url:
        frappe.throw(_("Reference URL is required."))

    parsed = urlparse(reference_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        frappe.throw(_("Reference URL must be a valid http or https URL."))
    return reference_url


def resolve_anchor_course(anchor_doctype: str, anchor_name: str) -> str:
    anchor_doctype = _normalize_text(anchor_doctype)
    anchor_name = _normalize_text(anchor_name)
    if anchor_doctype not in MATERIAL_ALLOWED_ANCHORS:
        frappe.throw(_("Unsupported material anchor type: {0}").format(anchor_doctype))
    if not anchor_name:
        frappe.throw(_("Anchor Name is required."))

    if anchor_doctype == "Course":
        if not frappe.db.exists("Course", anchor_name):
            frappe.throw(_("Course does not exist: {0}").format(anchor_name))
        return anchor_name

    if anchor_doctype == "Learning Unit":
        course = frappe.db.get_value("Learning Unit", anchor_name, "course")
    elif anchor_doctype == "Lesson":
        course = frappe.db.get_value("Lesson", anchor_name, "course")
        if not course:
            learning_unit = frappe.db.get_value("Lesson", anchor_name, "learning_unit")
            course = frappe.db.get_value("Learning Unit", learning_unit, "course") if learning_unit else None
    else:
        course = frappe.db.get_value("Task", anchor_name, "default_course")

    course = _normalize_text(course)
    if not course:
        frappe.throw(
            _("Could not resolve the authoritative Course for {doctype} {name}.").format(
                doctype=anchor_doctype, name=anchor_name
            )
        )
    return course


def resolve_material_origin(anchor_doctype: str) -> str:
    return "task" if _normalize_text(anchor_doctype) == "Task" else "curriculum"


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
    anchor_doc = _ensure_known_doctype(anchor_doctype, anchor_name)
    anchor_doc.check_permission("write")

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
    anchor_doc = _ensure_known_doctype(anchor_doctype, anchor_name)
    anchor_doc.check_permission("write")

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
    anchor_doc = _ensure_known_doctype(anchor_doctype, anchor_name)
    anchor_doc.check_permission("write")

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

    roles = set(frappe.get_roles(user) or [])
    if roles & _ADMIN_ROLES:
        return None

    courses = (
        _get_material_manageable_courses(user, roles) if manage_only else _get_material_readable_courses(user, roles)
    )
    if not courses:
        return "1=0"

    in_list = ", ".join(frappe.db.escape(course) for course in courses)
    return f"{table_alias}.course in ({in_list})"


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
