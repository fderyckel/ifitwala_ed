# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import os
from urllib.parse import urlparse

import frappe

_LEGACY_PARENTFIELD = "attachments"
_TASK_RESOURCE_ROLE = "task_resource"
_TASK_RESOURCE_SLOT_PREFIX = "supporting_material__"
_MATERIAL_ROLE = "supporting_material"
_MATERIAL_SLOT = "material_file"
_ACTIVE_DRIVE_FILE_STATUSES = ["active", "processing", "blocked"]


def execute():
    if not _table_exists("Task") or not _table_exists("Attached Document"):
        return

    migrated_drive_files: set[str] = set()
    for row in _legacy_attachment_rows():
        migrated_drive_file = _migrate_legacy_attachment_row(row)
        if migrated_drive_file:
            migrated_drive_files.add(migrated_drive_file)

    _migrate_active_orphan_task_resources(migrated_drive_files)


def _table_exists(doctype: str) -> bool:
    table_exists = getattr(frappe.db, "table_exists", None)
    if not callable(table_exists):
        return True
    return bool(table_exists(doctype))


def _clean(value) -> str:
    return str(value or "").strip()


def _legacy_attachment_rows() -> list[dict]:
    return frappe.get_all(
        "Attached Document",
        filters={
            "parenttype": "Task",
            "parentfield": _LEGACY_PARENTFIELD,
        },
        fields=[
            "name",
            "parent",
            "idx",
            "section_break_sbex",
            "file",
            "external_url",
            "description",
            "file_name",
            "file_size",
        ],
        order_by="parent asc, idx asc, name asc",
        limit=0,
    )


def _migrate_legacy_attachment_row(row: dict) -> str | None:
    row_name = _clean(row.get("name"))
    task = _clean(row.get("parent"))
    file_url = _clean(row.get("file"))
    external_url = _clean(row.get("external_url"))

    if not task:
        _delete_legacy_row(row_name)
        return None
    if not frappe.db.exists("Task", task):
        frappe.throw(f"Cannot migrate Task attachment {row_name}: Task {task} does not exist.")

    if file_url:
        drive_file = _migrate_file_attachment_row(task, row)
        _delete_legacy_row(row_name)
        return drive_file

    if external_url:
        _migrate_reference_attachment_row(task, row)
        _delete_legacy_row(row_name)
        return None

    _delete_legacy_row(row_name)
    return None


def _migrate_file_attachment_row(task: str, row: dict) -> str:
    file_row = _resolve_legacy_file(task, row)
    drive_file = _resolve_legacy_drive_file(
        task=task,
        file_id=_clean(file_row.get("name")),
        row_name=_clean(row.get("name")),
    )
    if not drive_file:
        frappe.throw(
            "Cannot migrate Task attachment {row}: governed Drive file was not found.".format(
                row=_clean(row.get("name"))
            )
        )

    material = _find_existing_file_material(task, _clean(file_row.get("name")))
    if not material:
        material = _create_file_material(task, row, file_row)
        _rehome_file_projection(_clean(file_row.get("name")), material)
        _rehome_drive_file_and_binding(drive_file, _clean(file_row.get("name")), task, material)
        _finalize_file_material(material, file_row)

    _ensure_task_material_placement(material, task, row)
    return _clean(drive_file.get("name"))


def _migrate_reference_attachment_row(task: str, row: dict) -> None:
    reference_url = _clean(row.get("external_url"))
    _validate_reference_url(reference_url, row_name=_clean(row.get("name")))
    material = _find_existing_reference_material(task, reference_url)
    if not material:
        material_doc = frappe.get_doc(
            {
                "doctype": "Supporting Material",
                "title": _material_title(row),
                "course": _task_course(task),
                "material_type": "Reference Link",
                "reference_url": reference_url,
                "description": _clean(row.get("description")) or None,
                "modality": "Read",
            }
        )
        material_doc.insert(ignore_permissions=True)
        material = material_doc.name
    _ensure_task_material_placement(material, task, row)


def _resolve_legacy_file(task: str, row: dict) -> dict:
    file_url = _clean(row.get("file"))
    file_row = frappe.db.get_value(
        "File",
        {
            "attached_to_doctype": "Task",
            "attached_to_name": task,
            "file_url": file_url,
        },
        ["name", "file_url", "file_name", "file_size"],
        as_dict=True,
    )
    if not file_row:
        frappe.throw(
            "Cannot migrate Task attachment {row}: native File projection was not found.".format(
                row=_clean(row.get("name"))
            )
        )
    return dict(file_row)


