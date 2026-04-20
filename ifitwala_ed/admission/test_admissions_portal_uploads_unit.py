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
    governed_uploads._resolve_upload_mime_type_hint = lambda **kwargs: None

    drive_admissions_api = ModuleType("ifitwala_drive.api.admissions")
    drive_admissions_api.upload_applicant_document = object()
    drive_admissions_api.upload_applicant_profile_image = object()
    drive_admissions_api.upload_applicant_guardian_image = object()

    drive_api = ModuleType("ifitwala_drive.api")
    drive_api.admissions = drive_admissions_api

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.admission.admission_utils": admission_utils,
            "ifitwala_ed.utilities.governed_uploads": governed_uploads,
            "ifitwala_drive.api": drive_api,
            "ifitwala_drive.api.admissions": drive_admissions_api,
        }
    ) as frappe:
        frappe.request = None
        sys.modules["frappe.utils"].cint = lambda value=0: int(value or 0)
        yield import_fresh("ifitwala_ed.admission.admissions_portal")


def _load_real_mime_type_resolver():
    image_utils = ModuleType("ifitwala_ed.utilities.image_utils")
    image_utils.EMPLOYEE_VARIANT_PRIORITY = []
    image_utils.file_url_is_accessible = lambda file_url, *, file_name=None, is_private=0: True
    image_utils.get_employee_image_variants_map = lambda employee_names: {}
    image_utils.get_preferred_employee_image_url = lambda employee_name, original_url=None, slots=None: original_url

    organization_media = ModuleType("ifitwala_ed.utilities.organization_media")
    organization_media.build_organization_media_slot = lambda **kwargs: "organization_media__test"

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.utilities.image_utils": image_utils,
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
        module = import_fresh("ifitwala_ed.utilities.governed_uploads")

    return module._resolve_upload_mime_type_hint


class TestAdmissionsPortalUploadMimeHints(TestCase):
    def test_upload_applicant_profile_image_uses_resolved_mime_type_hint(self):
        file_doc = SimpleNamespace(name="FILE-0001", file_url="/private/files/profile.jpg")

        with _admissions_portal_module() as admissions_portal:
            with (
                patch.object(
                    admissions_portal,
                    "_resolve_upload_mime_type_hint",
                    return_value="image/jpeg",
                ) as resolve_mime_type,
                patch.object(
                    admissions_portal,
                    "_drive_upload_and_finalize",
                    return_value=(
                        {"upload_session_id": "DUS-0001"},
                        {
                            "drive_file_id": "DRV-FILE-0001",
                            "canonical_ref": "drv:ORG-1:DRV-FILE-0001",
                            "slot": "profile_image",
                        },
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
        self.assertEqual(payload["drive_file_id"], "DRV-FILE-0001")
        self.assertEqual(payload["canonical_ref"], "drv:ORG-1:DRV-FILE-0001")

    def test_upload_applicant_profile_image_ignores_multipart_hint_and_falls_back_to_filename(self):
        file_doc = SimpleNamespace(name="FILE-0002", file_url="/private/files/profile.png")
        real_resolver = _load_real_mime_type_resolver()

        with _admissions_portal_module() as admissions_portal:
            with (
                patch.object(
                    admissions_portal,
                    "_resolve_upload_mime_type_hint",
                    wraps=real_resolver,
                ) as resolve_mime_type,
                patch.object(
                    admissions_portal,
                    "_drive_upload_and_finalize",
                    return_value=(
                        {"upload_session_id": "DUS-0002"},
                        {
                            "drive_file_id": "DRV-FILE-0002",
                            "canonical_ref": "drv:ORG-1:DRV-FILE-0002",
                            "slot": "profile_image",
                        },
                        file_doc,
                    ),
                ) as bridge,
            ):
                payload = admissions_portal.upload_applicant_profile_image(
                    student_applicant="APP-0001",
                    file_name="profile.png",
                    content=b"profile-bytes",
                    mime_type_hint="multipart/form-data",
                )

        resolve_mime_type.assert_called_once_with(filename="profile.png", explicit="multipart/form-data")
        bridge.assert_called_once()
        self.assertEqual(bridge.call_args.kwargs["payload"]["mime_type_hint"], "image/png")
        self.assertEqual(payload["drive_file_id"], "DRV-FILE-0002")
        self.assertEqual(payload["canonical_ref"], "drv:ORG-1:DRV-FILE-0002")
