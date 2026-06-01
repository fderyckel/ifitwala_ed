from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import calendar


class TestCalendarFacade(TestCase):
    def test_public_methods_remain_whitelisted(self):
        for method_name in calendar.__all__:
            self.assertIn(getattr(calendar, method_name), frappe.whitelisted)
            self.assertFalse(bool(getattr(getattr(calendar, method_name), "allow_guest", False)))

    def test_staff_calendar_delegates_to_schedule_owner(self):
        expected = {"events": []}

        with patch("ifitwala_ed.schedule.api.calendar.staff_feed.get_staff_calendar", return_value=expected) as impl:
            payload = calendar.get_staff_calendar(
                from_datetime="2026-04-01T00:00:00",
                to_datetime="2026-04-02T00:00:00",
                sources=["meeting"],
                force_refresh=True,
            )

        self.assertEqual(payload, expected)
        impl.assert_called_once_with(
            from_datetime="2026-04-01T00:00:00",
            to_datetime="2026-04-02T00:00:00",
            sources=["meeting"],
            force_refresh=True,
        )

    def test_subscription_metadata_delegates_to_schedule_owner(self):
        expected = {"active": False}

        with patch(
            "ifitwala_ed.schedule.api.calendar.subscription.get_my_staff_calendar_subscription",
            return_value=expected,
        ) as impl:
            self.assertEqual(calendar.get_my_staff_calendar_subscription(), expected)

        impl.assert_called_once_with()

    def test_quick_create_options_delegates_to_schedule_owner(self):
        expected = {"can_create_meeting": True}

        with patch(
            "ifitwala_ed.schedule.api.calendar.quick_create.get_event_quick_create_options", return_value=expected
        ) as impl:
            self.assertEqual(calendar.get_event_quick_create_options(), expected)

        impl.assert_called_once_with()

    def test_meeting_quick_create_delegates_to_schedule_owner(self):
        expected = {"status": "created", "doctype": "Meeting", "name": "MTG-1"}

        with patch(
            "ifitwala_ed.schedule.api.calendar.quick_create.create_meeting_quick", return_value=expected
        ) as impl:
            payload = calendar.create_meeting_quick(
                client_request_id="req-1",
                meeting_name="Planning",
                date="2026-05-31",
                start_time="09:00",
                end_time="10:00",
                school="SCHOOL-1",
                participants=[{"user": "staff@example.com", "kind": "employee"}],
                include_students=0,
                include_guardians=0,
            )

        self.assertEqual(payload, expected)
        impl.assert_called_once_with(
            meeting_name="Planning",
            date="2026-05-31",
            start_time="09:00",
            end_time="10:00",
            team=None,
            school="SCHOOL-1",
            location=None,
            meeting_category=None,
            virtual_meeting_link=None,
            agenda=None,
            visibility_scope=None,
            participants=[{"user": "staff@example.com", "kind": "employee"}],
            include_students=0,
            include_guardians=0,
            client_request_id="req-1",
        )

    def test_school_event_quick_create_delegates_to_schedule_owner(self):
        expected = {"status": "created", "doctype": "School Event", "name": "SE-1"}

        with patch(
            "ifitwala_ed.schedule.api.calendar.quick_create.create_school_event_quick", return_value=expected
        ) as impl:
            payload = calendar.create_school_event_quick(
                client_request_id="req-2",
                subject="Assembly",
                school="SCHOOL-1",
                starts_on="2026-05-31T09:00",
                ends_on="2026-05-31T10:00",
                audience_type="All Employees",
                event_category="Other",
            )

        self.assertEqual(payload, expected)
        impl.assert_called_once_with(
            subject="Assembly",
            school="SCHOOL-1",
            starts_on="2026-05-31T09:00",
            ends_on="2026-05-31T10:00",
            audience_type="All Employees",
            event_category="Other",
            all_day=0,
            location=None,
            description=None,
            audience_team=None,
            audience_student_group=None,
            include_guardians=0,
            include_students=0,
            reference_type=None,
            reference_name=None,
            custom_participants=None,
            publish_announcement=0,
            announcement_message=None,
            client_request_id="req-2",
        )

    def test_quick_create_support_methods_delegate_to_schedule_owner(self):
        attendee_results = {"results": [{"value": "student@example.com"}], "notes": ["note"]}
        team_results = {"team": "TEAM-1", "results": [{"value": "staff@example.com"}]}
        slot_results = {"slots": [{"start": "2026-05-31T09:00:00"}], "fallback_slots": [], "notes": []}
        room_results = {"rooms": [{"value": "ROOM-1"}], "notes": []}

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.search_meeting_attendees",
                return_value=attendee_results,
            ) as search_impl,
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.get_meeting_team_attendees",
                return_value=team_results,
            ) as team_impl,
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.suggest_meeting_slots",
                return_value=slot_results,
            ) as slot_impl,
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.suggest_meeting_rooms",
                return_value=room_results,
            ) as room_impl,
        ):
            self.assertEqual(
                calendar.search_meeting_attendees(query="stu", attendee_kinds=["employee", "student"], limit=6),
                attendee_results,
            )
            self.assertEqual(calendar.get_meeting_team_attendees(team="TEAM-1"), team_results)
            self.assertEqual(
                calendar.suggest_meeting_slots(
                    attendees=[{"user": "student@example.com", "kind": "student"}],
                    duration_minutes=45,
                    date_from="2026-05-31",
                    date_to="2026-06-01",
                    day_start_time="08:00",
                    day_end_time="17:00",
                    school="SCHOOL-1",
                    location_type="Hall",
                    require_room=True,
                ),
                slot_results,
            )
            self.assertEqual(
                calendar.suggest_meeting_rooms(
                    school="SCHOOL-1",
                    date="2026-05-31",
                    start_time="09:00",
                    end_time="10:00",
                    location_type="Hall",
                    capacity_needed=4,
                    limit=5,
                ),
                room_results,
            )

        search_impl.assert_called_once_with(query="stu", attendee_kinds=["employee", "student"], limit=6)
        team_impl.assert_called_once_with(team="TEAM-1")
        slot_impl.assert_called_once_with(
            attendees=[{"user": "student@example.com", "kind": "student"}],
            duration_minutes=45,
            date_from="2026-05-31",
            date_to="2026-06-01",
            day_start_time="08:00",
            day_end_time="17:00",
            school="SCHOOL-1",
            location_type="Hall",
            require_room=True,
        )
        room_impl.assert_called_once_with(
            school="SCHOOL-1",
            date="2026-05-31",
            start_time="09:00",
            end_time="10:00",
            location_type="Hall",
            selected_location=None,
            capacity_needed=4,
            limit=5,
        )
