from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import (
    StubPermissionError,
    StubValidationError,
    import_fresh,
    stubbed_frappe,
)


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


@contextmanager
def _drive_task_submission_module(task_submission_doc=None, *, session_student=None):
    extra_modules = {}
    if session_student is not None:
        courses = ModuleType("ifitwala_ed.api.courses")
        courses._require_student_name_for_session_user = lambda: session_student
        extra_modules["ifitwala_ed.api.courses"] = courses

    with stubbed_frappe(extra_modules=extra_modules) as frappe:
        task_submission_doc = task_submission_doc or SimpleNamespace(
            name="TSU-0001",
            student="STU-1",
            school="SCH-1",
            check_permission=lambda permission_type=None: None,
        )

        def fake_get_value(doctype, name, fieldname=None, as_dict=False):
            if doctype == "School" and fieldname == "organization":
                return "ORG-1"
            return None

        frappe.db.get_value = fake_get_value
        frappe.db.exists = lambda doctype, name=None: doctype == "Task Submission" and bool(name)
        frappe.get_doc = lambda doctype, name: task_submission_doc

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


class TestDriveTaskSubmissionContract(TestCase):
    def test_build_task_feedback_export_upload_contract_uses_assessment_feedback_purpose(self):
        task_submission_doc = SimpleNamespace(
            name="TSU-0001",
            student="STU-1",
            school="SCH-1",
            task="TASK-1",
            check_permission=lambda permission_type=None: None,
        )

        with _drive_task_submission_module(task_submission_doc) as module:
            payload = module.build_task_feedback_export_upload_contract(
                task_submission_doc,
                audience="student",
            )

        self.assertEqual(payload["purpose"], "assessment_feedback")
        self.assertEqual(payload["slot"], "feedback_export__released__student")
        self.assertEqual(payload["organization"], "ORG-1")
        self.assertEqual(payload["school"], "SCH-1")

    def test_validate_task_feedback_export_finalize_context_rejects_stale_submission_purpose(self):
        upload_session_doc = SimpleNamespace(
            owner_doctype="Task Submission",
            owner_name="TSU-0001",
            attached_doctype="Task Submission",
            attached_name="TSU-0001",
            organization="ORG-1",
            school="SCH-1",
            intended_primary_subject_type="Student",
            intended_primary_subject_id="STU-1",
            intended_data_class="assessment",
            intended_purpose="assessment_submission",
            intended_retention_policy="until_school_exit_plus_6m",
            intended_slot="feedback_export__released__student",
            upload_contract_json='{"workflow":{"workflow_payload":{"audience":"student"}}}',
        )

        with _drive_task_submission_module() as module:
            with self.assertRaises(StubValidationError):
                module.validate_task_feedback_export_finalize_context(upload_session_doc)

    def test_assert_task_submission_upload_access_allows_session_student_owner(self):
        task_submission_doc = SimpleNamespace(
            name="TSU-0001",
            student="STU-1",
            school="SCH-1",
            check_permission=lambda permission_type=None: (_ for _ in ()).throw(StubPermissionError("Not permitted.")),
        )

        with _drive_task_submission_module(task_submission_doc, session_student="STU-1") as module:
            resolved = module.assert_task_submission_upload_access("TSU-0001", permission_type="write")

        self.assertIs(resolved, task_submission_doc)

    def test_assert_task_submission_upload_access_rejects_non_owner_student(self):
        task_submission_doc = SimpleNamespace(
            name="TSU-0001",
            student="STU-1",
            school="SCH-1",
            check_permission=lambda permission_type=None: (_ for _ in ()).throw(StubPermissionError("Not permitted.")),
        )

        with _drive_task_submission_module(task_submission_doc, session_student="STU-OTHER") as module:
            with self.assertRaises(StubPermissionError):
                module.assert_task_submission_upload_access("TSU-0001", permission_type="write")
