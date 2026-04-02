# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/setup/doctype/meeting/test_meeting.py

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.setup.doctype.meeting.meeting import (
    _combine_date_and_time,
    _invalidate_student_calendar_caches_for_participants,
    _participant_user_ids,
    get_academic_year_for_date,
)


class TestMeeting(TestCase):
    def test_combine_date_and_time_returns_none_when_missing_parts(self):
        self.assertIsNone(_combine_date_and_time(None, "08:00:00"))
        self.assertIsNone(_combine_date_and_time("2026-02-01", None))

    @patch("ifitwala_ed.setup.doctype.meeting.meeting.get_datetime")
    def test_combine_date_and_time_delegates_to_frappe_get_datetime(self, mock_get_datetime):
        expected = datetime(2026, 2, 1, 8, 0, 0)
        mock_get_datetime.return_value = expected

        result = _combine_date_and_time("2026-02-01", "08:00:00")

        self.assertEqual(result, expected)
        mock_get_datetime.assert_called_once_with("2026-02-01 08:00:00")

    def test_get_academic_year_for_date_returns_none_for_missing_context(self):
        self.assertIsNone(get_academic_year_for_date("", "2026-02-01"))
        self.assertIsNone(get_academic_year_for_date("SCH-1", None))

    @patch("frappe.get_all")
    def test_get_academic_year_for_date_returns_latest_match(self, mock_get_all):
        mock_get_all.return_value = [{"name": "AY-2025"}]
        result = get_academic_year_for_date("SCH-1", "2026-02-01")
        self.assertEqual(result, "AY-2025")

    def test_participant_user_ids_include_previous_rows_when_requested(self):
        doc = frappe._dict(
            participants=[frappe._dict(participant="student.current@example.com")],
        )
        doc.get_doc_before_save = lambda: frappe._dict(
            participants=[frappe._dict(participant="student.previous@example.com")]
        )

        self.assertEqual(
            _participant_user_ids(doc, include_previous=True),
            {"student.current@example.com", "student.previous@example.com"},
        )

    @patch("ifitwala_ed.api.student_calendar.refresh_student_calendar_views")
    def test_invalidate_student_calendar_caches_for_participants_uses_previous_and_current_users(self, mocked):
        doc = frappe._dict(
            name="MTG-0001",
            participants=[frappe._dict(participant="student.current@example.com")],
        )
        doc.get_doc_before_save = lambda: frappe._dict(
            participants=[frappe._dict(participant="student.previous@example.com")]
        )

        _invalidate_student_calendar_caches_for_participants(doc, include_previous=True)

        mocked.assert_called_once_with(
            users=["student.current@example.com", "student.previous@example.com"],
            source="meeting",
            source_name="MTG-0001",
        )
