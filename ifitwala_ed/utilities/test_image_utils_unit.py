from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _image_utils_module():
    file_access = ModuleType("ifitwala_ed.api.file_access")
    file_access.resolve_employee_file_open_url = lambda **kwargs: (
        "/api/method/ifitwala_ed.api.file_access.download_employee_file"
        f"?file={kwargs.get('file_name')}&context_doctype={kwargs.get('context_doctype')}"
        f"&context_name={kwargs.get('context_name')}&derivative_role={kwargs.get('derivative_role')}"
    )
    file_access.resolve_guardian_file_open_url = lambda **kwargs: None
    file_access.resolve_academic_file_open_url = lambda **kwargs: None

    drive_root = ModuleType("ifitwala_drive")
    drive_services = ModuleType("ifitwala_drive.services")
    drive_files = ModuleType("ifitwala_drive.services.files")
    drive_derivatives = ModuleType("ifitwala_drive.services.files.derivatives")
    drive_derivatives.sync_preview_pipeline_for_current_version = lambda **kwargs: None
    pil_module = ModuleType("PIL")
    pil_image_module = ModuleType("PIL.Image")
    pil_module.Image = pil_image_module

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.api.file_access": file_access,
            "ifitwala_drive": drive_root,
            "ifitwala_drive.services": drive_services,
            "ifitwala_drive.services.files": drive_files,
            "ifitwala_drive.services.files.derivatives": drive_derivatives,
            "PIL": pil_module,
            "PIL.Image": pil_image_module,
        }
    ) as frappe:
        frappe.utils = SimpleNamespace(get_site_path=lambda *parts: "/tmp")
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.get_doc = lambda doctype, name: SimpleNamespace(name=name, doctype=doctype)
        yield import_fresh("ifitwala_ed.utilities.image_utils"), frappe


