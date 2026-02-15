# ifitwala_ed/hr/test_leave_utils.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.hr import utils as hr_utils


class TestLeaveUtilsHolidayResolution(FrappeTestCase):
	def test_get_holiday_list_prefers_staff_calendar(self):
		ctx = frappe._dict(current_holiday_lis="STAFF-CAL-1", organization="ORG-1")

		with patch("ifitwala_ed.hr.utils._get_employee_context", return_value=ctx):
			holiday_source = hr_utils.get_holiday_list_for_employee("HR-EMP-0001", raise_exception=False)

		self.assertEqual(holiday_source, "STAFF-CAL-1")

	def test_get_holiday_list_returns_none_without_staff_calendar_when_not_raising(self):
		ctx = frappe._dict(current_holiday_lis=None, organization="ORG-1")

		with patch("ifitwala_ed.hr.utils._get_employee_context", return_value=ctx):
			holiday_source = hr_utils.get_holiday_list_for_employee("HR-EMP-0001", raise_exception=False)

		self.assertIsNone(holiday_source)

	def test_get_holidays_uses_staff_calendar_doctype_when_available(self):
		ctx = frappe._dict(current_holiday_lis="STAFF-CAL-1", organization="ORG-1")
		rows = [frappe._dict(holiday_date="2026-02-01", description="Holiday", weekly_off=0)]

		with (
			patch("ifitwala_ed.hr.utils._get_employee_context", return_value=ctx),
			patch("frappe.get_all", return_value=rows) as get_all,
		):
			holidays = hr_utils.get_holidays_for_employee("HR-EMP-0001", "2026-02-01", "2026-02-02")

		self.assertEqual(len(holidays), 1)
		self.assertEqual(get_all.call_args.args[0], "Staff Calendar Holidays")

	def test_get_holidays_returns_empty_without_staff_calendar_when_not_raising(self):
		ctx = frappe._dict(current_holiday_lis=None, organization="ORG-1")

		with patch("ifitwala_ed.hr.utils._get_employee_context", return_value=ctx):
			holidays = hr_utils.get_holidays_for_employee("HR-EMP-0001", "2026-02-01", "2026-02-03")

		self.assertEqual(holidays, [])
