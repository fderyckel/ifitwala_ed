from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


@contextmanager
def _material_placement_module():
    materials_stub = ModuleType("ifitwala_ed.curriculum.materials")
    materials_stub.MATERIAL_ALLOWED_ANCHORS = {
        "Course Plan",
        "Unit Plan",
        "Class Teaching Plan",
        "Class Session",
        "Task",
    }
    materials_stub.get_material_permission_query_conditions = lambda user=None, table_alias="", manage_only=False: (
        f"{table_alias}.course in ('COURSE-1')"
    )
    materials_stub.normalize_material_origin = lambda value, anchor_doctype=None: (
        str(value or "").strip() or ("task" if anchor_doctype == "Task" else "curriculum")
    )
    materials_stub.normalize_material_usage_role = lambda value: str(value or "").strip() or "Reference"
    materials_stub.resolve_anchor_course = lambda anchor_doctype, anchor_name: "COURSE-1"
    materials_stub.user_can_manage_material_anchor = lambda user, anchor_doctype, anchor_name: (
        user in {"teacher@example.com", "coordinator@example.com"}
    )
    materials_stub.user_can_read_material_anchor = lambda user, anchor_doctype, anchor_name: (
        user in {"teacher@example.com", "coordinator@example.com"}
    )

    with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.materials": materials_stub}) as frappe:
        frappe.db.exists = lambda *args, **kwargs: True
        frappe.db.get_value = lambda *args, **kwargs: None
        yield import_fresh("ifitwala_ed.curriculum.doctype.material_placement.material_placement")


class TestMaterialPlacement(TestCase):
    def test_validate_anchor_rejects_legacy_lesson_anchor(self):
        with _material_placement_module() as module:
            placement = module.MaterialPlacement()
            placement.anchor_doctype = "Lesson"
            placement.anchor_name = "LESSON-1"

            with self.assertRaises(StubValidationError):
                placement._validate_anchor()

    def test_validate_course_alignment_rejects_different_anchor_course(self):
        with _material_placement_module() as module:
            module.frappe.db.get_value = lambda doctype, filters, fieldname=None, as_dict=False: (
                "COURSE-2" if doctype == "Supporting Material" else None
            )

            placement = module.MaterialPlacement()
            placement.supporting_material = "MAT-1"
            placement.anchor_doctype = "Task"
            placement.anchor_name = "TASK-1"

            with self.assertRaises(StubValidationError):
                placement._validate_course_alignment()

    def test_validate_duplicate_rejects_same_material_same_anchor(self):
        with _material_placement_module() as module:

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "Material Placement":
                    return "MAT-PLC-EXISTING"
                return None

            module.frappe.db.get_value = fake_get_value

            placement = module.MaterialPlacement()
            placement.name = "MAT-PLC-NEW"
            placement.supporting_material = "MAT-1"
            placement.anchor_doctype = "Task"
            placement.anchor_name = "TASK-1"

            with self.assertRaises(StubValidationError):
                placement._validate_duplicate()

    def test_has_permission_allows_program_scoped_coordinator_write(self):
        with _material_placement_module() as module:
            placement = module.MaterialPlacement()
            placement.anchor_doctype = "Task"
            placement.anchor_name = "TASK-1"

            self.assertTrue(module.has_permission(placement, ptype="read", user="coordinator@example.com"))
            self.assertTrue(module.has_permission(placement, ptype="write", user="coordinator@example.com"))
