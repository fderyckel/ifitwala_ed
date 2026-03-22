# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import re
import sys
from datetime import date, datetime
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

try:
    import frappe  # type: ignore
except ModuleNotFoundError:
    frappe = ModuleType("frappe")
    frappe.session = SimpleNamespace(user="Administrator")
    frappe.PermissionError = type("PermissionError", (Exception,), {})
    frappe.ValidationError = type("ValidationError", (Exception,), {})
    frappe.db = SimpleNamespace(sql=lambda *args, **kwargs: [], get_value=lambda *args, **kwargs: None)
    frappe.get_roles = lambda user: ["Administrator"]
    frappe.parse_json = lambda value: value
    frappe.log_error = lambda *args, **kwargs: None
    frappe.throw = lambda message, exc=None: (_ for _ in ()).throw((exc or Exception)(message))
    frappe.whitelist = lambda *args, **kwargs: lambda fn: fn

    frappe_utils = ModuleType("frappe.utils")

    def _getdate(value):
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value), "%Y-%m-%d").date()

    def _get_datetime(value):
        if isinstance(value, datetime):
            return value
        raw = str(value).strip().replace("T", " ")
        fmt = "%Y-%m-%d %H:%M:%S" if " " in raw else "%Y-%m-%d"
        parsed = datetime.strptime(raw, fmt)
        if fmt == "%Y-%m-%d":
            return datetime.combine(parsed.date(), datetime.min.time())
        return parsed

    def _strip_html(value):
        return re.sub(r"<[^>]+>", " ", str(value or "")).strip()

    frappe_utils.getdate = _getdate
    frappe_utils.get_datetime = _get_datetime
    frappe_utils.strip_html = _strip_html

    frappe_nestedset = ModuleType("frappe.utils.nestedset")
    frappe_nestedset.get_descendants_of = lambda *args, **kwargs: []

    student_log_stub = ModuleType("ifitwala_ed.students.doctype.student_log.student_log")
    student_log_stub.get_student_log_visibility_predicate = lambda *args, **kwargs: ("1=1", {})

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = frappe_utils
    sys.modules["frappe.utils.nestedset"] = frappe_nestedset
    sys.modules["ifitwala_ed.students.doctype.student_log.student_log"] = student_log_stub

from ifitwala_ed.api import student_log_dashboard as dashboard_api


class _CacheStub:
    def __init__(self):
        self.values = {}

    def get_value(self, key):
        return self.values.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.values[key] = value


