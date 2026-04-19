# Copyright (c) 2024, fdR and Contributors
# See license.txt

# ifitwala_ed/school_settings/doctype/school_event/test_school_event.py

from unittest import TestCase
from unittest.mock import Mock

import frappe

from ifitwala_ed.school_settings.doctype.school_event.school_event import SchoolEvent


class TestSchoolEvent(TestCase):
    def test_validate_audience_presence_can_be_skipped_for_system_events(self):
        doc = SchoolEvent.__new__(SchoolEvent)
        doc.flags = frappe._dict({"allow_empty_audience": True})
        doc.audience = []

        SchoolEvent.validate_audience_presence(doc)

    def test_validate_audience_rows_requires_student_group_for_student_audience(self):
        doc = SchoolEvent.__new__(SchoolEvent)
        doc.audience = [
            frappe._dict(
                {
                    "idx": 1,
                    "audience_type": "Students in Student Group",
                    "student_group": "",
                    "team": "",
                }
            )
        ]

        with self.assertRaises(frappe.ValidationError):
            SchoolEvent.validate_audience_rows(doc)

    def test_validate_custom_users_requires_participants(self):
        doc = SchoolEvent.__new__(SchoolEvent)
        doc.audience = [frappe._dict({"idx": 1, "audience_type": "Custom Users"})]
        doc.participants = []

        with self.assertRaises(frappe.ValidationError):
            SchoolEvent.validate_custom_users_require_participants(doc)

    def test_after_insert_syncs_employee_and_location_bookings(self):
        doc = SchoolEvent.__new__(SchoolEvent)
        doc.sync_employee_bookings = Mock()
        doc.sync_location_booking = Mock()

        SchoolEvent.after_insert(doc)

        doc.sync_employee_bookings.assert_called_once_with()
        doc.sync_location_booking.assert_called_once_with()

    def test_on_update_validates_date_then_syncs_bookings(self):
        doc = SchoolEvent.__new__(SchoolEvent)
        doc.validate_date = Mock()
        doc.sync_employee_bookings = Mock()
        doc.sync_location_booking = Mock()

        SchoolEvent.on_update(doc)

        doc.validate_date.assert_called_once_with()
        doc.sync_employee_bookings.assert_called_once_with()
        doc.sync_location_booking.assert_called_once_with()
