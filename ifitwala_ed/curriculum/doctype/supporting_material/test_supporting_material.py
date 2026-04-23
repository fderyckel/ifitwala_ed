from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


@contextmanager
def _supporting_material_module():
    materials_stub = ModuleType("ifitwala_ed.curriculum.materials")
    materials_stub.MATERIAL_BINDING_ROLE = "supporting_material"
    materials_stub.MATERIAL_FILE_SLOT = "material_file"
    materials_stub.MATERIAL_TYPE_FILE = "File"
    materials_stub.MATERIAL_TYPE_REFERENCE_LINK = "Reference Link"
    materials_stub.normalize_material_modality = lambda value: str(value or "").strip() or "Read"
    materials_stub.get_material_permission_query_conditions = lambda user=None, table_alias="", manage_only=False: (
        f"{table_alias}.course in ('COURSE-1')"
    )
    materials_stub.user_can_manage_course_material = lambda user, course: (
        course == "COURSE-1" and user in {"teacher@example.com", "coordinator@example.com"}
    )
    materials_stub.user_can_manage_supporting_material = lambda user, material_name, course=None: (
        course == "COURSE-1" and user in {"teacher@example.com", "coordinator@example.com"}
    )
    materials_stub.user_can_read_supporting_material = lambda user, material_name, course=None: (
        course == "COURSE-1" and user in {"teacher@example.com", "coordinator@example.com"}
    )

    def validate_reference_url(value):
        reference_url = str(value or "").strip()
        if not reference_url.startswith(("http://", "https://")):
            raise StubValidationError("Reference URL must be a valid http or https URL.")
        return reference_url

    materials_stub.validate_reference_url = validate_reference_url

    with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.materials": materials_stub}) as frappe:
        frappe.db.exists = lambda *args, **kwargs: False
        frappe.db.get_value = lambda *args, **kwargs: None
        yield import_fresh("ifitwala_ed.curriculum.doctype.supporting_material.supporting_material")


class TestSupportingMaterial(TestCase):
    def test_reference_material_clears_file_fields(self):
        with _supporting_material_module() as module:
            material = module.SupportingMaterial()
            material.flags = SimpleNamespace(allow_missing_file=False)
            material.title = "Study guide"
            material.course = "COURSE-1"
            material.material_type = "Reference Link"
            material.description = ""
            material.reference_url = "https://example.com/guide"
            material.file = "FILE-1"
            material.file_name = "guide.pdf"
            material.file_size = "42 KB"
            material.modality = "Read"

            material._normalize()
            material._validate_type_specific_fields()

        self.assertEqual(material.reference_url, "https://example.com/guide")
        self.assertIsNone(material.file)
        self.assertIsNone(material.file_name)
        self.assertIsNone(material.file_size)

    def test_file_material_requires_governed_upload_when_missing_file(self):
        with _supporting_material_module() as module:
            material = module.SupportingMaterial()
            material.flags = SimpleNamespace(allow_missing_file=False)
            material.title = "Worksheet"
            material.course = "COURSE-1"
            material.material_type = "File"
            material.description = ""
            material.reference_url = ""
            material.file = None
            material.file_name = None
            material.file_size = None
            material.modality = "Use"

            material._normalize()

            with self.assertRaises(StubValidationError):
                material._validate_type_specific_fields()

    def test_normalize_accepts_numeric_file_size_from_governed_upload_finalize(self):
        with _supporting_material_module() as module:
            material = module.SupportingMaterial()
            material.flags = SimpleNamespace(allow_missing_file=True)
            material.title = "Worksheet"
            material.course = "COURSE-1"
            material.material_type = "File"
            material.description = ""
            material.reference_url = ""
            material.file = "FILE-1"
            material.file_name = "worksheet.pdf"
            material.file_size = 2048
            material.modality = "Use"

            material._normalize()

        self.assertEqual(material.file_size, "2048")

    def test_validate_governed_file_rejects_wrong_attachment_owner(self):
        with _supporting_material_module() as module:

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "File":
                    return {
                        "name": "FILE-1",
                        "attached_to_doctype": "Task",
                        "attached_to_name": "TASK-1",
                    }
                return None

            module.frappe.db.get_value = fake_get_value

            material = module.SupportingMaterial()
            material.flags = SimpleNamespace(allow_missing_file=False)
            material.name = "MAT-1"
            material.title = "Worksheet"
            material.course = "COURSE-1"
            material.material_type = "File"
            material.file = "FILE-1"
            material.modality = "Use"

            with self.assertRaises(StubValidationError):
                material._validate_governed_file()

    def test_on_trash_blocks_when_active_placements_exist(self):
        with _supporting_material_module() as module:
            module.frappe.db.exists = lambda doctype, filters=None: bool(
                doctype == "Material Placement" and (filters or {}).get("supporting_material") == "MAT-1"
            )

            material = module.SupportingMaterial()
            material.name = "MAT-1"

            with self.assertRaises(StubValidationError):
                material.on_trash()

    def test_has_permission_allows_program_scoped_coordinator_write(self):
        with _supporting_material_module() as module:
            material = module.SupportingMaterial()
            material.name = "MAT-1"
            material.course = "COURSE-1"

            self.assertTrue(module.has_permission(material, ptype="read", user="coordinator@example.com"))
            self.assertTrue(module.has_permission(material, ptype="write", user="coordinator@example.com"))

    def test_has_permission_allows_create_for_unsaved_manageable_course(self):
        with _supporting_material_module() as module:
            material = module.SupportingMaterial()
            material.course = "COURSE-1"

            self.assertTrue(module.has_permission(material, ptype="create", user="coordinator@example.com"))
