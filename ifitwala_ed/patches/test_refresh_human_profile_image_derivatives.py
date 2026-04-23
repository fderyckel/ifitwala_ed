from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _patch_module():
    drive_root = ModuleType("ifitwala_drive")
    drive_services = ModuleType("ifitwala_drive.services")
    drive_files = ModuleType("ifitwala_drive.services.files")

    stale_calls: list[tuple[str, str]] = []
    sync_calls: list[tuple[str, str]] = []
    run_calls: list[str] = []

    derivatives = ModuleType("ifitwala_drive.services.files.derivatives")
    derivatives.mark_version_derivatives_stale = lambda *, drive_file_id, drive_file_version_id: (
        stale_calls.append((drive_file_id, drive_file_version_id)) or 1
    )
    derivatives.preview_plan_for_drive_file = lambda drive_file_doc, mime_type: {
        "supported": True,
        "derivative_roles": ["viewer_preview", "card", "thumb"],
    }
    derivatives.sync_preview_pipeline_for_current_version = lambda *, drive_file_doc, mime_type: (
        sync_calls.append((drive_file_doc.name, mime_type)) or {"drive_processing_job_id": f"DPJ-{drive_file_doc.name}"}
    )
    derivatives.run_preview_job = lambda *, drive_processing_job_id: run_calls.append(drive_processing_job_id)

    versions = ModuleType("ifitwala_drive.services.files.versions")
    versions.ensure_current_drive_file_version = lambda *, drive_file_doc: f"DFV-{drive_file_doc.name}"

    docs = {
        "DF-STU-1": SimpleNamespace(name="DF-STU-1", current_version=None),
        "DF-APP-1": SimpleNamespace(name="DF-APP-1", current_version=None),
        "DF-GRD-1": SimpleNamespace(name="DF-GRD-1", current_version=None),
        "DF-SKIP-1": SimpleNamespace(name="DF-SKIP-1", current_version=None),
    }

    with stubbed_frappe(
        extra_modules={
            "ifitwala_drive": drive_root,
            "ifitwala_drive.services": drive_services,
            "ifitwala_drive.services.files": drive_files,
            "ifitwala_drive.services.files.derivatives": derivatives,
            "ifitwala_drive.services.files.versions": versions,
        }
    ) as frappe:
        frappe.as_json = lambda value, indent=2: value
        frappe.log_error = lambda *args, **kwargs: None
        frappe.db.table_exists = lambda doctype: doctype in {"Drive File", "Drive File Version"}
        frappe.db.get_value = lambda doctype, name, fieldname: "image/png"
        frappe.get_all = lambda doctype, **kwargs: [
            {"name": "DF-STU-1", "primary_subject_type": "Student", "slot": "profile_image"},
            {"name": "DF-APP-1", "primary_subject_type": "Student Applicant", "slot": "profile_image"},
            {
                "name": "DF-GRD-1",
                "primary_subject_type": "Student Applicant",
                "slot": "guardian_profile_image__row-1",
            },
            {"name": "DF-SKIP-1", "primary_subject_type": "Student Applicant", "slot": "identity_document"},
        ]
        frappe.get_doc = lambda doctype, name: docs[name]

        yield (
            import_fresh("ifitwala_ed.patches.refresh_human_profile_image_derivatives"),
            stale_calls,
            sync_calls,
            run_calls,
        )


class TestRefreshHumanProfileImageDerivatives(TestCase):
    def test_execute_marks_stale_and_reruns_only_human_profile_image_slots(self):
        with _patch_module() as (module, stale_calls, sync_calls, run_calls):
            module.execute()

        self.assertEqual(
            stale_calls,
            [
                ("DF-STU-1", "DFV-DF-STU-1"),
                ("DF-APP-1", "DFV-DF-APP-1"),
                ("DF-GRD-1", "DFV-DF-GRD-1"),
            ],
        )
        self.assertEqual(
            sync_calls,
            [
                ("DF-STU-1", "image/png"),
                ("DF-APP-1", "image/png"),
                ("DF-GRD-1", "image/png"),
            ],
        )
        self.assertEqual(
            run_calls,
            ["DPJ-DF-STU-1", "DPJ-DF-APP-1", "DPJ-DF-GRD-1"],
        )
