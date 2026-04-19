from __future__ import annotations

from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.backfill_location_bookings_for_calendar_events import (
    _backfill_location_bookings_for_doctype,
    execute,
)


class TestBackfillLocationBookingsForCalendarEvents(FrappeTestCase):
    def test_execute_backfills_meetings_and_school_events(self):
        with (
            patch(
                "ifitwala_ed.patches.backfill_location_bookings_for_calendar_events.frappe.db.table_exists",
                return_value=True,
            ),
            patch(
                "ifitwala_ed.patches.backfill_location_bookings_for_calendar_events._backfill_location_bookings_for_doctype"
            ) as mocked_backfill,
        ):
            execute()

        mocked_backfill.assert_any_call("Meeting")
        mocked_backfill.assert_any_call("School Event")

    def test_backfill_location_bookings_for_doctype_syncs_each_located_doc(self):
        first_doc = Mock()
        second_doc = Mock()

        def mocked_table_exists(doctype):
            return doctype in {"Meeting", "Location Booking"}

        with (
            patch(
                "ifitwala_ed.patches.backfill_location_bookings_for_calendar_events.frappe.db.table_exists",
                side_effect=mocked_table_exists,
            ),
            patch(
                "ifitwala_ed.patches.backfill_location_bookings_for_calendar_events.frappe.get_all",
                return_value=["MTG-0001", "MTG-0002"],
            ) as mocked_get_all,
            patch(
                "ifitwala_ed.patches.backfill_location_bookings_for_calendar_events.frappe.get_doc",
                side_effect=[first_doc, second_doc],
            ) as mocked_get_doc,
        ):
            _backfill_location_bookings_for_doctype("Meeting")

        mocked_get_all.assert_called_once_with(
            "Meeting",
            filters={"location": ["is", "set"], "status": ["!=", "Cancelled"]},
            pluck="name",
            limit=100000,
        )
        mocked_get_doc.assert_any_call("Meeting", "MTG-0001")
        mocked_get_doc.assert_any_call("Meeting", "MTG-0002")
        first_doc.sync_location_booking.assert_called_once_with()
        second_doc.sync_location_booking.assert_called_once_with()
