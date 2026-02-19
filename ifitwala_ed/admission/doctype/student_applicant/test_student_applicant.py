# ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py
# Copyright (c) 2024, fdR and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.doctype.student_applicant.student_applicant import academic_year_intent_query


class TestStudentApplicant(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self._ensure_admissions_role("Administrator", "Admission Manager")
        self.org = self._create_org()
        self.parent_school = self._create_school("Admissions Root", "AR", self.org, is_group=1)
        self.leaf_school = self._create_school("Admissions Leaf", "AL", self.org, parent=self.parent_school, is_group=0)

        self.visible_ay = self._create_academic_year(self.leaf_school, "2025-2026", archived=0, visible=1)
        self.archived_ay = self._create_academic_year(self.leaf_school, "2024-2025", archived=1, visible=1)
        self.hidden_ay = self._create_academic_year(self.leaf_school, "2023-2024", archived=0, visible=0)

    def tearDown(self):
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_academic_year_query_filters_visibility(self):
        rows = academic_year_intent_query(
            "Academic Year",
            "",
            "name",
            0,
            50,
            {"school": self.leaf_school},
        )
        names = {r[0] for r in rows}
        self.assertIn(self.visible_ay, names)
        self.assertNotIn(self.archived_ay, names)
        self.assertNotIn(self.hidden_ay, names)

    def test_academic_year_query_scope_leaf_ancestor(self):
        orphan_leaf = self._create_school("Orphan Leaf", "OL", self.org, parent=self.parent_school, is_group=0)
        parent_ay = self._create_academic_year(self.parent_school, "2026-2027", archived=0, visible=1)
        rows = academic_year_intent_query(
            "Academic Year",
            "",
            "name",
            0,
            50,
            {"school": orphan_leaf},
        )
        names = {r[0] for r in rows}
        self.assertIn(parent_ay, names)

    def test_academic_year_query_scope_non_leaf_child_ancestor(self):
        intermediate_school = self._create_school(
            "Intermediate School", "IS", self.org, parent=self.parent_school, is_group=1
        )
        self._create_school("Intermediate Leaf A", "IA", self.org, parent=intermediate_school, is_group=0)
        self._create_school("Intermediate Leaf B", "IB", self.org, parent=intermediate_school, is_group=0)
        parent_ay = self._create_academic_year(self.parent_school, "2027-2028", archived=0, visible=1)

        rows = academic_year_intent_query(
            "Academic Year",
            "",
            "name",
            0,
            50,
            {"school": intermediate_school},
        )
        names = {r[0] for r in rows}
        self.assertIn(parent_ay, names)

    def test_validation_blocks_archived_ay(self):
        applicant = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Test",
                "last_name": "Applicant",
                "organization": self.org,
                "school": self.leaf_school,
                "academic_year": self.archived_ay,
                "application_status": "Draft",
            }
        )
        with self.assertRaises(frappe.ValidationError):
            applicant.insert(ignore_permissions=True)

    def test_title_autofills_from_name_parts_when_empty(self):
        applicant = self._create_student_applicant(
            first_name="Ada",
            middle_name="M.",
            last_name="Lovelace",
        )
        self.assertEqual(applicant.title, "Ada M. Lovelace")

    def test_title_is_not_overwritten_when_already_set(self):
        applicant = self._create_student_applicant(
            first_name="Grace",
            middle_name="Brewster",
            last_name="Hopper",
            title="Captain Hopper",
        )
        self.assertEqual(applicant.title, "Captain Hopper")

    def test_submitted_to_under_review_transition(self):
        applicant = self._create_student_applicant()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.reload()
        self.assertEqual(applicant.application_status, "Submitted")
        self.assertTrue(bool(applicant.submitted_at))

        applicant.mark_under_review()
        applicant.reload()
        self.assertEqual(applicant.application_status, "Under Review")

    def test_reject_disables_portal_user(self):
        user = self._create_user("Applicant", "Portal", add_role="Admissions Applicant")
        applicant = self._create_student_applicant()
        applicant.flags.from_applicant_invite = True
        applicant.applicant_user = user.name
        applicant.save(ignore_permissions=True)

        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.reject_application("Not eligible")

        user.reload()
        self.assertEqual(user.enabled, 0)

    def test_has_required_interviews_returns_recent_items(self):
        applicant = self._create_student_applicant()
        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": applicant.name,
                "interview_date": frappe.utils.nowdate(),
                "interview_type": "Student",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        payload = applicant.has_required_interviews()
        self.assertEqual(payload.get("count"), 1)
        self.assertTrue(payload.get("ok"))
        items = payload.get("items") or []
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get("name"), interview.name)

    def test_promotion_copies_approved_applicant_document_files(self):
        doc_type = self._create_applicant_document_type(code=f"promotable-{frappe.generate_hash(length=6)}")
        applicant = self._create_student_applicant()

        applicant_doc = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": applicant.name,
                "document_type": doc_type,
                "review_status": "Approved",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", applicant_doc.name))

        source_file = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document",
                "attached_to_name": applicant_doc.name,
                "file_name": "supporting.txt",
                "is_private": 1,
                "content": b"promote-me",
            }
        )
        source_file.insert(ignore_permissions=True)
        self._created.append(("File", source_file.name))

        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant._set_status("Approved", "Approval seeded for promotion test", permission_checker=None)

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))
        applicant.reload()
        self.assertEqual(applicant.application_status, "Promoted")

        copied_files = frappe.get_all(
            "File",
            filters={"attached_to_doctype": "Student", "attached_to_name": student_name},
            fields=["name"],
        )
        copied_file_names = [row["name"] for row in copied_files]
        self.assertTrue(copied_file_names)
        for name in copied_file_names:
            self._created.append(("File", name))

        copied_classifications = frappe.get_all(
            "File Classification",
            filters={
                "primary_subject_type": "Student",
                "primary_subject_id": student_name,
                "source_file": source_file.name,
            },
            fields=["name"],
        )
        copied_classification_names = [row["name"] for row in copied_classifications]
        self.assertTrue(copied_classification_names)
        for name in copied_classification_names:
            self._created.append(("File Classification", name))

    def _ensure_admissions_role(self, user, role):
        if not frappe.db.exists("Role", role):
            return
        if not frappe.db.exists("Has Role", {"parent": user, "role": role}):
            frappe.get_doc(
                {
                    "doctype": "Has Role",
                    "parent": user,
                    "parenttype": "User",
                    "parentfield": "roles",
                    "role": role,
                }
            ).insert(ignore_permissions=True)

    def _create_org(self):
        name = f"Org-{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": name,
                "abbr": name[:6].upper(),
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(self, school_name, abbr, organization, parent=None, is_group=0):
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": school_name,
                "abbr": abbr,
                "organization": organization,
                "is_group": 1 if is_group else 0,
                "parent_school": parent,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name

    def _create_academic_year(self, school, academic_year_name, archived=0, visible=1):
        doc = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": academic_year_name,
                "school": school,
                "archived": archived,
                "visible_to_admission": visible,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Academic Year", doc.name))
        return doc.name

    def _create_student_applicant(self, **overrides):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Test",
                "last_name": "Applicant",
                "organization": self.org,
                "school": self.leaf_school,
                "application_status": "Draft",
                **overrides,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        return doc

    def _create_user(self, first_name, last_name, add_role=None):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"user-{frappe.generate_hash(length=8)}@example.com",
                "first_name": first_name,
                "last_name": last_name,
                "enabled": 1,
            }
        )
        if add_role:
            if not frappe.db.exists("Role", add_role):
                frappe.get_doc({"doctype": "Role", "role_name": add_role}).insert(ignore_permissions=True)
                self._created.append(("Role", add_role))
            user.append("roles", {"role": add_role})
        user.insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        return user

    def _create_applicant_document_type(self, *, code):
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": f"Type {code}",
                "organization": self.org,
                "school": self.leaf_school,
                "is_active": 1,
                "is_required": 0,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name
