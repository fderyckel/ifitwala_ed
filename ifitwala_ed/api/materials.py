from __future__ import annotations

import mimetypes
import os
from typing import Any

import frappe
from frappe import _

from ifitwala_ed.api.attachment_previews import build_attachment_preview_item, extract_file_extension
from ifitwala_ed.api.file_access import (
    get_academic_file_thumbnail_ready_map,
    resolve_academic_file_open_url,
    resolve_academic_file_preview_url,
    resolve_academic_file_thumbnail_url,
)
from ifitwala_ed.curriculum import materials as materials_domain
from ifitwala_ed.utilities import governed_uploads

ALLOWED_TASK_ATTACHMENT_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf"}
ALLOWED_TASK_ATTACHMENT_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}


def _normalize_payload(value) -> dict[str, Any]:
    if isinstance(value, str):
        value = frappe.parse_json(value)
    if not isinstance(value, dict):
        frappe.throw(_("Payload must be a dict."))
    return value


def _material_thumbnail_ready_map(entries: list[dict[str, Any]]) -> dict[str, bool]:
    file_names = [
        str(entry.get("file") or "").strip()
        for entry in entries or []
        if entry.get("material_type") == materials_domain.MATERIAL_TYPE_FILE and str(entry.get("file") or "").strip()
    ]
    return get_academic_file_thumbnail_ready_map(file_names)


def _serialize_material(entry: dict[str, Any], *, thumbnail_ready_map: dict[str, bool] | None = None) -> dict[str, Any]:
    material_type = entry.get("material_type")
    first_placement = (entry.get("placements") or [{}])[0]
    owner_doctype = "Material Placement" if first_placement.get("placement") else "Supporting Material"
    owner_name = first_placement.get("placement") or entry.get("material")
    if material_type == materials_domain.MATERIAL_TYPE_FILE:
        resolved_file_id = entry.get("file")
        resolved_file_name = str(entry.get("file") or "").strip()
        thumbnail_url = resolve_academic_file_thumbnail_url(
            file_name=entry.get("file"),
            file_url=entry.get("file_url"),
            context_doctype="Material Placement" if first_placement.get("placement") else "Supporting Material",
            context_name=first_placement.get("placement") or entry.get("material"),
            thumbnail_ready=(
                thumbnail_ready_map.get(resolved_file_name)
                if thumbnail_ready_map is not None and resolved_file_name
                else None
            ),
        )
        preview_url = resolve_academic_file_preview_url(
            file_name=entry.get("file"),
            file_url=entry.get("file_url"),
            context_doctype="Material Placement" if first_placement.get("placement") else "Supporting Material",
            context_name=first_placement.get("placement") or entry.get("material"),
        )
        open_url = resolve_academic_file_open_url(
            file_name=entry.get("file"),
            file_url=entry.get("file_url"),
            context_doctype="Material Placement" if first_placement.get("placement") else "Supporting Material",
            context_name=first_placement.get("placement") or entry.get("material"),
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
        "course": entry.get("course"),
        "title": entry.get("title"),
        "material_type": material_type,
        "modality": entry.get("modality"),
        "description": entry.get("description"),
        "reference_url": entry.get("reference_url"),
        "thumbnail_url": thumbnail_url,
        "preview_url": preview_url,
        "open_url": open_url,
        "file": entry.get("file"),
        "file_name": entry.get("file_name"),
        "file_size": entry.get("file_size"),
        "placements": entry.get("placements") or [],
        "attachment_preview": attachment_preview,
    }


def _assert_supported_task_attachment_upload():
    request = getattr(frappe, "request", None)
    uploaded = getattr(request, "files", {}).get("file") if request and getattr(request, "files", None) else None
    if not uploaded:
        frappe.throw(_("No file uploaded."))

    filename = str(getattr(uploaded, "filename", None) or getattr(uploaded, "name", None) or "").strip()
    extension = os.path.splitext(filename)[1].lower().lstrip(".")
    mime_type = (
        str(getattr(uploaded, "mimetype", None) or getattr(uploaded, "content_type", None) or "").strip().lower()
    )
    normalized_mime_type = mime_type.split(";", 1)[0].strip() if mime_type else ""
    guessed_mime_type, _encoding = mimetypes.guess_type(filename)
    resolved_mime_type = normalized_mime_type or str(guessed_mime_type or "").strip().lower()

    if extension in ALLOWED_TASK_ATTACHMENT_EXTENSIONS:
        return
    if resolved_mime_type in ALLOWED_TASK_ATTACHMENT_MIME_TYPES:
        return

    frappe.throw(_("Task attachments support PDF, JPG, PNG, and WEBP files only."))