class TestImageUtilsUnit(TestCase):
    def test_apply_preferred_student_images_thumb_only_requeues_missing_derivatives(self):
        with _image_utils_module() as (image_utils, frappe):
            rows = [{"name": "STU-0001", "student_image": "/private/files/student-source.png"}]
            sync_calls = []
            cache_writes = []

            class _FakeCache:
                def get_value(self, key):
                    return None

                def set_value(self, key, value, expires_in_sec=None):
                    cache_writes.append((key, value, expires_in_sec))

            image_utils.get_current_drive_files_for_slots = lambda **kwargs: [
                {
                    "name": "DRIVE-STU-1",
                    "primary_subject_id": "STU-0001",
                    "slot": "profile_image",
                    "file": "FILE-STU-1",
                    "current_version": "DFV-STU-1",
                }
            ]

            def fake_get_all(doctype, filters=None, fields=None, limit=None, order_by=None):
                del filters, fields, limit, order_by
                if doctype == "File":
                    return [
                        {
                            "name": "FILE-STU-1",
                            "file_url": "/private/files/student-source.png",
                            "is_private": 1,
                        }
                    ]
                if doctype == "Drive File Derivative":
                    return []
                raise AssertionError(f"Unexpected get_all doctype: {doctype}")

            frappe.get_all = fake_get_all
            frappe.cache = lambda: _FakeCache()
            frappe.get_doc = lambda doctype, name: SimpleNamespace(name=name, doctype=doctype)
            frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: (
                "image/webp" if doctype == "Drive File Version" and name == "DFV-STU-1" else None
            )

            with (
                patch(
                    "ifitwala_drive.services.files.derivatives.sync_preview_pipeline_for_current_version",
                    side_effect=lambda **kwargs: sync_calls.append(kwargs),
                ),
                patch.object(image_utils, "_resolve_original_governed_image_url") as resolve_original,
            ):
                image_utils.apply_preferred_student_images(
                    rows,
                    student_field="name",
                    image_field="student_image",
                    slots=image_utils.PROFILE_IMAGE_THUMB_ONLY_SLOTS,
                    fallback_to_original=False,
                    request_missing_derivatives=True,
                )

        resolve_original.assert_not_called()
        self.assertIsNone(rows[0]["student_image"])
        self.assertEqual(len(sync_calls), 1)
        self.assertEqual(sync_calls[0]["mime_type"], "image/webp")
        self.assertEqual(sync_calls[0]["drive_file_doc"].name, "DRIVE-STU-1")
        self.assertEqual(len(cache_writes), 1)
        self.assertEqual(cache_writes[0][1], 1)
        self.assertEqual(cache_writes[0][2], 300)

    def test_apply_preferred_student_images_uses_unbounded_variant_queries_for_large_rosters(self):
        with _image_utils_module() as (image_utils, frappe):
            student_ids = [f"STU-{index:04d}" for index in range(1, 26)]
            rows = [
                {
                    "name": student_id,
                    "student_image": f"/private/files/{student_id.lower()}.png",
                }
                for student_id in student_ids
            ]
            file_rows = [
                {
                    "name": f"FILE-{student_id}",
                    "file_url": f"/private/files/{student_id.lower()}.png",
                    "is_private": 1,
                }
                for student_id in student_ids
            ]
            derivative_rows = [
                {
                    "drive_file": f"DRIVE-{student_id}",
                    "derivative_role": "thumb",
                }
                for student_id in student_ids
            ]
            file_limits = []
            derivative_limits = []

            image_utils.get_current_drive_files_for_slots = lambda **kwargs: [
                {
                    "name": f"DRIVE-{student_id}",
                    "primary_subject_id": student_id,
                    "slot": "profile_image",
                    "file": f"FILE-{student_id}",
                    "current_version": f"DFV-{student_id}",
                }
                for student_id in student_ids
            ]

            def fake_get_all(doctype, filters=None, fields=None, limit=None, order_by=None):
                del filters, fields, order_by
                if doctype == "File":
                    file_limits.append(limit)
                    return file_rows if limit == 0 else file_rows[:20]
                if doctype == "Drive File Derivative":
                    derivative_limits.append(limit)
                    return derivative_rows if limit == 0 else derivative_rows[:20]
                raise AssertionError(f"Unexpected get_all doctype: {doctype}")

            frappe.get_all = fake_get_all

            def fake_resolve_display_url(
                primary_subject_type,
                subject_name,
                *,
                file_name,
                file_url,
                drive_file_id=None,
                canonical_ref=None,
                derivative_role=None,
            ):
                del primary_subject_type, file_url, drive_file_id, canonical_ref
                suffix = derivative_role or "original"
                return f"/resolved/{subject_name}/{file_name}/{suffix}"

            with (
                patch.object(image_utils, "_resolve_governed_display_url", side_effect=fake_resolve_display_url),
                patch.object(image_utils, "_resolve_original_governed_image_url", return_value="/resolved/original"),
            ):
                image_utils.apply_preferred_student_images(rows, student_field="name", image_field="student_image")

        self.assertEqual(file_limits, [0])
        self.assertEqual(derivative_limits, [0])
        self.assertEqual(
            rows[-1]["student_image"],
            "/resolved/STU-0025/FILE-STU-0025/thumb",
        )

    def test_get_preferred_student_image_url_can_skip_original_fallback(self):
        with _image_utils_module() as (image_utils, _frappe):
            original_url = "/private/files/student/original.png"

            with (
                patch.object(image_utils, "_get_governed_image_variants_map", return_value={"STU-0001": {}}),
                patch.object(
                    image_utils,
                    "_resolve_original_governed_image_url",
                    return_value=original_url,
                ) as resolve_original,
            ):
                image_url = image_utils.get_preferred_student_image_url(
                    "STU-0001",
                    original_url=original_url,
                    fallback_to_original=False,
                )

        resolve_original.assert_not_called()
        self.assertIsNone(image_url)

    def test_get_preferred_employee_image_url_uses_ready_drive_derivative_role(self):
        with _image_utils_module() as (image_utils, frappe):
            image_utils.get_current_drive_files_for_slots = lambda **kwargs: [
                {
                    "name": "DRIVE-EMP-1",
                    "primary_subject_id": "EMP-0001",
                    "slot": "profile_image",
                    "file": "FILE-EMP-1",
                    "current_version": "DFV-EMP-1",
                }
            ]

            def fake_get_all(doctype, filters=None, fields=None, limit=None, order_by=None):
                del limit, order_by
                if doctype == "File":
                    return [
                        {
                            "name": "FILE-EMP-1",
                            "file_url": "/private/files/employee-source.png",
                            "is_private": 1,
                        }
                    ]
                if doctype == "Drive File Derivative":
                    self.assertEqual(filters["status"], "ready")
                    return [{"drive_file": "DRIVE-EMP-1", "derivative_role": "thumb"}]
                raise AssertionError(f"Unexpected get_all doctype: {doctype}")

            frappe.get_all = fake_get_all

            image_url = image_utils.get_preferred_employee_image_url(
                "EMP-0001",
                original_url="/private/files/employee-source.png",
            )

        self.assertIn("derivative_role=thumb", image_url)
        self.assertIn("file=FILE-EMP-1", image_url)

    def test_resolve_original_governed_image_url_uses_current_drive_file_without_storage_probe(self):
        with _image_utils_module() as (image_utils, frappe):
            with (
                patch.object(
                    image_utils,
                    "_get_current_governed_profile_file",
                    return_value=SimpleNamespace(
                        name="FILE-EMP-CURRENT",
                        file_url="/private/files/ifitwala_drive/files/aa/bb/employee-current.png",
                    ),
                ),
                patch.object(
                    image_utils,
                    "file_url_is_accessible",
                    side_effect=AssertionError("governed reads must not probe storage directly"),
                ),
            ):
                image_url = image_utils._resolve_original_governed_image_url(
                    "Employee",
                    "EMP-0001",
                    "/private/files/employee-stale.png",
                )

        self.assertIn("file=FILE-EMP-CURRENT", image_url)
        self.assertIn("context_name=EMP-0001", image_url)

    def test_get_preferred_employee_image_url_without_subject_hides_private_original(self):
        with _image_utils_module() as (image_utils, frappe):
            public_url = image_utils.get_preferred_employee_image_url(
                None,
                original_url="/files/employee/public-image.png",
            )
            private_url = image_utils.get_preferred_employee_image_url(
                None,
                original_url="/private/files/employee/private-image.png",
            )

        self.assertEqual(public_url, "/files/employee/public-image.png")
        self.assertIsNone(private_url)
