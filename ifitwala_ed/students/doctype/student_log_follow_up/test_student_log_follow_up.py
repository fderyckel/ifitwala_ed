# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.students.doctype.student_log_follow_up.student_log_follow_up import (
    StudentLogFollowUp,
    has_permission,
)


class TestStudentLogFollowUp(TestCase):
    def test_has_permission_allows_current_assignee_to_submit(self):
        doc = frappe._dict({"student_log": "LOG-0001"})

        with (
            patch(
                "ifitwala_ed.students.doctype.student_log_follow_up.student_log_follow_up.frappe.get_roles",
                return_value=[],
            ),
            patch(
                "ifitwala_ed.students.doctype.student_log_follow_up.student_log_follow_up._current_log_assignee",
                return_value="assignee@example.com",
            ),
        ):
            allowed = has_permission(doc, ptype="submit", user="assignee@example.com")

        self.assertTrue(allowed)

    def test_validate_rejects_non_assignee_with_actionable_message(self):
        doc = StudentLogFollowUp.__new__(StudentLogFollowUp)
        doc.student_log = "LOG-0001"
        doc.follow_up = "<p>Logged a quick update.</p>"
        doc.follow_up_author = None
        doc.name = None

        with (
            patch(
                "ifitwala_ed.students.doctype.student_log_follow_up.student_log_follow_up.frappe.db.get_value",
                return_value="Open",
            ),
            patch(
                "ifitwala_ed.students.doctype.student_log_follow_up.student_log_follow_up._can_manage_follow_up",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.students.doctype.student_log_follow_up.student_log_follow_up.frappe.throw",
                side_effect=frappe.PermissionError("blocked"),
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                doc.validate()

    def test_on_update_does_not_change_parent_status_for_draft_follow_up(self):
        doc = StudentLogFollowUp.__new__(StudentLogFollowUp)
        doc.docstatus = 0
        doc.student_log = "LOG-0001"

        with patch(
            "ifitwala_ed.students.doctype.student_log_follow_up.student_log_follow_up.frappe.get_doc"
        ) as get_doc:
            doc.on_update()

        get_doc.assert_not_called()