def _resolve_legacy_drive_file(*, task: str, file_id: str, row_name: str | None = None) -> dict | None:
    if not _table_exists("Drive File"):
        return None

    slot = f"{_TASK_RESOURCE_SLOT_PREFIX}{row_name}" if row_name else None
    filters = {
        "owner_doctype": "Task",
        "owner_name": task,
        "file": file_id,
        "status": ["in", _ACTIVE_DRIVE_FILE_STATUSES],
    }
    if slot:
        filters["slot"] = slot
    drive_file = frappe.db.get_value(
        "Drive File",
        filters,
        ["name", "file", "slot", "organization", "school", "status"],
        as_dict=True,
    )
    if drive_file:
        return dict(drive_file)

    if not _table_exists("Drive Binding"):
        return None
    binding_filters = {
        "binding_doctype": "Task",
        "binding_name": task,
        "binding_role": _TASK_RESOURCE_ROLE,
        "file": file_id,
        "status": "active",
    }
    if slot:
        binding_filters["slot"] = slot
    drive_file_id = frappe.db.get_value("Drive Binding", binding_filters, "drive_file")
    if not drive_file_id:
        return None
    drive_file = frappe.db.get_value(
        "Drive File",
        drive_file_id,
        ["name", "file", "slot", "organization", "school", "status"],
        as_dict=True,
    )
    return dict(drive_file) if drive_file else None


def _find_existing_file_material(task: str, file_id: str) -> str | None:
    rows = frappe.db.sql(
        """
        SELECT sm.name
        FROM `tabSupporting Material` sm
        INNER JOIN `tabMaterial Placement` mp ON mp.supporting_material = sm.name
        WHERE mp.anchor_doctype = 'Task'
          AND mp.anchor_name = %(task)s
          AND sm.file = %(file)s
        ORDER BY mp.creation ASC, mp.name ASC
        LIMIT 1
        """,
        {"task": task, "file": file_id},
        as_dict=True,
    )
    return _clean((rows or [{}])[0].get("name")) or None


def _find_existing_reference_material(task: str, reference_url: str) -> str | None:
    rows = frappe.db.sql(
        """
        SELECT sm.name
        FROM `tabSupporting Material` sm
        INNER JOIN `tabMaterial Placement` mp ON mp.supporting_material = sm.name
        WHERE mp.anchor_doctype = 'Task'
          AND mp.anchor_name = %(task)s
          AND sm.reference_url = %(reference_url)s
        ORDER BY mp.creation ASC, mp.name ASC
        LIMIT 1
        """,
        {"task": task, "reference_url": reference_url},
        as_dict=True,
    )
    return _clean((rows or [{}])[0].get("name")) or None


def _create_file_material(task: str, row: dict, file_row: dict) -> str:
    material_doc = frappe.get_doc(
        {
            "doctype": "Supporting Material",
            "title": _material_title(row, file_row=file_row),
            "course": _task_course(task),
            "material_type": "File",
            "description": _clean(row.get("description")) or None,
            "modality": "Read",
        }
    )
    material_doc.flags.allow_missing_file = True
    material_doc.insert(ignore_permissions=True)
    return material_doc.name


def _finalize_file_material(material: str, file_row: dict) -> None:
    material_doc = frappe.get_doc("Supporting Material", material)
    material_doc.flags.allow_missing_file = True
    material_doc.file = _clean(file_row.get("name"))
    material_doc.file_name = _clean(file_row.get("file_name")) or None
    material_doc.file_size = _clean(file_row.get("file_size")) or None
    material_doc.save(ignore_permissions=True)


def _ensure_task_material_placement(material: str, task: str, row: dict) -> str:
    existing = frappe.db.get_value(
        "Material Placement",
        {
            "supporting_material": material,
            "anchor_doctype": "Task",
            "anchor_name": task,
        },
        "name",
    )
    if existing:
        return existing

    placement = frappe.get_doc(
        {
            "doctype": "Material Placement",
            "supporting_material": material,
            "course": _task_course(task),
            "anchor_doctype": "Task",
            "anchor_name": task,
            "origin": "task",
            "usage_role": "Reference",
            "placement_order": row.get("idx"),
        }
    )
    placement.insert(ignore_permissions=True)
    return placement.name


def _rehome_file_projection(file_id: str, material: str) -> None:
    frappe.db.set_value(
        "File",
        file_id,
        {
            "attached_to_doctype": "Supporting Material",
            "attached_to_name": material,
            "attached_to_field": "file",
        },
        update_modified=False,
    )


