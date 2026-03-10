# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate


class TestStudentPatientVisit(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_visit_insert_does_not_create_student_log(self):
        student = _make_student("Visit Insert")
        patient = _make_student_patient(student.name)
        logs_before = frappe.db.count("Student Log", {"student": student.name})

        visit = frappe.get_doc(
            {
                "doctype": "Student Patient Visit",
                "date": nowdate(),
                "student_patient": patient.name,
                "note": "Student visited the nurse for observation.",
            }
        ).insert()

        self.assertTrue(visit.name)
        self.assertEqual(frappe.db.count("Student Log", {"student": student.name}), logs_before)

    def test_visit_submit_does_not_create_student_log(self):
        student = _make_student("Visit Submit")
        patient = _make_student_patient(student.name)
        logs_before = frappe.db.count("Student Log", {"student": student.name})

        visit = frappe.get_doc(
            {
                "doctype": "Student Patient Visit",
                "date": nowdate(),
                "student_patient": patient.name,
                "note": "Student was discharged after a short rest.",
            }
        ).insert()
        visit.submit()

        self.assertEqual(visit.docstatus, 1)
        self.assertEqual(frappe.db.count("Student Log", {"student": student.name}), logs_before)


def _make_student(prefix):
    student = frappe.get_doc(
        {
            "doctype": "Student",
            "student_first_name": prefix,
            "student_last_name": f"Test {frappe.generate_hash(length=6)}",
            "student_email": f"{frappe.generate_hash(length=8)}@example.com",
        }
    )
    previous_in_migration = bool(getattr(frappe.flags, "in_migration", False))
    frappe.flags.in_migration = True
    try:
        student.insert()
    finally:
        frappe.flags.in_migration = previous_in_migration
    return student


def _make_student_patient(student_name):
    return frappe.get_doc({"doctype": "Student Patient", "student": student_name}).insert()
