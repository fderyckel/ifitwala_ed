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
    get_student_log_visibility_predicate,
)


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
