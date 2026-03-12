# Copyright (c) 2024, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/students/doctype/student_log/test_student_log.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.students.doctype.student_log.student_log import (
    StudentLog,
    _interpolate_sql_params,
    _is_accreditation_visitor_only,
    dispatch_auto_close_completed_logs,
    get_student_log_visibility_predicate,
    process_auto_close_completed_logs_chunk,
)


class _DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyCache:
    def __init__(self):
        self.store = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value

    def lock(self, key, timeout=15):
        return _DummyLock()


class TestStudentLog(TestCase):
    def test_is_accreditation_visitor_only_requires_single_role(self):
        self.assertTrue(_is_accreditation_visitor_only({"Accreditation Visitor"}))
        self.assertFalse(_is_accreditation_visitor_only({"Accreditation Visitor", "Academic Staff"}))

    @patch("frappe.db.escape")
    def test_interpolate_sql_params_expands_scalars_and_lists(self, mock_escape):
        mock_escape.side_effect = lambda value: f"'{value}'"
        sql = "owner=%(user)s AND school IN %(schools)s"
        params = {"user": "u@example.com", "schools": ("SCH-1", "SCH-2")}

        expanded = _interpolate_sql_params(sql, params)

        self.assertIn("owner='u@example.com'", expanded)
        self.assertIn("school IN ('SCH-1', 'SCH-2')", expanded)

    def test_visibility_predicate_blocks_guest(self):
        sql, params = get_student_log_visibility_predicate(user="Guest")
        self.assertEqual(sql, "0=1")
        self.assertEqual(params, {})

    @patch("frappe.get_roles")
    def test_visibility_predicate_allows_admin_roles(self, mock_get_roles):
        mock_get_roles.return_value = ["System Manager"]
        sql, params = get_student_log_visibility_predicate(user="admin@example.com")
        self.assertEqual(sql, "1=1")
        self.assertEqual(params, {})

    @patch("frappe.db.exists", return_value=True)
    @patch("frappe.throw", side_effect=frappe.ValidationError("blocked"))
    def test_assert_amendment_allowed_blocks_when_source_has_followups(self, _throw, _exists):
        doc = StudentLog.__new__(StudentLog)
        doc.amended_from = "LOG-OLD-0001"

        with self.assertRaises(frappe.ValidationError):
            doc._assert_amendment_allowed()

    @patch("frappe.db.exists", return_value=True)
    @patch("frappe.throw", side_effect=frappe.ValidationError("immutable"))
    def test_assert_core_fields_immutable_after_followup_blocks_mutation(self, _throw, _exists):
        doc = StudentLog.__new__(StudentLog)
        doc.name = "LOG-0001"
        doc.docstatus = 1
        doc.student = "STU-0001"
        doc.log_type = "TYPE-NEW"
        doc.log = "Updated text"
        doc.date = "2026-01-01"
        doc.time = "09:30"
        doc.visible_to_student = 0
        doc.visible_to_guardians = 0
        doc.requires_follow_up = 1
        doc.next_step = "STEP-1"
        doc.follow_up_role = None
        doc.follow_up_person = "teacher@example.com"
        doc.program = "PROG-1"
        doc.academic_year = "AY-2026"
        doc.program_offering = "PO-1"
        doc.school = "SCH-1"
        doc.is_new = lambda: False
        doc.get_doc_before_save = lambda: frappe._dict(
            {
                "student": "STU-0001",
                "date": "2026-01-01",
                "time": "09:30",
                "log_type": "TYPE-OLD",
                "log": "Original text",
                "visible_to_student": 0,
                "visible_to_guardians": 0,
                "requires_follow_up": 1,
                "next_step": "STEP-1",
                "follow_up_role": None,
                "follow_up_person": "teacher@example.com",
                "program": "PROG-1",
                "academic_year": "AY-2026",
                "program_offering": "PO-1",
                "school": "SCH-1",
            }
        )
        doc.get = lambda fieldname: getattr(doc, fieldname, None)

        with self.assertRaises(frappe.ValidationError):
            doc._assert_core_fields_immutable_after_follow_up()

    def test_dispatch_auto_close_completed_logs_enqueues_long_queue_chunks(self):
        cache = _DummyCache()
        eligible_rows = [
            frappe._dict({"name": "LOG-0001"}),
            frappe._dict({"name": "LOG-0002"}),
            frappe._dict({"name": "LOG-0003"}),
        ]

        with (
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log._get_auto_close_eligible_rows",
                return_value=eligible_rows,
            ),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.enqueue") as enqueue,
        ):
            summary = dispatch_auto_close_completed_logs(chunk_size=2)

        self.assertEqual(summary["candidate_count"], 3)
        self.assertEqual(summary["chunk_count"], 2)
        self.assertEqual(enqueue.call_count, 2)
        first_call = enqueue.call_args_list[0]
        self.assertEqual(first_call.kwargs["queue"], "long")
        self.assertEqual(first_call.kwargs["log_names"], ["LOG-0001", "LOG-0002"])
        second_call = enqueue.call_args_list[1]
        self.assertEqual(second_call.kwargs["log_names"], ["LOG-0003"])

    def test_process_auto_close_completed_logs_chunk_only_updates_currently_eligible_logs(self):
        cache = _DummyCache()
        eligible_rows = [frappe._dict({"name": "LOG-0001", "auto_close_after_days": 7})]
        inserted_comments = []

        class _FakeComment:
            def __init__(self, payload):
                self.payload = payload

            def insert(self, ignore_permissions=False):
                inserted_comments.append((self.payload, ignore_permissions))
                return self

        with (
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log._get_auto_close_eligible_rows",
                return_value=eligible_rows,
            ),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.db.sql") as db_sql,
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.db.set_value") as db_set_value,
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.db.exists", return_value=False),
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log.frappe.get_doc",
                side_effect=lambda payload: _FakeComment(payload),
            ),
        ):
            summary = process_auto_close_completed_logs_chunk(["LOG-0001", "LOG-0002"])

        self.assertEqual(summary["requested_count"], 2)
        self.assertEqual(summary["processed_count"], 1)
        self.assertEqual(summary["skipped_count"], 1)
        db_sql.assert_called_once()
        db_set_value.assert_called_once_with("Student Log", "LOG-0001", "follow_up_status", "Completed")
        self.assertEqual(len(inserted_comments), 1)
        self.assertEqual(inserted_comments[0][0]["reference_name"], "LOG-0001")
