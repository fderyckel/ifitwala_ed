# ifitwala_ed/hr/doctype/leave_application/test_leave_application.py

from datetime import date
from unittest import TestCase

import frappe

from ifitwala_ed.hr.doctype.leave_application.leave_application import (
    LeaveApplication,
    daterange,
)


class TestLeaveApplication(TestCase):
    def test_daterange_is_inclusive(self):
        range_values = list(daterange("2026-02-01", "2026-02-03"))
        self.assertEqual(range_values, [date(2026, 2, 1), date(2026, 2, 2), date(2026, 2, 3)])

    def test_validate_status_transition_rejects_illegal_reopen(self):
        doc = LeaveApplication.__new__(LeaveApplication)
        doc.status = "Open"
        doc.has_value_changed = lambda fieldname: fieldname == "status"
        doc.get_doc_before_save = lambda: frappe._dict({"status": "Approved"})

        with self.assertRaises(frappe.ValidationError):
            LeaveApplication.validate_status_transition(doc)

    def test_validate_status_transition_short_circuits_when_status_unchanged(self):
        doc = LeaveApplication.__new__(LeaveApplication)
        doc.status = "Open"
        doc.has_value_changed = lambda _fieldname: False

        # Should not raise when status is unchanged.
        LeaveApplication.validate_status_transition(doc)
