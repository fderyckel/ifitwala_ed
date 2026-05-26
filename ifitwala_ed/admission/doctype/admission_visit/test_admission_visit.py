from __future__ import annotations

from unittest.mock import patch

import frappe

from ifitwala_ed.admission.doctype.admission_visit.admission_visit import (
    cancel_admission_visit,
    get_admission_visit_schedule_options,
    mark_admission_visit_no_show,
    notify_admission_visit_informed_users,
    reschedule_admission_visit,
    schedule_admission_visit,
)
from ifitwala_ed.api.calendar_staff_feed import PARTICIPANT_ONLY_SCHOOL_EVENT_REFERENCE_TYPES
from ifitwala_ed.stock.doctype.location_booking.location_booking import upsert_location_booking
from ifitwala_ed.tests.base import IfitwalaEdTestSuite
from ifitwala_ed.tests.factories.users import make_user
from ifitwala_ed.utilities.employee_booking import upsert_employee_booking


class TestAdmissionVisit(IfitwalaEdTestSuite):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        self.organization = self.bootstrap.organization
        self.school = self.bootstrap.child_school

    def test_schedule_admission_visit_from_inquiry_creates_calendar_and_crm_links(self):
        lead_user = make_user()
        self._make_employee(lead_user.name, first_name="Visit", last_name="Lead")
        informed_user = make_user()
        building = self._make_location("Admissions Building", is_group=1)
        room = self._make_location("Tour Room", parent_location=building.name)
        inquiry = self._make_inquiry()

        payload = schedule_admission_visit(
            inquiry=inquiry.name,
            starts_on="2030-05-07 09:00:00",
            duration_minutes=60,
            visit_type="Family Tour",
            visit_mode="In Person",
            building=building.name,
            location=room.name,
            lead_user=lead_user.name,
            informed_users=[informed_user.name],
            party_size=3,
        )

        self.assertTrue(payload.get("ok"))
        visit = frappe.get_doc("Admission Visit", payload.get("admission_visit"))
        self.assertEqual(visit.inquiry, inquiry.name)
        self.assertEqual(visit.conversation, payload.get("conversation"))
        self.assertEqual(visit.school_event, payload.get("school_event"))
        self.assertEqual(visit.lead_user, lead_user.name)
        self.assertEqual(visit.informed_users[0].user, informed_user.name)

        conversation = frappe.get_doc("Admission Conversation", visit.conversation)
        self.assertEqual(conversation.inquiry, inquiry.name)
        self.assertEqual(conversation.organization, self.organization)
        self.assertEqual(conversation.school, self.school)

        school_event = frappe.get_doc("School Event", visit.school_event)
        self.assertEqual(school_event.reference_type, "Admission Visit")
        self.assertEqual(school_event.reference_name, visit.name)
        self.assertEqual(school_event.event_category, "Admissions Event")
        self.assertEqual(school_event.location, room.name)
        self.assertEqual([row.participant for row in school_event.participants], [lead_user.name])
        self.assertNotIn(informed_user.name, [row.participant for row in school_event.participants])

        self.assertTrue(
            frappe.db.exists(
                "Employee Booking",
                {
                    "source_doctype": "School Event",
                    "source_name": school_event.name,
                },
            )
        )
        self.assertTrue(
            frappe.db.exists(
                "Location Booking",
                {
                    "source_doctype": "School Event",
                    "source_name": school_event.name,
                    "location": room.name,
                },
            )
        )

        activity = frappe.get_doc("Admission CRM Activity", visit.booked_crm_activity)
        self.assertEqual(activity.conversation, conversation.name)
        self.assertEqual(activity.activity_type, "Booked Tour")
        self.assertEqual(activity.inquiry, inquiry.name)

    def test_schedule_admission_visit_returns_staff_conflict_without_creating_visit(self):
        lead_user = make_user()
        employee = self._make_employee(lead_user.name, first_name="Busy", last_name="Lead")
        inquiry = self._make_inquiry()
        booking_name = upsert_employee_booking(
            employee=employee.name,
            start="2030-05-08 09:00:00",
            end="2030-05-08 10:00:00",
            source_doctype="Inquiry",
            source_name=inquiry.name,
            booking_type="Other",
            blocks_availability=1,
            school=self.school,
        )
        self.assertTrue(booking_name)

        before_count = frappe.db.count("Admission Visit", {"inquiry": inquiry.name})
        payload = schedule_admission_visit(
            inquiry=inquiry.name,
            starts_on="2030-05-08 09:15:00",
            duration_minutes=30,
            visit_mode="Online",
            lead_user=lead_user.name,
            suggestion_window_start_time="08:00:00",
            suggestion_window_end_time="12:00:00",
        )
        after_count = frappe.db.count("Admission Visit", {"inquiry": inquiry.name})

        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "EMPLOYEE_CONFLICT")
        self.assertGreaterEqual(len(payload.get("employee_conflicts") or []), 1)
        self.assertGreaterEqual(len(payload.get("suggestions") or []), 1)
        self.assertEqual(before_count, after_count)

    def test_schedule_admission_visit_to_building_does_not_check_or_book_rooms(self):
        lead_user = make_user()
        self._make_employee(lead_user.name, first_name="Building", last_name="Lead")
        building = self._make_location("Busy Building", is_group=1)
        room = self._make_location("Busy Child Room", parent_location=building.name)
        inquiry = self._make_inquiry()
        upsert_location_booking(
            location=room.name,
            from_datetime="2030-05-08 09:00:00",
            to_datetime="2030-05-08 10:00:00",
            occupancy_type="School Event",
            source_doctype="Inquiry",
            source_name=inquiry.name,
            slot_key=f"test-building-visit::{frappe.generate_hash(length=8)}",
            school=self.school,
        )

        payload = schedule_admission_visit(
            inquiry=inquiry.name,
            starts_on="2030-05-08 09:15:00",
            duration_minutes=30,
            visit_mode="In Person",
            building=building.name,
            lead_user=lead_user.name,
        )

        self.assertTrue(payload.get("ok"))
        visit = frappe.get_doc("Admission Visit", payload.get("admission_visit"))
        self.assertEqual(visit.building, building.name)
        self.assertFalse(visit.location)
        school_event = frappe.get_doc("School Event", visit.school_event)
        self.assertFalse(school_event.location)
        self.assertFalse(
            frappe.db.exists(
                "Location Booking",
                {"source_doctype": "School Event", "source_name": school_event.name},
            )
        )

    def test_schedule_admission_visit_treats_non_schedulable_location_as_area_context(self):
        lead_user = make_user()
        self._make_employee(lead_user.name, first_name="Area", last_name="Lead")
        non_bookable_area = self._make_location("Welcome Desk", maximum_capacity=0)
        applicant = self._make_student_applicant()

        options = get_admission_visit_schedule_options(student_applicant=applicant.name)
        self.assertNotIn(non_bookable_area.name, {row.get("value") for row in options.get("rooms") or []})
        self.assertIn(non_bookable_area.name, {row.get("value") for row in options.get("buildings") or []})

        payload = schedule_admission_visit(
            student_applicant=applicant.name,
            starts_on="2030-05-08 10:15:00",
            duration_minutes=30,
            visit_mode="In Person",
            location=non_bookable_area.name,
            lead_user=lead_user.name,
        )

        self.assertTrue(payload.get("ok"))
        visit = frappe.get_doc("Admission Visit", payload.get("admission_visit"))
        self.assertEqual(visit.building, non_bookable_area.name)
        self.assertFalse(visit.location)
        school_event = frappe.get_doc("School Event", visit.school_event)
        self.assertFalse(school_event.location)
        self.assertFalse(
            frappe.db.exists(
                "Location Booking",
                {"source_doctype": "School Event", "source_name": school_event.name},
            )
        )

    def test_admission_visit_school_events_are_participant_only_calendar_references(self):
        self.assertIn("Admission Visit", PARTICIPANT_ONLY_SCHOOL_EVENT_REFERENCE_TYPES)

    def test_reschedule_admission_visit_updates_projection_and_ignores_own_booking(self):
        lead_user = make_user()
        self._make_employee(lead_user.name, first_name="Visit", last_name="Lead")
        room = self._make_location("Tour Room")
        inquiry = self._make_inquiry()
        payload = schedule_admission_visit(
            inquiry=inquiry.name,
            starts_on="2030-05-09 09:00:00",
            duration_minutes=60,
            visit_mode="In Person",
            location=room.name,
            lead_user=lead_user.name,
        )
        self.assertTrue(payload.get("ok"))
        visit_name = payload.get("admission_visit")
        school_event = payload.get("school_event")

        update_payload = reschedule_admission_visit(
            admission_visit=visit_name,
            starts_on="2030-05-09 10:00:00",
            duration_minutes=45,
            visit_mode="In Person",
            location=room.name,
            lead_user=lead_user.name,
        )

        self.assertTrue(update_payload.get("ok"))
        visit = frappe.get_doc("Admission Visit", visit_name)
        self.assertEqual(visit.school_event, school_event)
        event = frappe.get_doc("School Event", school_event)
        self.assertEqual(str(event.starts_on), "2030-05-09 10:00:00")
        self.assertEqual(str(event.ends_on), "2030-05-09 10:45:00")

    def test_cancel_admission_visit_removes_calendar_projection_and_records_crm_note(self):
        lead_user = make_user()
        self._make_employee(lead_user.name, first_name="Cancel", last_name="Lead")
        room = self._make_location("Cancel Room")
        inquiry = self._make_inquiry()
        payload = schedule_admission_visit(
            inquiry=inquiry.name,
            starts_on="2030-05-10 09:00:00",
            duration_minutes=60,
            visit_mode="In Person",
            location=room.name,
            lead_user=lead_user.name,
        )
        school_event = payload.get("school_event")
        self.assertTrue(frappe.db.exists("School Event", school_event))

        cancel_payload = cancel_admission_visit(
            admission_visit=payload.get("admission_visit"), reason="Family unavailable"
        )

        self.assertTrue(cancel_payload.get("ok"))
        visit = frappe.get_doc("Admission Visit", payload.get("admission_visit"))
        self.assertEqual(visit.status, "Cancelled")
        self.assertFalse(visit.school_event)
        self.assertTrue(visit.cancelled_crm_activity)
        self.assertFalse(frappe.db.exists("School Event", school_event))
        self.assertFalse(
            frappe.db.exists(
                "Employee Booking",
                {"source_doctype": "School Event", "source_name": school_event},
            )
        )
        self.assertFalse(
            frappe.db.exists(
                "Location Booking",
                {"source_doctype": "School Event", "source_name": school_event},
            )
        )

    def test_no_show_and_informed_notice_are_crm_bound_without_booking_informed_user(self):
        lead_user = make_user()
        self._make_employee(lead_user.name, first_name="Visit", last_name="Lead")
        informed_user = make_user()
        inquiry = self._make_inquiry()
        payload = schedule_admission_visit(
            inquiry=inquiry.name,
            starts_on="2030-05-11 09:00:00",
            duration_minutes=60,
            visit_mode="Online",
            lead_user=lead_user.name,
            informed_users=[informed_user.name],
        )

        with patch("ifitwala_ed.admission.doctype.admission_visit.admission_visit.frappe.publish_realtime") as realtime:
            notify_payload = notify_admission_visit_informed_users(admission_visit=payload.get("admission_visit"))

        self.assertTrue(notify_payload.get("ok"))
        notification_calls = [
            call
            for call in realtime.call_args_list
            if call.kwargs.get("event") == "inbox_notification"
            and call.kwargs.get("message", {}).get("reference_doctype") == "Admission Visit"
        ]
        self.assertEqual(len(notification_calls), 1)
        self.assertEqual(notification_calls[0].kwargs.get("user"), informed_user.name)

        status_payload = mark_admission_visit_no_show(admission_visit=payload.get("admission_visit"))
        self.assertTrue(status_payload.get("ok"))
        visit = frappe.get_doc("Admission Visit", payload.get("admission_visit"))
        self.assertEqual(visit.status, "No Show")
        self.assertTrue(visit.no_show_crm_activity)

    def _make_inquiry(self):
        with (
            patch("ifitwala_ed.admission.doctype.inquiry.inquiry.notify_admission_manager"),
            patch("ifitwala_ed.admission.doctype.inquiry.inquiry.queue_inquiry_family_acknowledgement"),
        ):
            return frappe.get_doc(
                {
                    "doctype": "Inquiry",
                    "first_name": "Tour",
                    "last_name": "Family",
                    "email": f"tour-{frappe.generate_hash(length=8)}@example.com",
                    "phone_number": "+66000000001",
                    "type_of_inquiry": "Admission",
                    "source": "Website",
                    "organization": self.organization,
                    "school": self.school,
                    "grade_level_interest": "Grade 4",
                    "message": "We would like to visit the campus.",
                }
            ).insert(ignore_permissions=True)

    def _make_student_applicant(self):
        return frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Tour",
                "last_name": f"Applicant {frappe.generate_hash(length=6)}",
                "organization": self.organization,
                "school": self.school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)

    def _make_employee(self, user: str, *, first_name: str, last_name: str):
        return frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": first_name,
                "employee_last_name": last_name,
                "employee_gender": "Other",
                "employee_professional_email": user,
                "date_of_joining": "2028-01-01",
                "employment_status": "Active",
                "organization": self.organization,
                "school": self.school,
                "user_id": user,
            }
        ).insert(ignore_permissions=True)

    def _make_location(
        self,
        label: str,
        *,
        is_group: int = 0,
        parent_location: str | None = None,
        maximum_capacity: int = 12,
    ):
        return frappe.get_doc(
            {
                "doctype": "Location",
                "location_name": f"{label} {frappe.generate_hash(length=6)}",
                "school": self.school,
                "organization": self.organization,
                "parent_location": parent_location,
                "is_group": is_group,
                "maximum_capacity": maximum_capacity,
            }
        ).insert(ignore_permissions=True)
