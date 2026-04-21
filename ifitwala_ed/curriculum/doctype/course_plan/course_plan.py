# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from ifitwala_ed.curriculum import materials as materials_domain
from ifitwala_ed.curriculum import planning

ACTIVATION_MODE_MANUAL = "Manual"
ACTIVATION_MODE_ACADEMIC_YEAR_START = "Academic Year Start"
_VALID_ACTIVATION_MODES = {ACTIVATION_MODE_MANUAL, ACTIVATION_MODE_ACADEMIC_YEAR_START}
_AUTO_ACTIVATION_LOCK_KEY = "curriculum:course_plan:auto_activate"


class CoursePlan(Document):
    def before_validate(self):
        self.title = planning.normalize_text(self.title)
        self.course = planning.normalize_text(self.course)
        self.academic_year = planning.normalize_text(self.academic_year) or None
        self.cycle_label = planning.normalize_text(self.cycle_label) or None
        self.activation_mode = _normalize_activation_mode(getattr(self, "activation_mode", None))
        self.rollover_source_course_plan = (
            planning.normalize_text(getattr(self, "rollover_source_course_plan", None)) or None
        )
        self.summary = planning.normalize_long_text(self.summary)
        if not self.title and self.course:
            self.title = self.course

    def validate(self):
        if not self.title and self.course:
            self.title = self.course
        if self.activation_mode == ACTIVATION_MODE_ACADEMIC_YEAR_START and not self.academic_year:
            frappe.throw(
                _("Academic Year is required when activation is scheduled for the academic year start."),
                frappe.ValidationError,
            )
        if self.rollover_source_course_plan and self.rollover_source_course_plan == self.name:
            frappe.throw(_("A course plan cannot list itself as its rollover source."), frappe.ValidationError)

        course_school = _resolve_course_school(self.course, fallback=getattr(self, "school", None))
        _validate_course_plan_academic_year(
            course_school=course_school,
            academic_year=self.academic_year,
            previous_academic_year=self.get_db_value("academic_year") if hasattr(self, "get_db_value") else None,
        )
        _validate_unique_active_course_plan(self)


def _normalize_activation_mode(value: str | None) -> str:
    activation_mode = planning.normalize_text(value) or ACTIVATION_MODE_MANUAL
    if activation_mode not in _VALID_ACTIVATION_MODES:
        frappe.throw(_("Unsupported activation mode: {0}").format(activation_mode), frappe.ValidationError)
    return activation_mode


def _resolve_course_school(course: str | None, *, fallback: str | None = None) -> str | None:
    fallback_name = planning.normalize_text(fallback) or None
    course_name = planning.normalize_text(course)
    if not course_name:
        return fallback_name
    return planning.normalize_text(frappe.db.get_value("Course", course_name, "school")) or fallback_name


def _validate_course_plan_academic_year(
    *,
    course_school: str | None,
    academic_year: str | None,
    previous_academic_year: str | None = None,
) -> None:
    from ifitwala_ed.api import teaching_plans as teaching_plans_api

    teaching_plans_api._validate_course_plan_academic_year(
        course_school=course_school,
        academic_year=academic_year,
        previous_academic_year=previous_academic_year,
    )


def _resolve_academic_year_scope(school: str | None) -> list[str]:
    school_name = planning.normalize_text(school)
    if not school_name:
        return []

    from ifitwala_ed.api import teaching_plans as teaching_plans_api

    return list(teaching_plans_api._academic_year_scope_for_school(school_name) or [school_name])


def _validate_unique_active_course_plan(doc: CoursePlan) -> None:
    if planning.normalize_text(getattr(doc, "plan_status", None)) != "Active":
        return

    course_name = planning.normalize_text(getattr(doc, "course", None))
    if not course_name:
        return

    academic_year = planning.normalize_text(getattr(doc, "academic_year", None))
    duplicate = frappe.db.sql(
        """
        SELECT name
        FROM `tabCourse Plan`
        WHERE course = %(course)s
          AND plan_status = 'Active'
          AND COALESCE(academic_year, '') = %(academic_year)s
          AND name != %(name)s
        LIMIT 1
        """,
        {
            "course": course_name,
            "academic_year": academic_year,
            "name": planning.normalize_text(getattr(doc, "name", None)) or "",
        },
        as_dict=True,
    )
    if not duplicate:
        return

    if academic_year:
        frappe.throw(
            _("Only one active Course Plan is allowed for this Course and Academic Year."),
            frappe.ValidationError,
        )
    frappe.throw(
        _("Only one active Course Plan without an Academic Year is allowed for this Course."),
        frappe.ValidationError,
    )


