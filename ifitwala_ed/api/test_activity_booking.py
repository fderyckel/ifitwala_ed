# ifitwala_ed/api/test_activity_booking.py

from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api.activity_booking import (
    PAID_PORTAL_STATE_PENDING,
    _overlaps,
    _parse_json_list,
    _parse_name_list,
    _status_label,
    _student_rows,
)


class TestActivityBookingApi(TestCase):
    def test_student_rows_requests_derivative_only_student_images(self):
        captured_calls = []

        def fake_get_all(doctype, filters=None, fields=None, limit=None):
            self.assertEqual(doctype, "Student")
            self.assertEqual(filters, {"name": ["in", ["STU-0001"]]})
            self.assertIn("student_image", fields)
            self.assertEqual(limit, 100)
            return [
                {
                    "name": "STU-0001",
                    "student_full_name": "Amina Example",
                    "student_preferred_name": "Amina",
                    "student_first_name": "Amina",
                    "student_last_name": "Example",
                    "cohort": "Grade 5",
                    "student_image": "/private/files/student-source.png",
                    "account_holder": "GRD-0001",
                    "anchor_school": "SCH-0001",
                    "enabled": 1,
                }
            ]

        with (
            patch("ifitwala_ed.api.activity_booking.frappe.get_all", side_effect=fake_get_all),
            patch(
                "ifitwala_ed.api.activity_booking.apply_preferred_student_images",
                side_effect=lambda rows, **kwargs: captured_calls.append(kwargs) or rows,
            ),
        ):
            rows = _student_rows(["STU-0001"])

        self.assertEqual(
            rows,
            [
                {
                    "student": "STU-0001",
                    "full_name": "Amina",
                    "preferred_name": "Amina",
                    "cohort": "Grade 5",
                    "student_image": "/private/files/student-source.png",
                    "account_holder": "GRD-0001",
                    "anchor_school": "SCH-0001",
                }
            ],
        )
        self.assertEqual(
            captured_calls,
            [
                {
                    "student_field": "name",
                    "image_field": "student_image",
                    "slots": (
                        "profile_image_thumb",
                        "profile_image_card",
                        "profile_image_medium",
                    ),
                    "fallback_to_original": False,
                    "request_missing_derivatives": True,
                }
            ],
        )

    def test_parse_name_list_deduplicates_and_supports_json_string(self):
        payload = '[{"name":"STU-1"},{"name":"STU-1"},{"name":"STU-2"}]'
        self.assertEqual(_parse_name_list(payload), ["STU-1", "STU-2"])

    def test_parse_json_list_supports_dict_and_scalar_items(self):
        payload = '[{"student_group":"G-1"},"G-2","G-2"]'
        self.assertEqual(_parse_json_list(payload), ["G-1", "G-2"])

    def test_overlaps_helper(self):
        self.assertTrue(_overlaps(1, 5, 4, 9))
        self.assertFalse(_overlaps(1, 3, 3, 8))

    def test_status_label_handles_paid_pending_state(self):
        label = _status_label(
            "Confirmed",
            payment_required=1,
            amount=120,
            paid_portal_state=PAID_PORTAL_STATE_PENDING,
            outstanding_amount=120,
        )
        self.assertEqual(label, "Payment Pending")
