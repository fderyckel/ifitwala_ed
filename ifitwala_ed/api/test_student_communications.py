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
    def test_course_context_links_into_filtered_communication_center(self):
        with _student_communications_module() as module:
            item = module._resolve_org_comm_context(
                {"name": "COMM-1"},
                {
                    "group_map": {
                        "GROUP-1": {
                            "student_group_name": "Biology A",
                            "group_based_on": "Course",
                            "course": "COURSE-1",
                        }
                    }
                },
                "GROUP-1",
            )

        self.assertEqual(item["source_type"], "course")
        self.assertEqual(item["href"]["name"], "student-communications")
        self.assertEqual(
            item["href"]["query"],
            {
                "source": "course",
                "item": "org::COMM-1",
                "course_id": "COURSE-1",
                "student_group": "GROUP-1",
            },
        )
        self.assertEqual(item["href_label"], "Open class updates")

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

    def test_get_student_communication_center_course_scope_filters_to_requested_class(self):
        with _student_communications_module() as module:
            items = [
                {
                    "kind": "org_communication",
                    "item_id": "org::COMM-1",
                    "sort_at": "2026-04-10T09:00:00",
                    "source_type": "course",
                    "org_communication": {"name": "COMM-1", "priority": "Normal"},
                },
                {
                    "kind": "org_communication",
                    "item_id": "org::COMM-2",
                    "sort_at": "2026-04-09T09:00:00",
                    "source_type": "course",
                    "org_communication": {"name": "COMM-2", "priority": "Critical"},
                },
            ]

            with (
                patch.object(module, "_resolve_student_context", return_value={"user": "student@example.com"}),
                patch.object(module, "_get_student_course_communication_items", return_value=items),
                patch.object(module, "_fetch_student_org_communications", return_value=[]),
                patch.object(module, "_fetch_student_school_events", return_value=[]),
            ):
                payload = module.get_student_communication_center(
                    source="all",
                    course_id="COURSE-1",
                    student_group="GROUP-1",
                    item="org::COMM-2",
                    start=0,
                    page_length=1,
                )

        self.assertEqual(payload["meta"]["source"], "course")
        self.assertEqual(payload["meta"]["course_id"], "COURSE-1")
        self.assertEqual(payload["meta"]["student_group"], "GROUP-1")
        self.assertEqual(payload["meta"]["item"], "org::COMM-2")
        self.assertEqual(payload["summary"]["source_counts"], {"course": 2})
        self.assertEqual(payload["total_count"], 2)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["item_id"], "org::COMM-2")

    def test_fetch_student_org_communications_limits_to_feed_surfaces(self):
        with _student_communications_module() as module:
            captured: dict[str, object] = {}

            def fake_sql(sql, values, as_dict=False):
                captured["sql"] = sql
                captured["values"] = values
                return [
                    {
                        "name": "COMM-1",
                        "title": "Class update",
                        "message": "<p>Bring your calculator.</p>",
                        "communication_type": "Information",
                        "status": "Published",
                        "priority": "Normal",
                        "portal_surface": "Portal Feed",
                        "school": "SCH-1",
                        "organization": "ORG-1",
                        "publish_from": "2026-04-10 09:00:00",
                        "publish_to": None,
                        "brief_start_date": None,
                        "brief_end_date": None,
                        "interaction_mode": "Student Q&A",
                        "allow_private_notes": 0,
                        "allow_public_thread": 1,
                        "activity_program_offering": None,
                        "activity_booking": None,
                        "activity_student_group": None,
                        "creation": "2026-04-10 08:00:00",
                    }
                ]

            with (
                patch.object(module.frappe.db, "sql", side_effect=fake_sql),
                patch.object(module, "_fetch_matching_student_group_rows", return_value={"COMM-1": "SG-1"}),
            ):
                items = module._fetch_student_org_communications(
                    {
                        "user": "student@example.com",
                        "roles": {"Student"},
                        "group_names": {"SG-1"},
                        "eligible_school_targets": {"SCH-1"},
                        "audience_scope": {"student_name": "STU-1"},
                        "group_map": {
                            "SG-1": {
                                "student_group_name": "Biology A",
                                "group_based_on": "Course",
                                "course": "COURSE-1",
                            }
                        },
                    }
                )

        self.assertIn(
            "IFNULL(oc.portal_surface, 'Everywhere') IN ('Everywhere', 'Portal Feed')",
            str(captured.get("sql") or ""),
        )
        self.assertEqual(items[0]["org_communication"]["portal_surface"], "Portal Feed")

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
