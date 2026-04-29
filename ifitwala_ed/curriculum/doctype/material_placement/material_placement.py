from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.curriculum.materials import (
    MATERIAL_ALLOWED_ANCHORS,
    get_material_permission_query_conditions,
    normalize_material_origin,
    normalize_material_usage_role,
    resolve_anchor_course,
    user_can_manage_material_anchor,
    user_can_read_material_anchor,
)


class MaterialPlacement(Document):
    def validate(self):
        self._normalize()
        self._validate_anchor()
        self._validate_course_alignment()
        self._validate_duplicate()

    def _normalize(self):
        self.supporting_material = (self.supporting_material or "").strip()
        self.course = (self.course or "").strip()
        self.anchor_doctype = (self.anchor_doctype or "").strip()
        self.anchor_name = (self.anchor_name or "").strip()
        self.placement_note = (self.placement_note or "").strip() or None
        self.usage_role = normalize_material_usage_role(self.usage_role)
        self.origin = normalize_material_origin(self.origin, anchor_doctype=self.anchor_doctype)

        if not self.supporting_material:
            frappe.throw(_("Supporting Material is required."))
        if not self.anchor_doctype:
            frappe.throw(_("Anchor Doctype is required."))
        if not self.anchor_name:
            frappe.throw(_("Anchor Name is required."))

    def _validate_anchor(self):
        if self.anchor_doctype not in MATERIAL_ALLOWED_ANCHORS:
            frappe.throw(_("Unsupported material anchor type: {anchor_type}").format(anchor_type=self.anchor_doctype))
        if not frappe.db.exists(self.anchor_doctype, self.anchor_name):
            frappe.throw(
                _("Anchor document does not exist: {doctype} {name}").format(
                    doctype=self.anchor_doctype, name=self.anchor_name
                )
            )

    def _validate_course_alignment(self):
        material_course = frappe.db.get_value("Supporting Material", self.supporting_material, "course")
        if not material_course:
            frappe.throw(_("Supporting Material is missing its course context."))

        anchor_course = resolve_anchor_course(self.anchor_doctype, self.anchor_name)
        if material_course != anchor_course:
            frappe.throw(_("Material placement must stay inside the material's authoritative course."))

        self.course = material_course

    def _validate_duplicate(self):
        duplicate = frappe.db.get_value(
            "Material Placement",
            {
                "name": ["!=", self.name or ""],
                "supporting_material": self.supporting_material,
                "anchor_doctype": self.anchor_doctype,
                "anchor_name": self.anchor_name,
            },
            "name",
        )
        if duplicate:
            frappe.throw(_("This material is already shared in the selected context."))


def get_permission_query_conditions(user: str | None = None) -> str | None:
    return get_material_permission_query_conditions(
        user=user,
        table_alias="`tabMaterial Placement`",
    )


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    ptype = (ptype or "read").lower()
    if not doc:
        return True

    anchor_doctype = (getattr(doc, "anchor_doctype", None) or "").strip()
    anchor_name = (getattr(doc, "anchor_name", None) or "").strip()
    if not anchor_doctype or not anchor_name:
        return False

    if ptype in {"read", "select", "report", "print", "email", "share", "export"}:
        return user_can_read_material_anchor(user, anchor_doctype, anchor_name)

    return user_can_manage_material_anchor(user, anchor_doctype, anchor_name)
