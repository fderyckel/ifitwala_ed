from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _attendance_utils_stub_modules(helper_state: dict):
    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.getdate = lambda value: value
    frappe_utils.now_datetime = lambda: "2026-04-20 10:00:00"
    frappe_utils.nowdate = lambda: "2026-04-20"

    frappe_utils_caching = types.ModuleType("frappe.utils.caching")
    frappe_utils_caching.redis_cache = lambda ttl=0: lambda fn: fn

    frappe_utils_nestedset = types.ModuleType("frappe.utils.nestedset")
    frappe_utils_nestedset.get_descendants_of = lambda doctype, name: []

    schedule_utils = types.ModuleType("ifitwala_ed.schedule.schedule_utils")
    schedule_utils.get_effective_schedule_for_ay = lambda academic_year, school: None
    schedule_utils.get_rotation_dates = lambda *args, **kwargs: []

    student_group_scheduling = types.ModuleType("ifitwala_ed.schedule.student_group_scheduling")
    student_group_scheduling.get_school_for_student_group = lambda student_group: "SCH-001"

    term_module = types.ModuleType("ifitwala_ed.school_settings.doctype.term.term")
    term_module.get_current_term = lambda school, academic_year: None

    image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
    image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS = (
        "profile_image_thumb",
        "profile_image_card",
        "profile_image_medium",
    )

    def apply_preferred_student_images(rows, **kwargs):
        helper_state["calls"].append(kwargs)
        return rows

    image_utils.apply_preferred_student_images = apply_preferred_student_images

    return {
        "frappe.utils": frappe_utils,
        "frappe.utils.caching": frappe_utils_caching,
        "frappe.utils.nestedset": frappe_utils_nestedset,
        "ifitwala_ed.schedule.schedule_utils": schedule_utils,
        "ifitwala_ed.schedule.student_group_scheduling": student_group_scheduling,
        "ifitwala_ed.school_settings.doctype.term.term": term_module,
        "ifitwala_ed.utilities.image_utils": image_utils,
    }


class TestAttendanceUtilsUnit(TestCase):
    def test_get_student_group_students_requests_derivative_only_student_images(self):
        helper_state = {"calls": []}

        with stubbed_frappe(extra_modules=_attendance_utils_stub_modules(helper_state)) as frappe:
            frappe.db.sql = lambda query, params=None, as_dict=False: [
                {
                    "student": "STU-0001",
                    "student_name": "Amina Dar",
                    "preferred_name": "Amina",
                    "student_image": "/private/files/student/original.png",
                    "birth_date": "2010-01-01",
                    "medical_info": "Peanut allergy",
                }
            ]

            module = import_fresh("ifitwala_ed.schedule.attendance_utils")
            rows = module.get_student_group_students("SG-001", start=0, page_length=25, with_medical=True)

        self.assertEqual(rows[0]["student"], "STU-0001")
        self.assertEqual(
            helper_state["calls"],
            [
                {
                    "student_field": "student",
                    "image_field": "student_image",
                    "slots": (
                        "profile_image_thumb",
                        "profile_image_card",
                        "profile_image_medium",
                    ),
                    "fallback_to_original": False,
                    "request_missing_derivatives": True,
                }
            ],
        )
