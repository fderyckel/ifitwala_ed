from __future__ import annotations

import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _admissions_portal_module():
    admission_utils = ModuleType("ifitwala_ed.admission.admission_utils")
    admission_utils.get_applicant_document_slot_spec = lambda **kwargs: {}

    governed_uploads = ModuleType("ifitwala_ed.utilities.governed_uploads")
    governed_uploads._drive_upload_and_finalize = lambda **kwargs: None
    governed_uploads._load_drive_module = lambda module_name: None
    governed_uploads._resolve_upload_mime_type_hint = lambda **kwargs: None

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.admission.admission_utils": admission_utils,
            "ifitwala_ed.utilities.governed_uploads": governed_uploads,
        }
    ) as frappe:
        frappe.request = None
        sys.modules["frappe.utils"].cint = lambda value=0: int(value or 0)
        yield import_fresh("ifitwala_ed.admission.admissions_portal")


class TestAdmissionsPortalUploadMimeHints(TestCase):
    def test_upload_applicant_profile_image_uses_resolved_mime_type_hint(self):
        fake_drive_api = SimpleNamespace(upload_applicant_profile_image=object())
        file_doc = SimpleNamespace(name="FILE-0001", file_url="/private/files/profile.jpg")

        with _admissions_portal_module() as admissions_portal:
            with (
                patch.object(
                    admissions_portal,
                    "_resolve_upload_mime_type_hint",
                    return_value="image/jpeg",
                ) as resolve_mime_type,
                patch.object(admissions_portal, "_load_drive_module", return_value=fake_drive_api),
                patch.object(
                    admissions_portal,
                    "_drive_upload_and_finalize",
                    return_value=(
                        {"upload_session_id": "DUS-0001"},
                        {"classification": "CLS-0001", "slot": "profile_image"},
                        file_doc,
                    ),
                ) as bridge,
            ):
                payload = admissions_portal.upload_applicant_profile_image(
                    student_applicant="APP-0001",
                    file_name="profile.jpg",
                    content=b"profile-bytes",
                )

        resolve_mime_type.assert_called_once_with(filename="profile.jpg", explicit=None)
        bridge.assert_called_once()
        self.assertEqual(bridge.call_args.kwargs["payload"]["mime_type_hint"], "image/jpeg")
        self.assertEqual(payload["classification"], "CLS-0001")
