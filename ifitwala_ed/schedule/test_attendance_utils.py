# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/test_attendance_utils.py

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, nowdate

from ifitwala_ed.schedule import attendance_utils


class TestAttendanceUtils(FrappeTestCase):
	def test_bulk_upsert_attendance_calls_get_current_term_with_school_and_ay(self):
		att_date = nowdate()
		payload = [_attendance_payload(att_date)]
		sg = _student_group_stub()

		with patch.object(attendance_utils.frappe, "session", SimpleNamespace(user="test.user@example.com")), patch.object(
			attendance_utils.frappe, "get_roles", return_value=["Academic Admin"]
		), patch.object(attendance_utils.frappe, "get_cached_doc", return_value=sg), patch.object(
			attendance_utils, "get_school_for_student_group", return_value="SCH-001"
		), patch.object(
			attendance_utils,
			"get_current_term",
			side_effect=lambda school, academic_year: SimpleNamespace(
				name="TERM-001",
				term_start_date=getdate(att_date),
				term_end_date=getdate(att_date),
			),
		) as current_term_mock, patch.object(
			attendance_utils.frappe, "get_all", return_value=[]
		), patch.object(
			attendance_utils, "get_rotation_dates", return_value=[{"date": getdate(att_date), "rotation_day": 1}]
		), patch.object(
			attendance_utils, "get_meeting_dates", return_value=[att_date]
		), patch.object(
			attendance_utils.frappe.db, "sql", return_value=[]
		), patch.object(
			attendance_utils.frappe.db, "bulk_insert"
		) as bulk_insert_mock, patch.object(
			attendance_utils.frappe.db, "commit"
		):
			result = attendance_utils.bulk_upsert_attendance(payload)

		self.assertEqual(result, {"created": 1, "updated": 0})
		current_term_mock.assert_called_once_with("SCH-001", sg.academic_year)
		bulk_insert_mock.assert_called_once()

	def test_bulk_upsert_attendance_handles_missing_school_without_crash(self):
		att_date = nowdate()
		payload = [_attendance_payload(att_date)]
		sg = _student_group_stub()

		with patch.object(attendance_utils.frappe, "session", SimpleNamespace(user="test.user@example.com")), patch.object(
			attendance_utils.frappe, "get_roles", return_value=["Academic Admin"]
		), patch.object(attendance_utils.frappe, "get_cached_doc", return_value=sg), patch.object(
			attendance_utils, "get_school_for_student_group", return_value=None
		), patch.object(
			attendance_utils,
			"get_current_term",
			side_effect=lambda school, academic_year: None,
		) as current_term_mock, patch.object(
			attendance_utils.frappe, "get_all", return_value=[]
		), patch.object(
			attendance_utils, "get_rotation_dates", return_value=[{"date": getdate(att_date), "rotation_day": 1}]
		), patch.object(
			attendance_utils, "get_meeting_dates", return_value=[att_date]
		), patch.object(
			attendance_utils.frappe.db, "sql", return_value=[]
		), patch.object(
			attendance_utils.frappe.db, "bulk_insert"
		) as bulk_insert_mock, patch.object(
			attendance_utils.frappe.db, "commit"
		):
			result = attendance_utils.bulk_upsert_attendance(payload)

		self.assertEqual(result, {"created": 1, "updated": 0})
		current_term_mock.assert_called_once_with(None, sg.academic_year)
		bulk_insert_mock.assert_called_once()


def _student_group_stub() -> SimpleNamespace:
	return SimpleNamespace(
		name="SG-001",
		academic_year="AY-2025",
		school_schedule="SCH-SCHED-001",
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
