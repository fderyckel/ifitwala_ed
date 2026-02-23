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
        self.applicant = self._create_student_applicant(self.organization, self.school)

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
                "roles": [{"role": role_name}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        return user.name

    def _create_student_applicant(self, organization: str, school: str) -> str:
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
