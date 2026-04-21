from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _patch_module():
    repair_calls: list[str] = []
    sync_calls: list[tuple[str, str]] = []
    run_calls: list[str] = []

    repair_module = ModuleType("ifitwala_ed.patches.repair_governed_profile_images")
    repair_module.execute = lambda: repair_calls.append("repair")

    drive_root = ModuleType("ifitwala_drive")
    drive_services = ModuleType("ifitwala_drive.services")
    drive_files = ModuleType("ifitwala_drive.services.files")

    derivatives = ModuleType("ifitwala_drive.services.files.derivatives")
    derivatives.preview_plan_for_drive_file = lambda drive_file_doc, mime_type: {
        "supported": True,
        "derivative_roles": ["viewer_preview", "card", "thumb"],
    }
    derivatives.resolve_ready_preview_derivative_state = lambda drive_file_doc, derivative_role: {"state": "missing"}
    derivatives.sync_preview_pipeline_for_current_version = lambda *, drive_file_doc, mime_type: (
        sync_calls.append((drive_file_doc.name, mime_type)) or {"drive_processing_job_id": f"DPJ-{drive_file_doc.name}"}
    )
    derivatives.run_preview_job = lambda *, drive_processing_job_id: run_calls.append(drive_processing_job_id)

    versions = ModuleType("ifitwala_drive.services.files.versions")
    versions.ensure_current_drive_file_version = lambda *, drive_file_doc: f"DFV-{drive_file_doc.name}"

    drive_doc = SimpleNamespace(name="DF-0001", current_version=None)

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.patches.repair_governed_profile_images": repair_module,
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
        frappe.get_all = lambda doctype, **kwargs: [{"name": "DF-0001"}]
        frappe.get_doc = lambda doctype, name: drive_doc

        yield (
            import_fresh("ifitwala_ed.patches.rerun_governed_profile_image_repairs"),
            repair_calls,
            sync_calls,
            run_calls,
        )


class TestRerunGovernedProfileImageRepairs(TestCase):
    def test_execute_reruns_profile_image_repair_and_materializes_missing_derivatives(self):
        with _patch_module() as (module, repair_calls, sync_calls, run_calls):
            module.execute()

        self.assertEqual(repair_calls, ["repair"])
        self.assertEqual(sync_calls, [("DF-0001", "image/png")])
        self.assertEqual(run_calls, ["DPJ-DF-0001"])

    def test_execute_skips_render_when_current_profile_derivatives_are_already_ready(self):
        with _patch_module() as (module, repair_calls, sync_calls, run_calls):
            module.resolve_ready_preview_derivative_state = lambda drive_file_doc, derivative_role: {"state": "ready"}

            module.execute()

        self.assertEqual(repair_calls, ["repair"])
        self.assertEqual(sync_calls, [])
        self.assertEqual(run_calls, [])