def _material_rows_for_anchor(anchor_doctype: str, anchor_name: str) -> list[dict]:
    return frappe.get_all(
        "Material Placement",
        filters={"anchor_doctype": anchor_doctype, "anchor_name": anchor_name},
        fields=["supporting_material", "usage_role", "placement_note", "placement_order", "origin"],
        order_by="placement_order asc, creation asc",
        limit=0,
    )


def _copy_anchor_material_placements(
    *,
    source_anchor_doctype: str,
    source_anchor_name: str,
    target_anchor_doctype: str,
    target_anchor_name: str,
) -> int:
    copied = 0
    for row in _material_rows_for_anchor(source_anchor_doctype, source_anchor_name):
        materials_domain.create_material_placement(
            supporting_material=row.get("supporting_material"),
            anchor_doctype=target_anchor_doctype,
            anchor_name=target_anchor_name,
            usage_role=row.get("usage_role"),
            placement_note=row.get("placement_note"),
            origin=row.get("origin"),
            placement_order=row.get("placement_order"),
        )
        copied += 1
    return copied


def _serialize_standard_rows(source_doc) -> list[dict]:
    return [
        {
            "learning_standard": row.learning_standard,
            "framework_name": row.framework_name,
            "framework_version": row.framework_version,
            "subject_area": row.subject_area,
            "program": row.program,
            "strand": row.strand,
            "substrand": row.substrand,
            "standard_code": row.standard_code,
            "standard_description": row.standard_description,
            "coverage_level": row.coverage_level,
            "alignment_strength": row.alignment_strength,
            "alignment_type": row.alignment_type,
            "notes": row.notes,
        }
        for row in (source_doc.get("standards") or [])
    ]


def _create_rollover_course_plan(
    *,
    source_doc,
    target_academic_year: str,
    activation_mode: str,
    copy_plan_resources: int,
    copy_unit_resources: int,
) -> dict[str, int | str]:
    target_academic_year = planning.normalize_text(target_academic_year)
    activation_mode = _normalize_activation_mode(activation_mode)
    course_school = _resolve_course_school(source_doc.course, fallback=getattr(source_doc, "school", None))

    if not target_academic_year:
        frappe.throw(_("Target Academic Year is required."), frappe.ValidationError)
    if target_academic_year == planning.normalize_text(source_doc.academic_year):
        frappe.throw(
            _("Choose a different Academic Year for the rollover target."),
            frappe.ValidationError,
        )

    _validate_course_plan_academic_year(course_school=course_school, academic_year=target_academic_year)

    existing_target = frappe.db.exists(
        "Course Plan",
        {
            "course": source_doc.course,
            "academic_year": target_academic_year,
            "plan_status": ["!=", "Archived"],
            "name": ["!=", source_doc.name],
        },
    )
    if existing_target:
        frappe.throw(
            _(
                "Course {course} already has a non-archived Course Plan for Academic Year {academic_year}: {course_plan}"
            ).format(course=source_doc.course, academic_year=target_academic_year, course_plan=existing_target),
            frappe.ValidationError,
        )

    frappe.db.savepoint("course_plan_rollover")
    try:
        target_doc = frappe.new_doc("Course Plan")
        target_doc.title = source_doc.title
        target_doc.course = source_doc.course
        target_doc.academic_year = target_academic_year
        target_doc.cycle_label = source_doc.cycle_label
        target_doc.plan_status = "Draft"
        target_doc.activation_mode = activation_mode
        target_doc.rollover_source_course_plan = source_doc.name
        target_doc.summary = source_doc.summary
        target_doc.insert(ignore_permissions=True)

        created_units = 0
        copied_unit_resources = 0
        source_units = planning.get_unit_plan_rows(source_doc.name)
        for source_unit_row in source_units:
            source_unit = frappe.get_doc("Unit Plan", source_unit_row.get("name"))
            target_unit = frappe.new_doc("Unit Plan")
            target_unit.course_plan = target_doc.name
            target_unit.title = source_unit.title
            target_unit.program = source_unit.program
            target_unit.unit_code = source_unit.unit_code
            target_unit.unit_order = source_unit.unit_order
            target_unit.unit_status = "Draft"
            target_unit.version = source_unit.version
            target_unit.duration = source_unit.duration
            target_unit.estimated_duration = source_unit.estimated_duration
            target_unit.is_published = 0
            target_unit.overview = source_unit.overview
            target_unit.essential_understanding = source_unit.essential_understanding
            target_unit.misconceptions = source_unit.misconceptions
            target_unit.content = source_unit.content
            target_unit.skills = source_unit.skills
            target_unit.concepts = source_unit.concepts
            planning.replace_unit_plan_standards(target_unit, _serialize_standard_rows(source_unit))
            planning.ensure_linked_unit_plan_standards(target_unit)
            target_unit.set("reflections", [])
            target_unit.insert(ignore_permissions=True)
            created_units += 1

            if copy_unit_resources:
                copied_unit_resources += _copy_anchor_material_placements(
                    source_anchor_doctype="Unit Plan",
                    source_anchor_name=source_unit.name,
                    target_anchor_doctype="Unit Plan",
                    target_anchor_name=target_unit.name,
                )

        copied_plan_resources = 0
        if copy_plan_resources:
            copied_plan_resources = _copy_anchor_material_placements(
                source_anchor_doctype="Course Plan",
                source_anchor_name=source_doc.name,
                target_anchor_doctype="Course Plan",
                target_anchor_name=target_doc.name,
            )

        return {
            "course_plan": target_doc.name,
            "units_created": created_units,
            "plan_resources_copied": copied_plan_resources,
            "unit_resources_copied": copied_unit_resources,
        }
    except Exception:
        frappe.db.rollback(save_point="course_plan_rollover")
        raise


