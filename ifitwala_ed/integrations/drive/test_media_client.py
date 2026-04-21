from __future__ import annotations

import sys
import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh


def _purge_modules(*prefixes: str) -> None:
    for module_name in list(sys.modules):
        if any(module_name == prefix or module_name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(module_name, None)


class TestMediaClient(TestCase):
    def test_request_profile_image_preview_derivatives_prefers_media_api_wrapper(self):
        _purge_modules(
            "ifitwala_ed.integrations.drive.media_client",
            "ifitwala_drive",
        )
        recorder = {}
        drive_root = types.ModuleType("ifitwala_drive")
        drive_api = types.ModuleType("ifitwala_drive.api")
        drive_media = types.ModuleType("ifitwala_drive.api.media")

        def _request_student_image_preview_derivatives(**kwargs):
            recorder["payload"] = kwargs
            return {"status": "ok"}

        drive_media.request_student_image_preview_derivatives = _request_student_image_preview_derivatives
        sys.modules["ifitwala_drive"] = drive_root
        sys.modules["ifitwala_drive.api"] = drive_api
        sys.modules["ifitwala_drive.api.media"] = drive_media

        module = import_fresh("ifitwala_ed.integrations.drive.media_client")
        response = module.request_profile_image_preview_derivatives(
            "Student",
            "STU-0001",
            file_id="FILE-STU-1",
            derivative_roles=["thumb", "card"],
        )

        self.assertEqual(
            recorder["payload"],
            {
                "student": "STU-0001",
                "file_id": "FILE-STU-1",
                "derivative_roles": ["thumb", "card"],
            },
        )
        self.assertEqual(response, {"status": "ok"})

    def test_request_profile_image_preview_derivatives_fails_closed_without_media_api_wrapper(self):
        _purge_modules(
            "ifitwala_ed.integrations.drive.media_client",
            "ifitwala_drive",
        )
        drive_root = types.ModuleType("ifitwala_drive")
        drive_services = types.ModuleType("ifitwala_drive.services")
        drive_integration = types.ModuleType("ifitwala_drive.services.integration")
        drive_media_service = types.ModuleType("ifitwala_drive.services.integration.ifitwala_ed_media")
        sys.modules["ifitwala_drive"] = drive_root
        sys.modules["ifitwala_drive.services"] = drive_services
        sys.modules["ifitwala_drive.services.integration"] = drive_integration
        sys.modules["ifitwala_drive.services.integration.ifitwala_ed_media"] = drive_media_service

        module = import_fresh("ifitwala_ed.integrations.drive.media_client")
        response = module.request_profile_image_preview_derivatives(
            "Guardian",
            "GRD-0001",
            file_id="FILE-GRD-1",
            derivative_roles=["thumb"],
        )

        self.assertIsNone(response)
