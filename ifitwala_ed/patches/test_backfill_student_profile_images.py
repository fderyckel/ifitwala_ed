from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillStudentProfileImages(TestCase):
    def test_execute_repairs_students_with_existing_profile_images(self):
        image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
        ensure_calls: list[tuple[str, str, str]] = []
        image_utils.ensure_student_profile_image = lambda student_name, **kwargs: ensure_calls.append(
            (student_name, kwargs.get("original_url"), kwargs.get("upload_source"))
        )

        with stubbed_frappe(extra_modules={"ifitwala_ed.utilities.image_utils": image_utils}) as frappe:
            frappe.db.table_exists = lambda doctype: doctype == "Student"
            frappe.get_all = lambda doctype, **kwargs: [
                {"name": "STU-0001", "student_image": "/private/files/student-one.png"},
                {"name": "STU-0002", "student_image": "/files/student-two.png"},
            ]
            module = import_fresh("ifitwala_ed.patches.backfill_student_profile_images")

            module.execute()

        self.assertEqual(
            ensure_calls,
            [
                ("STU-0001", "/private/files/student-one.png", "Patch"),
                ("STU-0002", "/files/student-two.png", "Patch"),
            ],
        )

    def test_execute_returns_when_student_table_is_missing(self):
        image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
        image_utils.ensure_student_profile_image = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("ensure_student_profile_image should not run")
        )

        with stubbed_frappe(extra_modules={"ifitwala_ed.utilities.image_utils": image_utils}) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when Student table is missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_profile_images")

            module.execute()
