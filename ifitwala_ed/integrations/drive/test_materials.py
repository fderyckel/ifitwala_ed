from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


@contextmanager
def _drive_materials_module():
    student_groups_api = ModuleType("ifitwala_ed.api.student_groups")

    with stubbed_frappe(extra_modules={"ifitwala_ed.api.student_groups": student_groups_api}) as frappe:

        def fake_get_value(doctype, name, fieldname=None, as_dict=False):
            if doctype == "Course" and fieldname == "school":
                return "SCH-1"
            if doctype == "School" and fieldname == "organization":
                return "ORG-1"
            return None

        frappe.db.get_value = fake_get_value
        frappe.db.exists = lambda doctype, name=None: doctype == "Supporting Material" and bool(name)
        frappe.get_doc = lambda doctype, name: SimpleNamespace(
            name=name,
            course="COURSE-1",
            check_permission=lambda permission_type=None: None,
        )

        import_fresh("ifitwala_ed.curriculum.materials")
        yield import_fresh("ifitwala_ed.integrations.drive.materials")


class TestDriveSupportingMaterialContract(TestCase):
    def test_build_supporting_material_upload_contract_uses_learning_resource_purpose(self):
        with _drive_materials_module() as module:
            payload = module.build_supporting_material_upload_contract(
                SimpleNamespace(name="MAT-0001", course="COURSE-1")
            )

        self.assertEqual(payload["purpose"], "learning_resource")
        self.assertEqual(payload["slot"], "material_file")
        self.assertEqual(payload["organization"], "ORG-1")
        self.assertEqual(payload["school"], "SCH-1")

    def test_validate_supporting_material_finalize_context_rejects_stale_academic_report_purpose(self):
        upload_session_doc = SimpleNamespace(
            owner_doctype="Supporting Material",
            owner_name="MAT-0001",
            attached_doctype="Supporting Material",
            attached_name="MAT-0001",
            organization="ORG-1",
            school="SCH-1",
            intended_primary_subject_type="Organization",
            intended_primary_subject_id="ORG-1",
            intended_data_class="academic",
            intended_purpose="academic_report",
            intended_retention_policy="until_program_end_plus_1y",
            intended_slot="material_file",
        )

        with _drive_materials_module() as module:
            with self.assertRaises(StubValidationError):
                module.validate_supporting_material_finalize_context(upload_session_doc)
