# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Unit Plan"):
        return

    if frappe.db.table_exists("Learning Unit"):
        learning_units = frappe.get_all(
            "Learning Unit",
            fields=[
                "name",
                "course",
                "program",
                "unit_name",
                "unit_code",
                "duration",
                "unit_order",
                "unit_status",
                "version",
                "estimated_duration",
                "is_published",
                "unit_overview",
                "essential_understanding",
                "misconceptions",
                "content",
                "skills",
                "concepts",
            ],
            order_by="course asc, unit_order asc, creation asc",
            limit=0,
        )

        course_plan_by_course: dict[str, str] = {}
        for row in learning_units or []:
            course = (row.get("course") or "").strip()
            if not course:
                continue

            course_plan = course_plan_by_course.get(course)
            if not course_plan:
                course_plan = _resolve_course_plan_for_course(course)
                course_plan_by_course[course] = course_plan

            if frappe.db.exists("Unit Plan", row["name"]):
                _update_existing_unit_plan(row["name"], course_plan, row)
            else:
                _create_unit_plan(row["name"], course_plan, row)

            _copy_child_rows(
                child_doctype="Learning Unit Standard Alignment",
                source_parent=row["name"],
                target_parent=row["name"],
                parentfield="standards",
            )
            _copy_child_rows(
                child_doctype="Curriculum Planning Reflection",
                source_parent=row["name"],
                target_parent=row["name"],
                parentfield="reflections",
            )

    _backfill_unit_plan_link("Lesson", "learning_unit", "unit_plan")
    _backfill_unit_plan_link("Task", "learning_unit", "unit_plan")

    if frappe.db.table_exists("Material Placement"):
        frappe.db.sql(
            """
            UPDATE `tabMaterial Placement`
            SET anchor_doctype = 'Unit Plan'
            WHERE anchor_doctype = 'Learning Unit'
            """
        )


def _resolve_course_plan_for_course(course: str) -> str:
    existing = frappe.get_all(
        "Course Plan",
        filters={"course": course, "plan_status": ["!=", "Archived"]},
        fields=["name"],
        order_by="modified desc, creation desc",
        limit=2,
    )
    if len(existing) == 1:
        return existing[0]["name"]

    title = "Migrated Unit Plan Backbone"
    existing_name = frappe.db.get_value("Course Plan", {"course": course, "title": title}, "name")
    if existing_name:
        return existing_name

    doc = frappe.new_doc("Course Plan")
    doc.title = title
    doc.course = course
    doc.plan_status = "Active"
    doc.insert(ignore_permissions=True)
    return doc.name


def _create_unit_plan(target_name: str, course_plan: str, row: dict) -> None:
    doc = frappe.new_doc("Unit Plan")
    doc.name = target_name
    doc.title = (row.get("unit_name") or "").strip() or target_name
    doc.course_plan = course_plan
    doc.program = row.get("program")
    doc.unit_code = row.get("unit_code")
    doc.unit_order = row.get("unit_order")
    doc.unit_status = row.get("unit_status") or "Active"
    doc.version = row.get("version")
    doc.duration = row.get("duration")
    doc.estimated_duration = row.get("estimated_duration")
    doc.is_published = row.get("is_published") or 0
    doc.overview = row.get("unit_overview")
    doc.essential_understanding = row.get("essential_understanding")
    doc.misconceptions = row.get("misconceptions")
    doc.content = row.get("content")
    doc.skills = row.get("skills")
    doc.concepts = row.get("concepts")
    doc.insert(ignore_permissions=True)
    if doc.name != target_name and not frappe.db.exists("Unit Plan", target_name):
        frappe.rename_doc("Unit Plan", doc.name, target_name, force=True)


def _update_existing_unit_plan(unit_plan: str, course_plan: str, row: dict) -> None:
    updates = {
        "course_plan": course_plan,
        "program": row.get("program"),
        "unit_code": row.get("unit_code"),
        "unit_order": row.get("unit_order"),
        "unit_status": row.get("unit_status") or "Active",
        "version": row.get("version"),
        "duration": row.get("duration"),
        "estimated_duration": row.get("estimated_duration"),
        "is_published": row.get("is_published") or 0,
        "overview": row.get("unit_overview"),
        "essential_understanding": row.get("essential_understanding"),
        "misconceptions": row.get("misconceptions"),
        "content": row.get("content"),
        "skills": row.get("skills"),
        "concepts": row.get("concepts"),
    }
    if not frappe.db.get_value("Unit Plan", unit_plan, "title"):
        updates["title"] = (row.get("unit_name") or "").strip() or unit_plan
    frappe.db.set_value("Unit Plan", unit_plan, updates, update_modified=False)


def _copy_child_rows(*, child_doctype: str, source_parent: str, target_parent: str, parentfield: str) -> None:
    if not frappe.db.table_exists(child_doctype):
        return

    frappe.db.delete(child_doctype, {"parent": target_parent, "parenttype": "Unit Plan", "parentfield": parentfield})

    rows = frappe.get_all(
        child_doctype,
        filters={"parent": source_parent, "parenttype": "Learning Unit"},
        fields=["*"],
        order_by="idx asc",
        limit=0,
    )
    meta = frappe.get_meta(child_doctype)
    fieldnames = [
        field.fieldname
        for field in meta.fields
        if field.fieldname not in {"parent", "parenttype", "parentfield", "idx"}
    ]

    for idx, row in enumerate(rows or [], start=1):
        doc = frappe.new_doc(child_doctype)
        for fieldname in fieldnames:
            if fieldname in row:
                setattr(doc, fieldname, row.get(fieldname))
        doc.parent = target_parent
        doc.parenttype = "Unit Plan"
        doc.parentfield = parentfield
        doc.idx = idx
        doc.db_insert(ignore_if_duplicate=False)


def _backfill_unit_plan_link(doctype: str, source_field: str, target_field: str) -> None:
    if not frappe.db.table_exists(doctype):
        return
    if not frappe.db.has_column(doctype, source_field) or not frappe.db.has_column(doctype, target_field):
        return

    if doctype == "Lesson" and source_field == "learning_unit" and target_field == "unit_plan":
        frappe.db.sql(
            """
            UPDATE `tabLesson`
            SET `unit_plan` = `learning_unit`
            WHERE COALESCE(`unit_plan`, '') = ''
              AND COALESCE(`learning_unit`, '') != ''
            """
        )
        return

    if doctype == "Task" and source_field == "learning_unit" and target_field == "unit_plan":
        frappe.db.sql(
            """
            UPDATE `tabTask`
            SET `unit_plan` = `learning_unit`
            WHERE COALESCE(`unit_plan`, '') = ''
              AND COALESCE(`learning_unit`, '') != ''
            """
        )
