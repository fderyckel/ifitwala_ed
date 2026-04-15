from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


class _FakeTaskDoc(SimpleNamespace):
    def get(self, fieldname, default=None):
        return getattr(self, fieldname, default)


@contextmanager
def _drive_tasks_module(task_doc=None):
    with stubbed_frappe() as frappe:
        task_doc = task_doc or _FakeTaskDoc(
            name="TASK-0001",
            default_course="COURSE-1",
            attachments=[SimpleNamespace(name="row-001")],
            check_permission=lambda permission_type=None: None,
        )

        def fake_get_value(doctype, name, fieldname=None, as_dict=False):
            if doctype == "Course" and fieldname == "school":
                return "SCH-1"
            if doctype == "School" and fieldname == "organization":
                return "ORG-1"
            return None

        frappe.db.get_value = fake_get_value
        frappe.db.exists = lambda doctype, name=None: doctype == "Task" and bool(name)
        frappe.get_doc = lambda doctype, name: task_doc

        yield import_fresh("ifitwala_ed.integrations.drive.tasks")


class TestDriveTaskResourceContract(TestCase):
    def test_build_task_resource_upload_contract_uses_learning_resource_purpose(self):
        task_doc = _FakeTaskDoc(
            name="TASK-0001",
            default_course="COURSE-1",
            attachments=[SimpleNamespace(name="row-001")],
        )

        with _drive_tasks_module(task_doc) as module:
            payload = module.build_task_resource_upload_contract(task_doc, row_name="row-001")

        self.assertEqual(payload["purpose"], "learning_resource")
        self.assertEqual(payload["slot"], "supporting_material__row-001")
        self.assertEqual(payload["organization"], "ORG-1")
        self.assertEqual(payload["school"], "SCH-1")

    def test_validate_task_resource_finalize_context_rejects_stale_academic_report_purpose(self):
        upload_session_doc = SimpleNamespace(
            owner_doctype="Task",
            owner_name="TASK-0001",
            attached_doctype="Task",
            attached_name="TASK-0001",
            organization="ORG-1",
            school="SCH-1",
            intended_primary_subject_type="Organization",
            intended_primary_subject_id="ORG-1",
            intended_data_class="academic",
            intended_purpose="academic_report",
            intended_retention_policy="until_program_end_plus_1y",
            intended_slot="supporting_material__row-001",
        )

        with _drive_tasks_module() as module:
            with self.assertRaises(StubValidationError):
                module.validate_task_resource_finalize_context(upload_session_doc)