def _course_plan_rows_for_scope(scope_schools: list[str], source_academic_years: list[str]) -> list[dict]:
    if not scope_schools or not source_academic_years:
        return []
    return frappe.get_all(
        "Course Plan",
        filters={
            "school": ["in", scope_schools],
            "academic_year": ["in", source_academic_years],
            "plan_status": "Active",
        },
        fields=["name", "title", "course", "school", "academic_year"],
        order_by="school asc, course asc, modified desc",
        limit=0,
    )


def build_curriculum_handover_preview(
    *,
    school_scope: list[str],
    source_academic_years: list[str],
    target_academic_year_name: str,
    user: str,
    roles: list[str] | tuple[str, ...] | None = None,
) -> dict:
    roles = list(roles or frappe.get_roles(user) or [])
    school_scope = [planning.normalize_text(row) for row in school_scope if planning.normalize_text(row)]
    source_academic_years = [
        planning.normalize_text(row) for row in source_academic_years if planning.normalize_text(row)
    ]
    target_academic_year_name = planning.normalize_text(target_academic_year_name)
    target_year_rows = frappe.get_all(
        "Academic Year",
        filters={
            "academic_year_name": target_academic_year_name,
            "school": ["in", school_scope],
        },
        fields=["name", "school"],
        limit=0,
    )
    target_year_by_school = {
        planning.normalize_text(row.get("school")): planning.normalize_text(row.get("name"))
        for row in target_year_rows
        if planning.normalize_text(row.get("school")) and planning.normalize_text(row.get("name"))
    }

    rows = []
    summary = {
        "source_plan_count": 0,
        "ready_count": 0,
        "existing_count": 0,
        "missing_target_academic_year_count": 0,
        "no_permission_count": 0,
    }
    for row in _course_plan_rows_for_scope(school_scope, source_academic_years):
        summary["source_plan_count"] += 1
        school_name = planning.normalize_text(row.get("school"))
        target_year = target_year_by_school.get(school_name)
        status = "ready"
        if not target_year:
            status = "missing_target_academic_year"
            summary["missing_target_academic_year_count"] += 1
        elif not planning.user_can_manage_course_curriculum(user, row.get("course"), roles):
            status = "no_permission"
            summary["no_permission_count"] += 1
        elif frappe.db.exists(
            "Course Plan",
            {
                "course": row.get("course"),
                "academic_year": target_year,
                "plan_status": ["!=", "Archived"],
                "name": ["!=", row.get("name")],
            },
        ):
            status = "existing_target"
            summary["existing_count"] += 1
        else:
            summary["ready_count"] += 1

        rows.append(
            {
                "source_course_plan": row.get("name"),
                "title": row.get("title"),
                "course": row.get("course"),
                "school": school_name,
                "source_academic_year": row.get("academic_year"),
                "target_academic_year": target_year,
                "status": status,
            }
        )

    return {"summary": summary, "rows": rows}


