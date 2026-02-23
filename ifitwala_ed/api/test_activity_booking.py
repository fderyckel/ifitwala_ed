# ifitwala_ed/api/test_activity_booking.py

from unittest import TestCase

from ifitwala_ed.api.activity_booking import (
    PAID_PORTAL_STATE_PENDING,
    _overlaps,
    _parse_json_list,
    _parse_name_list,
    _status_label,
)


class TestActivityBookingApi(TestCase):
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
