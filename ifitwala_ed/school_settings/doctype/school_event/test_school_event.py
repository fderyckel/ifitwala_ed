# Copyright (c) 2024, fdR and Contributors
# See license.txt

# ifitwala_ed/school_settings/doctype/school_event/test_school_event.py

from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from ifitwala_ed.school_settings.doctype.school_event import school_event as school_event_controller
from ifitwala_ed.school_settings.doctype.school_event.school_event import SchoolEvent


class TestSchoolEvent(TestCase):
    @staticmethod
    def _raw_get_user_membership():
        return getattr(
            school_event_controller.get_user_membership,
            "__wrapped__",
            school_event_controller.get_user_membership,
        )

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

    def test_get_user_membership_matches_team_via_login_email_fallback(self):
        def fake_get_all(doctype, filters=None, pluck=None, fields=None, or_filters=None, limit=None, **kwargs):
            if doctype in {"Student Group Student", "Student Group Instructor", "Guardian", "Guardian Student"}:
                return []

            if doctype == "Employee" and filters == {"user_id": "staff.user"} and pluck == "name":
                return []

            if doctype == "Employee" and filters == {"employee_professional_email": "staff@example.com"}:
                self.assertEqual(fields, ["name", "user_id"])
                self.assertEqual(limit, 2)
                return [frappe._dict({"name": "EMP-0001", "user_id": ""})]

            if doctype == "Team Member":
                self.assertEqual(
                    or_filters,
                    {"member": "staff.user", "employee": ["in", ["EMP-0001"]]},
                )
                self.assertEqual(pluck, "parent")
                return ["TEAM-OPS"]

            self.fail(f"Unexpected get_all call for {doctype}: filters={filters}, or_filters={or_filters}")

        with (
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.db.get_value",
                return_value="staff@example.com",
            ),
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.get_all",
                side_effect=fake_get_all,
            ),
        ):
            membership = self._raw_get_user_membership()("staff.user")

        self.assertEqual(membership["teams"], {"TEAM-OPS"})

    def test_get_user_membership_ignores_email_fallback_linked_to_other_user(self):
        def fake_get_all(doctype, filters=None, pluck=None, fields=None, or_filters=None, limit=None, **kwargs):
            if doctype in {"Student Group Student", "Student Group Instructor", "Guardian", "Guardian Student"}:
                return []

            if doctype == "Employee" and filters == {"user_id": "staff.user"} and pluck == "name":
                return []

            if doctype == "Employee" and filters == {"employee_professional_email": "staff@example.com"}:
                self.assertEqual(fields, ["name", "user_id"])
                self.assertEqual(limit, 2)
                return [frappe._dict({"name": "EMP-OTHER", "user_id": "other.user"})]

            if doctype == "Team Member":
                self.assertEqual(or_filters, {"member": "staff.user"})
                self.assertEqual(pluck, "parent")
                return []

            self.fail(f"Unexpected get_all call for {doctype}: filters={filters}, or_filters={or_filters}")

        with (
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.db.get_value",
                return_value="staff@example.com",
            ),
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.get_all",
                side_effect=fake_get_all,
            ),
        ):
            membership = self._raw_get_user_membership()("staff.user")

        self.assertEqual(membership["teams"], set())

    def test_get_employees_for_booking_uses_team_member_employee_links(self):
        doc = SchoolEvent.__new__(SchoolEvent)
        doc.participants = []
        doc.audience = [frappe._dict({"audience_type": "Employees in Team", "team": "TEAM-OPS"})]

        def fake_get_all(doctype, filters=None, pluck=None, **kwargs):
            if doctype == "Team Member":
                self.assertEqual(
                    filters,
                    {
                        "parent": ["in", ["TEAM-OPS"]],
                        "parenttype": "Team",
                        "parentfield": "members",
                    },
                )
                self.assertEqual(pluck, "employee")
                return ["EMP-0001", "EMP-0002"]

            if doctype == "Employee":
                self.fail("Team audience employee resolution should use Team Member.employee directly.")

            return []

        with patch(
            "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.get_all",
            side_effect=fake_get_all,
        ):
            employees = SchoolEvent._get_employees_for_booking(doc)

        self.assertEqual(employees, {"EMP-0001", "EMP-0002"})

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
