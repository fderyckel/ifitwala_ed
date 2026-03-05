# ifitwala_ed/admission/doctype/applicant_interview_feedback/test_applicant_interview_feedback.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApplicantInterviewFeedback(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []

        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant = self._create_applicant(self.organization, self.school)

        self.interviewer = self._create_user("feedback-interviewer")
        self._create_employee(self.interviewer, first_name="Panel", last_name="Interviewer")

        self.outsider = self._create_user("feedback-outsider")
        self._create_employee(self.outsider, first_name="Panel", last_name="Outsider")

        self.interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": "2030-07-01",
                "interview_start": "2030-07-01 10:00:00",
                "interview_end": "2030-07-01 10:30:00",
                "interview_type": "Student",
                "interviewers": [{"interviewer": self.interviewer.name}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", self.interview.name))

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_assigned_interviewer_can_create_and_submit_feedback(self):
        frappe.set_user(self.interviewer.name)

        doc = frappe.get_doc(
            {
                "doctype": "Applicant Interview Feedback",
                "applicant_interview": self.interview.name,
                "interviewer_user": self.interviewer.name,
                "feedback_status": "Draft",
                "strengths": "Clear communication and motivation",
            }
        ).insert()
        self._created.append(("Applicant Interview Feedback", doc.name))

        self.assertEqual(doc.student_applicant, self.applicant.name)
        self.assertEqual(doc.feedback_status, "Draft")

        doc.feedback_status = "Submitted"
        doc.concerns = "Needs time-management support"
        doc.save()

        refreshed = frappe.get_doc("Applicant Interview Feedback", doc.name)
        self.assertEqual(refreshed.feedback_status, "Submitted")
        self.assertTrue(bool(refreshed.submitted_on))

    def test_non_interviewer_cannot_create_feedback(self):
        frappe.set_user(self.outsider.name)

        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {
                    "doctype": "Applicant Interview Feedback",
                    "applicant_interview": self.interview.name,
                    "interviewer_user": self.outsider.name,
                    "feedback_status": "Draft",
                    "strengths": "Attempt",
                }
            ).insert()

    def _create_organization(self) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Org-{frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=5)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(self, organization: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"School-{frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name

    def _create_user(self, label: str):
        doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"{label}-{frappe.generate_hash(length=8)}@example.com",
                "first_name": "Feedback",
                "last_name": "User",
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", doc.name))
        return doc

    def _create_employee(self, user, *, first_name: str, last_name: str):
        doc = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": first_name,
                "employee_last_name": last_name,
                "employee_gender": "Male",
                "employee_professional_email": user.email,
                "date_of_joining": "2028-01-01",
                "employment_status": "Active",
                "organization": self.organization,
                "school": self.school,
                "user_id": user.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", doc.name))
        return doc

    def _create_applicant(self, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Feedback",
                "last_name": f"Applicant-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        return doc
