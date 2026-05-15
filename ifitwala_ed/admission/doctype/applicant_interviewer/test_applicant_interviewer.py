# ifitwala_ed/admission/doctype/applicant_interviewer/test_applicant_interviewer.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApplicantInterviewer(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []

    def tearDown(self):
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_applicant_interviewer_child_row(self):
        # Applicant Interviewer is a child table on Applicant Interview.
        # We test that we can add an interviewer to an interview.
        org = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Org-{frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", org.name))

        school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"School-{frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": org.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", school.name))

        applicant = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Applicant",
                "last_name": f"Test-{frappe.generate_hash(length=6)}",
                "organization": org.name,
                "school": school.name,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", applicant.name))

        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"interviewer-{frappe.generate_hash(length=8)}@example.com",
                "first_name": "Interviewer",
                "last_name": "Test",
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))

        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": applicant.name,
                "interview_date": frappe.utils.nowdate(),
                "interview_type": "Student",
                "interviewers": [{"interviewer": user.name}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        loaded = frappe.get_doc("Applicant Interview", interview.name)
        self.assertEqual(len(loaded.interviewers), 1)
        self.assertEqual(loaded.interviewers[0].interviewer, user.name)
