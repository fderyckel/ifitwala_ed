# ifitwala_ed/students/print_format/test_student_profile_print_format.py

import json
import unittest
from pathlib import Path

from jinja2 import Environment

from ifitwala_ed.students.print_format.sync import (
    STUDENT_PROFILE_PRINT_FORMAT_PATH,
    get_student_profile_print_format_values,
    load_student_profile_print_format_payload,
)

PRINT_FORMAT_PATH = Path(__file__).resolve().parent / "student_profile" / "student_profile.json"


class TestStudentProfilePrintFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PRINT_FORMAT_PATH.read_text(encoding="utf-8"))
        cls.html = cls.payload["html"]
        cls.css = cls.payload["css"]

    def test_sync_module_targets_exported_print_format_path(self):
        self.assertEqual(STUDENT_PROFILE_PRINT_FORMAT_PATH, PRINT_FORMAT_PATH)

    def test_exported_metadata_matches_contract(self):
        self.assertEqual(self.payload["doctype"], "Print Format")
        self.assertEqual(self.payload["doc_type"], "Student")
        self.assertEqual(self.payload["print_format_type"], "Jinja")
        self.assertEqual(self.payload["module"], "Students")
        self.assertEqual(self.payload["name"], "Student Profile")
        self.assertEqual(self.payload["standard"], "Yes")
        self.assertTrue(self.payload["custom_format"])
        self.assertTrue(self.html)
        self.assertTrue(self.css)

    def test_template_parses_as_valid_jinja(self):
        Environment().parse(self.html)

    def test_sync_helpers_load_expected_payload(self):
        payload = load_student_profile_print_format_payload()
        values = get_student_profile_print_format_values()
        self.assertEqual(payload["name"], "Student Profile")
        self.assertEqual(values["doc_type"], "Student")
        self.assertEqual(values["print_format_type"], "Jinja")
        self.assertEqual(values["module"], "Students")
        self.assertEqual(values["standard"], "Yes")
        self.assertEqual(values["html"], self.html)
        self.assertEqual(values["css"], self.css)

    def test_excludes_internal_student_fields(self):
        for token in (
            "student_applicant",
            "allow_direct_creation",
            "additional_comment",
            "contact_html",
            "address_html",
        ):
            self.assertNotIn(token, self.html)

    def test_uses_real_guardian_child_fields(self):
        for token in (
            "row.guardian_name",
            "row.relation",
            "row.can_consent",
            "row.phone",
            "row.email",
        ):
            self.assertIn(token, self.html)

        for token in (
            "row.relationship",
            "row.mobile_number",
            "row.full_name",
        ):
            self.assertNotIn(token, self.html)

    def test_uses_real_sibling_child_fields(self):
        for token in (
            "row.sibling_name",
            "row.sibling_gender",
            "row.sibling_date_of_birth",
        ):
            self.assertIn(token, self.html)

        for token in (
            "row.relationship",
            "row.cohort",
            "row.enabled",
            "row.student_name",
            "row.full_name",
        ):
            self.assertNotIn(token, self.html)

    def test_compact_image_and_status_styling_are_present(self):
        self.assertIn(".hero-image img", self.css)
        self.assertIn("width: 82px;", self.css)
        self.assertIn("height: 104px;", self.css)
        self.assertIn(".status-pill", self.css)


if __name__ == "__main__":
    unittest.main()
