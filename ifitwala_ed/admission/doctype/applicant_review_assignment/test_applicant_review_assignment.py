# ifitwala_ed/admission/doctype/applicant_review_assignment/test_applicant_review_assignment.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApplicantReviewAssignment(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant = self._create_applicant(self.organization, self.school)
        self.reviewer_user = self._create_user()

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_sync_scope_from_student_applicant(self):
        assignment = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "student_applicant": self.applicant.name,
                "target_type": "Student Applicant",
                "target_name": self.applicant.name,
                "assigned_to_user": self.reviewer_user,
                "status": "Open",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment.name))

        self.assertEqual(assignment.organization, self.organization)
        self.assertEqual(assignment.school, self.school)

    def test_assignment_actor_validation(self):
        # Both user and role
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Review Assignment",
                    "student_applicant": self.applicant.name,
                    "target_type": "Student Applicant",
                    "target_name": self.applicant.name,
                    "assigned_to_user": self.reviewer_user,
                    "assigned_to_role": "Admission Officer",
                    "status": "Open",
                }
            )
            doc.insert(ignore_permissions=True)

        # Neither user nor role
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Review Assignment",
                    "student_applicant": self.applicant.name,
                    "target_type": "Student Applicant",
                    "target_name": self.applicant.name,
                    "status": "Open",
                }
            )
            doc.insert(ignore_permissions=True)

    def test_decision_validation(self):
        assignment = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "student_applicant": self.applicant.name,
                "target_type": "Student Applicant",
                "target_name": self.applicant.name,
                "assigned_to_user": self.reviewer_user,
                "status": "Done",
                "decision": "Recommend Admit",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment.name))

        # Invalid decision for target type
        assignment.decision = "Cleared"
        with self.assertRaises(frappe.ValidationError):
            assignment.save(ignore_permissions=True)

    def test_unique_open_assignment(self):
        assignment = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "student_applicant": self.applicant.name,
                "target_type": "Student Applicant",
                "target_name": self.applicant.name,
                "assigned_to_user": self.reviewer_user,
                "status": "Open",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment.name))

        # Another open assignment for same target and reviewer
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Review Assignment",
                    "student_applicant": self.applicant.name,
                    "target_type": "Student Applicant",
                    "target_name": self.applicant.name,
                    "assigned_to_user": self.reviewer_user,
                    "status": "Open",
                }
            )
            doc.insert(ignore_permissions=True)

    def _create_organization(self) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Org-{frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=4)}",
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

    def _create_user(self) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"reviewer-{frappe.generate_hash(length=8)}@example.com",
                "first_name": "Reviewer",
                "last_name": "Test",
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", doc.name))
        return doc.name

    def _create_applicant(self, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Applicant",
                "last_name": f"Test-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        return doc
