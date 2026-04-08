from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from ifitwala_ed.curriculum.materials import (
    MATERIAL_DATA_CLASS,
    MATERIAL_FILE_SLOT,
    MATERIAL_PURPOSE,
    MATERIAL_RETENTION_POLICY,
    get_course_school_context,
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