@frappe.whitelist()
def create_rollover_course_plan(
    course_plan: str,
    target_academic_year: str,
    activation_mode: str | None = None,
    copy_plan_resources: int | None = 1,
    copy_unit_resources: int | None = 1,
) -> dict[str, int | str]:
    source_name = planning.normalize_text(course_plan)
    source_doc = frappe.get_doc("Course Plan", source_name)
    user = frappe.session.user
    roles = frappe.get_roles(user)
    planning.assert_can_manage_course_curriculum(
        user,
        source_doc.course,
        roles,
        action_label=_("create a rollover course plan for this course"),
    )

    created = _create_rollover_course_plan(
        source_doc=source_doc,
        target_academic_year=target_academic_year,
        activation_mode=activation_mode or ACTIVATION_MODE_MANUAL,
        copy_plan_resources=planning.normalize_flag(copy_plan_resources),
        copy_unit_resources=planning.normalize_flag(copy_unit_resources),
    )
    return {
        **created,
        "activation_mode": _normalize_activation_mode(activation_mode),
    }


def activate_due_course_plan_rollovers() -> dict[str, int]:
    logger = frappe.logger("ifitwala.curriculum", allow_site=True)
    rows = frappe.get_all(
        "Course Plan",
        filters={
            "plan_status": "Draft",
            "activation_mode": ACTIVATION_MODE_ACADEMIC_YEAR_START,
        },
        fields=["name", "academic_year"],
        limit=0,
    )
    today = getdate(nowdate())
    summary = {"evaluated_count": len(rows or []), "due_count": 0, "activated_count": 0, "skipped_count": 0}
    cache = frappe.cache()
    with cache.lock(_AUTO_ACTIVATION_LOCK_KEY, timeout=60 * 15):
        for row in rows or []:
            academic_year = planning.normalize_text(row.get("academic_year"))
            if not academic_year:
                summary["skipped_count"] += 1
                continue

            start_date = frappe.db.get_value("Academic Year", academic_year, "year_start_date")
            if not start_date or getdate(start_date) > today:
                continue

            summary["due_count"] += 1
            try:
                doc = frappe.get_doc("Course Plan", row.get("name"))
                if planning.normalize_text(doc.plan_status) != "Draft":
                    summary["skipped_count"] += 1
                    continue
                doc.plan_status = "Active"
                doc.save(ignore_permissions=True)
                summary["activated_count"] += 1
            except Exception:
                summary["skipped_count"] += 1
                logger.exception("Failed to auto-activate Course Plan %s", row.get("name"))
    return summary


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def rollover_academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
    filters = filters or {}
    course_plan_name = planning.normalize_text(filters.get("course_plan"))
    if not course_plan_name:
        return []

    source_doc = frappe.get_doc("Course Plan", course_plan_name)
    user = frappe.session.user
    roles = frappe.get_roles(user)
    planning.assert_can_manage_course_curriculum(
        user,
        source_doc.course,
        roles,
        action_label=_("prepare a rollover course plan for this course"),
    )

    school_scope = _resolve_academic_year_scope(_resolve_course_school(source_doc.course, fallback=source_doc.school))
    if not school_scope:
        return []

    placeholders = ", ".join(["%s"] * len(school_scope))
    search_txt = f"%{txt or ''}%"
    return frappe.db.sql(
        f"""
        SELECT name
        FROM `tabAcademic Year`
        WHERE school IN ({placeholders})
          AND name LIKE %s
        ORDER BY year_start_date DESC, name DESC
        LIMIT %s, %s
        """,
        [*school_scope, search_txt, start, page_len],
    )
