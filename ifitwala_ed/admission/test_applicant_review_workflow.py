# ifitwala_ed/admission/test_applicant_review_workflow.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.applicant_review_workflow import materialize_application_review_assignments
from ifitwala_ed.tests.factories.users import make_user


class TestApplicantReviewWorkflow(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Administrator", "Admission Manager")
        frappe.clear_cache(user="Administrator")

        self.reviewer_user = self._make_admissions_user("Admission Officer")
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.student_applicant = self._create_student_applicant(self.organization, self.school)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def test_materialize_no_rules_returns_empty(self):
        names = materialize_application_review_assignments(student_applicant=self.student_applicant.name)
        self.assertEqual(names, [])

    def test_materialize_merges_same_scope_reviewers_and_dedupes(self):
        role_name = "Admission Officer"
        self._create_review_rule(
            reviewers=[{"reviewer_role": role_name}],
        )
        self._create_review_rule(
            reviewers=[{"reviewer_user": self.reviewer_user}],
        )
        # Duplicate on purpose; should dedupe by (reviewer_user, reviewer_role)
        self._create_review_rule(
            reviewers=[{"reviewer_user": self.reviewer_user}],
        )

        names = materialize_application_review_assignments(student_applicant=self.student_applicant.name)
        self.assertEqual(len(names), 2)

        rows = frappe.get_all(
            "Applicant Review Assignment",
            filters={
                "target_type": "Student Applicant",
                "target_name": self.student_applicant.name,
                "status": "Open",
            },
            fields=["assigned_to_user", "assigned_to_role"],
        )
        actor_set = {
            (
                (row.get("assigned_to_user") or "").strip() or None,
                (row.get("assigned_to_role") or "").strip() or None,
            )
            for row in rows
        }
        self.assertEqual(
            actor_set,
            {
                (None, role_name),
                (self.reviewer_user, None),
            },
        )

    def _ensure_role(self, user: str, role: str):
        if not frappe.db.exists("Role", role):
            self.skipTest(f"Missing Role '{role}' in this site.")
        if frappe.db.exists("Has Role", {"parent": user, "role": role}):
            return
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parent": user,
                "parenttype": "User",
                "parentfield": "roles",
                "role": role,
            }
        ).insert(ignore_permissions=True)

    def _make_admissions_user(self, role: str) -> str:
        user = make_user()
        self._ensure_role(user.name, role)
        self._created.append(("User", user.name))
        return user.name

    def _create_organization(self) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Org {frappe.generate_hash(length=6)}",
                "abbr": f"ORG{frappe.generate_hash(length=4)}",
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

    def _create_student_applicant(self, organization: str, school: str):
        frappe.set_user(self.reviewer_user)
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Workflow",
                "last_name": f"Applicant-{frappe.generate_hash(length=5)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        frappe.set_user("Administrator")
        return doc

    def _create_review_rule(self, reviewers: list[dict]):
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Review Rule",
                "is_active": 1,
                "organization": self.organization,
                "school": self.school,
                "target_type": "Student Applicant",
                "reviewers": reviewers,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Rule", doc.name))
        return doc
