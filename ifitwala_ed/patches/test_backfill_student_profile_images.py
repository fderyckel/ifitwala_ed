from __future__ import annotations

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.backfill_student_profile_images import execute


class TestBackfillStudentProfileImages(FrappeTestCase):
    def test_execute_repairs_existing_student_profile_images(self):
        student_rows = [
            {
                "name": "STU-0001",
                "student_image": "/private/files/student-one.png",
            },
            {
                "name": "STU-0002",
                "student_image": "/private/files/student-two.png",
            },
        ]

        with (
            patch("ifitwala_ed.patches.backfill_student_profile_images.frappe.db.table_exists", return_value=True),
            patch(
                "ifitwala_ed.patches.backfill_student_profile_images.frappe.get_all",
                return_value=student_rows,
            ) as mocked_get_all,
            patch("ifitwala_ed.patches.backfill_student_profile_images.ensure_student_profile_image") as ensure_image,
        ):
            execute()

        mocked_get_all.assert_called_once_with(
            "Student",
            filters={"student_image": ["is", "set"]},
            fields=["name", "student_image"],
            limit=100000,
        )
        ensure_image.assert_any_call(
            "STU-0001",
            original_url="/private/files/student-one.png",
            upload_source="API",
        )
        ensure_image.assert_any_call(
            "STU-0002",
            original_url="/private/files/student-two.png",
            upload_source="API",
        )
