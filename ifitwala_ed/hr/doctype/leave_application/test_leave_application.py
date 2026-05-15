# ifitwala_ed/hr/doctype/leave_application/test_leave_application.py

from datetime import date
from unittest import TestCase
from unittest.mock import Mock, patch

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

    def test_create_or_update_attendance_updates_canonical_fields_only(self):
        leave_application = LeaveApplication.__new__(LeaveApplication)
        leave_application.name = "HR-LA-0001"
        leave_application.leave_type = "Annual Leave"
        leave_application.half_day_date = None

        attendance = frappe._dict(docstatus=0)
        attendance.db_set = Mock()

        with patch(
            "ifitwala_ed.hr.doctype.leave_application.leave_application.frappe.get_doc",
            return_value=attendance,
        ):
            LeaveApplication.create_or_update_attendance(
                leave_application,
                attendance_name="HR-EATT-0001",
                date="2026-03-12",
            )

        attendance.db_set.assert_called_once_with(
            {
                "status": "On Leave",
                "leave_type": "Annual Leave",
                "leave_application": "HR-LA-0001",
                "half_day_status": None,
                "attendance_method": "Manual",
            }
        )

    def test_create_or_update_attendance_creates_employee_attendance_without_generic_source_fields(self):
        class AttendanceStub:
            def __init__(self):
                self.insert = Mock()
                self.submit = Mock()

        leave_application = LeaveApplication.__new__(LeaveApplication)
        leave_application.name = "HR-LA-0001"
        leave_application.employee = "HR-EMP-0001"
        leave_application.employee_full_name = "Staff Member"
        leave_application.organization = "ORG-001"
        leave_application.school = "SCH-001"
        leave_application.department = "Teaching"
        leave_application.leave_type = "Annual Leave"
        leave_application.half_day_date = "2026-03-12"
        leave_application.get = lambda fieldname, default=None: getattr(leave_application, fieldname, default)

        attendance = AttendanceStub()

        with patch(
            "ifitwala_ed.hr.doctype.leave_application.leave_application.frappe.new_doc",
            return_value=attendance,
        ):
            LeaveApplication.create_or_update_attendance(
                leave_application,
                attendance_name=None,
                date="2026-03-12",
            )

        self.assertEqual(attendance.employee, "HR-EMP-0001")
        self.assertEqual(attendance.employee_full_name, "Staff Member")
        self.assertEqual(attendance.attendance_date, "2026-03-12")
        self.assertEqual(attendance.organization, "ORG-001")
        self.assertEqual(attendance.school, "SCH-001")
        self.assertEqual(attendance.department, "Teaching")
        self.assertEqual(attendance.leave_type, "Annual Leave")
        self.assertEqual(attendance.leave_application, "HR-LA-0001")
        self.assertEqual(attendance.status, "Half Day")
        self.assertEqual(attendance.half_day_status, "Present")
        self.assertEqual(attendance.attendance_method, "Manual")
        self.assertFalse(hasattr(attendance, "source_transaction_type"))
        self.assertFalse(hasattr(attendance, "source_transaction_name"))
        attendance.insert.assert_called_once_with(ignore_permissions=True)
        attendance.submit.assert_called_once_with()
