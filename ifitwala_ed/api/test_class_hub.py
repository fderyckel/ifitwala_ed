# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import class_hub


class TestClassHub(FrappeTestCase):
    def test_get_bundle_exposes_student_log_permission_from_doctype(self):
        with (
            patch("ifitwala_ed.api.class_hub._assert_instructor"),
            patch(
                "ifitwala_ed.api.class_hub.frappe.db.get_value",
                return_value={
                    "student_group_abbreviation": "G7-A",
                    "student_group_name": "Grade 7 A",
                    "course": "Science",
                    "academic_year": "2025-2026",
                },
            ),
            patch(
                "ifitwala_ed.api.class_hub.frappe.get_all",
                return_value=[{"student": "STU-001", "student_name": "Amina Dar"}],
            ),
            patch(
                "ifitwala_ed.api.class_hub._can_create_student_log_for_session_user",
                return_value=True,
            ),
        ):
            payload = class_hub.get_bundle("SG-0001")

        self.assertTrue(payload["permissions"]["can_create_student_log"])
