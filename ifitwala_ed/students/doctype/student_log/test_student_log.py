# Copyright (c) 2024, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/students/doctype/student_log/test_student_log.py

from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.students.doctype.student_log.student_log import (
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
