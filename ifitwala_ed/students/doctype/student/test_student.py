# ifitwala_ed/students/doctype/student/test_student.py
# Copyright (c) 2024, fdR and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestStudent(FrappeTestCase):
    def _student_payload(self) -> dict:
        seed = frappe.generate_hash(length=8)
        return {
            "doctype": "Student",
            "student_first_name": "Test",
            "student_last_name": f"Student{seed}",
            "student_email": f"student-{seed}@example.com",
        }

    def test_direct_creation_is_blocked_without_applicant_or_import_context(self):
        doc = frappe.get_doc(self._student_payload())
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_import_context_allows_direct_creation(self):
        prev_import = getattr(frappe.flags, "in_import", False)
        frappe.flags.in_import = True
        try:
            doc = frappe.get_doc(self._student_payload())
            doc.allow_direct_creation = 1
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = prev_import

        self.assertTrue(bool(doc.name))

    def test_import_context_requires_allow_direct_creation(self):
        prev_import = getattr(frappe.flags, "in_import", False)
        frappe.flags.in_import = True
        try:
            doc = frappe.get_doc(self._student_payload())
            with self.assertRaises(frappe.ValidationError):
                doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = prev_import

    def test_update_after_migration_insert_without_allow_direct_creation_is_allowed(self):
        prev_migration = getattr(frappe.flags, "in_migration", False)
        frappe.flags.in_migration = True
        try:
            doc = frappe.get_doc(self._student_payload())
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_migration = prev_migration

        doc.student_preferred_name = "Updated Name"
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.student_preferred_name, "Updated Name")
