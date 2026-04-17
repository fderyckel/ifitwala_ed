# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/test_student_overview_dashboard.py

from unittest.mock import patch

import frappe

from ifitwala_ed.api.student_overview_dashboard import (
    _attendance_block,
    _ensure_student_overview_access,
    _history_block,
    _identity_block,
    _students_for_guardian,
    _task_rows,
    _wellbeing_block,
    get_filter_meta,
    get_student_center_snapshot,
    search_students,
)
from ifitwala_ed.tests.base import IfitwalaFrappeTestCase


class TestStudentOverviewDashboard(IfitwalaFrappeTestCase):
    def test_ensure_student_overview_access_rejects_academic_assistant(self):
        with (
            patch("ifitwala_ed.api.student_overview_dashboard._current_user", return_value="assistant@example.com"),
            patch("ifitwala_ed.api.student_overview_dashboard._user_roles", return_value={"Academic Assistant"}),
            patch("ifitwala_ed.api.student_overview_dashboard._get_student_scope", return_value=[]),
        ):
            with self.assertRaises(frappe.PermissionError):
                _ensure_student_overview_access()

    def test_students_for_guardian_uses_single_join_query(self):
        seen_query = None

        def fake_sql(query, params=None, as_list=False, as_dict=False):
            nonlocal seen_query
            seen_query = query
            self.assertEqual(params, {"user": "guardian@example.com"})
            self.assertTrue(as_list)
            self.assertFalse(as_dict)
            return [("STU-001",), ("STU-002",)]

        with patch("ifitwala_ed.api.student_overview_dashboard.frappe.db.sql", side_effect=fake_sql):
            students = _students_for_guardian("guardian@example.com")

        self.assertEqual(students, ["STU-001", "STU-002"])
        self.assertIn("SELECT DISTINCT sg.parent", seen_query)
        self.assertIn("INNER JOIN `tabGuardian` g", seen_query)

    def test_identity_block_uses_preferred_student_photo(self):
        def fake_get_value(doctype, name_or_filters, fieldname, as_dict=False, order_by=None):
            if doctype == "Student":
                self.assertEqual(name_or_filters, "STU-001")
                self.assertEqual(
                    fieldname,
                    [
                        "name",
                        "student_full_name",
                        "student_image",
                        "cohort",
                        "student_gender",
                        "student_date_of_birth",
                        "anchor_school",
                    ],
                )
                self.assertTrue(as_dict)
                return frappe._dict(
                    {
                        "name": "STU-001",
                        "student_full_name": "Amina Example",
                        "student_image": "/private/files/original-student.png",
                        "cohort": "G6",
                        "student_gender": "Female",
                        "student_date_of_birth": "2014-03-02",
                        "anchor_school": "SCH-001",
                    }
                )

            if doctype == "School":
                self.assertEqual(name_or_filters, "SCH-001")
                self.assertEqual(fieldname, "school_name")
                return "School One"

            self.fail(f"Unexpected get_value doctype: {doctype}")

        def fake_get_all(doctype, **kwargs):
            if doctype == "Program Enrollment":
                self.assertEqual(kwargs.get("filters"), {"student": "STU-001"})
                self.assertEqual(kwargs.get("order_by"), "enrollment_date desc")
                self.assertEqual(kwargs.get("limit"), 1)
                return []

            self.fail(f"Unexpected get_all doctype: {doctype}")

        with (
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.db.sql", return_value=[]),
            patch(
                "ifitwala_ed.api.student_overview_dashboard.get_preferred_student_image_url",
                return_value="/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1&context_doctype=Student&context_name=STU-001",
            ) as image_url_mock,
        ):
            payload = _identity_block("STU-001", None, None)

        image_url_mock.assert_called_once_with("STU-001", original_url="/private/files/original-student.png")
        self.assertEqual(
            payload["photo"],
            "/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1&context_doctype=Student&context_name=STU-001",
        )

    def test_identity_block_matches_program_enrollment_on_program_subtree(self):
        def fake_get_value(doctype, name_or_filters, fieldname, as_dict=False, order_by=None):
            if doctype == "Program":
                self.assertEqual(name_or_filters, "PROG-ROOT")
                self.assertEqual(fieldname, ["lft", "rgt"])
                return (10, 20)

            if doctype == "Student":
                return frappe._dict(
                    {
                        "name": "STU-001",
                        "student_full_name": "Amina Example",
                        "student_image": None,
                        "cohort": "G6",
                        "student_gender": "Female",
                        "student_date_of_birth": "2014-03-02",
                        "anchor_school": "SCH-001",
                    }
                )

            if doctype == "School":
                self.assertEqual(name_or_filters, "SCH-001")
                return "School One"

            self.fail(f"Unexpected get_value doctype: {doctype}")

        def fake_get_all(doctype, **kwargs):
            if doctype == "Program":
                self.assertEqual(kwargs.get("filters"), {"lft": (">=", 10), "rgt": ("<=", 20)})
                self.assertEqual(kwargs.get("pluck"), "name")
                return ["PROG-ROOT", "PROG-CHILD"]

            if doctype == "Program Enrollment":
                self.assertEqual(
                    kwargs.get("filters"),
                    {
                        "student": "STU-001",
                        "program": ["in", ["PROG-ROOT", "PROG-CHILD"]],
                        "school": ["in", ["SCH-001", "SCH-CHILD"]],
                    },
                )
                self.assertEqual(kwargs.get("limit"), 1)
                return [
                    frappe._dict(
                        {
                            "name": "PE-001",
                            "program": "PROG-CHILD",
                            "program_offering": "PO-001",
                            "academic_year": "2025-2026",
                            "enrollment_date": "2025-08-15",
                            "archived": 0,
                            "school": "SCH-001",
                        }
                    )
                ]

            self.fail(f"Unexpected get_all doctype: {doctype}")

        with (
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.db.sql", return_value=[]),
            patch("ifitwala_ed.api.student_overview_dashboard.get_preferred_student_image_url", return_value=None),
            patch(
                "ifitwala_ed.api.student_overview_dashboard.get_descendant_schools",
                return_value=["SCH-001", "SCH-CHILD"],
            ),
        ):
            payload = _identity_block("STU-001", "PROG-ROOT", "SCH-001")

        self.assertEqual(payload["program_enrollment"]["program"], "PROG-CHILD")
        self.assertEqual(payload["program_enrollment"]["academic_year"], "2025-2026")

    def test_wellbeing_block_merges_logs_referrals_visits_and_health_note(self):
        logs = [
            frappe._dict(
                name="LOG-001",
                date="2026-03-02",
                academic_year="2025-2026",
                log_type="Positive Attitude",
                log="<p>Encouraging progress</p>",
                follow_up_status="Open",
                requires_follow_up=1,
            )
        ]
        referrals = [
            frappe._dict(
                name="SRF-001",
                date="2026-03-03",
                academic_year="2025-2026",
                referral_category="Pastoral",
                referral_source="Staff",
                referral_description="<p>Needs counselor check-in</p>",
            )
        ]
        nurse_visits = [
            frappe._dict(
                name="PAV-001",
                date="2026-03-04",
                note="<p>Rested for 20 minutes before class</p>",
            )
        ]
        health_note = {
            "doctype": "Student Patient",
            "name": "PATIENT-001",
            "title": "Health note to staff",
            "summary": "Carry inhaler during PE.",
            "updated_on": "2026-03-01 08:00:00",
            "is_sensitive": True,
        }

        with (
            patch("ifitwala_ed.api.student_overview_dashboard._get_visible_student_logs", return_value=logs),
            patch(
                "ifitwala_ed.api.student_overview_dashboard._visible_student_log_support_counts",
                return_value=(4, 2),
            ),
            patch("ifitwala_ed.api.student_overview_dashboard._get_visible_student_referrals", return_value=referrals),
            patch(
                "ifitwala_ed.api.student_overview_dashboard._visible_student_referral_counts",
                return_value=(3, 3),
            ),
            patch(
                "ifitwala_ed.api.student_overview_dashboard._get_visible_student_nurse_visits",
                return_value=nurse_visits,
            ),
            patch("ifitwala_ed.api.student_overview_dashboard._visible_student_nurse_visit_count", return_value=5),
            patch("ifitwala_ed.api.student_overview_dashboard._get_student_health_note", return_value=health_note),
        ):
            payload = _wellbeing_block("STU-001", "2025-2026")

        self.assertEqual(payload["health_note"], health_note)
        self.assertEqual(
            [row["type"] for row in payload["timeline"]],
            ["nurse_visit", "referral", "student_log"],
        )
        self.assertEqual(payload["timeline"][0]["summary"], "Rested for 20 minutes before class")
        self.assertEqual(payload["timeline"][1]["summary"], "Needs counselor check-in")
        self.assertEqual(payload["timeline"][2]["summary"], "Encouraging progress")
        self.assertEqual(payload["metrics"]["student_logs"]["open_followups"], 2)
        self.assertEqual(payload["metrics"]["referrals"]["active"], 3)
        self.assertEqual(payload["metrics"]["nurse_visits"]["this_term"], 5)

    def test_wellbeing_block_preserves_full_timeline_summary_text(self):
        long_log = (
            '<p>Theo was observed attempting a "Silly Walk" in the main hallway between Period 2 and 3. '
            "While his technique was high-quality, it caused a serious traffic slowdown and required a "
            "follow-up conversation about timing, safety, and audience selection.</p>"
        )

        with (
            patch(
                "ifitwala_ed.api.student_overview_dashboard._get_visible_student_logs",
                return_value=[
                    frappe._dict(
                        name="LOG-001",
                        date="2026-03-02",
                        academic_year="2025-2026",
                        log_type="Behaviour",
                        log=long_log,
                        follow_up_status="Open",
                        requires_follow_up=1,
                    )
                ],
            ),
            patch(
                "ifitwala_ed.api.student_overview_dashboard._visible_student_log_support_counts",
                return_value=(1, 1),
            ),
            patch("ifitwala_ed.api.student_overview_dashboard._get_visible_student_referrals", return_value=[]),
            patch(
                "ifitwala_ed.api.student_overview_dashboard._visible_student_referral_counts",
                return_value=(0, 0),
            ),
            patch("ifitwala_ed.api.student_overview_dashboard._get_visible_student_nurse_visits", return_value=[]),
            patch("ifitwala_ed.api.student_overview_dashboard._visible_student_nurse_visit_count", return_value=0),
            patch("ifitwala_ed.api.student_overview_dashboard._get_student_health_note", return_value=None),
        ):
            payload = _wellbeing_block("STU-001", "2025-2026")

        self.assertEqual(
            payload["timeline"][0]["summary"],
            (
                'Theo was observed attempting a "Silly Walk" in the main hallway between Period 2 and 3. '
                "While his technique was high-quality, it caused a serious traffic slowdown and required a "
                "follow-up conversation about timing, safety, and audience selection."
            ),
        )

    def test_attendance_block_counts_excused_unexcused_and_late_correctly(self):
        def fake_get_all(doctype, **kwargs):
            if doctype == "Student Attendance Code":
                filters = kwargs.get("filters") or {}
                if filters == {"show_in_reports": 1}:
                    return [
                        frappe._dict(value="P", label="Present", count_as_present=1, color="#22c55e"),
                        frappe._dict(value="L", label="Late", count_as_present=1, color="#f59e0b"),
                        frappe._dict(value="IA", label="Informed Absence", count_as_present=0, color="#94a3b8"),
                        frappe._dict(value="A", label="Absent", count_as_present=0, color="#ef4444"),
                    ]

                return [
                    frappe._dict(
                        name="P",
                        attendance_code="P",
                        attendance_code_name="Present",
                        count_as_present=1,
                        color="#22c55e",
                    ),
                    frappe._dict(
                        name="L", attendance_code="L", attendance_code_name="Late", count_as_present=1, color="#f59e0b"
                    ),
                    frappe._dict(
                        name="IA",
                        attendance_code="IA",
                        attendance_code_name="Informed Absence",
                        count_as_present=0,
                        color="#94a3b8",
                    ),
                    frappe._dict(
                        name="A",
                        attendance_code="A",
                        attendance_code_name="Absent",
                        count_as_present=0,
                        color="#ef4444",
                    ),
                ]

            if doctype == "Student Attendance":
                self.assertEqual(kwargs.get("filters"), {"student": "STU-001", "academic_year": "2025-2026"})
                return [
                    frappe._dict(
                        attendance_date="2026-01-10",
                        attendance_code="P",
                        course=None,
                        academic_year="2025-2026",
                        whole_day=1,
                    ),
                    frappe._dict(
                        attendance_date="2026-01-11",
                        attendance_code="IA",
                        course=None,
                        academic_year="2025-2026",
                        whole_day=1,
                    ),
                    frappe._dict(
                        attendance_date="2026-01-12",
                        attendance_code="L",
                        course=None,
                        academic_year="2025-2026",
                        whole_day=1,
                    ),
                    frappe._dict(
                        attendance_date="2026-01-13",
                        attendance_code="A",
                        course=None,
                        academic_year="2025-2026",
                        whole_day=1,
                    ),
                ]

            self.fail(f"Unexpected get_all doctype: {doctype}")

        with patch("ifitwala_ed.api.student_overview_dashboard.frappe.get_all", side_effect=fake_get_all):
            payload = _attendance_block("STU-001", "2025-2026")

        self.assertEqual(
            payload["summary"],
            {
                "present_percentage": 0.5,
                "total_days": 4,
                "present_days": 2,
                "excused_absences": 1,
                "unexcused_absences": 1,
                "late_count": 1,
                "most_impacted_course": None,
            },
        )

    def test_history_block_uses_distinct_flag_for_attendance_years(self):
        def fake_get_all(doctype, **kwargs):
            if doctype == "Program Enrollment":
                self.assertEqual(kwargs.get("filters"), {"student": "STU-001"})
                self.assertEqual(kwargs.get("fields"), ["academic_year"])
                self.assertTrue(kwargs.get("distinct"))
                return [
                    frappe._dict(academic_year="2025-2026"),
                    frappe._dict(academic_year="2024-2025"),
                ]

            if doctype == "Student Attendance":
                self.assertEqual(kwargs.get("filters"), {"student": "STU-001"})
                self.assertEqual(kwargs.get("fields"), ["academic_year"])
                self.assertTrue(kwargs.get("distinct"))
                self.assertEqual(kwargs.get("order_by"), "academic_year desc")
                return [
                    frappe._dict(academic_year="2025-2026"),
                    frappe._dict(academic_year="2024-2025"),
                ]

            self.fail(f"Unexpected get_all doctype: {doctype}")

        def fake_attendance_block(student, academic_year):
            summaries = {
                "2025-2026": {"present_percentage": 0.95, "unexcused_absences": 1},
                "2024-2025": {"present_percentage": 0.88, "unexcused_absences": 3},
            }
            self.assertEqual(student, "STU-001")
            return {"summary": summaries[academic_year]}

        task_rows = [
            frappe._dict(academic_year="2025-2026", status="Graded", complete=1),
            frappe._dict(academic_year="2025-2026", status="Assigned", complete=0),
            frappe._dict(academic_year="2024-2025", status="Returned", complete=1),
        ]

        with (
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.api.student_overview_dashboard._task_rows", return_value=task_rows),
            patch("ifitwala_ed.api.student_overview_dashboard._attendance_block", side_effect=fake_attendance_block),
        ):
            payload = _history_block("STU-001", "PROG-001")

        self.assertEqual(
            payload.get("year_options"),
            [
                {"key": "current", "label": "This year", "academic_year": "2025-2026"},
                {"key": "previous", "label": "Last year", "academic_year": "2024-2025"},
                {
                    "key": "all",
                    "label": "All years",
                    "academic_years": ["2025-2026", "2024-2025"],
                },
            ],
        )
        self.assertEqual(
            payload.get("attendance_trend"),
            [
                {
                    "academic_year": "2024-2025",
                    "label": "2024-2025",
                    "present_percentage": 0.88,
                    "unexcused_absences": 3,
                },
                {
                    "academic_year": "2025-2026",
                    "label": "2025-2026",
                    "present_percentage": 0.95,
                    "unexcused_absences": 1,
                },
            ],
        )

    def test_task_rows_returns_empty_when_legacy_task_source_is_unavailable(self):
        sql_called = False

        def fake_sql(*args, **kwargs):
            nonlocal sql_called
            sql_called = True
            return []

        def fake_table_exists(doctype):
            self.assertEqual(doctype, "Task Student")
            return False

        with (
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.db.table_exists", side_effect=fake_table_exists),
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.db.sql", side_effect=fake_sql),
        ):
            rows = _task_rows("STU-001", "PROG-001")

        self.assertEqual(rows, [])
        self.assertFalse(sql_called)

    def test_get_filter_meta_student_scope_uses_distinct_flag(self):
        def fake_get_all(doctype, **kwargs):
            if doctype == "Program Enrollment":
                self.assertEqual(
                    kwargs.get("filters"),
                    {"student": ["in", ["STU-001"]], "archived": 0},
                )
                self.assertEqual(kwargs.get("fields"), ["school", "program"])
                self.assertTrue(kwargs.get("distinct"))
                return [
                    frappe._dict(school="SCH-001", program="PROG-001"),
                    frappe._dict(school="SCH-001", program="PROG-001"),
                    frappe._dict(school="SCH-002", program="PROG-002"),
                ]

            if doctype == "School":
                self.assertEqual(kwargs.get("order_by"), "lft")
                return [
                    frappe._dict(name="SCH-001", label="School One"),
                    frappe._dict(name="SCH-002", label="School Two"),
                ]

            if doctype == "Program":
                self.assertEqual(kwargs.get("order_by"), "program_name")
                return [
                    frappe._dict(name="PROG-001", label="Program One"),
                    frappe._dict(name="PROG-002", label="Program Two"),
                ]

            self.fail(f"Unexpected get_all doctype: {doctype}")

        with (
            patch("ifitwala_ed.api.student_overview_dashboard._current_user", return_value="student@example.com"),
            patch("ifitwala_ed.api.student_overview_dashboard._user_roles", return_value={"Student"}),
            patch("ifitwala_ed.api.student_overview_dashboard._get_student_scope", return_value=["STU-001"]),
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.get_all", side_effect=fake_get_all),
        ):
            payload = get_filter_meta()

        self.assertEqual(payload.get("default_school"), "SCH-001")
        self.assertEqual(
            payload.get("schools"),
            [
                frappe._dict(name="SCH-001", label="School One"),
                frappe._dict(name="SCH-002", label="School Two"),
            ],
        )
        self.assertEqual(
            payload.get("programs"),
            [
                frappe._dict(name="PROG-001", label="Program One"),
                frappe._dict(name="PROG-002", label="Program Two"),
            ],
        )

    def test_get_filter_meta_rejects_user_without_student_overview_access(self):
        with (
            patch("ifitwala_ed.api.student_overview_dashboard._current_user", return_value="assistant@example.com"),
            patch("ifitwala_ed.api.student_overview_dashboard._user_roles", return_value={"Academic Assistant"}),
            patch("ifitwala_ed.api.student_overview_dashboard._get_student_scope", return_value=[]),
        ):
            with self.assertRaises(frappe.PermissionError):
                get_filter_meta()

    def test_search_students_staff_scope_intersects_selected_school_and_program_subtree(self):
        sql_calls = []

        def fake_sql(query, params=None, as_dict=False):
            sql_calls.append(
                {
                    "query": query,
                    "params": params,
                    "as_dict": as_dict,
                }
            )
            self.assertIn("pe.school IN %(schools)s", query)
            self.assertIn("pe.program IN %(programs)s", query)
            self.assertIn("ORDER BY s.student_full_name", query)
            self.assertEqual(
                params,
                {
                    "schools": ("SCH-CHILD",),
                    "programs": ("PROG-ROOT", "PROG-CHILD"),
                    "txt": "%Ada%",
                },
            )
            self.assertTrue(as_dict)
            return [frappe._dict(student="STU-001", student_full_name="Ada One")]

        with (
            patch("ifitwala_ed.api.student_overview_dashboard._current_user", return_value="instructor@example.com"),
            patch("ifitwala_ed.api.student_overview_dashboard._user_roles", return_value={"Instructor"}),
            patch("ifitwala_ed.api.student_overview_dashboard._get_student_scope", return_value=[]),
            patch(
                "ifitwala_ed.api.student_overview_dashboard.get_authorized_schools",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
            patch(
                "ifitwala_ed.api.student_overview_dashboard.get_descendant_schools",
                return_value=["SCH-CHILD", "SCH-OUTSIDE"],
            ),
            patch(
                "ifitwala_ed.api.student_overview_dashboard.frappe.db.get_value",
                return_value=(10, 20),
            ),
            patch(
                "ifitwala_ed.api.student_overview_dashboard.frappe.get_all",
                return_value=["PROG-ROOT", "PROG-CHILD"],
            ),
            patch("ifitwala_ed.api.student_overview_dashboard.frappe.db.sql", side_effect=fake_sql),
        ):
            rows = search_students(search_text="Ada", school="SCH-ROOT", program="PROG-ROOT")

        self.assertEqual(len(sql_calls), 1)
        self.assertEqual(
            rows,
            [{"student": "STU-001", "student_full_name": "Ada One"}],
        )

    def test_search_students_rejects_user_without_student_overview_access(self):
        with (
            patch("ifitwala_ed.api.student_overview_dashboard._current_user", return_value="assistant@example.com"),
            patch("ifitwala_ed.api.student_overview_dashboard._user_roles", return_value={"Academic Assistant"}),
            patch("ifitwala_ed.api.student_overview_dashboard._get_student_scope", return_value=[]),
        ):
            with self.assertRaises(frappe.PermissionError):
                search_students(search_text="Ada", school="SCH-ROOT", program="PROG-ROOT")

    def test_get_student_center_snapshot_assembles_blocks_and_hides_sensitive_sections_for_guardian_view(self):
        identity = {
            "student": "STU-001",
            "full_name": "Ada One",
            "program_enrollment": {
                "name": "PE-001",
                "program": "PROG-001",
                "academic_year": "2025-2026",
            },
        }

        with (
            patch("ifitwala_ed.api.student_overview_dashboard._ensure_can_view_student") as ensure_can_view,
            patch("ifitwala_ed.api.student_overview_dashboard._identity_block", return_value=identity),
            patch(
                "ifitwala_ed.api.student_overview_dashboard._kpi_block",
                return_value={"attendance": {}, "tasks": {}, "academic": {}, "support": {}},
            ) as kpi_block,
            patch(
                "ifitwala_ed.api.student_overview_dashboard._learning_block",
                return_value={"current_courses": [], "task_progress": {}, "recent_tasks": []},
            ) as learning_block,
            patch(
                "ifitwala_ed.api.student_overview_dashboard._attendance_block",
                return_value={
                    "summary": {
                        "present_percentage": 1,
                        "total_days": 1,
                        "present_days": 1,
                        "excused_absences": 0,
                        "unexcused_absences": 0,
                        "late_count": 0,
                    },
                    "view_mode": "all_day",
                    "all_day_heatmap": [],
                    "by_course_heatmap": [],
                    "by_course_breakdown": [],
                },
            ) as attendance_block,
            patch(
                "ifitwala_ed.api.student_overview_dashboard._wellbeing_block",
                return_value={"timeline": [], "metrics": {}},
            ) as wellbeing_block,
            patch(
                "ifitwala_ed.api.student_overview_dashboard._history_block",
                return_value={
                    "year_options": [],
                    "selected_year_scope": "all",
                    "academic_trend": [],
                    "attendance_trend": [],
                    "reflection_flags": [],
                },
            ) as history_block,
        ):
            payload = get_student_center_snapshot(
                student="STU-001",
                school="SCH-001",
                program="PROG-001",
                view_mode="guardian",
            )

        ensure_can_view.assert_called_once_with("STU-001", "SCH-001", "PROG-001")
        kpi_block.assert_called_once_with("STU-001", "2025-2026")
        learning_block.assert_called_once_with("STU-001", "PROG-001", "2025-2026")
        attendance_block.assert_called_once_with("STU-001", None)
        wellbeing_block.assert_called_once_with("STU-001", "2025-2026")
        history_block.assert_called_once_with("STU-001", "PROG-001")

        self.assertEqual(payload["meta"]["student"], "STU-001")
        self.assertEqual(payload["meta"]["student_name"], "Ada One")
        self.assertEqual(payload["meta"]["current_academic_year"], "2025-2026")
        self.assertEqual(payload["identity"], identity)
        self.assertFalse(payload["meta"]["permissions"]["can_view_task_marks"])
        self.assertFalse(payload["meta"]["permissions"]["can_view_logs"])
        self.assertFalse(payload["meta"]["permissions"]["can_view_referrals"])
        self.assertFalse(payload["meta"]["permissions"]["can_view_nurse_details"])
        self.assertTrue(payload["meta"]["permissions"]["can_view_tasks"])
        self.assertTrue(payload["meta"]["permissions"]["can_view_attendance_details"])
