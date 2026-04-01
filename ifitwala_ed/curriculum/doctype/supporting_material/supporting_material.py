from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.curriculum.materials import (
    MATERIAL_BINDING_ROLE,
    MATERIAL_FILE_SLOT,
    MATERIAL_TYPE_FILE,
    MATERIAL_TYPE_REFERENCE_LINK,
    get_material_permission_query_conditions,
    normalize_material_modality,
    user_can_manage_supporting_material,
    user_can_read_supporting_material,
    validate_reference_url,
)


class SupportingMaterial(Document):
    def validate(self):
        self._normalize()
        self._validate_type_specific_fields()
        self._validate_governed_file()

    def on_trash(self):
        if frappe.db.exists("Material Placement", {"supporting_material": self.name}):
            frappe.throw(_("This material is still shared in one or more placements. Unshare it first."))

    def _normalize(self):
        self.title = (self.title or "").strip()
        self.course = (self.course or "").strip()
        self.material_type = (self.material_type or "").strip()
        self.description = (self.description or "").strip() or None
        self.reference_url = (self.reference_url or "").strip() or None
        self.file = (self.file or "").strip() or None
        self.file_name = (self.file_name or "").strip() or None
        self.file_size = (self.file_size or "").strip() or None
        self.modality = normalize_material_modality(self.modality)

        if not self.title:
            frappe.throw(_("Material title is required."))
        if not self.course:
            frappe.throw(_("Course is required for a supporting material."))

    def _validate_type_specific_fields(self):
        if self.material_type == MATERIAL_TYPE_REFERENCE_LINK:
            self.reference_url = validate_reference_url(self.reference_url or "")
            self.file = None
            self.file_name = None
            self.file_size = None
            return

        if self.material_type != MATERIAL_TYPE_FILE:
            frappe.throw(_("Unsupported material type: {0}").format(self.material_type))

        self.reference_url = None
        if self.file or getattr(self.flags, "allow_missing_file", False):
            return
        frappe.throw(_("File materials must be uploaded through the governed materials flow."))

    def _validate_governed_file(self):
        if self.material_type != MATERIAL_TYPE_FILE or not self.file:
            return

        file_row = frappe.db.get_value(
            "File",
            self.file,
            ["name", "attached_to_doctype", "attached_to_name"],
            as_dict=True,
        )
        if not file_row:
            frappe.throw(_("Material file does not exist: {0}").format(self.file))
        if (
            file_row.get("attached_to_doctype") != "Supporting Material"
            or file_row.get("attached_to_name") != self.name
        ):
            frappe.throw(_("Material files must stay attached to their Supporting Material owner."))

        binding = frappe.db.get_value(
            "Drive Binding",
            {
                "binding_doctype": "Supporting Material",
                "binding_name": self.name,
                "binding_role": MATERIAL_BINDING_ROLE,
                "slot": MATERIAL_FILE_SLOT,
                "file": self.file,
                "status": "active",
            },
            "name",
        )
        if not binding:
            frappe.throw(_("Material files must be uploaded through the governed materials action."))


def get_permission_query_conditions(user: str | None = None) -> str | None:
    return get_material_permission_query_conditions(
        user=user,
        table_alias="`tabSupporting Material`",
    )


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    if not doc:
        return True

    material_name = (getattr(doc, "name", None) or "").strip()
    course = (getattr(doc, "course", None) or "").strip() or None
    if not material_name:
        return False

    if ptype in {"read", "select", "report", "print", "email", "share", "export", None}:
        return user_can_read_supporting_material(user, material_name, course=course)

    return user_can_manage_supporting_material(user, material_name, course=course)