def _rehome_drive_file_and_binding(drive_file: dict, file_id: str, task: str, material: str) -> None:
    drive_file_id = _clean(drive_file.get("name"))
    if not drive_file_id:
        frappe.throw(f"Cannot migrate Task material {material}: Drive File name is missing.")

    if _table_exists("Drive File"):
        frappe.db.set_value(
            "Drive File",
            drive_file_id,
            {
                "owner_doctype": "Supporting Material",
                "owner_name": material,
                "attached_doctype": "Supporting Material",
                "attached_name": material,
                "slot": _MATERIAL_SLOT,
            },
            update_modified=False,
        )

    if not _table_exists("Drive Binding"):
        return

    legacy_binding = frappe.db.get_value(
        "Drive Binding",
        {
            "drive_file": drive_file_id,
            "binding_doctype": "Task",
            "binding_name": task,
            "binding_role": _TASK_RESOURCE_ROLE,
            "file": file_id,
        },
        ["name", "status", "is_primary"],
        as_dict=True,
    )
    if legacy_binding:
        values = {
            "binding_doctype": "Supporting Material",
            "binding_name": material,
            "binding_role": _MATERIAL_ROLE,
            "slot": _MATERIAL_SLOT,
            "status": "active",
            "is_primary": 1,
            "primary_key": _binding_primary_key(drive_file_id, material),
        }
        frappe.db.set_value("Drive Binding", legacy_binding["name"], values, update_modified=False)
        return

    binding = frappe.get_doc(
        {
            "doctype": "Drive Binding",
            "drive_file": drive_file_id,
            "file": file_id,
            "status": "active",
            "binding_doctype": "Supporting Material",
            "binding_name": material,
            "binding_role": _MATERIAL_ROLE,
            "slot": _MATERIAL_SLOT,
            "is_primary": 1,
            "sort_order": 0,
            "organization": drive_file.get("organization"),
            "school": drive_file.get("school"),
        }
    )
    binding.insert(ignore_permissions=True)


def _binding_primary_key(drive_file_id: str, material: str) -> str:
    return "|".join((drive_file_id, "Supporting Material", material, _MATERIAL_ROLE, _MATERIAL_SLOT))


def _migrate_active_orphan_task_resources(migrated_drive_files: set[str]) -> None:
    if not _table_exists("Drive File"):
        return

    rows = frappe.get_all(
        "Drive File",
        filters={
            "owner_doctype": "Task",
            "slot": ["like", f"{_TASK_RESOURCE_SLOT_PREFIX}%"],
            "status": ["in", _ACTIVE_DRIVE_FILE_STATUSES],
        },
        fields=[
            "name",
            "file",
            "slot",
            "owner_name",
            "display_name",
            "organization",
            "school",
            "status",
        ],
        order_by="modified asc, creation asc, name asc",
        limit=0,
    )
    for row in rows or []:
        drive_file_id = _clean(row.get("name"))
        if not drive_file_id or drive_file_id in migrated_drive_files:
            continue
        task = _clean(row.get("owner_name"))
        file_id = _clean(row.get("file"))
        if not task or not file_id:
            continue
        if not frappe.db.exists("Task", task):
            frappe.throw(f"Cannot migrate Task resource {drive_file_id}: Task {task} does not exist.")

        file_row = frappe.db.get_value(
            "File",
            file_id,
            ["name", "file_url", "file_name", "file_size"],
            as_dict=True,
        )
        if not file_row:
            frappe.throw(f"Cannot migrate Task resource {drive_file_id}: native File {file_id} does not exist.")

        patch_row = {
            "name": _clean(row.get("slot")).removeprefix(_TASK_RESOURCE_SLOT_PREFIX),
            "section_break_sbex": row.get("display_name"),
            "description": None,
            "idx": None,
        }
        material = _find_existing_file_material(task, file_id)
        if not material:
            material = _create_file_material(task, patch_row, dict(file_row))
            _rehome_file_projection(file_id, material)
            _rehome_drive_file_and_binding(dict(row), file_id, task, material)
            _finalize_file_material(material, dict(file_row))
        _ensure_task_material_placement(material, task, patch_row)


def _task_course(task: str) -> str:
    fields = ["default_course"]
    try:
        meta = frappe.get_meta("Task")
        if meta.get_field("course"):
            fields.append("course")
    except Exception:
        pass

    task_row = frappe.db.get_value("Task", task, fields, as_dict=True) or {}
    course = _clean(task_row.get("default_course")) or _clean(task_row.get("course"))
    if not course:
        frappe.throw(f"Cannot migrate Task attachments for {task}: Task course is missing.")
    return course


def _material_title(row: dict, *, file_row: dict | None = None) -> str:
    title = (
        _clean(row.get("section_break_sbex"))
        or _clean(row.get("file_name"))
        or _clean((file_row or {}).get("file_name"))
        or _basename_from_url(_clean(row.get("file") or row.get("external_url")))
    )
    return title or f"Migrated task attachment {_clean(row.get('name'))}"


def _basename_from_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    candidate = parsed.path or value
    return os.path.basename(candidate.rstrip("/"))


def _validate_reference_url(reference_url: str, *, row_name: str) -> None:
    parsed = urlparse(reference_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        frappe.throw(f"Cannot migrate Task attachment {row_name}: reference URL must be http or https.")


def _delete_legacy_row(row_name: str) -> None:
    if not row_name:
        return
    delete_doc = getattr(frappe, "delete_doc", None)
    if callable(delete_doc):
        delete_doc("Attached Document", row_name, ignore_permissions=True, force=True)
        return
    frappe.db.delete("Attached Document", {"name": row_name})
