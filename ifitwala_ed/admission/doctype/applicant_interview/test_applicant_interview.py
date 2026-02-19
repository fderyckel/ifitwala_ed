# ifitwala_ed/admission/doctype/applicant_interview/test_applicant_interview.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApplicantInterview(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant = self._create_applicant(self.organization, self.school)

    def tearDown(self):
        if self.applicant and self.applicant.name:
            comments = frappe.get_all(
                "Comment",
                filters={
                    "reference_doctype": "Student Applicant",
                    "reference_name": self.applicant.name,
                },
                pluck="name",
            )
            for name in comments:
                if frappe.db.exists("Comment", name):
                    frappe.delete_doc("Comment", name, force=1, ignore_permissions=True)

        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_interview_audit_comment_contains_clickable_link(self):
        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": frappe.utils.nowdate(),
                "interview_type": "Student",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        comments = frappe.get_all(
            "Comment",
            filters={
                "reference_doctype": "Student Applicant",
                "reference_name": self.applicant.name,
            },
            fields=["content"],
            order_by="creation desc",
            limit_page_length=10,
        )
        payload = "\n".join(row.get("content") or "" for row in comments)
        self.assertIn(interview.name, payload)
        self.assertIn("/app/applicant-interview/", payload)

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

    def _create_applicant(self, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Interview",
                "last_name": f"Applicant-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        return doc
