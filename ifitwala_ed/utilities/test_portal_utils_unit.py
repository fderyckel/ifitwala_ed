from __future__ import annotations

import importlib.machinery
import io
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _stub_module(name: str, *, is_package: bool = False) -> ModuleType:
    module = ModuleType(name)
    module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=is_package)
    if is_package:
        module.__path__ = []
        module.__package__ = name
    else:
        module.__package__ = name.rpartition(".")[0]
    return module


def _portal_utils_extra_modules() -> dict[str, ModuleType]:
    notification_log = _stub_module("frappe.desk.doctype.notification_log.notification_log")
    notification_log.enqueue_create_notification = lambda *args, **kwargs: None

    frappe_exceptions = _stub_module("frappe.exceptions")
    frappe_exceptions.UniqueValidationError = type("UniqueValidationError", (Exception,), {})

    frappe_utils = _stub_module("frappe.utils")
    frappe_utils.add_to_date = lambda value, **kwargs: value
    frappe_utils.now_datetime = lambda: "2026-04-27 09:00:00"
    frappe_utils.today = lambda: "2026-04-27"

    return {
        "frappe.desk": _stub_module("frappe.desk", is_package=True),
        "frappe.desk.doctype": _stub_module("frappe.desk.doctype", is_package=True),
        "frappe.desk.doctype.notification_log": _stub_module(
            "frappe.desk.doctype.notification_log",
            is_package=True,
        ),
        "frappe.desk.doctype.notification_log.notification_log": notification_log,
        "frappe.exceptions": frappe_exceptions,
        "frappe.utils": frappe_utils,
    }


class TestPortalUtilsUnit(TestCase):
    def test_self_referral_upload_uses_drive_generic_workflow_boundary(self):
        create_session_calls = []
        drive_uploads = _stub_module("ifitwala_drive.api.uploads")

        def create_upload_session(**kwargs):
            create_session_calls.append(kwargs)
            return {"upload_session_id": "DUS-REF-0001"}

        drive_uploads.create_upload_session = create_upload_session
        drive_api = _stub_module("ifitwala_drive.api", is_package=True)
        drive_api.uploads = drive_uploads
        drive_root = _stub_module("ifitwala_drive", is_package=True)
        drive_root.api = drive_api

        governed_uploads = _stub_module("ifitwala_ed.utilities.governed_uploads")
        observed = {}

        def fake_drive_upload_and_finalize(*, create_session_callable, payload, content):
            observed["create_session_callable"] = create_session_callable
            observed["payload"] = payload
            observed["content"] = content
            create_session_callable(**payload)
            return (
                {"upload_session_id": "DUS-REF-0001"},
                {
                    "file_id": "FILE-REF-0001",
                    "drive_file_id": "DF-REF-0001",
                    "canonical_ref": "drv:ORG-0001:DF-REF-0001",
                    "preview_status": "pending",
                },
                SimpleNamespace(
                    name="FILE-REF-0001",
                    file_name="note.pdf",
                    file_size=32,
                    file_url="/private/files/note.pdf",
                ),
            )

        governed_uploads._drive_upload_and_finalize = fake_drive_upload_and_finalize
        governed_uploads._ensure_file_on_disk = lambda file_doc: observed.setdefault("ensured", file_doc.name)
        governed_uploads._resolve_upload_mime_type_hint = lambda *, filename, explicit=None: "application/pdf"

        extra_modules = {
            **_portal_utils_extra_modules(),
            "ifitwala_drive": drive_root,
            "ifitwala_drive.api": drive_api,
            "ifitwala_drive.api.uploads": drive_uploads,
            "ifitwala_ed.utilities.governed_uploads": governed_uploads,
        }

        with stubbed_frappe(extra_modules=extra_modules) as frappe:
            frappe.request = SimpleNamespace(
                files={
                    "file": SimpleNamespace(
                        filename="note.pdf",
                        stream=io.BytesIO(b"student referral attachment"),
                    )
                }
            )
            portal_utils = import_fresh("ifitwala_ed.utilities.portal_utils")
            referral = SimpleNamespace(name="SRF-2026-0001")

            with (
                patch.object(
                    portal_utils,
                    "assert_self_referral_attachment_upload_access",
                    return_value=referral,
                ),
                patch.object(
                    portal_utils,
                    "build_student_referral_attachment_slot",
                    return_value="student_referral_attachment__abc123",
                ),
            ):
                response = portal_utils.upload_self_referral_file("SRF-2026-0001")

        self.assertIs(observed["create_session_callable"], create_upload_session)
        self.assertEqual(create_session_calls[0]["workflow_id"], "student_referral.attachment")
        self.assertEqual(
            observed["payload"]["workflow_payload"],
            {
                "student_referral": "SRF-2026-0001",
                "slot": "student_referral_attachment__abc123",
            },
        )
        self.assertEqual(observed["payload"]["filename_original"], "note.pdf")
        self.assertEqual(observed["payload"]["mime_type_hint"], "application/pdf")
        self.assertEqual(observed["payload"]["upload_source"], "Student Portal")
        self.assertEqual(observed["content"], b"student referral attachment")
        self.assertEqual(response["name"], "FILE-REF-0001")
        self.assertEqual(response["drive_file_id"], "DF-REF-0001")
        self.assertNotIn("file_url", response)
        self.assertEqual(observed["ensured"], "FILE-REF-0001")
