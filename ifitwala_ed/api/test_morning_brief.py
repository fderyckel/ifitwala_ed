# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from datetime import date, datetime
from unittest.mock import patch

import frappe

from ifitwala_ed.api import morning_brief
from ifitwala_ed.tests.base import IfitwalaFrappeTestCase


class TestMorningBrief(IfitwalaFrappeTestCase):
    def test_get_staff_birthdays_filters_active_employees_with_birthdays_only(self):
        captured = {}

        def fake_sql(query, values=None, as_dict=False, **kwargs):
            captured["query"] = query
            captured["values"] = values
            captured["as_dict"] = as_dict
            return []

        with (
            patch.object(morning_brief, "today", return_value="2026-03-23"),
            patch.object(morning_brief.frappe.db, "sql", side_effect=fake_sql),
        ):
            rows = morning_brief.get_staff_birthdays()

        self.assertEqual(rows, [])
        self.assertTrue(captured["as_dict"])
        self.assertEqual(captured["values"], ("03-19", "03-27"))
        self.assertIn("employment_status = 'Active'", captured["query"])
        self.assertIn("employee_date_of_birth IS NOT NULL", captured["query"])
        self.assertNotRegex(captured["query"], r"(?<!employment_)status = 'Active'")

    def test_query_clinic_visit_counts_falls_back_to_student_anchor_school(self):
        captured = {}

        def fake_sql(query, values=None, as_dict=False, **kwargs):
            captured["query"] = query
            captured["values"] = values
            captured["as_dict"] = as_dict
            return []

        with patch.object(morning_brief.frappe.db, "sql", side_effect=fake_sql):
            rows = morning_brief._query_clinic_visit_counts(
                ["SCH-PARENT", "SCH-CHILD"],
                date(2025, 11, 1),
                date(2025, 11, 30),
            )

        self.assertEqual(rows, [])
        self.assertTrue(captured["as_dict"])
        self.assertIn("COALESCE(NULLIF(spv.school, ''), st.anchor_school) AS school", captured["query"])
        self.assertIn("LEFT JOIN `tabStudent Patient` sp", captured["query"])
        self.assertIn("LEFT JOIN `tabStudent` st", captured["query"])
        self.assertIn("COALESCE(NULLIF(spv.school, ''), st.anchor_school) IN %(schools)s", captured["query"])
        self.assertEqual(captured["values"]["schools"], ("SCH-PARENT", "SCH-CHILD"))

    def test_resolve_clinic_scope_falls_back_to_employee_default_school(self):
        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False, **kwargs):
            if doctype == "Employee":
                return frappe._dict(default_school="SCH-PARENT", school="SCH-CHILD")
            if doctype == "School" and filters == "SCH-PARENT" and fieldname == "school_name":
                return "Parent School"
            return None

        with (
            patch.object(morning_brief, "get_user_default_school", return_value=None),
            patch.object(morning_brief.frappe, "session", frappe._dict(user="nurse@example.com")),
            patch.object(morning_brief.frappe.db, "has_column", return_value=True),
            patch.object(morning_brief.frappe.db, "get_value", side_effect=fake_get_value),
            patch.object(
                morning_brief,
                "get_descendant_schools",
                return_value=["SCH-PARENT", "SCH-CHILD-A", "SCH-CHILD-B"],
            ),
        ):
            scope = morning_brief._resolve_clinic_scope()

        self.assertEqual(scope["base_school"], "SCH-PARENT")
        self.assertEqual(scope["school_scope"], ["SCH-PARENT", "SCH-CHILD-A", "SCH-CHILD-B"])
        self.assertEqual(scope["scope_label"], "Parent School + 2 schools")
        self.assertIsNone(scope["error"])

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

    def test_resolve_clinic_trend_start_date_uses_calendar_year_for_ytd(self):
        self.assertEqual(
            morning_brief._resolve_clinic_trend_start_date("YTD", date(2026, 3, 22)),
            date(2026, 1, 1),
        )

    def test_resolve_clinic_trend_start_date_ytd_uses_scoped_academic_year_window(self):
        rows = [
            {"year_start_date": "2025-08-15", "year_end_date": "2026-06-15"},
            {"year_start_date": "2025-08-01", "year_end_date": "2026-06-30"},
            {"year_start_date": "2024-08-01", "year_end_date": "2025-06-30"},
        ]

        with patch.object(morning_brief.frappe, "get_all", return_value=rows) as get_all:
            start_date = morning_brief._resolve_clinic_trend_start_date(
                "YTD",
                date(2026, 3, 23),
                ["SCH-PARENT", "SCH-CHILD"],
            )

        self.assertEqual(start_date, date(2025, 8, 1))
        get_all.assert_called_once_with(
            "Academic Year",
            filters={
                "school": ["in", ["SCH-PARENT", "SCH-CHILD"]],
                "archived": 0,
                "year_start_date": ["<=", date(2026, 3, 23)],
                "year_end_date": [">=", date(2026, 3, 23)],
            },
            fields=["year_start_date"],
            order_by="year_start_date asc",
            limit=50,
        )
