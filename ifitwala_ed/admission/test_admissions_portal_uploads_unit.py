from __future__ import annotations

import base64
import importlib.machinery
import sys
from contextlib import contextmanager
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


@contextmanager
def _admissions_portal_module():
    admission_utils = ModuleType("ifitwala_ed.admission.admission_utils")
    admission_utils.get_applicant_document_slot_spec = lambda **kwargs: {}

    governed_uploads = ModuleType("ifitwala_ed.utilities.governed_uploads")
    governed_uploads._drive_upload_and_finalize = lambda **kwargs: None
    governed_uploads._resolve_upload_mime_type_hint = lambda **kwargs: None
    governed_uploads._workflow_result_payload = lambda response: dict((response or {}).get("workflow_result") or {})

    drive_admissions_api = _stub_module("ifitwala_drive.api.admissions")
    drive_admissions_api.upload_applicant_document = object()
    drive_admissions_api.upload_applicant_profile_image = object()
    drive_admissions_api.upload_applicant_guardian_image = object()

    drive_root = _stub_module("ifitwala_drive", is_package=True)
    drive_api = _stub_module("ifitwala_drive.api", is_package=True)
    drive_api.admissions = drive_admissions_api
    drive_root.api = drive_api

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.admission.admission_utils": admission_utils,
            "ifitwala_ed.utilities.governed_uploads": governed_uploads,
            "ifitwala_drive": drive_root,
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
    image_utils.get_employee_image_variants_map = lambda employee_names, **kwargs: {}
    image_utils.get_preferred_employee_avatar_url = lambda employee_name, original_url=None: original_url
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
    def test_upload_applicant_document_resolves_parent_from_item_when_type_is_not_bound(self):
        file_doc = SimpleNamespace(name="FILE-0003", file_url="/private/files/transcript.pdf")
        document_doc = SimpleNamespace(
            name="APP-DOC-0001",
            student_applicant="APP-0001",
            document_type="Transcript",
        )
        item_doc = SimpleNamespace(
            name="ADI-0001",
            item_key="aisl_2019",
            item_label="AISL transcript 2019",
        )

        class FakeLock:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeCache:
            def get_value(self, key):
                return None

            def set_value(self, key, value, expires_in_sec=None):
                return None

            def lock(self, key, timeout=15):
                return FakeLock()

        with _admissions_portal_module() as admissions_portal:
            captured_resolver_kwargs = {}

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Applicant Document Type" and fieldname == "code":
                    return "transcript"
                if doctype == "Student Applicant" and as_dict:
                    return {"organization": "ORG-1", "school": "SCH-1"}
                return None

            def fake_resolve_applicant_document(**kwargs):
                captured_resolver_kwargs.update(kwargs)
                return document_doc

            with (
                patch.object(admissions_portal.frappe, "cache", return_value=FakeCache(), create=True),
                patch.object(admissions_portal.frappe.db, "get_value", side_effect=fake_get_value, create=True),
                patch.object(
                    admissions_portal,
                    "get_applicant_document_slot_spec",
                    return_value={
                        "slot": "academic_report",
                        "data_class": "academic",
                        "purpose": "academic_report",
                        "retention_policy": "until_school_exit_plus_6m",
                    },
                ),
                patch.object(
                    admissions_portal,
                    "_resolve_applicant_document",
                    side_effect=fake_resolve_applicant_document,
                ),
                patch.object(
                    admissions_portal,
                    "_resolve_applicant_document_item",
                    return_value=item_doc,
                ),
                patch.object(
                    admissions_portal,
                    "_drive_upload_and_finalize",
                    return_value=(
                        {"upload_session_id": "DUS-0003"},
                        {
                            "drive_file_id": "DRV-FILE-0003",
                            "canonical_ref": "drv:ORG-1:DRV-FILE-0003",
                            "workflow_result": {
                                "applicant_document": document_doc.name,
                                "applicant_document_item": item_doc.name,
                                "item_key": item_doc.item_key,
                                "item_label": item_doc.item_label,
                            },
                        },
                        file_doc,
                    ),
                ),
            ):
                payload = admissions_portal.upload_applicant_document(
                    applicant_document_item=item_doc.name,
                    file_name="transcript.pdf",
                    content=base64.b64encode(b"pdf-bytes").decode(),
                )

        self.assertEqual(captured_resolver_kwargs["applicant_document_item"], item_doc.name)
        self.assertEqual(payload["applicant_document"], document_doc.name)
        self.assertEqual(payload["applicant_document_item"], item_doc.name)

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
                            "workflow_result": {"slot": "profile_image"},
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
                            "workflow_result": {"slot": "profile_image"},
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
