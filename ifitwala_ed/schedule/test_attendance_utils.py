# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/test_attendance_utils.py

from types import SimpleNamespace
from unittest.mock import call, patch

from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from ifitwala_ed.schedule import attendance_utils


class TestAttendanceUtils(FrappeTestCase):
    def test_fetch_blocks_for_day_uses_effective_schedule_when_group_schedule_missing(self):
        att_date = nowdate()
        sg = _student_group_stub(school_schedule=None)

        with (
            patch.object(attendance_utils.frappe, "get_cached_doc", return_value=sg),
            patch.object(attendance_utils, "get_school_for_student_group", return_value="SCH-001"),
            patch.object(
                attendance_utils,
                "get_effective_schedule_for_ay",
                return_value="SCH-SCHED-FALLBACK",
            ) as effective_schedule_mock,
            patch.object(
                attendance_utils,
                "get_rotation_dates",
                return_value=[{"date": getdate(att_date), "rotation_day": 2}],
            ) as rotation_dates_mock,
            patch.object(
                attendance_utils.frappe,
                "get_all",
                return_value=[SimpleNamespace(block_number=3), SimpleNamespace(block_number=4)],
            ),
        ):
            result = attendance_utils.fetch_blocks_for_day("SG-001", att_date)

        self.assertEqual(result, [3, 4])
        effective_schedule_mock.assert_called_once_with(sg.academic_year, "SCH-001")
        rotation_dates_mock.assert_called_once_with("SCH-SCHED-FALLBACK", sg.academic_year, include_holidays=False)

    def test_bulk_upsert_attendance_calls_get_current_term_with_school_and_ay(self):
        att_date = nowdate()
        payload = [_attendance_payload(att_date)]
        sg = _student_group_stub()

        with (
            patch.object(attendance_utils.frappe, "session", SimpleNamespace(user="test.user@example.com")),
            patch.object(attendance_utils.frappe, "get_roles", return_value=["Academic Admin"]),
            patch.object(attendance_utils.frappe, "get_cached_doc", return_value=sg),
            patch.object(
                attendance_utils,
                "get_school_for_student_group",
                return_value="SCH-001",
            ) as school_resolver_mock,
            patch.object(
                attendance_utils,
                "get_current_term",
                side_effect=lambda school, academic_year: SimpleNamespace(
                    name="TERM-001",
                    term_start_date=getdate(att_date),
                    term_end_date=getdate(att_date),
                ),
            ) as current_term_mock,
            patch.object(attendance_utils.frappe, "get_all", return_value=[]),
            patch.object(attendance_utils.frappe.db, "get_value", return_value=None),
            patch.object(
                attendance_utils, "get_rotation_dates", return_value=[{"date": getdate(att_date), "rotation_day": 1}]
            ),
            patch.object(attendance_utils, "get_meeting_dates", return_value=[att_date]),
            patch.object(attendance_utils.frappe.db, "sql", return_value=[]),
            patch.object(attendance_utils.frappe.db, "bulk_insert") as bulk_insert_mock,
            patch.object(attendance_utils.frappe.db, "commit"),
        ):
            result = attendance_utils.bulk_upsert_attendance(payload)

        self.assertEqual(result, {"created": 1, "updated": 0})
        current_term_mock.assert_called_once_with("SCH-001", sg.academic_year)
        school_resolver_mock.assert_called_once_with(sg.name)
        bulk_insert_mock.assert_called_once()

    def test_bulk_upsert_attendance_handles_missing_school_without_crash(self):
        att_date = nowdate()
        payload = [_attendance_payload(att_date)]
        sg = _student_group_stub()

        with (
            patch.object(attendance_utils.frappe, "session", SimpleNamespace(user="test.user@example.com")),
            patch.object(attendance_utils.frappe, "get_roles", return_value=["Academic Admin"]),
            patch.object(attendance_utils.frappe, "get_cached_doc", return_value=sg),
            patch.object(attendance_utils, "get_school_for_student_group", return_value=None),
            patch.object(
                attendance_utils,
                "get_current_term",
                side_effect=lambda school, academic_year: None,
            ) as current_term_mock,
            patch.object(attendance_utils.frappe, "get_all", return_value=[]),
            patch.object(attendance_utils.frappe.db, "get_value", return_value=None),
            patch.object(
                attendance_utils, "get_rotation_dates", return_value=[{"date": getdate(att_date), "rotation_day": 1}]
            ),
            patch.object(attendance_utils, "get_meeting_dates", return_value=[att_date]),
            patch.object(attendance_utils.frappe.db, "sql", return_value=[]),
            patch.object(attendance_utils.frappe.db, "bulk_insert") as bulk_insert_mock,
            patch.object(attendance_utils.frappe.db, "commit"),
        ):
            result = attendance_utils.bulk_upsert_attendance(payload)

        self.assertEqual(result, {"created": 1, "updated": 0})
        current_term_mock.assert_called_once_with(None, sg.academic_year)
        bulk_insert_mock.assert_called_once()

    def test_bulk_upsert_attendance_tolerates_legacy_three_arg_get_current_term(self):
        att_date = nowdate()
        payload = [_attendance_payload(att_date)]
        sg = _student_group_stub()

        def legacy_signature(_legacy_ctx, school, academic_year):
            return None

        with (
            patch.object(attendance_utils.frappe, "session", SimpleNamespace(user="test.user@example.com")),
            patch.object(attendance_utils.frappe, "get_roles", return_value=["Academic Admin"]),
            patch.object(attendance_utils.frappe, "get_cached_doc", return_value=sg),
            patch.object(attendance_utils, "get_school_for_student_group", return_value="SCH-001"),
            patch.object(
                attendance_utils,
                "get_current_term",
                side_effect=legacy_signature,
            ) as current_term_mock,
            patch.object(attendance_utils.frappe, "get_all", return_value=[]),
            patch.object(attendance_utils.frappe.db, "get_value", return_value=None),
            patch.object(
                attendance_utils, "get_rotation_dates", return_value=[{"date": getdate(att_date), "rotation_day": 1}]
            ),
            patch.object(attendance_utils, "get_meeting_dates", return_value=[att_date]),
            patch.object(attendance_utils.frappe.db, "sql", return_value=[]),
            patch.object(attendance_utils.frappe.db, "bulk_insert") as bulk_insert_mock,
            patch.object(attendance_utils.frappe.db, "commit"),
        ):
            result = attendance_utils.bulk_upsert_attendance(payload)

        self.assertEqual(result, {"created": 1, "updated": 0})
        self.assertEqual(
            current_term_mock.call_args_list,
            [
                call("SCH-001", sg.academic_year),
                call(None, "SCH-001", sg.academic_year),
            ],
        )
        bulk_insert_mock.assert_called_once()

    def test_bulk_upsert_attendance_allows_past_date_within_academic_year_when_term_missing(self):
        att_date = add_days(nowdate(), -5)
        payload = [_attendance_payload(att_date)]
        sg = _student_group_stub()

        with (
            patch.object(attendance_utils.frappe, "session", SimpleNamespace(user="test.user@example.com")),
            patch.object(attendance_utils.frappe, "get_roles", return_value=["Academic Admin"]),
            patch.object(attendance_utils.frappe, "get_cached_doc", return_value=sg),
            patch.object(attendance_utils, "get_school_for_student_group", return_value=None),
            patch.object(
                attendance_utils,
                "get_current_term",
                return_value=None,
            ),
            patch.object(attendance_utils.frappe, "get_all", return_value=[]),
            patch.object(
                attendance_utils.frappe.db,
                "get_value",
                return_value={
                    "year_start_date": getdate(add_days(nowdate(), -120)),
                    "year_end_date": getdate(add_days(nowdate(), 120)),
                },
            ),
            patch.object(
                attendance_utils, "get_rotation_dates", return_value=[{"date": getdate(att_date), "rotation_day": 1}]
            ),
            patch.object(attendance_utils, "get_meeting_dates", return_value=[att_date]),
            patch.object(attendance_utils.frappe.db, "sql", return_value=[]),
            patch.object(attendance_utils.frappe.db, "bulk_insert") as bulk_insert_mock,
            patch.object(attendance_utils.frappe.db, "commit"),
        ):
            result = attendance_utils.bulk_upsert_attendance(payload)

        self.assertEqual(result, {"created": 1, "updated": 0})
        bulk_insert_mock.assert_called_once()

    def test_bulk_upsert_attendance_uses_effective_schedule_when_group_schedule_missing(self):
        att_date = nowdate()
        payload = [_attendance_payload(att_date)]
        sg = _student_group_stub(school_schedule=None)

        with (
            patch.object(attendance_utils.frappe, "session", SimpleNamespace(user="test.user@example.com")),
            patch.object(attendance_utils.frappe, "get_roles", return_value=["Academic Admin"]),
            patch.object(attendance_utils.frappe, "get_cached_doc", return_value=sg),
            patch.object(attendance_utils, "get_school_for_student_group", return_value="SCH-001"),
            patch.object(attendance_utils, "get_current_term", return_value=None),
            patch.object(
                attendance_utils,
                "get_effective_schedule_for_ay",
                return_value="SCH-SCHED-FALLBACK",
            ) as effective_schedule_mock,
            patch.object(attendance_utils.frappe, "get_all", return_value=[]),
            patch.object(attendance_utils.frappe.db, "get_value", return_value=None),
            patch.object(
                attendance_utils,
                "get_rotation_dates",
                return_value=[{"date": getdate(att_date), "rotation_day": 1}],
            ) as rotation_dates_mock,
            patch.object(attendance_utils, "get_meeting_dates", return_value=[att_date]),
            patch.object(attendance_utils.frappe.db, "sql", return_value=[]),
            patch.object(attendance_utils.frappe.db, "bulk_insert") as bulk_insert_mock,
            patch.object(attendance_utils.frappe.db, "commit"),
        ):
            result = attendance_utils.bulk_upsert_attendance(payload)

        self.assertEqual(result, {"created": 1, "updated": 0})
        effective_schedule_mock.assert_called_once_with(sg.academic_year, "SCH-001")
        rotation_dates_mock.assert_called_once_with("SCH-SCHED-FALLBACK", sg.academic_year, include_holidays=False)
        bulk_insert_mock.assert_called_once()


def _student_group_stub(*, school_schedule="SCH-SCHED-001") -> SimpleNamespace:
    return SimpleNamespace(
        name="SG-001",
        academic_year="AY-2025",
        school_schedule=school_schedule,
        term="TERM-001",
        program="PROG-001",
        course="COURSE-001",
    )


def _attendance_payload(attendance_date: str) -> dict:
    return {
        "student": "STU-001",
        "student_group": "SG-001",
        "attendance_date": attendance_date,
        "attendance_code": "P",
        "block_number": 1,
        "remark": "",
    }
