# ifitwala_ed/admission/doctype/applicant_review_assignment/test_applicant_review_assignment.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApplicantReviewAssignment(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self._ensure_role("Admission Officer")
        self._ensure_role("Admission Manager")
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant = self._create_applicant(self.organization, self.school)
        self.reviewer_user = self._create_staff_user("Admission Officer")
        self.manager_user = self._create_staff_user("Admission Manager")
        self.outsider_user = self._create_user()

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

    def test_parent_document_target_is_no_longer_allowed(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Applicant Review Assignment",
                    "student_applicant": self.applicant.name,
                    "target_type": "Applicant Document",
                    "target_name": "APPL-DOC-TEST",
                    "assigned_to_user": self.reviewer_user,
                    "status": "Open",
                }
            ).insert(ignore_permissions=True)

    def test_permission_hook_allows_scoped_reviewer_and_blocks_outsider(self):
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

        self.assertTrue(
            frappe.has_permission("Applicant Review Assignment", doc=assignment.as_dict(), user=self.reviewer_user)
        )
        self.assertTrue(
            frappe.has_permission("Applicant Review Assignment", doc=assignment.as_dict(), user=self.manager_user)
        )
        self.assertFalse(
            frappe.has_permission("Applicant Review Assignment", doc=assignment.as_dict(), user=self.outsider_user)
        )

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

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

    def _create_staff_user(self, role: str) -> str:
        email = f"{frappe.scrub(role)}-{frappe.generate_hash(length=8)}@example.com"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": role.split(" ")[0],
                "last_name": role.split(" ")[-1],
                "enabled": 1,
                "roles": [{"role": role}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))

        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": role.split(" ")[0],
                "employee_last_name": role.split(" ")[-1],
                "employee_professional_email": email,
                "organization": self.organization,
                "school": self.school,
                "user_id": user.name,
                "date_of_joining": frappe.utils.nowdate(),
                "employment_status": "Active",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", employee.name))
        frappe.clear_cache(user=user.name)
        return user.name

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
