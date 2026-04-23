# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import dataclasses
import types
from datetime import date
from unittest import TestCase
from unittest.mock import Mock, patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe

_stdlib_dataclass = dataclasses.dataclass


class _AttrDict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class _FakeCache:
    def __init__(self):
        self.data: dict[str, object] = {}

    def get_value(self, key: str):
        return self.data.get(key)

    def set_value(self, key: str, value, expires_in_sec: int | None = None):
        self.data[key] = value

    def get_keys(self, pattern: str):
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [key for key in list(self.data.keys()) if key.startswith(prefix)]

    def delete_value(self, key: str):
        self.data.pop(key, None)


def _course_schedule_extra_modules(schedule_utils_module, student_group_module):
    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.formatdate = lambda value, fmt=None: "Friday"
    frappe_utils.getdate = lambda value: value if isinstance(value, date) else date.fromisoformat(value)
    frappe_utils.nowdate = lambda: "2026-04-17"

    return {
        "frappe.utils": frappe_utils,
        "ifitwala_ed.schedule.schedule_utils": schedule_utils_module,
        "ifitwala_ed.schedule.student_group_scheduling": student_group_module,
    }


class TestCourseScheduleCache(TestCase):
    def test_get_today_courses_reuses_shared_inputs_until_invalidated(self):
        schedule_utils = types.ModuleType("ifitwala_ed.schedule.schedule_utils")
        schedule_utils.get_effective_schedule_for_ay = Mock(return_value="SCHED-1")
        schedule_utils.get_rotation_dates = Mock(return_value=[{"date": date(2026, 4, 17), "rotation_day": 2}])

        student_group_scheduling = types.ModuleType("ifitwala_ed.schedule.student_group_scheduling")
        student_group_scheduling.get_school_for_student_group = Mock(return_value="SCH-1")

        cache = _FakeCache()

        with stubbed_frappe(
            extra_modules=_course_schedule_extra_modules(schedule_utils, student_group_scheduling)
        ) as frappe:
            frappe.cache = lambda: cache
            frappe.session.user = "student@example.com"

            term_lookup_calls: list[str] = []

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False, **kwargs):
                if doctype == "User":
                    return "student@example.com"
                if doctype == "Student":
                    return "STU-1"
                if doctype == "Term":
                    term_lookup_calls.append(name_or_filters)
                    return _AttrDict(term_start_date="2026-04-01", term_end_date="2026-04-30")
                return None

            def fake_sql(query, params=None, as_dict=False):
                if "FROM `tabStudent Group Student`" not in query:
                    return []
                return [
                    _AttrDict(
                        student_group="GROUP-1",
                        student_group_name="Biology A",
                        group_based_on="Course",
                        status="Active",
                        course="COURSE-1",
                        program="PROG-1",
                        program_offering="PO-1",
                        school="SCH-1",
                        school_schedule="SCHED-1",
                        academic_year="AY-1",
                        term="TERM-1",
                        course_name="Biology",
                        course_group="Science",
                        course_image="/files/biology.jpg",
                    ),
                    _AttrDict(
                        student_group="GROUP-2",
                        student_group_name="History A",
                        group_based_on="Course",
                        status="Active",
                        course="COURSE-2",
                        program="PROG-1",
                        program_offering="PO-1",
                        school="SCH-1",
                        school_schedule="SCHED-1",
                        academic_year="AY-1",
                        term="TERM-1",
                        course_name="History",
                        course_group="Humanities",
                        course_image="/files/history.jpg",
                    ),
                ]

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, **kwargs):
                if doctype != "Student Group Schedule":
                    return []
                return [
                    _AttrDict(
                        parent="GROUP-1",
                        rotation_day=2,
                        block_number=1,
                        from_time="09:00:00",
                        to_time="10:00:00",
                        instructor=None,
                        location="Room 1",
                    ),
                    _AttrDict(
                        parent="GROUP-2",
                        rotation_day=2,
                        block_number=2,
                        from_time="11:00:00",
                        to_time="12:00:00",
                        instructor=None,
                        location="Room 2",
                    ),
                ]

            frappe.db.get_value = Mock(side_effect=fake_get_value)
            frappe.db.sql = Mock(side_effect=fake_sql)
            frappe.db.get_all = Mock(side_effect=fake_get_all)

            with patch("dataclasses.dataclass", side_effect=self._dataclass_without_slots):
                module = import_fresh("ifitwala_ed.api.course_schedule")

            first = module.get_today_courses()
            second = module.get_today_courses()

            self.assertEqual(first["date"], "2026-04-17")
            self.assertEqual(second["courses"][0]["course"], "COURSE-1")
            self.assertEqual(len(second["courses"]), 2)
            self.assertEqual(term_lookup_calls, ["TERM-1"])
            self.assertEqual(schedule_utils.get_rotation_dates.call_count, 1)

            cache.set_value("ifw:eff_sched_ay:AY-1:SCH-1", "SCHED-1")
            cache.set_value("effective_schedule::CAL-1::SCH-1", "SCHED-1")

            module.invalidate_course_schedule_cache()

            self.assertFalse(any(key.startswith(module.COURSE_SCHEDULE_CACHE_PREFIX) for key in cache.data))
            self.assertNotIn("ifw:eff_sched_ay:AY-1:SCH-1", cache.data)
            self.assertNotIn("effective_schedule::CAL-1::SCH-1", cache.data)

            third = module.get_today_courses()

            self.assertEqual(third["courses"][1]["course"], "COURSE-2")
            self.assertEqual(term_lookup_calls, ["TERM-1", "TERM-1"])
            self.assertEqual(schedule_utils.get_rotation_dates.call_count, 2)

    def test_term_invalidation_only_clears_term_window_cache(self):
        schedule_utils = types.ModuleType("ifitwala_ed.schedule.schedule_utils")
        schedule_utils.get_effective_schedule_for_ay = Mock(return_value=None)
        schedule_utils.get_rotation_dates = Mock(return_value=[])

        student_group_scheduling = types.ModuleType("ifitwala_ed.schedule.student_group_scheduling")
        student_group_scheduling.get_school_for_student_group = Mock(return_value=None)

        cache = _FakeCache()

        with stubbed_frappe(
            extra_modules=_course_schedule_extra_modules(schedule_utils, student_group_scheduling)
        ) as frappe:
            frappe.cache = lambda: cache
            frappe.db.get_value = Mock(return_value=None)
            frappe.get_all = Mock(return_value=[])

            with patch("dataclasses.dataclass", side_effect=self._dataclass_without_slots):
                module = import_fresh("ifitwala_ed.api.course_schedule")

            cache.set_value(module._cache_key_for_term("TERM-1"), {"term_start_date": "2026-04-01"})
            cache.set_value(module._cache_key_for_rotation("SCHED-1", "AY-1"), {"2026-04-17": 2})
            cache.set_value("ifw:eff_sched_ay:AY-1:SCH-1", "SCHED-1")

            module.invalidate_course_schedule_cache(_AttrDict(doctype="Term", name="TERM-1"))

            self.assertNotIn(module._cache_key_for_term("TERM-1"), cache.data)
            self.assertIn(module._cache_key_for_rotation("SCHED-1", "AY-1"), cache.data)
            self.assertIn("ifw:eff_sched_ay:AY-1:SCH-1", cache.data)

    def test_calendar_invalidation_clears_related_rotation_and_resolution_keys_only(self):
        schedule_utils = types.ModuleType("ifitwala_ed.schedule.schedule_utils")
        schedule_utils.get_effective_schedule_for_ay = Mock(return_value=None)
        schedule_utils.get_rotation_dates = Mock(return_value=[])

        student_group_scheduling = types.ModuleType("ifitwala_ed.schedule.student_group_scheduling")
        student_group_scheduling.get_school_for_student_group = Mock(return_value=None)

        cache = _FakeCache()

        with stubbed_frappe(
            extra_modules=_course_schedule_extra_modules(schedule_utils, student_group_scheduling)
        ) as frappe:
            frappe.cache = lambda: cache

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False, **kwargs):
                if doctype == "School Calendar" and name_or_filters == "CAL-1":
                    return "AY-1"
                return None

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, **kwargs):
                if doctype == "School Schedule" and filters == {"school_calendar": "CAL-1"}:
                    return [_AttrDict(name="SCHED-1"), _AttrDict(name="SCHED-2")]
                return []

            frappe.db.get_value = Mock(side_effect=fake_get_value)
            frappe.get_all = Mock(side_effect=fake_get_all)

            with patch("dataclasses.dataclass", side_effect=self._dataclass_without_slots):
                module = import_fresh("ifitwala_ed.api.course_schedule")

            cache.set_value(module._cache_key_for_rotation("SCHED-1", "AY-1"), {"2026-04-17": 2})
            cache.set_value(module._cache_key_for_rotation("SCHED-2", "AY-1"), {"2026-04-17": 3})
            cache.set_value(module._cache_key_for_rotation("SCHED-9", "AY-9"), {"2026-04-17": 1})
            cache.set_value("effective_schedule::CAL-1::SCH-1", "SCHED-1")
            cache.set_value("effective_schedule::CAL-9::SCH-9", "SCHED-9")
            cache.set_value("ifw:eff_sched_ay:AY-1:SCH-1", "SCHED-1")
            cache.set_value("ifw:eff_sched_ay:AY-9:SCH-9", "SCHED-9")
            cache.set_value(module._cache_key_for_term("TERM-1"), {"term_start_date": "2026-04-01"})

            module.invalidate_course_schedule_cache(
                _AttrDict(doctype="School Calendar", name="CAL-1", academic_year="AY-1")
            )

            self.assertNotIn(module._cache_key_for_rotation("SCHED-1", "AY-1"), cache.data)
            self.assertNotIn(module._cache_key_for_rotation("SCHED-2", "AY-1"), cache.data)
            self.assertIn(module._cache_key_for_rotation("SCHED-9", "AY-9"), cache.data)
            self.assertNotIn("effective_schedule::CAL-1::SCH-1", cache.data)
            self.assertIn("effective_schedule::CAL-9::SCH-9", cache.data)
            self.assertNotIn("ifw:eff_sched_ay:AY-1:SCH-1", cache.data)
            self.assertIn("ifw:eff_sched_ay:AY-9:SCH-9", cache.data)
            self.assertIn(module._cache_key_for_term("TERM-1"), cache.data)

    def test_school_invalidation_keeps_term_and_rotation_inputs(self):
        schedule_utils = types.ModuleType("ifitwala_ed.schedule.schedule_utils")
        schedule_utils.get_effective_schedule_for_ay = Mock(return_value=None)
        schedule_utils.get_rotation_dates = Mock(return_value=[])

        student_group_scheduling = types.ModuleType("ifitwala_ed.schedule.student_group_scheduling")
        student_group_scheduling.get_school_for_student_group = Mock(return_value=None)

        cache = _FakeCache()

        with stubbed_frappe(
            extra_modules=_course_schedule_extra_modules(schedule_utils, student_group_scheduling)
        ) as frappe:
            frappe.cache = lambda: cache
            frappe.db.get_value = Mock(return_value=None)
            frappe.get_all = Mock(return_value=[])

            with patch("dataclasses.dataclass", side_effect=self._dataclass_without_slots):
                module = import_fresh("ifitwala_ed.api.course_schedule")

            cache.set_value(module._cache_key_for_term("TERM-1"), {"term_start_date": "2026-04-01"})
            cache.set_value(module._cache_key_for_rotation("SCHED-1", "AY-1"), {"2026-04-17": 2})
            cache.set_value("ifw:eff_sched_ay:AY-1:SCH-1", "SCHED-1")
            cache.set_value("effective_schedule::CAL-1::SCH-1", "SCHED-1")

            module.invalidate_course_schedule_cache(_AttrDict(doctype="School", name="SCH-1"))

            self.assertIn(module._cache_key_for_term("TERM-1"), cache.data)
            self.assertIn(module._cache_key_for_rotation("SCHED-1", "AY-1"), cache.data)
            self.assertNotIn("ifw:eff_sched_ay:AY-1:SCH-1", cache.data)
            self.assertNotIn("effective_schedule::CAL-1::SCH-1", cache.data)

    @staticmethod
    def _dataclass_without_slots(*args, **kwargs):
        kwargs.pop("slots", None)
        return _stdlib_dataclass(*args, **kwargs)
