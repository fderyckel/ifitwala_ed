from __future__ import annotations

import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _governed_uploads_module():
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
        yield import_fresh("ifitwala_ed.utilities.governed_uploads")


@contextmanager
def _patched_drive_api_module(module_name: str, **attributes):
    root_module = ModuleType("ifitwala_drive")
    api_module = ModuleType("ifitwala_drive.api")
    child_module = ModuleType(module_name)
    for key, value in attributes.items():
        setattr(child_module, key, value)
    setattr(api_module, module_name.rsplit(".", 1)[-1], child_module)
    setattr(root_module, "api", api_module)
    with patch.dict(
        sys.modules,
        {
            "ifitwala_drive": root_module,
            "ifitwala_drive.api": api_module,
            module_name: child_module,
        },
    ):
        yield child_module


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
    def test_drive_upload_and_finalize_injects_idempotency_key_and_uses_drive_owned_ingest(self):
        ingest_calls = []
        uploads_api = SimpleNamespace(
            ingest_upload_session_content=lambda **kwargs: ingest_calls.append(kwargs),
            finalize_upload_session=lambda **kwargs: {"file_id": "FILE-EMP-0001"},
        )
        file_doc = SimpleNamespace(name="FILE-EMP-0001")
        observed = {}

        def strict_wrapper(
            *,
            employee,
            filename_original,
            mime_type_hint=None,
            expected_size_bytes=None,
            idempotency_key=None,
            upload_source=None,
        ):
            observed.update(
                {
                    "employee": employee,
                    "filename_original": filename_original,
                    "mime_type_hint": mime_type_hint,
                    "expected_size_bytes": expected_size_bytes,
                    "idempotency_key": idempotency_key,
                    "upload_source": upload_source,
                }
            )
            return {
                "upload_session_id": "DUS-EMP-1",
                "upload_token": "drive-token-123",
                "upload_target": {"headers": {"X-Drive-Upload-Token": "drive-token-123"}},
            }

        def fake_get_doc(doctype, name):
            if doctype == "File":
                self.assertEqual(name, "FILE-EMP-0001")
                return file_doc
            raise AssertionError(f"Unexpected get_doc call: {doctype} {name}")

        with _governed_uploads_module() as governed_uploads:
            base_payload = {
                "employee": "EMP-0001",
                "filename_original": "employee-photo.png",
                "mime_type_hint": "image/png",
                "expected_size_bytes": len(b"employee-content"),
                "upload_source": "Desk",
            }
            expected_idempotency_key = governed_uploads._build_drive_idempotency_key(
                payload=base_payload,
                content=b"employee-content",
            )

            with _patched_drive_api_module(
                "ifitwala_drive.api.uploads",
                ingest_upload_session_content=uploads_api.ingest_upload_session_content,
                finalize_upload_session=uploads_api.finalize_upload_session,
            ):
                with patch.object(governed_uploads.frappe, "get_doc", side_effect=fake_get_doc):
                    session_response, finalize_response, returned_file_doc = (
                        governed_uploads._drive_upload_and_finalize(
                            create_session_callable=strict_wrapper,
                            payload=base_payload,
                            content=b"employee-content",
                        )
                    )

        self.assertEqual(observed["employee"], "EMP-0001")
        self.assertEqual(observed["filename_original"], "employee-photo.png")
        self.assertEqual(observed["mime_type_hint"], "image/png")
        self.assertEqual(observed["expected_size_bytes"], len(b"employee-content"))
        self.assertEqual(observed["idempotency_key"], expected_idempotency_key)
        self.assertEqual(observed["upload_source"], "Desk")
        self.assertEqual(
            ingest_calls,
            [
                {
                    "upload_session_id": "DUS-EMP-1",
                    "upload_token": "drive-token-123",
                    "content": b"employee-content",
                }
            ],
        )
        self.assertEqual(session_response["upload_session_id"], "DUS-EMP-1")
        self.assertEqual(finalize_response["file_id"], "FILE-EMP-0001")
        self.assertIs(returned_file_doc, file_doc)

    def test_ensure_file_on_disk_accepts_drive_backed_storage_when_accessible(self):
        file_doc = SimpleNamespace(
            name="FILE-EMP-0001",
            file_url="/private/files/ifitwala_drive/files/aa/bb/employee-photo.png",
            is_private=1,
        )

        with _governed_uploads_module() as governed_uploads:
            governed_uploads._ensure_file_on_disk(file_doc)

    def test_ensure_file_on_disk_rejects_inaccessible_storage_target(self):
        file_doc = SimpleNamespace(
            name="FILE-EMP-0001",
            file_url="/private/files/ifitwala_drive/files/aa/bb/employee-photo.png",
            is_private=1,
        )

        with _governed_uploads_module() as governed_uploads:
            governed_uploads.file_url_is_accessible = lambda file_url, *, file_name=None, is_private=0: False

            with self.assertRaises(governed_uploads.frappe.ValidationError):
                governed_uploads._ensure_file_on_disk(file_doc)

    def test_resolve_upload_mime_type_hint_ignores_multipart_envelope(self):
        with _governed_uploads_module() as governed_uploads:
            governed_uploads.frappe.request = SimpleNamespace(
                mimetype="multipart/form-data",
                files={"file": SimpleNamespace(mimetype="image/png", content_type="image/png")},
            )

            mime_type_hint = governed_uploads._resolve_upload_mime_type_hint(
                filename="student-photo.png",
                explicit="multipart/form-data",
            )

        self.assertEqual(mime_type_hint, "image/png")

    def test_upload_student_image_uses_uploaded_file_mime_type_not_request_envelope(self):
        doc = _FakeDoc(
            name="STU-0001",
            anchor_school="SCH-0001",
            student_image="",
        )
        doc.sync_student_contact_image = lambda: None
        fake_drive_api = SimpleNamespace(upload_student_image=object())
        file_doc = SimpleNamespace(
            name="FILE-STU-0001",
            file_url="/private/files/student-photo.png",
            file_name="student-photo.png",
            file_size=640,
        )

        with _governed_uploads_module() as governed_uploads:
            governed_uploads.frappe.request = SimpleNamespace(
                mimetype="multipart/form-data",
                files={"file": SimpleNamespace(mimetype="image/png", content_type="image/png")},
            )
            with (
                patch.object(governed_uploads, "_require_doc", return_value=doc),
                patch.object(
                    governed_uploads,
                    "_get_uploaded_file",
                    return_value=("student-photo.png", b"student-content"),
                ),
                patch.object(
                    governed_uploads,
                    "_get_drive_media_callable",
                    return_value=fake_drive_api.upload_student_image,
                ),
                patch.object(governed_uploads, "_ensure_file_on_disk"),
                patch.object(
                    governed_uploads,
                    "_drive_upload_and_finalize",
                    return_value=({"upload_session_id": "DUS-STU-1"}, {"file_id": "FILE-STU-0001"}, file_doc),
                ) as bridge,
                patch.object(governed_uploads.frappe.db, "set_value") as set_value,
            ):
                payload = governed_uploads.upload_student_image(student="STU-0001")

        bridge.assert_called_once()
        self.assertEqual(bridge.call_args.kwargs["payload"]["mime_type_hint"], "image/png")
        set_value.assert_called_once_with(
            "Student",
            "STU-0001",
            "student_image",
            "/private/files/student-photo.png",
            update_modified=False,
        )
        self.assertEqual(payload["file"], "FILE-STU-0001")

    def test_get_drive_media_callable_requires_public_media_api_method(self):
        with _governed_uploads_module() as governed_uploads:
            with _patched_drive_api_module("ifitwala_drive.api.media"):
                with self.assertRaises(governed_uploads.frappe.ValidationError):
                    governed_uploads._get_drive_media_callable("upload_guardian_image")

    def test_upload_guardian_image_uses_drive_wrapper_and_persists_org_anchor(self):
        doc = _FakeDoc(name="GRD-0001", organization="", guardian_image="")
        doc.resolve_profile_image_organization = lambda: "ORG-0001"
        fake_drive_api = SimpleNamespace(upload_guardian_image=object())
        file_doc = SimpleNamespace(
            name="FILE-0009",
            file_url="/private/files/guardian-photo.png",
            file_name="guardian-photo.png",
            file_size=321,
        )

        with _governed_uploads_module() as governed_uploads:
            with _patched_drive_api_module(
                "ifitwala_drive.api.media",
                upload_guardian_image=fake_drive_api.upload_guardian_image,
            ):
                with (
                    patch.object(governed_uploads, "_require_doc", return_value=doc),
                    patch.object(
                        governed_uploads, "_get_uploaded_file", return_value=("guardian-photo.png", b"content")
                    ),
                    patch.object(governed_uploads, "_ensure_file_on_disk"),
                    patch.object(
                        governed_uploads,
                        "_drive_upload_and_finalize",
                        return_value=({"upload_session_id": "DUS-9"}, {"file_id": "FILE-0009"}, file_doc),
                    ) as bridge,
                    patch.object(governed_uploads.frappe.db, "set_value") as set_value,
                ):
                    payload = governed_uploads.upload_guardian_image(guardian="GRD-0001")

        bridge.assert_called_once()
        self.assertIs(bridge.call_args.kwargs["create_session_callable"], fake_drive_api.upload_guardian_image)
        self.assertEqual(bridge.call_args.kwargs["payload"]["guardian"], "GRD-0001")
        set_value.assert_called_once_with(
            "Guardian",
            "GRD-0001",
            {
                "guardian_image": "/private/files/guardian-photo.png",
                "organization": "ORG-0001",
            },
            update_modified=False,
        )
        self.assertEqual(payload["file"], "FILE-0009")

    def test_upload_employee_image_uses_drive_wrapper_and_syncs_user_image(self):
        doc = _FakeDoc(name="EMP-0001", organization="ORG-0001")
        fake_drive_api = SimpleNamespace(upload_employee_image=object())
        file_doc = SimpleNamespace(
            name="FILE-EMP-0001",
            file_url="/private/files/employee-photo.png",
            file_name="employee-photo.png",
            file_size=640,
        )

        with _governed_uploads_module() as governed_uploads:
            with _patched_drive_api_module(
                "ifitwala_drive.api.media",
                upload_employee_image=fake_drive_api.upload_employee_image,
            ):
                with (
                    patch.object(governed_uploads, "_require_doc", return_value=doc),
                    patch.object(
                        governed_uploads,
                        "_get_uploaded_file",
                        return_value=("employee-photo.png", b"employee-content"),
                    ),
                    patch.object(governed_uploads, "_ensure_file_on_disk"),
                    patch.object(
                        governed_uploads,
                        "_drive_upload_and_finalize",
                        return_value=({"upload_session_id": "DUS-EMP-1"}, {"file_id": "FILE-EMP-0001"}, file_doc),
                    ) as bridge,
                    patch.object(governed_uploads, "_sync_linked_employee_user_image") as sync_user_image,
                    patch.object(governed_uploads.frappe.db, "set_value") as set_value,
                ):
                    payload = governed_uploads.upload_employee_image(employee="EMP-0001")

        bridge.assert_called_once()
        self.assertIs(bridge.call_args.kwargs["create_session_callable"], fake_drive_api.upload_employee_image)
        self.assertEqual(bridge.call_args.kwargs["payload"]["employee"], "EMP-0001")
        self.assertEqual(bridge.call_args.kwargs["payload"]["filename_original"], "employee-photo.png")
        self.assertEqual(bridge.call_args.kwargs["payload"]["expected_size_bytes"], len(b"employee-content"))
        self.assertEqual(bridge.call_args.kwargs["payload"]["upload_source"], "Desk")
        set_value.assert_called_once_with(
            "Employee",
            "EMP-0001",
            "employee_image",
            "/private/files/employee-photo.png",
            update_modified=False,
        )
        sync_user_image.assert_called_once_with("EMP-0001", original_url="/private/files/employee-photo.png")
        self.assertEqual(payload["file"], "FILE-EMP-0001")

    def test_upload_supporting_material_file_uses_drive_wrapper(self):
        doc = _FakeDoc(name="MAT-0001", course="COURSE-1")
        drive_materials_api = SimpleNamespace(upload_supporting_material=object())
        file_doc = SimpleNamespace(
            name="FILE-MAT-0001",
            file_url="/private/files/materials/worksheet.pdf",
            file_name="worksheet.pdf",
            file_size=2048,
        )

        with _governed_uploads_module() as governed_uploads:
            with _patched_drive_api_module(
                "ifitwala_drive.api.materials",
                upload_supporting_material=drive_materials_api.upload_supporting_material,
            ):
                with (
                    patch.object(governed_uploads, "_require_doc", return_value=doc),
                    patch.object(governed_uploads, "_require_clean_saved_doc", return_value=doc),
                    patch.object(
                        governed_uploads,
                        "_get_uploaded_file",
                        return_value=("worksheet.pdf", b"worksheet-content"),
                    ),
                    patch.object(governed_uploads, "_ensure_file_on_disk"),
                    patch.object(
                        governed_uploads,
                        "_drive_upload_and_finalize",
                        return_value=({"upload_session_id": "DUS-MAT-1"}, {"file_id": "FILE-MAT-0001"}, file_doc),
                    ) as bridge,
                ):
                    payload = governed_uploads.upload_supporting_material_file(material="MAT-0001")

        bridge.assert_called_once()
        self.assertIs(
            bridge.call_args.kwargs["create_session_callable"], drive_materials_api.upload_supporting_material
        )
        self.assertEqual(bridge.call_args.kwargs["payload"]["material"], "MAT-0001")
        self.assertEqual(bridge.call_args.kwargs["payload"]["upload_source"], "SPA")
        self.assertEqual(bridge.call_args.kwargs["payload"]["expected_size_bytes"], len(b"worksheet-content"))
        self.assertEqual(payload["file"], "FILE-MAT-0001")

    def test_build_drive_idempotency_key_includes_material(self):
        with _governed_uploads_module() as governed_uploads:
            first = governed_uploads._build_drive_idempotency_key(
                payload={"material": "MAT-0001", "filename_original": "worksheet.pdf"},
                content=b"same-content",
            )
            second = governed_uploads._build_drive_idempotency_key(
                payload={"material": "MAT-0002", "filename_original": "worksheet.pdf"},
                content=b"same-content",
            )

        self.assertNotEqual(first, second)

    def test_sync_linked_employee_user_image_uses_preferred_variant(self):
        user_doc = _FakeDoc(user_image=None, flags=SimpleNamespace(ignore_permissions=False))

        with _governed_uploads_module() as governed_uploads:
            with (
                patch.object(governed_uploads.frappe.db, "get_value", return_value="staff@example.com"),
                patch.object(
                    governed_uploads,
                    "get_preferred_employee_image_url",
                    return_value="/files/thumb_employee.webp",
                ) as get_preferred,
                patch.object(governed_uploads.frappe, "get_doc", return_value=user_doc) as get_doc,
            ):
                governed_uploads._sync_linked_employee_user_image(
                    "EMP-0001",
                    original_url="/private/files/employee-photo.png",
                )

        get_preferred.assert_called_once_with(
            "EMP-0001",
            original_url="/private/files/employee-photo.png",
            slots=governed_uploads.EMPLOYEE_VARIANT_PRIORITY,
        )
        get_doc.assert_called_once_with("User", "staff@example.com")
        self.assertTrue(user_doc.flags.ignore_permissions)
        self.assertEqual(user_doc.user_image, "/files/thumb_employee.webp")
        self.assertEqual(user_doc.saved, 1)

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
            with _patched_drive_api_module(
                "ifitwala_drive.api.submissions",
                upload_task_submission_artifact=fake_drive_api.upload_task_submission_artifact,
            ):
                with (
                    patch.object(governed_uploads, "_require_doc", return_value=doc),
                    patch.object(governed_uploads, "_get_uploaded_file", return_value=("submission.pdf", b"content")),
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
            with _patched_drive_api_module(
                "ifitwala_drive.api.resources",
                upload_task_resource=fake_drive_api.upload_task_resource,
            ):
                with (
                    patch.object(governed_uploads, "_require_doc", return_value=doc),
                    patch.object(governed_uploads, "_require_clean_saved_doc", return_value=doc),
                    patch.object(governed_uploads, "_get_uploaded_file", return_value=("resource.pdf", b"content")),
                    patch.object(governed_uploads, "_ensure_file_on_disk"),
                    patch.object(
                        governed_uploads,
                        "_drive_upload_and_finalize",
                        return_value=(
                            {
                                "upload_session_id": "DUS-2",
                                "workflow_result": {"row_name": "row-001"},
                            },
                            {
                                "file_id": "FILE-0002",
                                "workflow_result": {"row_name": "row-001"},
                            },
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
