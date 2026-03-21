# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from datetime import date, datetime
from unittest.mock import patch

import frappe

from ifitwala_ed.api import morning_brief
from ifitwala_ed.tests.base import IfitwalaFrappeTestCase


class TestMorningBrief(IfitwalaFrappeTestCase):
    def test_get_briefing_widgets_includes_clinic_volume_for_nurse(self):
        clinic_payload = {
            "default_view": "3D",
            "school": "Upper School",
            "views": {"3D": [], "3W": []},
            "error": None,
        }

        with (
            patch.object(morning_brief.frappe, "session", frappe._dict(user="nurse@example.com")),
            patch.object(morning_brief.frappe, "get_roles", return_value=["Nurse"]),
            patch.object(morning_brief, "now_datetime", return_value=datetime(2026, 3, 23, 8, 30, 0)),
            patch.object(morning_brief, "get_daily_bulletin", return_value=[]),
            patch.object(morning_brief, "_can_view_clinic_metrics", return_value=True),
            patch.object(morning_brief, "get_clinic_activity", return_value=clinic_payload),
        ):
            payload = morning_brief.get_briefing_widgets()

        self.assertEqual(payload.get("clinic_volume"), clinic_payload)
        self.assertNotIn("admissions_pulse", payload)
        self.assertNotIn("critical_incidents", payload)

    def test_get_clinic_activity_skips_weekends_and_holidays_for_business_days(self):
        context = {
            "SCH-1": [
                {
                    "start_date": date(2026, 1, 1),
                    "end_date": date(2026, 12, 31),
                    "weekend_days": {6, 0},
                    "holidays": {date(2026, 3, 18)},
                }
            ]
        }

        with (
            patch.object(
                morning_brief,
                "_resolve_clinic_scope",
                return_value={
                    "base_school": "SCH-1",
                    "school_scope": ["SCH-1"],
                    "scope_label": "Upper School",
                    "error": None,
                },
            ),
            patch.object(morning_brief, "today", return_value="2026-03-23"),
            patch.object(morning_brief, "_load_clinic_calendar_context", return_value=context),
            patch.object(
                morning_brief,
                "_query_clinic_visit_counts",
                return_value=[
                    {"school": "SCH-1", "date": "2026-03-23", "count": 2},
                    {"school": "SCH-1", "date": "2026-03-20", "count": 5},
                    {"school": "SCH-1", "date": "2026-03-19", "count": 3},
                    {"school": "SCH-1", "date": "2026-03-18", "count": 9},
                ],
            ),
        ):
            payload = morning_brief.get_clinic_activity()

        self.assertEqual(
            payload["views"]["3D"],
            [
                {"label": "23-Mar", "count": 2},
                {"label": "20-Mar", "count": 5},
                {"label": "19-Mar", "count": 3},
            ],
        )
        self.assertIsNone(payload["error"])

    def test_get_clinic_visits_trend_filters_non_business_days(self):
        context = {
            "SCH-1": [
                {
                    "start_date": date(2026, 1, 1),
                    "end_date": date(2026, 12, 31),
                    "weekend_days": {6, 0},
                    "holidays": {date(2026, 3, 18)},
                }
            ]
        }

        with (
            patch.object(morning_brief.frappe, "session", frappe._dict(user="nurse@example.com")),
            patch.object(morning_brief, "_can_view_clinic_metrics", return_value=True),
            patch.object(
                morning_brief,
                "_resolve_clinic_scope",
                return_value={
                    "base_school": "SCH-1",
                    "school_scope": ["SCH-1"],
                    "scope_label": "Upper School",
                    "error": None,
                },
            ),
            patch.object(morning_brief, "today", return_value="2026-03-23"),
            patch.object(morning_brief, "_resolve_clinic_trend_start_date", return_value=date(2026, 3, 17)),
            patch.object(morning_brief, "_load_clinic_calendar_context", return_value=context),
            patch.object(
                morning_brief,
                "_query_clinic_visit_counts",
                return_value=[
                    {"school": "SCH-1", "date": "2026-03-17", "count": 1},
                    {"school": "SCH-1", "date": "2026-03-18", "count": 4},
                    {"school": "SCH-1", "date": "2026-03-20", "count": 2},
                    {"school": "SCH-1", "date": "2026-03-23", "count": 3},
                ],
            ),
        ):
            payload = morning_brief.get_clinic_visits_trend(time_range="1M")

        self.assertEqual(
            payload["data"],
            [
                {"date": "2026-03-17", "count": 1},
                {"date": "2026-03-19", "count": 0},
                {"date": "2026-03-20", "count": 2},
                {"date": "2026-03-23", "count": 3},
            ],
        )
        self.assertEqual(payload["school"], "Upper School")
