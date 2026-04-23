# ifitwala_ed/api/test_guardian_home.py

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.guardian_home import (
    _assert_no_internal_schedule_keys,
    _build_communication_bundle,
    _build_preparation_items,
    _find_forbidden_keys,
    _resolve_chip_status,
    _resolve_guardian_scope,
    get_guardian_home_snapshot,
    get_guardian_student_learning_brief,
)


class TestGuardianHome(FrappeTestCase):
    def test_resolve_guardian_scope_requests_derivative_only_student_images(self):
        captured_calls = []

        def fake_get_all(doctype, filters=None, fields=None, order_by=None):
            if doctype == "Student Guardian":
                return [{"parent": "STU-0001"}]
            if doctype == "Guardian Student":
                return []
            if doctype == "Student":
                self.assertEqual(filters, {"name": ["in", ["STU-0001"]], "enabled": 1})
                self.assertEqual(fields, ["name", "student_full_name", "anchor_school", "student_image"])
                self.assertEqual(order_by, "student_full_name asc, name asc")
                return [
                    {
                        "name": "STU-0001",
                        "student_full_name": "Amina Example",
                        "anchor_school": "SCH-0001",
                        "student_image": "/private/files/student-source.png",
                    }
                ]
            self.fail(f"Unexpected get_all call: {doctype}")

        with (
            patch("ifitwala_ed.api.guardian_home.frappe.db.get_value", return_value="GRD-0001"),
            patch("ifitwala_ed.api.guardian_home.frappe.get_all", side_effect=fake_get_all),
            patch(
                "ifitwala_ed.api.guardian_home.apply_preferred_student_images",
                side_effect=lambda rows, **kwargs: captured_calls.append(kwargs) or rows,
            ),
        ):
            guardian_name, children = _resolve_guardian_scope("guardian@example.com")

        self.assertEqual(guardian_name, "GRD-0001")
        self.assertEqual(
            children,
            [
                {
                    "student": "STU-0001",
                    "full_name": "Amina Example",
                    "school": "SCH-0001",
                    "student_image_url": "/private/files/student-source.png",
                }
            ],
        )
        self.assertEqual(
            captured_calls,
            [
                {
                    "student_field": "name",
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

    def test_snapshot_returns_empty_structure_when_guardian_has_no_linked_children(self):
        with (
            patch("ifitwala_ed.api.guardian_home.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_home.now_datetime",
                return_value=frappe.utils.get_datetime("2026-02-02 08:00:00"),
            ),
            patch("ifitwala_ed.api.guardian_home._resolve_guardian_scope", return_value=("GRD-0001", [])),
            patch("ifitwala_ed.api.guardian_home._get_student_group_membership") as membership_mock,
        ):
            payload = get_guardian_home_snapshot(anchor_date="2026-02-02", school_days=7)

        self.assertEqual(payload["meta"]["guardian"]["name"], "GRD-0001")
        self.assertEqual(payload["family"]["children"], [])
        self.assertEqual(payload["policies"], {"pending_count": 0, "items": []})
        self.assertEqual(payload["zones"]["family_timeline"], [])
        self.assertEqual(payload["zones"]["attention_needed"], [])
        self.assertEqual(payload["zones"]["preparation_and_support"], [])
        self.assertEqual(payload["zones"]["recent_activity"], [])
        self.assertEqual(payload["zones"]["learning_highlights"], [])
        self.assertEqual(
            payload["counts"],
            {
                "unread_communications": 0,
                "unread_visible_student_logs": 0,
                "upcoming_due_tasks": 0,
                "upcoming_assessments": 0,
            },
        )
        membership_mock.assert_not_called()

    def test_snapshot_assembles_phase1_sections_from_helper_bundles(self):
        children = [
            {
                "student": "STU-0001",
                "full_name": "Amina Example",
                "school": "SCHOOL-1",
                "student_image_url": None,
            }
        ]
        membership = {"STU-0001": {"GRP-1"}}
        group_context = {
            "GRP-1": {
                "name": "GRP-1",
                "student_group_name": "Group 1",
                "school_schedule": "SCHED-1",
                "academic_year": "AY-2026",
                "course": "COURSE-1",
            }
        }
        task_bundle = {
            "chips_by_student_date": {},
            "upcoming_due_count": 2,
            "upcoming_assessments_count": 1,
            "recent_task_results": [
                {
                    "type": "task_result",
                    "student": "STU-0001",
                    "task_outcome": "OUT-1",
                    "title": "Published task",
                    "published_on": "2026-02-01T12:00:00",
                }
            ],
        }
        family_timeline = [
            {
                "date": "2026-02-02",
                "label": "Mon 02 Feb",
                "is_school_day": True,
                "children": [
                    {
                        "student": "STU-0001",
                        "day_summary": {"start_time": "08:00", "end_time": "14:00", "note": None},
                        "blocks": [{"start_time": "08:00", "end_time": "09:00", "title": "Math", "kind": "course"}],
                        "tasks_due": [],
                        "assessments_upcoming": [],
                    }
                ],
            }
        ]
        log_bundle = {
            "attention_items": [
                {
                    "type": "student_log",
                    "student": "STU-0001",
                    "student_log": "LOG-1",
                    "date": "2026-02-02",
                    "summary": "Needs a follow-up",
                }
            ],
            "recent_activity_items": [
                {
                    "type": "student_log",
                    "student": "STU-0001",
                    "student_log": "LOG-1",
                    "date": "2026-02-02",
                    "summary": "Needs a follow-up",
                }
            ],
            "unread_count": 1,
        }
        attendance_attention = [
            {"type": "attendance", "student": "STU-0001", "date": "2026-02-02", "summary": "Absent"}
        ]
        communication_bundle = {
            "attention_items": [
                {
                    "type": "communication",
                    "communication": "COMM-1",
                    "date": "2026-02-01",
                    "title": "School message",
                    "is_unread": True,
                }
            ],
            "recent_activity_items": [
                {
                    "type": "communication",
                    "communication": "COMM-1",
                    "date": "2026-02-01",
                    "title": "School message",
                    "is_unread": True,
                }
            ],
            "unread_count": 3,
        }
        prep_items = [
            {"student": "STU-0001", "date": "2026-02-02", "label": "Prepare for: Math quiz", "source": "task"}
        ]
        recent_activity = [
            {"type": "communication", "communication": "COMM-1", "date": "2026-02-01", "title": "School message"}
        ]
        learning_highlights = [
            {
                "student": "STU-0001",
                "student_name": "Amina Example",
                "course": "COURSE-1",
                "course_name": "Biology",
                "unit_title": "Cells and Systems",
            }
        ]

        with (
            patch("ifitwala_ed.api.guardian_home.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_home.now_datetime",
                return_value=frappe.utils.get_datetime("2026-02-02 08:00:00"),
            ),
            patch("ifitwala_ed.api.guardian_home._resolve_guardian_scope", return_value=("GRD-0001", children)),
            patch(
                "ifitwala_ed.api.guardian_policy.get_guardian_policy_home_summary",
                return_value={"pending_count": 2, "items": [{"policy_version": "VER-1"}]},
            ),
            patch("ifitwala_ed.api.guardian_home._get_student_group_membership", return_value=membership),
            patch("ifitwala_ed.api.guardian_home._get_student_group_context", return_value=group_context),
            patch("ifitwala_ed.api.guardian_home._build_task_bundle", return_value=task_bundle),
            patch("ifitwala_ed.api.guardian_home._build_family_timeline", return_value=family_timeline),
            patch("ifitwala_ed.api.guardian_home._build_student_log_bundle", return_value=log_bundle),
            patch("ifitwala_ed.api.guardian_home._build_attendance_attention", return_value=attendance_attention),
            patch("ifitwala_ed.api.guardian_home._build_communication_bundle", return_value=communication_bundle),
            patch("ifitwala_ed.api.guardian_home._build_preparation_items", return_value=prep_items),
            patch("ifitwala_ed.api.guardian_home._build_recent_activity", return_value=recent_activity),
            patch("ifitwala_ed.api.guardian_home._build_learning_highlights", return_value=learning_highlights),
            patch("ifitwala_ed.api.guardian_home._assert_no_internal_schedule_keys") as leakage_mock,
        ):
            payload = get_guardian_home_snapshot(anchor_date="2026-02-02", school_days=7)

        self.assertEqual(payload["meta"]["guardian"]["name"], "GRD-0001")
        self.assertEqual(payload["family"]["children"], children)
        self.assertEqual(payload["policies"]["pending_count"], 2)
        self.assertEqual(payload["zones"]["family_timeline"], family_timeline)
        self.assertEqual(payload["zones"]["preparation_and_support"], prep_items)
        self.assertEqual(payload["zones"]["recent_activity"], recent_activity)
        self.assertEqual(payload["zones"]["learning_highlights"], learning_highlights)
        self.assertEqual(payload["counts"]["unread_communications"], 3)
        self.assertEqual(payload["counts"]["unread_visible_student_logs"], 1)
        self.assertEqual(payload["counts"]["upcoming_due_tasks"], 2)
        self.assertEqual(payload["counts"]["upcoming_assessments"], 1)
        attention_types = [item["type"] for item in payload["zones"]["attention_needed"]]
        self.assertEqual(len(attention_types), 3)
        self.assertEqual(attention_types[-1], "communication")
        self.assertCountEqual(attention_types[:2], ["student_log", "attendance"])
        leakage_mock.assert_called_once()

    def test_build_communication_bundle_includes_organization_guardian_rows(self):
        children = [
            {
                "student": "STU-0001",
                "full_name": "Amina Example",
                "school": "SCHOOL-CHILD",
                "student_image_url": None,
            }
        ]
        membership = {"STU-0001": set()}

        with (
            patch.object(
                frappe.db,
                "sql",
                return_value=[
                    {
                        "name": "COMM-ORG",
                        "title": "Health advisory",
                        "organization": "ORG-ROOT",
                        "publish_from": frappe.utils.get_datetime("2026-02-01 08:00:00"),
                        "publish_to": None,
                        "creation": frappe.utils.get_datetime("2026-02-01 07:00:00"),
                        "activity_program_offering": None,
                        "activity_booking": None,
                        "activity_student_group": None,
                    }
                ],
            ),
            patch.object(
                frappe,
                "get_all",
                return_value=[
                    {
                        "parent": "COMM-ORG",
                        "target_mode": "Organization",
                        "school": None,
                        "student_group": None,
                        "include_descendants": 0,
                        "to_guardians": 1,
                    }
                ],
            ),
            patch("ifitwala_ed.api.guardian_home.get_seen_org_communication_names", return_value=[]),
            patch(
                "ifitwala_ed.api.guardian_home.get_school_organization_map",
                return_value={"SCHOOL-CHILD": "ORG-CHILD"},
            ),
            patch("ifitwala_ed.api.guardian_home.get_ancestor_organizations", return_value=["ORG-ROOT"]),
        ):
            bundle = _build_communication_bundle(
                anchor=date(2026, 2, 2),
                user="guardian@example.com",
                children=children,
                membership=membership,
            )

        self.assertEqual(bundle["unread_count"], 1)
        self.assertEqual(bundle["attention_items"][0]["communication"], "COMM-ORG")
        self.assertEqual(bundle["recent_activity_items"][0]["communication"], "COMM-ORG")

    def test_resolve_chip_status_respects_availability_and_lock_window(self):
        anchor = date(2026, 2, 2)

        self.assertEqual(
            _resolve_chip_status(
                outcome=None,
                due=date(2026, 2, 5),
                anchor=anchor,
                available_from=date(2026, 2, 4),
                lock_date=None,
            ),
            "assigned",
        )
        self.assertEqual(
            _resolve_chip_status(
                outcome=None,
                due=date(2026, 2, 1),
                anchor=anchor,
                available_from=None,
                lock_date=date(2026, 2, 4),
            ),
            "assigned",
        )
        self.assertEqual(
            _resolve_chip_status(
                outcome=None,
                due=date(2026, 2, 1),
                anchor=anchor,
                available_from=None,
                lock_date=date(2026, 2, 1),
            ),
            "missing",
        )

    def test_build_preparation_items_builds_low_noise_forward_looking_rows(self):
        family_timeline = [
            {
                "date": "2026-02-02",
                "children": [
                    {
                        "student": "STU-0001",
                        "assessments_upcoming": [{"title": "Math quiz", "task_delivery": "DEL-QUIZ"}],
                        "tasks_due": [{"title": "Reading journal", "task_delivery": "DEL-TASK"}],
                        "blocks": [
                            {
                                "kind": "activity",
                                "title": "Science fair",
                                "start_time": "10:00",
                                "end_time": "11:00",
                            },
                            {
                                "kind": "course",
                                "title": "Math",
                                "start_time": "08:00",
                                "end_time": "09:00",
                            },
                        ],
                    }
                ],
            }
        ]

        items = _build_preparation_items(
            family_timeline=family_timeline,
            communication_bundle={"attention_items": []},
        )

        self.assertEqual(
            items,
            [
                {
                    "student": "STU-0001",
                    "date": "2026-02-02",
                    "label": "Due soon: Reading journal",
                    "source": "task",
                    "related": {"task_delivery": "DEL-TASK"},
                },
                {
                    "student": "STU-0001",
                    "date": "2026-02-02",
                    "label": "Prepare for: Math quiz",
                    "source": "task",
                    "related": {"task_delivery": "DEL-QUIZ"},
                },
                {
                    "student": "STU-0001",
                    "date": "2026-02-02",
                    "label": "Science fair",
                    "source": "schedule",
                    "related": {"schedule_hint": {"start_time": "10:00", "end_time": "11:00"}},
                },
            ],
        )

    def test_forbidden_key_detection_finds_rotation_and_block(self):
        payload = {
            "zones": {
                "family_timeline": [
                    {
                        "children": [
                            {
                                "rotation_day": 1,
                                "blocks": [{"title": "Class", "block_number": 2}],
                            }
                        ]
                    }
                ]
            }
        }
        found = _find_forbidden_keys(payload)
        self.assertTrue(any(path.endswith(".rotation_day") for path in found))
        self.assertTrue(any(path.endswith(".block_number") for path in found))

    def test_assert_no_internal_schedule_keys_throws_in_debug(self):
        payload = {"zones": {"family_timeline": [{"rotation_day": 1}]}}
        warnings: list[str] = []

        with self.assertRaises(frappe.ValidationError):
            _assert_no_internal_schedule_keys(payload=payload, debug_mode=True, debug_warnings=warnings)

        self.assertEqual(warnings, [])

    def test_assert_no_internal_schedule_keys_warns_when_not_debug(self):
        payload = {"zones": {"family_timeline": [{"block_number": 2}]}}
        warnings: list[str] = []

        _assert_no_internal_schedule_keys(payload=payload, debug_mode=False, debug_warnings=warnings)
        self.assertEqual(len(warnings), 1)
        self.assertIn("guardian_home_forbidden_keys_detected", warnings[0])

    def test_guardian_student_learning_brief_rejects_non_linked_student(self):
        with patch(
            "ifitwala_ed.api.guardian_home._resolve_guardian_scope",
            return_value=(
                "GRD-0001",
                [{"student": "STU-0001", "full_name": "Amina Example", "school": "School One"}],
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                get_guardian_student_learning_brief("STU-9999")

    def test_guardian_student_learning_brief_serializes_course_briefs(self):
        child = {"student": "STU-0001", "full_name": "Amina Example", "school": "School One"}
        course_briefs = [{"course": "COURSE-1", "course_name": "Biology"}]

        with (
            patch("ifitwala_ed.api.guardian_home.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_home._resolve_guardian_scope",
                return_value=("GRD-0001", [child]),
            ),
            patch(
                "ifitwala_ed.api.guardian_home._build_guardian_student_course_briefs",
                return_value=course_briefs,
            ),
            patch(
                "ifitwala_ed.api.guardian_home.now_datetime",
                return_value=frappe.utils.get_datetime("2026-02-02 08:00:00"),
            ),
        ):
            payload = get_guardian_student_learning_brief("STU-0001")

        self.assertEqual(payload["meta"]["guardian"]["name"], "GRD-0001")
        self.assertEqual(payload["student"]["student"], "STU-0001")
        self.assertEqual(payload["course_briefs"], course_briefs)
