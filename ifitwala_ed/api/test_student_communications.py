from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _student_communications_module():
    org_comm_utils = ModuleType("ifitwala_ed.api.org_comm_utils")
    org_comm_utils.build_audience_summary = lambda comm_name: {}
    org_comm_utils.check_audience_match = lambda *args, **kwargs: True

    org_archive = ModuleType("ifitwala_ed.api.org_communication_archive")
    org_archive.get_audience_label = lambda comm_name: "Audience"

    org_interactions = ModuleType("ifitwala_ed.api.org_communication_interactions")
    org_interactions.get_seen_org_communication_names = lambda *, user, communication_names: set()

    school_tree = ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree.get_ancestor_schools = lambda school_name: [school_name] if school_name else []

    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.add_days = lambda value, days: "2026-01-10"
    frappe_utils.getdate = lambda value: value
    frappe_utils.now_datetime = lambda: "2026-04-10 10:00:00"
    frappe_utils.strip_html = lambda value: str(value or "").replace("<p>", "").replace("</p>", "")
    frappe_utils.today = lambda: "2026-04-10"

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.api.org_comm_utils": org_comm_utils,
            "ifitwala_ed.api.org_communication_archive": org_archive,
            "ifitwala_ed.api.org_communication_interactions": org_interactions,
            "ifitwala_ed.utilities.school_tree": school_tree,
        }
    ) as frappe:
        frappe.db.sql = lambda *args, **kwargs: []
        yield import_fresh("ifitwala_ed.api.student_communications")


class TestStudentCommunicationsApi(TestCase):
    def test_get_student_course_communication_summary_counts_unread_and_priority(self):
        with _student_communications_module() as module:
            items = [
                {
                    "kind": "org_communication",
                    "sort_at": "2026-04-10T09:00:00",
                    "org_communication": {"name": "COMM-1", "priority": "High"},
                },
                {
                    "kind": "org_communication",
                    "sort_at": "2026-04-09T09:00:00",
                    "org_communication": {"name": "COMM-2", "priority": "Normal"},
                },
            ]

            with (
                patch.object(module, "_resolve_student_context", return_value={"user": "student@example.com"}),
                patch.object(module, "_get_student_course_communication_items", return_value=items),
                patch.object(
                    module,
                    "get_seen_org_communication_names",
                    return_value={"COMM-2"},
                ),
            ):
                summary = module.get_student_course_communication_summary(
                    "STU-1",
                    course_id="COURSE-1",
                    student_group="GROUP-1",
                )

        self.assertEqual(
            summary,
            {
                "total_count": 2,
                "unread_count": 1,
                "high_priority_count": 1,
                "has_high_priority": 1,
                "latest_publish_at": "2026-04-10T09:00:00",
            },
        )

    def test_get_student_course_communication_drawer_includes_focused_item_and_unread_flags(self):
        with _student_communications_module() as module:
            items = [
                {
                    "kind": "org_communication",
                    "item_id": "org::COMM-1",
                    "sort_at": "2026-04-10T09:00:00",
                    "org_communication": {"name": "COMM-1", "priority": "Normal"},
                },
                {
                    "kind": "org_communication",
                    "item_id": "org::COMM-2",
                    "sort_at": "2026-04-09T09:00:00",
                    "org_communication": {"name": "COMM-2", "priority": "Critical"},
                },
            ]

            with (
                patch.object(module, "_resolve_student_context", return_value={"user": "student@example.com"}),
                patch.object(module, "_get_student_course_communication_items", return_value=items),
                patch.object(
                    module,
                    "get_seen_org_communication_names",
                    return_value={"COMM-1"},
                ),
            ):
                payload = module.get_student_course_communication_drawer(
                    course_id="COURSE-1",
                    student_group="GROUP-1",
                    focus_communication="COMM-2",
                    start=0,
                    page_length=1,
                )

        self.assertEqual(payload["summary"]["total_count"], 2)
        self.assertEqual(payload["summary"]["unread_count"], 1)
        self.assertEqual(payload["summary"]["high_priority_count"], 1)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["org_communication"]["name"], "COMM-2")
        self.assertTrue(payload["items"][0]["is_unread"])

    def test_fetch_student_school_events_does_not_query_missing_event_type_column(self):
        with _student_communications_module() as module:
            captured: dict[str, object] = {}

            def fake_sql(sql, values, as_dict=False):
                captured["sql"] = sql
                captured["values"] = values
                return [
                    {
                        "name": "SE-0001",
                        "subject": "Assembly",
                        "school": "SCH-1",
                        "location": "Hall",
                        "event_category": "Other",
                        "description": "<p>Bring your planner.</p>",
                        "starts_on": "2026-04-10 08:00:00",
                        "ends_on": "2026-04-10 09:00:00",
                        "all_day": 0,
                        "creation": "2026-04-09 12:00:00",
                    }
                ]

            with patch.object(module.frappe.db, "sql", side_effect=fake_sql):
                items = module._fetch_student_school_events(
                    {
                        "user": "student@example.com",
                        "group_names": {"SG-1"},
                    }
                )

        self.assertNotIn("se.event_type", str(captured.get("sql") or ""))
        self.assertEqual(
            captured.get("values"),
            {
                "recent_start": "2026-01-10",
                "user": "student@example.com",
                "event_student_groups": ("SG-1",),
            },
        )
        self.assertEqual(items[0]["school_event"]["subject"], "Assembly")
        self.assertEqual(items[0]["school_event"]["event_category"], "Other")
        self.assertIsNone(items[0]["school_event"]["event_type"])
