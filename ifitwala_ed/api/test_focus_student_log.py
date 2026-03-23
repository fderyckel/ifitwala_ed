# ifitwala_ed/api/test_focus_student_log.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint

from ifitwala_ed.api.focus import get_focus_context


class TestFocusStudentLog(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                if doctype == "Student Log":
                    docstatus = cint(frappe.db.get_value(doctype, name, "docstatus") or 0)
                    if docstatus == 1:
                        frappe.get_doc(doctype, name).cancel()
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def test_get_focus_context_includes_student_log_time(self):
        student = self._make_student()
        log_type = self._make_student_log_type()
        log = frappe.get_doc(
            {
                "doctype": "Student Log",
                "student": student.name,
                "date": "2026-04-01",
                "time": "10:15:00",
                "log_type": log_type.name,
                "log": "Observed a pastoral concern and recorded the first action taken.",
                "requires_follow_up": 0,
            }
        ).insert(ignore_permissions=True)
        log.submit()
        self._created.append(("Student Log", log.name))

        ctx = get_focus_context(
            reference_doctype="Student Log",
            reference_name=log.name,
            action_type="student_log.follow_up.act.submit",
        )

        self.assertEqual((ctx.get("log") or {}).get("date"), "2026-04-01")
        self.assertEqual((ctx.get("log") or {}).get("time"), "10:15:00")

    def _make_student(self):
        student = frappe.get_doc(
            {
                "doctype": "Student",
                "student_first_name": "Focus",
                "student_last_name": f"Log-{frappe.generate_hash(length=6)}",
                "student_email": f"{frappe.generate_hash(length=8)}@example.com",
            }
        )
        previous_in_migration = bool(getattr(frappe.flags, "in_migration", False))
        frappe.flags.in_migration = True
        try:
            student.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_migration = previous_in_migration
        self._created.append(("Student", student.name))
        return student

    def _make_student_log_type(self):
        doc = frappe.get_doc(
            {
                "doctype": "Student Log Type",
                "log_type": f"Focus Test {frappe.generate_hash(length=6)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Log Type", doc.name))
        return doc
