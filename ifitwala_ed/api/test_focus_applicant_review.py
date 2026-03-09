# ifitwala_ed/api/test_focus_applicant_review.py

from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.focus import (
    claim_applicant_review_assignment,
    download_applicant_review_file,
    get_focus_context,
    list_focus_items,
    reassign_applicant_review_assignment,
    submit_applicant_review_assignment,
)
from ifitwala_ed.tests.factories.users import make_user


class TestFocusApplicantReview(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Administrator", "Admission Manager")
        frappe.clear_cache(user="Administrator")

        self.role_name = "Admission Officer"
        self.reviewer_one = self._make_user_with_role(self.role_name)
        self.reviewer_two = self._make_user_with_role(self.role_name)

        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.student_applicant = self._create_student_applicant(self.organization, self.school)
        self.assignment = self._create_role_assignment(self.student_applicant.name, self.role_name)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def test_role_assignment_visible_to_all_role_holders_and_single_completion_closes_it(self):
        frappe.set_user(self.reviewer_one)
        items_one = list_focus_items(open_only=1, limit=50, offset=0)
        self.assertTrue(any(row.get("reference_name") == self.assignment.name for row in items_one))

        frappe.set_user(self.reviewer_two)
        items_two = list_focus_items(open_only=1, limit=50, offset=0)
        self.assertTrue(any(row.get("reference_name") == self.assignment.name for row in items_two))

        frappe.set_user(self.reviewer_one)
        result = submit_applicant_review_assignment(
            assignment=self.assignment.name,
            decision="Recommend Admit",
            notes="Looks complete.",
        )
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "processed")

        self.assignment.reload()
        self.assertEqual(self.assignment.status, "Done")
        self.assertEqual(self.assignment.decision, "Recommend Admit")

        frappe.set_user(self.reviewer_two)
        items_after = list_focus_items(open_only=1, limit=50, offset=0)
        self.assertFalse(any(row.get("reference_name") == self.assignment.name for row in items_after))

    def test_role_holder_can_claim_role_assignment(self):
        frappe.set_user(self.reviewer_two)
        result = claim_applicant_review_assignment(assignment=self.assignment.name)
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "processed")

        self.assignment.reload()
        self.assertEqual((self.assignment.assigned_to_user or "").strip(), self.reviewer_two)
        self.assertEqual((self.assignment.assigned_to_role or "").strip(), "")

        items_two = list_focus_items(open_only=1, limit=50, offset=0)
        self.assertTrue(any(row.get("reference_name") == self.assignment.name for row in items_two))

        frappe.set_user(self.reviewer_one)
        items_one = list_focus_items(open_only=1, limit=50, offset=0)
        self.assertFalse(any(row.get("reference_name") == self.assignment.name for row in items_one))

    def test_role_holder_can_reassign_role_assignment_to_role_member(self):
        frappe.set_user(self.reviewer_one)
        result = reassign_applicant_review_assignment(
            assignment=self.assignment.name,
            reassign_to_user=self.reviewer_two,
        )
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "processed")

        self.assignment.reload()
        self.assertEqual((self.assignment.assigned_to_user or "").strip(), self.reviewer_two)
        self.assertEqual((self.assignment.assigned_to_role or "").strip(), "")

        frappe.set_user(self.reviewer_two)
        items_two = list_focus_items(open_only=1, limit=50, offset=0)
        self.assertTrue(any(row.get("reference_name") == self.assignment.name for row in items_two))

        frappe.set_user(self.reviewer_one)
        items_one = list_focus_items(open_only=1, limit=50, offset=0)
        self.assertFalse(any(row.get("reference_name") == self.assignment.name for row in items_one))

    def test_reassign_rejects_target_without_required_role(self):
        target_user = make_user()
        self._created.append(("User", target_user.name))

        frappe.set_user(self.reviewer_one)
        with self.assertRaises(frappe.ValidationError):
            reassign_applicant_review_assignment(
                assignment=self.assignment.name,
                reassign_to_user=target_user.name,
            )

    def test_get_focus_context_returns_secure_download_url_for_document_item_file(self):
        focus_role = "Academic Assistant"
        focus_reviewer = self._make_user_with_role(focus_role)
        assignment, file_doc = self._create_document_item_assignment_with_file(role_name=focus_role)

        frappe.set_user(focus_reviewer)
        focus_rows = list_focus_items(open_only=1, limit=50, offset=0)
        focus_item = next((row for row in focus_rows if row.get("reference_name") == assignment.name), None)
        self.assertIsNotNone(focus_item)

        ctx = get_focus_context(focus_item_id=focus_item.get("id"))
        preview = (ctx.get("review_assignment") or {}).get("preview") or {}
        preview_url = (preview.get("file_url") or "").strip()

        self.assertTrue(preview_url)
        self.assertNotIn("/private/files/", preview_url)

        parsed = urlparse(preview_url)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.focus.download_applicant_review_file")
        query = parse_qs(parsed.query)
        self.assertEqual((query.get("assignment") or [None])[0], assignment.name)

        frappe.local.response = {}
        download_applicant_review_file(assignment=assignment.name)
        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), file_doc.file_name)
        self.assertEqual(frappe.local.response.get("filecontent"), b"focus-file")

    def test_download_applicant_review_file_requires_assignment_membership(self):
        focus_role = "Academic Assistant"
        self._make_user_with_role(focus_role)
        assignment, _ = self._create_document_item_assignment_with_file(role_name=focus_role)

        outsider = make_user()
        self._created.append(("User", outsider.name))

        frappe.set_user(outsider.name)
        with self.assertRaises(frappe.PermissionError):
            download_applicant_review_file(assignment=assignment.name)

    def test_admissions_user_is_redirected_away_from_document_item_focus_work(self):
        assignment, _ = self._create_document_item_assignment_with_file(role_name=self.role_name)

        frappe.set_user(self.reviewer_one)
        focus_rows = list_focus_items(open_only=1, limit=50, offset=0)
        self.assertFalse(any(row.get("reference_name") == assignment.name for row in focus_rows))

        with self.assertRaises(frappe.PermissionError):
            claim_applicant_review_assignment(assignment=assignment.name)

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

    def _make_user_with_role(self, role: str) -> str:
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
        frappe.set_user(self.reviewer_one)
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Focus",
                "last_name": f"Applicant-{frappe.generate_hash(length=5)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        frappe.set_user("Administrator")
        return doc

    def _create_document_type(self, organization: str, school: str) -> str:
        code = f"focus_doc_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": f"Type {code}",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "classification_slot": f"admissions_{frappe.scrub(code)}",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name

    def _create_applicant_document(self, student_applicant: str, document_type: str):
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": student_applicant,
                "document_type": document_type,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", doc.name))
        return doc

    def _create_document_item(self, applicant_document: str):
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_document,
                "item_key": f"focus_item_{frappe.generate_hash(length=6)}",
                "item_label": "Focus Review File",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", doc.name))
        return doc

    def _attach_private_file(self, target_name: str):
        doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"focus-{frappe.generate_hash(length=6)}.txt",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": target_name,
                "is_private": 1,
                "content": b"focus-file",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", doc.name))
        return doc

    def _create_document_item_assignment_with_file(self, role_name: str):
        document_type = self._create_document_type(self.organization, self.school)
        applicant_document = self._create_applicant_document(self.student_applicant.name, document_type)
        document_item = self._create_document_item(applicant_document.name)
        file_doc = self._attach_private_file(document_item.name)
        assignment = self._create_role_assignment(
            self.student_applicant.name,
            role_name,
            target_type="Applicant Document Item",
            target_name=document_item.name,
        )
        return assignment, file_doc

    def _create_role_assignment(
        self,
        student_applicant: str,
        role_name: str,
        target_type: str = "Student Applicant",
        target_name: str | None = None,
    ):
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "target_type": target_type,
                "target_name": target_name or student_applicant,
                "student_applicant": student_applicant,
                "assigned_to_role": role_name,
                "status": "Open",
                "source_event": "application_submitted",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", doc.name))
        return doc
