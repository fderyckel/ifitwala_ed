# Copyright (c) 2024, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/students/doctype/student_log/test_student_log.py

from unittest import TestCase
from unittest.mock import call, patch

import frappe

from ifitwala_ed.students.doctype.student_log.student_log import (
    StudentLog,
    _get_auto_close_eligible_rows,
    _interpolate_sql_params,
    _is_accreditation_visitor_only,
    assign_follow_up,
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

    @patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.get_value", return_value=None)
    def test_validate_persists_academic_staff_default_when_next_step_has_no_associated_role(self, _get_value):
        doc = StudentLog.__new__(StudentLog)
        doc.requires_follow_up = 1
        doc.next_step = "STEP-1"
        doc.follow_up_role = None
        doc.follow_up_person = None
        doc.follow_up_status = None
        doc.school = "SCH-1"
        doc.name = None
        doc.docstatus = 0
        doc.is_new = lambda: True
        doc._current_assignee = lambda: None
        doc._compute_follow_up_status = lambda: None
        doc._apply_status = lambda *args, **kwargs: None
        doc._ensure_delivery_context = lambda: None
        doc._resolve_school = lambda: "SCH-1"
        doc._assert_amendment_allowed = lambda: None
        doc._assert_core_fields_immutable_after_follow_up = lambda: None
        doc._assert_followup_transition_and_immutability = lambda: None

        doc.validate()

        self.assertEqual(doc.follow_up_role, "Academic Staff")

    def test_validate_seeds_delivery_context_for_new_logs_only(self):
        doc = StudentLog.__new__(StudentLog)
        doc.requires_follow_up = 0
        doc.next_step = None
        doc.follow_up_person = None
        doc.follow_up_status = None
        doc.student = "STU-0001"
        doc.program = None
        doc.academic_year = None
        doc.program_offering = None
        doc.school = None
        doc.name = None
        doc.docstatus = 0
        doc.is_new = lambda: True
        doc._unassign = lambda: None
        doc._apply_status = lambda *args, **kwargs: None
        doc._assert_amendment_allowed = lambda: None
        doc._assert_core_fields_immutable_after_follow_up = lambda: None
        doc._assert_followup_transition_and_immutability = lambda: None

        def seed_context():
            doc.program = "PROG-1"
            doc.academic_year = "AY-2026"

        with (
            patch.object(doc, "_ensure_delivery_context", side_effect=seed_context) as ensure_delivery_context,
            patch.object(doc, "_resolve_school", return_value="SCH-1") as resolve_school,
        ):
            doc.validate()

        ensure_delivery_context.assert_called_once_with()
        resolve_school.assert_called_once_with()
        self.assertEqual(doc.school, "SCH-1")

    def test_validate_skips_delivery_context_backfill_for_existing_logs(self):
        doc = StudentLog.__new__(StudentLog)
        doc.requires_follow_up = 0
        doc.next_step = None
        doc.follow_up_person = None
        doc.follow_up_status = None
        doc.student = "STU-0001"
        doc.program = None
        doc.academic_year = None
        doc.program_offering = None
        doc.school = None
        doc.name = "LOG-0001"
        doc.docstatus = 0
        doc.is_new = lambda: False
        doc._unassign = lambda: None
        doc._apply_status = lambda *args, **kwargs: None
        doc._assert_amendment_allowed = lambda: None
        doc._assert_core_fields_immutable_after_follow_up = lambda: None
        doc._assert_followup_transition_and_immutability = lambda: None

        with (
            patch.object(doc, "_ensure_delivery_context") as ensure_delivery_context,
            patch.object(doc, "_resolve_school", return_value="SCH-1") as resolve_school,
        ):
            doc.validate()

        ensure_delivery_context.assert_not_called()
        resolve_school.assert_not_called()
        self.assertIsNone(doc.school)

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

    def test_get_auto_close_eligible_rows_prefers_next_step_policy_over_school_default(self):
        student_log_rows = [
            frappe._dict(
                {
                    "name": "LOG-0001",
                    "modified": "2026-03-15 08:00:00",
                    "school": "SCH-1",
                    "next_step": "STEP-1",
                }
            ),
            frappe._dict(
                {
                    "name": "LOG-0002",
                    "modified": "2026-03-17 08:00:00",
                    "school": "SCH-2",
                    "next_step": "STEP-2",
                }
            ),
            frappe._dict(
                {
                    "name": "LOG-0003",
                    "modified": "2026-03-16 08:00:00",
                    "school": None,
                    "next_step": None,
                }
            ),
        ]
        school_rows = [
            frappe._dict({"name": "SCH-1", "default_follow_up_due_in_days": 7}),
            frappe._dict({"name": "SCH-2", "default_follow_up_due_in_days": 5}),
        ]
        next_step_rows = [
            frappe._dict({"name": "STEP-1", "auto_close_after_days": 3}),
            frappe._dict({"name": "STEP-2", "auto_close_after_days": None}),
        ]

        def fake_get_all(doctype, filters=None, fields=None):
            if doctype == "Student Log":
                self.assertEqual(filters, {"follow_up_status": "In Progress"})
                self.assertEqual(fields, ["name", "modified", "school", "next_step"])
                return student_log_rows
            if doctype == "School":
                self.assertEqual(fields, ["name", "default_follow_up_due_in_days"])
                self.assertEqual(filters, {"name": ["in", ["SCH-1", "SCH-2"]]})
                return school_rows
            if doctype == "Student Log Next Step":
                self.assertEqual(fields, ["name", "auto_close_after_days"])
                self.assertEqual(filters, {"name": ["in", ["STEP-1", "STEP-2"]]})
                return next_step_rows
            self.fail(f"Unexpected doctype lookup: {doctype}")

        with (
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.utils.today", return_value="2026-03-21"),
        ):
            eligible = _get_auto_close_eligible_rows()

        self.assertEqual([row.name for row in eligible], ["LOG-0001", "LOG-0003"])
        self.assertEqual(eligible[0].auto_close_due_in_days, 3)
        self.assertEqual(eligible[1].auto_close_due_in_days, 5)

    def test_assign_to_uses_due_date_helper_even_without_program_context(self):
        doc = StudentLog.__new__(StudentLog)
        doc.doctype = "Student Log"
        doc.name = "LOG-0001"
        doc.student_name = "Focus Student"
        doc.school = "SCH-1"
        doc.next_step = "STEP-1"
        doc._resolve_school = lambda: "SCH-1"

        with (
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.db.exists", return_value=False),
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log._get_follow_up_due_days",
                return_value=4,
            ),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.utils.today", return_value="2026-04-19"),
            patch("ifitwala_ed.students.doctype.student_log.student_log.assign_add") as assign_add,
        ):
            doc._assign_to("assignee@example.com")

        assign_add.assert_called_once()
        payload = assign_add.call_args.args[0]
        self.assertEqual(payload["assign_to"], ["assignee@example.com"])
        self.assertEqual(payload["due_date"], "2026-04-23")

    def test_assign_follow_up_uses_persisted_role_without_repairing_it(self):
        inserted_todos = []

        class _FakeToDo:
            def __init__(self, payload):
                self.payload = payload

            def insert(self, ignore_permissions=False):
                inserted_todos.append((self.payload, ignore_permissions))
                return self

        def fake_db_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Student Log":
                return frappe._dict(
                    {
                        "name": "LOG-0001",
                        "owner": "author@example.com",
                        "school": "SCH-1",
                        "student_name": "Focus Student",
                        "follow_up_status": None,
                        "follow_up_role": "Counselor",
                        "next_step": "STEP-1",
                    }
                )
            if doctype == "ToDo":
                return None
            raise AssertionError(f"Unexpected get_value lookup: {doctype!r}")

        def fake_get_roles(user=None):
            if user == "assignee@example.com":
                return ["Counselor"]
            return ["Academic Admin"]

        with (
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log.frappe.defaults.get_user_default",
                return_value="SCH-1",
            ),
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log.frappe.db.get_value",
                side_effect=fake_db_get_value,
            ),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.db.sql", side_effect=[[(1,)], None]),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.get_roles", side_effect=fake_get_roles),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.get_value") as get_value,
            patch("ifitwala_ed.students.doctype.student_log.student_log._get_follow_up_due_days", return_value=4),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.utils.today", return_value="2026-04-19"),
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log.frappe.utils.add_days", return_value="2026-04-23"
            ),
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log.frappe.get_doc",
                side_effect=lambda payload: _FakeToDo(payload),
            ),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.db.set_value") as set_value,
            patch.object(frappe.session, "user", "admin@example.com"),
        ):
            result = assign_follow_up("LOG-0001", "assignee@example.com")

        self.assertEqual(result["assigned_to"], "assignee@example.com")
        self.assertEqual(result["status"], "Open")
        get_value.assert_not_called()
        self.assertEqual(
            set_value.call_args_list,
            [
                call("Student Log", "LOG-0001", "follow_up_person", "assignee@example.com"),
                call("Student Log", "LOG-0001", "follow_up_status", "Open"),
            ],
        )
        self.assertEqual(inserted_todos[0][0]["allocated_to"], "assignee@example.com")

    def test_assign_follow_up_blocks_missing_follow_up_role_without_runtime_backfill(self):
        def fake_db_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Student Log":
                return frappe._dict(
                    {
                        "name": "LOG-0002",
                        "owner": "author@example.com",
                        "school": "SCH-1",
                        "student_name": "Focus Student",
                        "follow_up_status": None,
                        "follow_up_role": None,
                        "next_step": "STEP-1",
                    }
                )
            if doctype == "Employee":
                return "SCH-1"
            raise AssertionError(f"Unexpected get_value lookup: {doctype!r}")

        with (
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log.frappe.defaults.get_user_default",
                return_value=None,
            ),
            patch(
                "ifitwala_ed.students.doctype.student_log.student_log.frappe.db.get_value",
                side_effect=fake_db_get_value,
            ),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.db.sql", return_value=[(1,)]),
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.get_value") as get_value,
            patch("ifitwala_ed.students.doctype.student_log.student_log.frappe.db.set_value") as set_value,
        ):
            with self.assertRaises(frappe.ValidationError):
                assign_follow_up("LOG-0002", "assignee@example.com")

        get_value.assert_not_called()
        set_value.assert_not_called()

    def test_process_auto_close_completed_logs_chunk_only_updates_currently_eligible_logs(self):
        cache = _DummyCache()
        eligible_rows = [frappe._dict({"name": "LOG-0001", "auto_close_due_in_days": 7})]
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
