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

    image_utils = ModuleType("ifitwala_ed.utilities.image_utils")
    image_utils.EMPLOYEE_VARIANT_PRIORITY = []
    image_utils.get_employee_image_variants_map = lambda employee_names: {}
    image_utils.get_preferred_employee_image_url = lambda employee_name, original_url=None, slots=None: original_url

    organization_media = ModuleType("ifitwala_ed.utilities.organization_media")
    organization_media.build_organization_media_slot = lambda **kwargs: "organization_media__test"

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.utilities.file_dispatcher": file_dispatcher,
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

    def test_get_drive_media_callable_falls_back_to_integration_service(self):
        api_module = SimpleNamespace()
        observed = {}

        def fake_service(payload):
            observed.update(payload)
            return {"upload_session_id": "DUS-42"}

        integration_module = SimpleNamespace(upload_guardian_image_service=fake_service)

        with _governed_uploads_module() as governed_uploads:
            with (
                patch.object(governed_uploads, "_load_drive_module", return_value=api_module),
                patch.object(governed_uploads.importlib, "import_module", return_value=integration_module),
                patch.object(governed_uploads.importlib, "reload", side_effect=lambda module: module),
            ):
                callable_ = governed_uploads._get_drive_media_callable("upload_guardian_image")
                response = callable_(guardian="GRD-0001", filename_original="photo.png")

        self.assertEqual(response["upload_session_id"], "DUS-42")
        self.assertEqual(observed["guardian"], "GRD-0001")
        self.assertEqual(observed["filename_original"], "photo.png")

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
            with (
                patch.object(governed_uploads, "_require_doc", return_value=doc),
                patch.object(governed_uploads, "_get_uploaded_file", return_value=("guardian-photo.png", b"content")),
                patch.object(governed_uploads, "_load_drive_module", return_value=fake_drive_api),
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
            with (
                patch.object(governed_uploads, "_require_doc", return_value=doc),
                patch.object(
                    governed_uploads,
                    "_get_uploaded_file",
                    return_value=("employee-photo.png", b"employee-content"),
                ),
                patch.object(governed_uploads, "_load_drive_module", return_value=fake_drive_api),
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
