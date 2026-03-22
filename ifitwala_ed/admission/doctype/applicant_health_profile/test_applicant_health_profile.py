# ifitwala_ed/admission/doctype/applicant_health_profile/test_applicant_health_profile.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApplicantHealthProfile(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_admin_admissions_role("Admission Manager")
        frappe.clear_cache(user="Administrator")
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.user = self._create_user_with_role("Admissions Applicant")
        self.applicant = self._create_student_applicant(self.organization, self.school, self.user)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_family_can_create_profile_with_default_pending_review_status(self):
        frappe.set_user(self.user)
        profile = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": self.applicant,
                "blood_group": "O Positive",
            }
        ).insert(ignore_permissions=True)

        self._created.append(("Applicant Health Profile", profile.name))
        self.assertEqual(profile.review_status, "Pending")

    def test_family_can_edit_health_profile_after_submission(self):
        frappe.db.set_value(
            "Student Applicant",
            self.applicant,
            "application_status",
            "Submitted",
            update_modified=False,
        )
        frappe.set_user(self.user)
        profile = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": self.applicant,
                "blood_group": "A Positive",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Health Profile", profile.name))

        profile.diet_requirements = "No peanuts"
        profile.save(ignore_permissions=True)
        self.assertEqual(profile.diet_requirements, "No peanuts")

    def test_nurse_can_edit_health_review_fields(self):
        frappe.db.set_value(
            "Student Applicant",
            self.applicant,
            "application_status",
            "Submitted",
            update_modified=False,
        )
        frappe.set_user(self.user)
        profile = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": self.applicant,
                "blood_group": "A Positive",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Health Profile", profile.name))

        nurse_user = self._create_user_with_role("Nurse")
        frappe.clear_cache(user=nurse_user)
        frappe.set_user(nurse_user)

        profile.review_status = "Needs Follow-Up"
        profile.review_notes = "Vaccination date is missing."
        profile.save(ignore_permissions=True)

        self.assertEqual(profile.review_status, "Needs Follow-Up")
        self.assertEqual(profile.review_notes, "Vaccination date is missing.")
        self.assertEqual(profile.reviewed_by, nurse_user)
        self.assertIsNotNone(profile.reviewed_on)

    def test_assigned_health_reviewer_gets_read_only_health_and_applicant_access(self):
        frappe.db.set_value(
            "Student Applicant",
            self.applicant,
            "application_status",
            "Submitted",
            update_modified=False,
        )
        frappe.set_user(self.user)
        profile = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": self.applicant,
                "blood_group": "AB Positive",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Health Profile", profile.name))

        reviewer_user = self._create_user_with_role("Academic Assistant")
        assignment = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "target_type": "Applicant Health Profile",
                "target_name": profile.name,
                "student_applicant": self.applicant,
                "assigned_to_user": reviewer_user,
                "status": "Open",
                "source_event": "health_declared_complete",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment.name))

        frappe.clear_cache(user=reviewer_user)
        self.assertTrue(
            frappe.has_permission("Applicant Health Profile", ptype="read", doc=profile.name, user=reviewer_user)
        )
        self.assertFalse(
            frappe.has_permission("Applicant Health Profile", ptype="write", doc=profile.name, user=reviewer_user)
        )
        self.assertTrue(
            frappe.has_permission("Student Applicant", ptype="read", doc=self.applicant, user=reviewer_user)
        )
        self.assertFalse(
            frappe.has_permission("Student Applicant", ptype="write", doc=self.applicant, user=reviewer_user)
        )

    def test_mixed_role_staff_user_is_evaluated_as_staff_not_family(self):
        mixed_user = self._create_user_with_roles(["Admission Manager", "Admissions Applicant"])
        self._create_employee(user_id=mixed_user, school=self.school)
        frappe.clear_cache(user=mixed_user)
        frappe.set_user(mixed_user)

        profile = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": self.applicant,
                "blood_group": "B Positive",
            }
        ).insert(ignore_permissions=True)

        self._created.append(("Applicant Health Profile", profile.name))
        self.assertEqual(profile.review_status, "Pending")

    def _create_organization(self) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Org {frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(self, organization: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"School {frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name

    def _create_user_with_role(self, role_name: str) -> str:
        return self._create_user_with_roles([role_name])

    def _create_user_with_roles(self, role_names: list[str]) -> str:
        for role_name in role_names:
            if not frappe.db.exists("Role", role_name):
                frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
                self._created.append(("Role", role_name))

        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"health-{frappe.generate_hash(length=8)}@example.com",
                "first_name": "Admissions",
                "last_name": "Applicant",
                "enabled": 1,
                "roles": [{"role": role_name} for role_name in role_names],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        return user.name

    def _create_employee(self, *, user_id: str, school: str):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Admissions",
                "employee_last_name": "Staff",
                "employee_gender": "Male",
                "employee_professional_email": user_id,
                "date_of_joining": "2028-01-01",
                "employment_status": "Active",
                "organization": self.organization,
                "school": school,
                "user_id": user_id,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", employee.name))
        return employee.name

    def _create_student_applicant(self, organization: str, school: str, applicant_user: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Health",
                "last_name": f"Applicant-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        doc.db_set("applicant_user", applicant_user, update_modified=False)
        doc.db_set("application_status", "Invited", update_modified=False)
        doc.reload()
        self._created.append(("Student Applicant", doc.name))
        return doc.name

    def _ensure_admin_admissions_role(self, role_name: str):
        if not frappe.db.exists("Role", role_name):
            role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
            self._created.append(("Role", role.name))
        if not frappe.db.exists("Has Role", {"parent": "Administrator", "role": role_name}):
            frappe.get_doc(
                {
                    "doctype": "Has Role",
                    "parent": "Administrator",
                    "parenttype": "User",
                    "parentfield": "roles",
                    "role": role_name,
                }
            ).insert(ignore_permissions=True)
        frappe.clear_cache(user="Administrator")
