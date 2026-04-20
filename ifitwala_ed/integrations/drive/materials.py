from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from ifitwala_ed.curriculum import materials as materials_domain
from ifitwala_ed.curriculum.materials import (
    MATERIAL_DATA_CLASS,
    MATERIAL_FILE_SLOT,
    MATERIAL_PURPOSE,
    MATERIAL_RETENTION_POLICY,
    get_course_school_context,
)
from ifitwala_ed.integrations.drive.authority import (
    get_current_drive_file_for_attachment,
    get_drive_file_by_id,
)


def _get_doc(doctype: str, name: str, *, permission_type: str | None = None):
    if not frappe.db.exists(doctype, name):
        frappe.throw(_("{doctype} does not exist: {name}").format(doctype=doctype, name=name))

    doc = frappe.get_doc(doctype, name)
    if permission_type:
        doc.check_permission(permission_type)
    return doc


def build_supporting_material_upload_contract(material_doc) -> dict[str, Any]:
    course = (getattr(material_doc, "course", None) or "").strip()
    if not course:
        frappe.throw(_("Supporting Material is missing its authoritative course context."))

    school, organization = get_course_school_context(course)
    return {
        "owner_doctype": "Supporting Material",
        "owner_name": material_doc.name,
        "attached_doctype": "Supporting Material",
        "attached_name": material_doc.name,
        "organization": organization,
        "school": school,
        "primary_subject_type": "Organization",
        "primary_subject_id": organization,
        "data_class": MATERIAL_DATA_CLASS,
        "purpose": MATERIAL_PURPOSE,
        "retention_policy": MATERIAL_RETENTION_POLICY,
        "slot": MATERIAL_FILE_SLOT,
        "course": course,
    }


def assert_supporting_material_upload_access(material: str, *, permission_type: str = "write"):
    return _get_doc("Supporting Material", material, permission_type=permission_type)


def _is_supporting_material_drive_file(drive_file: dict[str, Any] | None, material_name: str) -> bool:
    if not drive_file:
        return False

    return (
        str(drive_file.get("owner_doctype") or "").strip() == "Supporting Material"
        and str(drive_file.get("owner_name") or "").strip() == material_name
    )


def _resolve_supporting_material_drive_file(
    material_name: str,
    *,
    drive_file_id: str | None = None,
) -> dict[str, Any] | None:
    resolved_drive_file_id = str(drive_file_id or "").strip()
    if resolved_drive_file_id:
        drive_file = get_drive_file_by_id(
            resolved_drive_file_id,
            fields=[
                "name",
                "file",
                "canonical_ref",
                "owner_doctype",
                "owner_name",
            ],
            statuses=("active", "processing", "blocked"),
        )
        if _is_supporting_material_drive_file(drive_file, material_name):
            return drive_file

    drive_file = get_current_drive_file_for_attachment(
        attached_doctype="Supporting Material",
        attached_name=material_name,
        fields=[
            "name",
            "file",
            "canonical_ref",
            "owner_doctype",
            "owner_name",
        ],
        statuses=("active", "processing", "blocked"),
    )
    if _is_supporting_material_drive_file(drive_file, material_name):
        return drive_file

    return None


def assert_supporting_material_read_access(
    material: str,
    *,
    placement: str | None = None,
    drive_file_id: str | None = None,
) -> dict[str, Any]:
    material_name = str(material or "").strip()
    placement_name = str(placement or "").strip()
    if not material_name:
        frappe.throw(_("Missing required field: material"))
    if not frappe.db.exists("Supporting Material", material_name):
        frappe.throw(_("Supporting Material does not exist: {0}").format(material_name))

    course = str(frappe.db.get_value("Supporting Material", material_name, "course") or "").strip() or None
    if placement_name:
        placement_row = frappe.db.get_value(
            "Material Placement",
            placement_name,
            ["name", "supporting_material", "anchor_doctype", "anchor_name"],
            as_dict=True,
        )
        if not placement_row:
            frappe.throw(_("Material placement not found."), frappe.DoesNotExistError)
        if str(placement_row.get("supporting_material") or "").strip() != material_name:
            frappe.throw(_("Material placement does not belong to this material."), frappe.PermissionError)
        if not materials_domain.user_can_read_material_anchor(
            frappe.session.user,
            placement_row.get("anchor_doctype"),
            placement_row.get("anchor_name"),
        ):
            frappe.throw(_("You do not have permission to access this file."), frappe.PermissionError)
    elif not materials_domain.user_can_read_supporting_material(
        frappe.session.user,
        material_name,
        course=course,
    ):
        frappe.throw(_("You do not have permission to access this file."), frappe.PermissionError)

    drive_file = _resolve_supporting_material_drive_file(material_name, drive_file_id=drive_file_id)
    if not drive_file or not drive_file.get("name"):
        frappe.throw(_("Governed attachment file was not found."), frappe.DoesNotExistError)

    return {
        "material": material_name,
        "placement": placement_name or None,
        "drive_file_id": str(drive_file.get("name") or "").strip(),
        "file_id": str(drive_file.get("file") or "").strip() or None,
        "canonical_ref": str(drive_file.get("canonical_ref") or "").strip() or None,
    }


def validate_supporting_material_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != "Supporting Material":
        return None

    material_doc = assert_supporting_material_upload_access(upload_session_doc.owner_name, permission_type="write")
    authoritative = build_supporting_material_upload_contract(material_doc)

    field_map = {
        "owner_doctype": "owner_doctype",
        "owner_name": "owner_name",
        "attached_doctype": "attached_doctype",
        "attached_name": "attached_name",
        "organization": "organization",
        "school": "school",
        "intended_primary_subject_type": "primary_subject_type",
        "intended_primary_subject_id": "primary_subject_id",
        "intended_data_class": "data_class",
        "intended_purpose": "purpose",
        "intended_retention_policy": "retention_policy",
        "intended_slot": "slot",
    }

    for session_field, authoritative_field in field_map.items():
        if getattr(upload_session_doc, session_field, None) != authoritative[authoritative_field]:
            frappe.throw(
                _(
                    "Upload session no longer matches the authoritative Supporting Material context for field '{field_name}'."
                ).format(field_name=session_field)
            )

    return authoritative


def get_supporting_material_context_override(owner_name: str | None, slot: str | None) -> dict[str, Any] | None:
    if not owner_name or not frappe.db.exists("Supporting Material", owner_name):
        return None

    material_doc = _get_doc("Supporting Material", owner_name)
    course = (getattr(material_doc, "course", None) or "").strip()
    if not course:
        return None

    return {
        "root_folder": "Home/Courses",
        "subfolder": f"{course}/Materials",
        "file_category": "Supporting Material",
        "logical_key": str(slot or "").strip() or f"supporting_material_{material_doc.name}",
    }


def run_material_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Supporting Material":
        return {}

    material_doc = frappe.get_doc("Supporting Material", upload_session_doc.owner_name)
    file_name = getattr(created_file, "file_name", None) or frappe.db.get_value("File", created_file.name, "file_name")
    file_size = getattr(created_file, "file_size", None) or frappe.db.get_value("File", created_file.name, "file_size")

    material_doc.flags.allow_missing_file = True
    material_doc.file = created_file.name
    material_doc.file_name = file_name
    material_doc.file_size = file_size
    material_doc.save(ignore_permissions=True)

    return {
        "material": material_doc.name,
        "file": created_file.name,
    }
