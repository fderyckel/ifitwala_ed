# ifitwala_ed/api/test_student_log_api.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from ifitwala_ed.api import student_log as student_log_api


class _CacheStub:
    def __init__(self):
        self.values = {}

    def get_value(self, key):
        return self.values.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.values[key] = value


class TestStudentLogApi(TestCase):
    def test_can_create_student_log_for_session_user_accepts_write_permission(self):
        with (
            patch.object(student_log_api.frappe, "session", SimpleNamespace(user="coord@example.com")),
            patch(
                "ifitwala_ed.api.student_log.frappe.has_permission",
                side_effect=lambda doctype, ptype="read", user=None: doctype == "Student Log" and ptype == "write",
            ),
        ):
            allowed = student_log_api._can_create_student_log_for_session_user()

        self.assertTrue(allowed)

    def test_school_scope_parent_plus_one_includes_self_descendants_and_parent(self):
        with (
            patch("ifitwala_ed.api.student_log.get_descendants_of", return_value=["SCH-A", "SCH-A-1"]),
            patch("ifitwala_ed.api.student_log.frappe.db.get_value", return_value="SCH-P"),
        ):
            scope = student_log_api._get_school_scope_parent_plus_one("SCH-A", include_descendants=True)

        self.assertEqual(scope, ["SCH-A", "SCH-A-1", "SCH-P"])

    def test_get_staff_scope_schools_uses_canonical_parent_plus_one_helper(self):
        cache = _CacheStub()
        with (
            patch.object(student_log_api.frappe, "session", SimpleNamespace(user="teacher@example.com")),
            patch("ifitwala_ed.api.student_log.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.api.student_log._get_employee_school_for_session_user",
                return_value="SCH-A",
            ),
            patch(
                "ifitwala_ed.api.student_log._get_school_scope_parent_plus_one",
                return_value=["SCH-A", "SCH-A-1", "SCH-P"],
            ) as scope_helper,
        ):
            scope = student_log_api._get_staff_scope_schools_for_session_user()

        self.assertEqual(scope, ["SCH-A", "SCH-A-1", "SCH-P"])
        scope_helper.assert_called_once_with("SCH-A", include_descendants=True)

    def test_submit_student_log_rejects_out_of_scope_student_before_schema_work(self):
        payload = {
            "student": "STU-0001",
            "log_type": "LTYPE-1",
            "log": "Observed behavior.",
            "requires_follow_up": 0,
            "visible_to_student": 0,
            "visible_to_guardians": 0,
        }

        with (
            patch("ifitwala_ed.api.student_log._is_student_in_session_scope", return_value=False),
            patch("ifitwala_ed.api.student_log._is_log_type_allowed_for_student_school") as log_type_guard,
            patch(
                "ifitwala_ed.api.student_log.frappe.throw",
                side_effect=frappe.PermissionError("forbidden"),
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                student_log_api.submit_student_log(**payload)

        log_type_guard.assert_not_called()

    def test_submit_student_log_rejects_ineligible_assignee(self):
        payload = {
            "student": "STU-0001",
            "log_type": "LTYPE-1",
            "log": "Observed behavior.",
            "requires_follow_up": 1,
            "next_step": "STEP-1",
            "follow_up_person": "teacher@example.com",
            "visible_to_student": 0,
            "visible_to_guardians": 0,
        }

        with (
            patch("ifitwala_ed.api.student_log._is_student_in_session_scope", return_value=True),
            patch("ifitwala_ed.api.student_log._get_student_school", return_value="SCH-A"),
            patch("ifitwala_ed.api.student_log._is_log_type_allowed_for_student_school", return_value=True),
            patch("ifitwala_ed.api.student_log._is_next_step_allowed_for_student_school", return_value=True),
            patch("ifitwala_ed.api.student_log._is_follow_up_person_allowed", return_value=False),
            patch(
                "ifitwala_ed.api.student_log.frappe.new_doc",
                return_value=MagicMock(),
            ) as new_doc,
            patch(
                "ifitwala_ed.api.student_log.frappe.throw",
                side_effect=frappe.ValidationError("invalid"),
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                student_log_api.submit_student_log(**payload)

        new_doc.assert_not_called()

    def test_submit_student_log_uses_ignore_permissions_when_write_but_not_create(self):
        payload = {
            "student": "STU-0001",
            "log_type": "LTYPE-1",
            "log": "Observed behavior.",
            "requires_follow_up": 0,
            "visible_to_student": 0,
            "visible_to_guardians": 0,
        }
        doc = MagicMock()
        doc.name = "LOG-0001"

        def _fake_has_permission(doctype, ptype="read", user=None):
            return doctype == "Student Log" and ptype == "write"

        with (
            patch.object(student_log_api.frappe, "session", SimpleNamespace(user="coord@example.com")),
            patch("ifitwala_ed.api.student_log._is_student_in_session_scope", return_value=True),
            patch("ifitwala_ed.api.student_log._get_student_school", return_value="SCH-A"),
            patch("ifitwala_ed.api.student_log._is_log_type_allowed_for_student_school", return_value=True),
            patch("ifitwala_ed.api.student_log.nowdate", return_value="2026-03-26"),
            patch("ifitwala_ed.api.student_log.nowtime", return_value="09:45:30"),
            patch("ifitwala_ed.api.student_log.frappe.has_permission", side_effect=_fake_has_permission),
            patch("ifitwala_ed.api.student_log.frappe.new_doc", return_value=doc),
        ):
            result = student_log_api.submit_student_log(**payload)

        doc.insert.assert_called_once_with(ignore_permissions=True)
        doc.submit.assert_called_once_with()
        self.assertEqual(result, {"name": "LOG-0001"})

    def test_get_student_log_detail_remains_read_only(self):
        log_row = frappe._dict(
            {
                "name": "LOG-0001",
                "student": "STU-0001",
                "visible_to_student": 1,
                "date": "2026-03-15",
                "time": "09:00:00",
                "log_type": "Academic",
                "author_name": "Teacher Example",
                "log": "<p>Detail body</p>",
            }
        )

        with (
            patch(
                "ifitwala_ed.api.student_log._resolve_current_student",
                return_value="STU-0001",
            ),
            patch("ifitwala_ed.api.student_log.frappe.db.get_value", return_value=log_row),
            patch("ifitwala_ed.api.student_log._upsert_student_log_read_receipt") as mark_read_mock,
        ):
            result = student_log_api.get_student_log_detail("LOG-0001")

        self.assertEqual(result, log_row)
        mark_read_mock.assert_not_called()

    def test_mark_student_log_read_marks_log_read_with_timestamp(self):
        log_row = frappe._dict(
            {
                "name": "LOG-0001",
                "student": "STU-0001",
                "visible_to_student": 1,
            }
        )
        read_at = frappe.utils.get_datetime("2026-03-15 11:30:00")

        with (
            patch(
                "ifitwala_ed.api.student_log._resolve_current_student",
                return_value="STU-0001",
            ),
            patch("ifitwala_ed.api.student_log.now_datetime", return_value=read_at),
            patch("ifitwala_ed.api.student_log.frappe.session", SimpleNamespace(user="student@example.com")),
            patch("ifitwala_ed.api.student_log.frappe.db.get_value", return_value=log_row),
            patch("ifitwala_ed.api.student_log._upsert_student_log_read_receipt") as mark_read_mock,
        ):
            result = student_log_api.mark_student_log_read("LOG-0001")

        self.assertEqual(result, {"ok": True, "student_log": "LOG-0001", "read_at": read_at})
        mark_read_mock.assert_called_once_with(
            user="student@example.com",
            log_name="LOG-0001",
            read_at=read_at,
        )
