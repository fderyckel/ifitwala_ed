from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _morning_brief_module():
    org_comm_utils = ModuleType("ifitwala_ed.api.org_comm_utils")
    org_comm_utils.check_audience_match = lambda *args, **kwargs: True

    interactions = ModuleType("ifitwala_ed.api.org_communication_interactions")
    interactions.get_seen_org_communication_names = lambda **kwargs: set()

    schedule_utils = ModuleType("ifitwala_ed.schedule.schedule_utils")
    schedule_utils.get_weekend_days_for_calendar = lambda *args, **kwargs: set()

    school_settings_utils = ModuleType("ifitwala_ed.school_settings.school_settings_utils")
    school_settings_utils.resolve_school_calendars_for_window = lambda *args, **kwargs: {}

    student_log = ModuleType("ifitwala_ed.students.doctype.student_log.student_log")
    student_log.get_student_log_visibility_predicate = lambda *args, **kwargs: None

    image_helper_state = {"calls": []}
    image_utils = ModuleType("ifitwala_ed.utilities.image_utils")
    image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS = (
        "profile_image_thumb",
        "profile_image_card",
        "profile_image_medium",
    )
    image_utils.apply_preferred_employee_images = lambda rows, **kwargs: rows

    def apply_preferred_student_images(rows, **kwargs):
        image_helper_state["calls"].append(kwargs)
        return rows

    image_utils.apply_preferred_student_images = apply_preferred_student_images

    school_tree = ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree.get_descendant_schools = lambda school: [school]
    school_tree.get_user_default_school = lambda user: None

    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.add_days = lambda date_value, days: f"{date_value}:{days}"
    frappe_utils.formatdate = lambda value, fmt=None: {"2026-03-23:-4": "03-19", "2026-03-23:4": "03-27"}.get(
        value,
        value,
    )
    frappe_utils.getdate = lambda value: value
    frappe_utils.now_datetime = lambda: "2026-03-23 08:00:00"
    frappe_utils.strip_html = lambda value: value
    frappe_utils.today = lambda: "2026-03-23"

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.api.org_comm_utils": org_comm_utils,
            "ifitwala_ed.api.org_communication_interactions": interactions,
            "ifitwala_ed.schedule.schedule_utils": schedule_utils,
            "ifitwala_ed.school_settings.school_settings_utils": school_settings_utils,
            "ifitwala_ed.students.doctype.student_log.student_log": student_log,
            "ifitwala_ed.utilities.image_utils": image_utils,
            "ifitwala_ed.utilities.school_tree": school_tree,
        }
    ) as frappe:
        yield import_fresh("ifitwala_ed.api.morning_brief"), frappe, image_helper_state


class TestMorningBriefUnit(TestCase):
    def test_get_recent_student_logs_requests_derivative_only_student_images(self):
        with _morning_brief_module() as (morning_brief, frappe, image_helper_state):
            morning_brief.get_student_log_visibility_predicate = lambda **kwargs: ("1=1", {})
            frappe.db.sql = lambda query, values=None, as_dict=False, **kwargs: [
                SimpleNamespace(
                    name="LOG-1",
                    student="STU-0001",
                    student_name="Amina Learner",
                    student_image="/private/files/student-source.png",
                    log_type="Behaviour",
                    date="2026-03-23",
                    requires_follow_up=1,
                    follow_up_status="Open",
                    log="Needs support",
                )
            ]

            rows = morning_brief.get_recent_student_logs("staff@example.com")

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            image_helper_state["calls"],
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

    def test_get_my_student_birthdays_requests_derivative_only_student_images(self):
        with _morning_brief_module() as (morning_brief, frappe, image_helper_state):
            captured = {}

            def fake_sql(query, values=None, as_dict=False, **kwargs):
                del kwargs
                captured["query"] = query
                captured["values"] = values
                captured["as_dict"] = as_dict
                return [
                    {
                        "student": "STU-0001",
                        "first_name": "Amina",
                        "last_name": "Learner",
                        "image": "/private/files/student-source.png",
                        "date_of_birth": "2014-03-23",
                    }
                ]

            frappe.db.sql = fake_sql

            rows = morning_brief.get_my_student_birthdays(["SG-1"])

        self.assertEqual(len(rows), 1)
        self.assertTrue(captured["as_dict"])
        self.assertEqual(captured["values"]["group_names"], ("SG-1",))
        self.assertEqual(
            image_helper_state["calls"],
            [
                {
                    "student_field": "student",
                    "image_field": "image",
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
