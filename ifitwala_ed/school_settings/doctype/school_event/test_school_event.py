# Copyright (c) 2024, fdR and Contributors
# See license.txt

# ifitwala_ed/school_settings/doctype/school_event/test_school_event.py

from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from ifitwala_ed.school_settings.doctype.school_event import school_event as school_event_controller
from ifitwala_ed.school_settings.doctype.school_event.school_event import SchoolEvent


class TestSchoolEvent(TestCase):
    class _FakeOrgCommunicationDoc(frappe._dict):
        def __init__(self, payload):
            super().__init__(payload)
            self.checked_permissions = []
            self.saved = False

        def check_permission(self, ptype):
            self.checked_permissions.append(ptype)

        def set(self, fieldname, value):
            self[fieldname] = value
            setattr(self, fieldname, value)

        def append(self, fieldname, value):
            rows = list(self.get(fieldname) or [])
            rows.append(value)
            self[fieldname] = rows
            setattr(self, fieldname, rows)
            return frappe._dict(value)

        def save(self):
            self.saved = True
            return self

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
        doc.sync_linked_announcement = Mock()

        SchoolEvent.on_update(doc)

        doc.validate_date.assert_called_once_with()
        doc.sync_employee_bookings.assert_called_once_with()
        doc.sync_location_booking.assert_called_once_with()
        doc.sync_linked_announcement.assert_called_once_with()

    def test_on_cancel_archives_linked_announcement(self):
        doc = SchoolEvent.__new__(SchoolEvent)
        doc.doctype = "School Event"
        doc.name = "SE-TEST-0001"
        doc.archive_linked_announcement = Mock()

        with patch(
            "ifitwala_ed.school_settings.doctype.school_event.school_event.delete_location_bookings_for_source"
        ) as mocked_delete:
            SchoolEvent.on_cancel(doc)

        mocked_delete.assert_called_once_with(source_doctype="School Event", source_name="SE-TEST-0001")
        doc.archive_linked_announcement.assert_called_once_with()

    def test_on_trash_archives_linked_announcement(self):
        doc = SchoolEvent.__new__(SchoolEvent)
        doc.doctype = "School Event"
        doc.name = "SE-TEST-0001"
        doc.archive_linked_announcement = Mock()

        with patch(
            "ifitwala_ed.school_settings.doctype.school_event.school_event.delete_location_bookings_for_source"
        ) as mocked_delete:
            SchoolEvent.on_trash(doc)

        mocked_delete.assert_called_once_with(source_doctype="School Event", source_name="SE-TEST-0001")
        doc.archive_linked_announcement.assert_called_once_with()

    def test_publish_companion_org_communication_for_event_links_school_event_reference(self):
        event_doc = frappe._dict(
            {
                "name": "SE-26-04-00001",
                "subject": "Parent MYP Workshop",
                "school": "ISS",
                "description": "Workshop presentation",
                "audience": [frappe._dict({"audience_type": "All Guardians", "include_students": 0})],
            }
        )

        with (
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.db.get_value",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.db.set_value"
            ) as mocked_set_value,
            patch(
                "ifitwala_ed.api.org_communication_quick_create.create_org_communication_quick",
                return_value={
                    "status": "created",
                    "name": "ORG-COMM-26-04-00001",
                    "title": "Parent MYP Workshop",
                },
            ) as mocked_publish,
        ):
            payload = school_event_controller.publish_companion_org_communication_for_event(
                event_doc=event_doc,
                request_id="req-publish-1",
                announcement_message="Workshop presentation",
            )

        self.assertEqual(payload["name"], "ORG-COMM-26-04-00001")
        mocked_publish.assert_called_once()
        self.assertEqual(mocked_publish.call_args.kwargs["portal_surface"], "Portal Feed")
        self.assertEqual(mocked_publish.call_args.kwargs["organization"], "ORG-ROOT")
        self.assertEqual(mocked_publish.call_args.kwargs["audiences"][0]["include_descendants"], 1)
        mocked_set_value.assert_called_once_with(
            "School Event",
            "SE-26-04-00001",
            {
                "reference_type": "Org Communication",
                "reference_name": "ORG-COMM-26-04-00001",
            },
            update_modified=False,
        )
        self.assertEqual(event_doc.reference_type, "Org Communication")
        self.assertEqual(event_doc.reference_name, "ORG-COMM-26-04-00001")

    def test_sync_linked_org_communication_for_event_updates_title_audience_and_mirrored_message(self):
        event_doc = frappe._dict(
            {
                "name": "SE-26-04-00001",
                "subject": "Parent MYP Workshop",
                "school": "ISS",
                "description": "New workshop presentation",
                "reference_type": "Org Communication",
                "reference_name": "ORG-COMM-26-04-00001",
                "audience": [frappe._dict({"audience_type": "All Guardians", "include_students": 0})],
            }
        )
        event_doc.get_doc_before_save = lambda: frappe._dict({"description": "Old workshop presentation"})
        communication_doc = self._FakeOrgCommunicationDoc(
            {
                "name": "ORG-COMM-26-04-00001",
                "title": "Old title",
                "message": "Old workshop presentation",
                "portal_surface": "Desk",
                "internal_note": "",
                "status": "Published",
                "audiences": [{"target_mode": "Team", "team": "TEAM-OLD"}],
            }
        )

        with (
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.db.exists",
                return_value=True,
            ),
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.get_doc",
                return_value=communication_doc,
            ),
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.db.get_value",
                return_value="ORG-ROOT",
            ),
        ):
            synced_name = school_event_controller.sync_linked_org_communication_for_event(event_doc)

        self.assertEqual(synced_name, "ORG-COMM-26-04-00001")
        self.assertEqual(communication_doc.checked_permissions, ["write"])
        self.assertTrue(communication_doc.saved)
        self.assertEqual(communication_doc.title, "Parent MYP Workshop")
        self.assertEqual(communication_doc.communication_type, "Event Announcement")
        self.assertEqual(communication_doc.organization, "ORG-ROOT")
        self.assertEqual(communication_doc.school, "ISS")
        self.assertEqual(communication_doc.portal_surface, "Portal Feed")
        self.assertEqual(communication_doc.message, "New workshop presentation")
        self.assertEqual(communication_doc.audiences[0]["target_mode"], "School Scope")
        self.assertEqual(communication_doc.audiences[0]["to_guardians"], 1)

    def test_archive_linked_org_communication_for_event_marks_linked_announcement_archived(self):
        event_doc = frappe._dict(
            {
                "name": "SE-26-04-00001",
                "reference_type": "Org Communication",
                "reference_name": "ORG-COMM-26-04-00001",
            }
        )
        communication_doc = self._FakeOrgCommunicationDoc(
            {
                "name": "ORG-COMM-26-04-00001",
                "status": "Published",
                "internal_note": "",
            }
        )

        with (
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.db.exists",
                return_value=True,
            ),
            patch(
                "ifitwala_ed.school_settings.doctype.school_event.school_event.frappe.get_doc",
                return_value=communication_doc,
            ),
        ):
            archived_name = school_event_controller.archive_linked_org_communication_for_event(event_doc)

        self.assertEqual(archived_name, "ORG-COMM-26-04-00001")
        self.assertEqual(communication_doc.checked_permissions, ["write"])
        self.assertTrue(communication_doc.saved)
        self.assertEqual(communication_doc.status, "Archived")
