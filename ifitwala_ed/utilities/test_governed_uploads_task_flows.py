from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _governed_uploads_module():
    file_dispatcher = ModuleType("ifitwala_ed.utilities.file_dispatcher")
    file_dispatcher.create_and_classify_file = lambda **kwargs: None

    organization_media = ModuleType("ifitwala_ed.utilities.organization_media")
    organization_media.build_organization_media_slot = lambda **kwargs: "organization_media__test"

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.utilities.file_dispatcher": file_dispatcher,
            "ifitwala_ed.utilities.organization_media": organization_media,
        }
    ) as frappe:
        frappe.form_dict = {}
        frappe.request = None
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.set_value = lambda *args, **kwargs: None
        frappe.generate_hash = lambda length=10: "x" * length
        frappe.scrub = lambda value: str(value or "").strip().lower().replace(" ", "_")
        frappe.utils = SimpleNamespace(get_site_path=lambda *parts: "/tmp")
        yield import_fresh("ifitwala_ed.utilities.governed_uploads")


class _FakeDoc:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.append_calls = []
        self.saved = 0

    def append(self, fieldname, row):
        self.append_calls.append((fieldname, row))
        return SimpleNamespace(**row)

    def save(self, ignore_permissions=False):
        self.saved += 1
        return self


class TestGovernedUploadTaskFlows(TestCase):
    def test_upload_task_submission_attachment_uses_drive_wrapper(self):
        doc = _FakeDoc(name="TSUB-0001", school="SCH-0001", student="STU-0001")
        fake_drive_api = SimpleNamespace(upload_task_submission_artifact=object())
        file_doc = SimpleNamespace(
            name="FILE-0001",
            file_url="/private/files/submission.pdf",
            file_name="submission.pdf",
            file_size=256,
        )

        with _governed_uploads_module() as governed_uploads:
            with (
                patch.object(governed_uploads, "_require_doc", return_value=doc),
                patch.object(governed_uploads, "_get_uploaded_file", return_value=("submission.pdf", b"content")),
                patch.object(governed_uploads, "_load_drive_module", return_value=fake_drive_api),
                patch.object(governed_uploads, "_ensure_file_on_disk"),
                patch.object(
                    governed_uploads,
                    "_drive_upload_and_finalize",
                    return_value=({"upload_session_id": "DUS-1"}, {"file_id": "FILE-0001"}, file_doc),
                ) as bridge,
            ):
                payload = governed_uploads.upload_task_submission_attachment(task_submission="TSUB-0001")

        bridge.assert_called_once()
        self.assertIs(
            bridge.call_args.kwargs["create_session_callable"], fake_drive_api.upload_task_submission_artifact
        )
        self.assertEqual(bridge.call_args.kwargs["payload"]["task_submission"], "TSUB-0001")
        self.assertEqual(doc.saved, 1)
        self.assertEqual(doc.append_calls[0][0], "attachments")
        self.assertEqual(doc.append_calls[0][1]["file"], "/private/files/submission.pdf")
        self.assertEqual(payload["file"], "FILE-0001")

    def test_upload_task_resource_uses_drive_wrapper(self):
        doc = _FakeDoc(name="TASK-0001")
        fake_drive_api = SimpleNamespace(upload_task_resource=object())
        file_doc = SimpleNamespace(
            name="FILE-0002",
            file_url="/private/files/resource.pdf",
            file_name="resource.pdf",
            file_size=512,
        )

        with _governed_uploads_module() as governed_uploads:
            with (
                patch.object(governed_uploads, "_require_doc", return_value=doc),
                patch.object(governed_uploads, "_require_clean_saved_doc", return_value=doc),
                patch.object(governed_uploads, "_get_uploaded_file", return_value=("resource.pdf", b"content")),
                patch.object(governed_uploads, "_load_drive_module", return_value=fake_drive_api),
                patch.object(governed_uploads, "_ensure_file_on_disk"),
                patch.object(
                    governed_uploads,
                    "_drive_upload_and_finalize",
                    return_value=(
                        {"upload_session_id": "DUS-2", "row_name": "row-001"},
                        {"file_id": "FILE-0002", "row_name": "row-001"},
                        file_doc,
                    ),
                ) as bridge,
            ):
                payload = governed_uploads.upload_task_resource(task="TASK-0001")

        bridge.assert_called_once()
        self.assertIs(bridge.call_args.kwargs["create_session_callable"], fake_drive_api.upload_task_resource)
        self.assertEqual(bridge.call_args.kwargs["payload"]["task"], "TASK-0001")
        self.assertEqual(payload["file"], "FILE-0002")
        self.assertEqual(payload["row_name"], "row-001")
