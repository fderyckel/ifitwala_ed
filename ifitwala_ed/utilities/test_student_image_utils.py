# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.utilities import image_utils


class TestStudentImageUtils(FrappeTestCase):
    def test_get_preferred_student_image_url_prefers_thumb_variant(self):
        with patch(
            "ifitwala_ed.utilities.image_utils._get_governed_image_variants_map",
            return_value={
                "STU-0001": {
                    "profile_image_thumb": "/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-THUMB&context_doctype=Student&context_name=STU-0001&derivative_role=thumb",
                    "profile_image_card": "/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-CARD&context_doctype=Student&context_name=STU-0001&derivative_role=card",
                }
            },
        ):
            image_url = image_utils.get_preferred_student_image_url(
                "STU-0001",
                original_url="/private/files/student/original_student.png",
            )

        self.assertEqual(
            image_url,
            "/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-THUMB&context_doctype=Student&context_name=STU-0001&derivative_role=thumb",
        )

    def test_apply_preferred_student_images_uses_governed_variant_routes(self):
        rows = [{"name": "STU-0001", "student_image": "/private/files/student/original_student.png"}]

        with patch(
            "ifitwala_ed.utilities.image_utils._get_governed_image_variants_map",
            return_value={
                "STU-0001": {
                    "profile_image_thumb": "/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-THUMB&context_doctype=Student&context_name=STU-0001&derivative_role=thumb"
                }
            },
        ):
            image_utils.apply_preferred_student_images(rows, student_field="name", image_field="student_image")

        self.assertEqual(
            rows[0]["student_image"],
            "/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-THUMB&context_doctype=Student&context_name=STU-0001&derivative_role=thumb",
        )

    def test_apply_preferred_student_images_falls_back_to_governed_original(self):
        rows = [{"name": "STU-0001", "student_image": "/private/files/student/original_student.png"}]

        with (
            patch("ifitwala_ed.utilities.image_utils._get_governed_image_variants_map", return_value={"STU-0001": {}}),
            patch(
                "ifitwala_ed.utilities.image_utils._resolve_original_governed_image_url",
                return_value="/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-ORIGINAL&context_doctype=Student&context_name=STU-0001",
            ) as resolve_original,
        ):
            image_utils.apply_preferred_student_images(rows, student_field="name", image_field="student_image")

        resolve_original.assert_called_once_with("Student", "STU-0001", "/private/files/student/original_student.png")
        self.assertEqual(
            rows[0]["student_image"],
            "/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-ORIGINAL&context_doctype=Student&context_name=STU-0001",
        )

    def test_apply_preferred_student_images_can_skip_original_fallback(self):
        rows = [{"name": "STU-0001", "student_image": "/private/files/student/original_student.png"}]

        with (
            patch("ifitwala_ed.utilities.image_utils._get_governed_image_variants_map", return_value={"STU-0001": {}}),
            patch("ifitwala_ed.utilities.image_utils._resolve_original_governed_image_url") as resolve_original,
        ):
            image_utils.apply_preferred_student_images(
                rows,
                student_field="name",
                image_field="student_image",
                fallback_to_original=False,
            )

        resolve_original.assert_not_called()
        self.assertIsNone(rows[0]["student_image"])

    def test_ensure_student_profile_image_reuses_current_governed_source_and_syncs_field(self):
        student_doc = frappe._dict({"name": "STU-0001", "anchor_school": "SCH-0001"})
        current_file_doc = frappe._dict(
            {
                "name": "FILE-STU-CURRENT",
                "file_url": "/private/files/student-current.png",
            }
        )

        with (
            patch(
                "ifitwala_ed.utilities.image_utils._get_current_governed_profile_file",
                return_value=current_file_doc,
            ),
            patch("ifitwala_ed.utilities.image_utils.frappe.get_doc", return_value=student_doc),
            patch("ifitwala_ed.utilities.image_utils.frappe.db.set_value") as set_value,
        ):
            image_url = image_utils.ensure_student_profile_image("STU-0001")

        self.assertEqual(image_url, "/private/files/student-current.png")
        set_value.assert_called_once_with(
            "Student",
            "STU-0001",
            "student_image",
            "/private/files/student-current.png",
            update_modified=False,
        )

    def test_ensure_student_profile_image_uploads_drive_managed_copy_when_source_exists(self):
        student_doc = frappe._dict({"name": "STU-0001", "anchor_school": "SCH-0001"})
        source_file_doc = frappe._dict(
            {
                "name": "FILE-STU-0001",
                "attached_to_doctype": "Student",
                "attached_to_name": "STU-0001",
                "attached_to_field": "student_image",
                "file_url": "/private/files/student-source.png",
                "file_name": "student-source.png",
            }
        )
        uploaded_file_doc = frappe._dict(
            {
                "name": "FILE-STU-UPLOADED",
                "file_url": "/private/files/student-source.png",
            }
        )

        with (
            patch("ifitwala_ed.utilities.image_utils._get_current_governed_profile_file", return_value=None),
            patch("ifitwala_ed.utilities.image_utils.frappe.get_doc", return_value=student_doc),
            patch("ifitwala_ed.integrations.drive.media.build_student_image_contract", return_value={}),
            patch("ifitwala_drive.api.media.upload_student_image", new=object()),
            patch("ifitwala_ed.utilities.image_utils._resolve_unique_file_doc_by_url", return_value=source_file_doc),
            patch("ifitwala_ed.utilities.image_utils._read_managed_file_bytes", return_value=b"student-bytes"),
            patch(
                "ifitwala_ed.integrations.drive.content_uploads.upload_content_via_drive",
                return_value=({}, {}, uploaded_file_doc),
            ) as upload_content,
            patch("ifitwala_ed.utilities.image_utils.frappe.db.set_value") as set_value,
        ):
            image_url = image_utils.ensure_student_profile_image(
                "STU-0001",
                original_url="/private/files/student-source.png",
            )

        self.assertEqual(image_url, "/private/files/student-source.png")
        upload_content.assert_called_once()
        set_value.assert_called_once_with(
            "Student",
            "STU-0001",
            "student_image",
            "/private/files/student-source.png",
            update_modified=False,
        )
