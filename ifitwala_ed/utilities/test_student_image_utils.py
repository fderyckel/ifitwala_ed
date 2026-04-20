# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

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