class TestStudentLogDashboard(TestCase):
    def test_get_dashboard_data_escapes_date_format_tokens_in_union_query(self):
        seen_union_query = None

        def fake_sql(query, params=None, as_dict=False):
            nonlocal seen_union_query
            if "UNION ALL" in query and "'log_type' AS metric" in query:
                seen_union_query = query
                return [
                    {"metric": "date", "label": "2026-03-10", "value": 2},
                    {"metric": "open_follow_ups", "label": "open_follow_ups", "value": 1},
                ]
            raise AssertionError(f"Unexpected SQL in test_get_dashboard_data_escapes_date_format_tokens: {query}")

        with (
            patch.object(dashboard_api, "_ensure_student_log_analytics_access", return_value="Administrator"),
            patch.object(dashboard_api, "get_student_log_visibility_predicate", return_value=("1=1", {})),
            patch.object(dashboard_api.frappe.db, "sql", side_effect=fake_sql),
        ):
            result = dashboard_api.get_dashboard_data(filters={})

        self.assertIn("DATE_FORMAT(sl.date,'%%Y-%%m-%%d')", seen_union_query)
        self.assertEqual(result.get("incidentsOverTime"), [{"label": "2026-03-10", "value": 2}])
        self.assertEqual(result.get("openFollowUps"), 1)

    def test_get_dashboard_data_includes_follow_up_summaries_for_selected_student_rows(self):
        def fake_sql(query, params=None, as_dict=False):
            # Consolidated UNION query for dashboard aggregates (metric column identifies result type)
            if "UNION ALL" in query and "'log_type' AS metric" in query:
                return [{"metric": "open_follow_ups", "label": "open_follow_ups", "value": 0}]
            if "FROM `tabStudent Log Follow Up` fu" in query:
                return [
                    {
                        "name": "SLFU-0001",
                        "student_log": "SLOG-0001",
                        "date": "2026-03-10",
                        "follow_up_author": "Counselor Jane",
                        "follow_up": "<p>Met student and guardian.</p>",
                        "responded_at": "2026-03-10 11:30:00",
                    }
                ]
            if "sl.student = %(field_student)s" in query:
                return [
                    {
                        "name": "SLOG-0001",
                        "date": "2026-03-10",
                        "log_type": "Wellbeing",
                        "content": "Needs counselor follow-up.",
                        "author": "Teacher One",
                        "requires_follow_up": 1,
                        "next_step": "Refer to Counselor",
                        "created_at": "2026-03-10 08:00:00",
                    }
                ]
            raise AssertionError(f"Unexpected SQL in test_get_dashboard_data: {query}")

        with (
            patch.object(dashboard_api, "_ensure_student_log_analytics_access", return_value="Administrator"),
            patch.object(dashboard_api, "get_student_log_visibility_predicate", return_value=("1=1", {})),
            patch.object(dashboard_api.frappe.db, "sql", side_effect=fake_sql),
        ):
            result = dashboard_api.get_dashboard_data(filters={"student": "STU-0001"})

        student_logs = result.get("studentLogs") or []
        self.assertEqual(len(student_logs), 1)
        self.assertEqual(student_logs[0].get("follow_up_count"), 1)

        follow_ups = student_logs[0].get("follow_ups") or []
        self.assertEqual(len(follow_ups), 1)
        self.assertEqual(follow_ups[0].get("doctype"), "Student Log Follow Up")
        self.assertEqual(follow_ups[0].get("next_step"), "Refer to Counselor")
        self.assertEqual(follow_ups[0].get("responded_in_minutes"), 210)
        self.assertEqual(follow_ups[0].get("responded_in_label"), "3h 30m")
        self.assertEqual(follow_ups[0].get("comment_text"), "Met student and guardian.")

    def test_get_recent_logs_includes_submitted_follow_up_stack(self):
        def fake_sql(query, params=None, as_dict=False):
            if "FROM `tabStudent Log Follow Up` fu" in query:
                return [
                    {
                        "name": "SLFU-0002",
                        "student_log": "SLOG-0002",
                        "date": "2026-03-11",
                        "follow_up_author": "Pastoral Lead",
                        "follow_up": "<div>Spoke with family and created a support plan.</div>",
                        "responded_at": "2026-03-11 10:45:00",
                    }
                ]
            if "FROM `tabStudent Log` sl" in query and "LIMIT %(start)s, %(page_len)s" in query:
                return [
                    {
                        "name": "SLOG-0002",
                        "date": "2026-03-11",
                        "student": "STU-0002",
                        "student_full_name": "Student Two",
                        "program": "PYP",
                        "log_type": "Pastoral",
                        "content": "Student arrived distressed.",
                        "author": "Teacher Two",
                        "requires_follow_up": 1,
                        "next_step": "Parent Call",
                        "created_at": "2026-03-11 09:00:00",
                    }
                ]
            raise AssertionError(f"Unexpected SQL in test_get_recent_logs: {query}")

        with (
            patch.object(dashboard_api, "_ensure_student_log_analytics_access", return_value="Administrator"),
            patch.object(dashboard_api, "get_student_log_visibility_predicate", return_value=("1=1", {})),
            patch.object(dashboard_api.frappe.db, "sql", side_effect=fake_sql),
        ):
            rows = dashboard_api.get_recent_logs(filters={}, start=0, page_length=25)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("follow_up_count"), 1)
        self.assertEqual(rows[0].get("follow_ups")[0].get("responded_in_label"), "1h 45m")
        self.assertEqual(
            rows[0].get("follow_ups")[0].get("comment_text"), "Spoke with family and created a support plan."
        )

    def test_get_filter_meta_uses_scoped_cache(self):
        cache = _CacheStub()
        sql_calls = []

        def fake_sql(query, params=None, as_dict=False):
            sql_calls.append(query)
            if "JOIN `tabSchool` sc" in query:
                return [{"name": "SCH-1", "label": "School One"}]
            if "JOIN `tabAcademic Year` ay" in query:
                return [
                    {
                        "name": "AY-1",
                        "label": "AY 1",
                        "year_start_date": "2026-08-01",
                        "year_end_date": "2027-06-30",
                        "school": "SCH-1",
                    }
                ]
            if "JOIN `tabProgram` p" in query:
                return [{"name": "PRG-1", "label": "Program One"}]
            if "JOIN `tabEmployee` e" in query:
                return [{"user_id": "teacher@example.com", "label": "Teacher Example"}]
            raise AssertionError(f"Unexpected SQL in test_get_filter_meta_uses_scoped_cache: {query}")

        defaults = SimpleNamespace(get_user_default=lambda *args, **kwargs: "SCH-1")

        with (
            patch.object(dashboard_api, "_ensure_student_log_analytics_access", return_value="teacher@example.com"),
            patch.object(dashboard_api, "get_student_log_visibility_predicate", return_value=("1=1", {})),
            patch.object(dashboard_api.frappe.db, "sql", side_effect=fake_sql),
            patch.object(dashboard_api.frappe, "cache", return_value=cache, create=True),
            patch.object(dashboard_api.frappe, "defaults", defaults, create=True),
        ):
            first = dashboard_api.get_filter_meta()
            second = dashboard_api.get_filter_meta()

        self.assertEqual(first, second)
        self.assertEqual(len(sql_calls), 4)
        self.assertTrue(cache.values)
