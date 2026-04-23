from __future__ import annotations

import importlib.machinery
import sys
import types
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh


def _purge_modules(*prefixes: str) -> None:
    for module_name in list(sys.modules):
        if any(module_name == prefix or module_name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(module_name, None)


def _stub_module(name: str, *, is_package: bool = False) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=is_package)
    if is_package:
        module.__path__ = []
        module.__package__ = name
    else:
        module.__package__ = name.rpartition(".")[0]
    return module


class TestMediaClient(TestCase):
    def test_request_profile_image_preview_derivatives_prefers_media_api_wrapper(self):
        _purge_modules(
            "ifitwala_ed.integrations.drive.media_client",
            "ifitwala_drive",
        )
        recorder = {}
        drive_root = _stub_module("ifitwala_drive", is_package=True)
        drive_api = _stub_module("ifitwala_drive.api", is_package=True)
        drive_media = _stub_module("ifitwala_drive.api.media")

        def _request_student_image_preview_derivatives(**kwargs):
            recorder["payload"] = kwargs
            return {"status": "ok"}

        drive_media.request_student_image_preview_derivatives = _request_student_image_preview_derivatives
        with patch.dict(
            sys.modules,
            {
                "ifitwala_drive": drive_root,
                "ifitwala_drive.api": drive_api,
                "ifitwala_drive.api.media": drive_media,
            },
        ):
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
        drive_root = _stub_module("ifitwala_drive", is_package=True)
        drive_services = _stub_module("ifitwala_drive.services", is_package=True)
        drive_integration = _stub_module("ifitwala_drive.services.integration", is_package=True)
        drive_media_service = _stub_module("ifitwala_drive.services.integration.ifitwala_ed_media")
        with patch.dict(
            sys.modules,
            {
                "ifitwala_drive": drive_root,
                "ifitwala_drive.services": drive_services,
                "ifitwala_drive.services.integration": drive_integration,
                "ifitwala_drive.services.integration.ifitwala_ed_media": drive_media_service,
            },
        ):
            module = import_fresh("ifitwala_ed.integrations.drive.media_client")
            response = module.request_profile_image_preview_derivatives(
                "Guardian",
                "GRD-0001",
                file_id="FILE-GRD-1",
                derivative_roles=["thumb"],
            )

        self.assertIsNone(response)
