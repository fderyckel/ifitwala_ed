# ifitwala_ed/api/test_calendar.py

from datetime import datetime, time, timedelta
from unittest import TestCase

from ifitwala_ed.api.calendar import (
	CAL_MIN_DURATION,
	_attach_duration,
	_coerce_time,
	_time_to_str,
)


class TestCalendarApi(TestCase):
	def test_coerce_time_supports_multiple_input_types(self):
		self.assertEqual(_coerce_time(time(9, 15, 0)), time(9, 15, 0))
		self.assertEqual(_coerce_time(datetime(2026, 2, 1, 11, 0, 0)), time(11, 0, 0))
		self.assertEqual(_coerce_time(timedelta(hours=3, minutes=5)), time(3, 5, 0))
		self.assertIsNone(_coerce_time("not-a-time"))

	def test_time_to_str_normalizes_values(self):
		self.assertEqual(_time_to_str(time(8, 0, 1)), "08:00:01")
		self.assertEqual(_time_to_str(timedelta(hours=1, minutes=2, seconds=3)), "01:02:03")
		self.assertEqual(_time_to_str(b"12:34:56"), "12:34:56")

	def test_attach_duration_enforces_minimum_duration(self):
		start_dt = datetime(2026, 2, 1, 10, 0, 0)
		self.assertEqual(_attach_duration(start_dt, None), CAL_MIN_DURATION)
		self.assertEqual(_attach_duration(start_dt, datetime(2026, 2, 1, 9, 0, 0)), CAL_MIN_DURATION)
		self.assertEqual(_attach_duration(start_dt, datetime(2026, 2, 1, 11, 30, 0)), timedelta(hours=1, minutes=30))