def _serialize_task_material(
    entry: dict[str, Any], *, thumbnail_ready_map: dict[str, bool] | None = None
) -> dict[str, Any]:
    placement = (entry.get("placements") or [{}])[0]
    return {
        **_serialize_material(entry, thumbnail_ready_map=thumbnail_ready_map),
        "placement": placement.get("placement"),
        "origin": placement.get("origin"),
        "usage_role": placement.get("usage_role"),
        "placement_note": placement.get("placement_note"),
        "placement_order": placement.get("placement_order"),
    }


def _require_task_write(task: str):
    if not task:
        frappe.throw(_("Task is required."))
    task_doc = frappe.get_doc("Task", task)
    task_doc.check_permission("write")
    return task_doc


@frappe.whitelist()
def list_task_materials(task: str) -> dict[str, Any]:
    task_doc = _require_task_write(task)
    rows = materials_domain.list_anchor_materials("Task", task_doc.name)
    thumbnail_ready_map = _material_thumbnail_ready_map(rows)
    materials = [_serialize_task_material(entry, thumbnail_ready_map=thumbnail_ready_map) for entry in rows]
    return {
        "task": task_doc.name,
        "materials": materials,
    }


@frappe.whitelist()
def create_task_reference_material(payload=None, **kwargs) -> dict[str, Any]:
    data = _normalize_payload(payload if payload is not None else kwargs)
    task = (data.get("task") or "").strip()
    title = (data.get("title") or "").strip()
    reference_url = data.get("reference_url")

    _require_task_write(task)
    if not title:
        frappe.throw(_("Title is required."))

    material, placement = materials_domain.create_reference_material(
        anchor_doctype="Task",
        anchor_name=task,
        title=title,
        reference_url=reference_url,
        description=data.get("description"),
        modality=data.get("modality"),
        usage_role=data.get("usage_role"),
        placement_note=data.get("placement_note"),
        origin="task",
        placement_order=data.get("placement_order"),
    )

    materials = materials_domain.list_anchor_materials("Task", task)
    created = next((row for row in materials if row.get("material") == material.name), None)
    if not created:
        frappe.throw(_("Material was created but could not be reloaded."))

    serialized = _serialize_task_material(created, thumbnail_ready_map=_material_thumbnail_ready_map(materials))
    serialized["placement"] = placement.name
    return serialized


@frappe.whitelist()
def upload_task_material_file(
    task: str | None = None,
    title: str | None = None,
    description: str | None = None,
    modality: str | None = None,
    usage_role: str | None = None,
    placement_note: str | None = None,
):
    form_dict = getattr(frappe, "form_dict", None) or {}

    task_name = (task or form_dict.get("task") or "").strip()
    title = (title or form_dict.get("title") or "").strip()
    description = description if description is not None else form_dict.get("description")
    modality = modality if modality is not None else form_dict.get("modality")
    usage_role = usage_role if usage_role is not None else form_dict.get("usage_role")
    placement_note = placement_note if placement_note is not None else form_dict.get("placement_note")

    _require_task_write(task_name)
    if not title:
        frappe.throw(_("Title is required."))
    _assert_supported_task_attachment_upload()

    frappe.db.savepoint("upload_task_material_file")
    try:
        material = materials_domain.create_file_material_record(
            anchor_doctype="Task",
            anchor_name=task_name,
            title=title,
            description=description,
            modality=modality,
        )
        governed_uploads.upload_supporting_material_file(material=material.name)
        placement = materials_domain.create_material_placement(
            supporting_material=material.name,
            anchor_doctype="Task",
            anchor_name=task_name,
            usage_role=usage_role,
            placement_note=placement_note,
            origin="task",
        )
    except Exception:
        frappe.db.rollback(save_point="upload_task_material_file")
        raise

    materials = materials_domain.list_anchor_materials("Task", task_name)
    created = next((row for row in materials if row.get("material") == material.name), None)
    if not created:
        frappe.throw(_("Material upload succeeded but the task material could not be reloaded."))

    serialized = _serialize_task_material(created, thumbnail_ready_map=_material_thumbnail_ready_map(materials))
    serialized["placement"] = placement.name
    return serialized


@frappe.whitelist()
def remove_task_material(payload=None, **kwargs) -> dict[str, Any]:
    data = _normalize_payload(payload if payload is not None else kwargs)
    task = (data.get("task") or "").strip()
    placement = (data.get("placement") or "").strip()
    if not placement:
        frappe.throw(_("Placement is required."))

    materials_domain.delete_task_material_placement(placement, task=task)
    return {
        "task": task,
        "placement": placement,
        "removed": 1,
    }
