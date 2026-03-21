# ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py
# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.doctype.student_applicant.student_applicant import academic_year_intent_query


class TestStudentApplicant(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self._auto_hydrate_setting_before = frappe.db.get_single_value(
            "Admission Settings", "auto_hydrate_enrollment_request_after_promotion"
        )
        frappe.db.set_single_value("Admission Settings", "auto_hydrate_enrollment_request_after_promotion", 1)
        self._ensure_role("Admissions Applicant")
        self._ensure_role("Student")
        self._ensure_role("Guardian")
        self._ensure_gender("Female")
        self._ensure_gender("Male")
        self._ensure_gender("Other")
        self._ensure_admissions_role("Administrator", "Admission Manager")
        frappe.clear_cache(user="Administrator")
        self.staff_user = self._create_user("Admissions", "Staff", add_role="Admission Manager")
        frappe.set_user(self.staff_user.name)
        self.org = self._create_org()
        self.parent_school = self._create_school("Admissions Root", "AR", self.org, is_group=1)
        self.leaf_school = self._create_school("Admissions Leaf", "AL", self.org, parent=self.parent_school, is_group=0)
        self._create_employee_for_user(
            self.staff_user.name,
            first_name="Admissions",
            last_name="Staff",
            organization=self.org,
            school=self.leaf_school,
        )

        self.visible_ay = self._create_academic_year(self.leaf_school, "2025-2026", archived=0, visible=1)
        self.archived_ay = self._create_academic_year(self.leaf_school, "2024-2025", archived=1, visible=1)
        self.hidden_ay = self._create_academic_year(self.leaf_school, "2023-2024", archived=0, visible=0)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value(
            "Admission Settings",
            "auto_hydrate_enrollment_request_after_promotion",
            0 if self._auto_hydrate_setting_before in (None, "") else self._auto_hydrate_setting_before,
        )
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
        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.reload()
        self.assertEqual(applicant.application_status, "Submitted")
        self.assertTrue(bool(applicant.submitted_at))

        applicant.mark_under_review()
        applicant.reload()
        self.assertEqual(applicant.application_status, "Under Review")

    def test_submit_application_allows_invited_without_manual_in_progress_step(self):
        applicant = self._create_student_applicant()
        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()

        applicant.submit_application()
        applicant.reload()

        self.assertEqual(applicant.application_status, "Submitted")
        self.assertTrue(bool(applicant.submitted_at))

    def test_submit_application_allows_missing_info_without_manual_in_progress_step(self):
        applicant = self._create_student_applicant()
        applicant.db_set("application_status", "Missing Info", update_modified=False)
        applicant.reload()

        applicant.submit_application()
        applicant.reload()

        self.assertEqual(applicant.application_status, "Submitted")
        self.assertTrue(bool(applicant.submitted_at))

    def test_reject_disables_portal_user(self):
        user = self._create_user("Applicant", "Portal", add_role="Admissions Applicant")
        applicant = self._create_student_applicant()
        applicant.flags.from_applicant_invite = True
        applicant.applicant_user = user.name
        applicant.save(ignore_permissions=True)

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.reject_application("Not eligible")

        user.reload()
        self.assertEqual(user.enabled, 0)

    def test_has_required_interviews_returns_recent_items(self):
        applicant = self._create_student_applicant()
        interviewer_user = self._create_user("Interview", "Reviewer")

        older_interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": applicant.name,
                "interview_date": "2026-03-01",
                "interview_start": "2026-03-01 09:00:00",
                "interview_end": "2026-03-01 09:30:00",
                "interview_type": "Family",
                "interviewers": [
                    {"interviewer": self.staff_user.name},
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", older_interview.name))
        recent_interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": applicant.name,
                "interview_date": "2026-03-02",
                "interview_start": "2026-03-02 10:00:00",
                "interview_end": "2026-03-02 10:45:00",
                "interview_type": "Student",
                "interviewers": [
                    {"interviewer": self.staff_user.name},
                    {"interviewer": interviewer_user.name},
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", recent_interview.name))
        recent_feedback = frappe.get_doc(
            {
                "doctype": "Applicant Interview Feedback",
                "applicant_interview": recent_interview.name,
                "student_applicant": applicant.name,
                "interviewer_user": interviewer_user.name,
                "feedback_status": "Submitted",
                "strengths": "Clear communication",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview Feedback", recent_feedback.name))

        payload = applicant.has_required_interviews()
        self.assertEqual(payload.get("count"), 2)
        self.assertTrue(payload.get("ok"))
        items = payload.get("items") or []
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].get("name"), recent_interview.name)
        self.assertEqual(items[1].get("name"), older_interview.name)
        self.assertEqual(items[0].get("feedback_status_label"), "1/2 submitted")
        self.assertEqual(items[1].get("feedback_status_label"), "0/1 submitted")

        recent_interviewers = items[0].get("interviewers") or []
        self.assertEqual(
            [row.get("user") for row in recent_interviewers],
            [self.staff_user.name, interviewer_user.name],
        )
        staff_label = frappe.db.get_value("User", self.staff_user.name, "full_name") or self.staff_user.name
        reviewer_label = frappe.db.get_value("User", interviewer_user.name, "full_name") or interviewer_user.name
        expected_recent_labels = [
            staff_label,
            reviewer_label,
        ]
        self.assertEqual(items[0].get("interviewer_labels"), expected_recent_labels)

    def test_promotion_copies_approved_applicant_document_files(self):
        doc_type = self._create_applicant_document_type(code="application_form")
        applicant = self._create_student_applicant(student_joining_date=frappe.utils.nowdate())
        self._create_applicant_health_profile(applicant.name)

        frappe.set_user("Administrator")
        try:
            applicant_doc = frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": applicant.name,
                    "document_type": doc_type,
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.set_user(self.staff_user.name)
        self._created.append(("Applicant Document", applicant_doc.name))

        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_doc.name,
                "item_key": "application_form",
                "item_label": "Application Form",
                "review_status": "Approved",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", item.name))

        source_file = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": item.name,
                "file_name": "supporting.txt",
                "is_private": 1,
                "content": b"promote-me",
            }
        )
        source_file.insert(ignore_permissions=True)
        self._created.append(("File", source_file.name))

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

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

    def test_required_document_type_from_parent_school_applies_to_child_school_applicant(self):
        code = f"parent_req_{frappe.generate_hash(length=6)}"
        doc_type = self._create_applicant_document_type(
            code=code,
            school=self.parent_school,
            is_required=1,
        )
        applicant = self._create_student_applicant()

        missing_payload = applicant.has_required_documents()
        self.assertFalse(missing_payload.get("ok"))
        self.assertIn(code, missing_payload.get("missing") or [])

        frappe.set_user("Administrator")
        try:
            applicant_doc = frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": applicant.name,
                    "document_type": doc_type,
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.set_user(self.staff_user.name)
        self._created.append(("Applicant Document", applicant_doc.name))

        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_doc.name,
                "item_key": "required_1",
                "item_label": "Required Document",
                "review_status": "Approved",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", item.name))

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": item.name,
                "file_name": "required.txt",
                "is_private": 1,
                "content": b"required-file",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        approved_payload = applicant.has_required_documents()
        self.assertTrue(approved_payload.get("ok"))
        self.assertNotIn(code, approved_payload.get("missing") or [])
        self.assertNotIn(code, approved_payload.get("unapproved") or [])

    def test_has_required_documents_returns_secure_file_links(self):
        code = f"secure_doc_{frappe.generate_hash(length=6)}"
        doc_type = self._create_applicant_document_type(code=code, is_required=1)
        applicant = self._create_student_applicant()

        frappe.set_user("Administrator")
        try:
            applicant_doc = frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": applicant.name,
                    "document_type": doc_type,
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.set_user(self.staff_user.name)
        self._created.append(("Applicant Document", applicant_doc.name))

        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_doc.name,
                "item_key": "required_secure_1",
                "item_label": "Required Document",
                "review_status": "Approved",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", item.name))

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": item.name,
                "file_name": "required-secure.txt",
                "is_private": 1,
                "content": b"required-secure-file",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        payload = applicant.has_required_documents()
        required_rows = payload.get("required_rows") or []
        target_row = next((row for row in required_rows if row.get("document_type") == doc_type), None)
        self.assertIsNotNone(target_row)
        secure_url = (target_row.get("file_url") or "").strip()

        self.assertTrue(secure_url)
        self.assertNotIn("/private/files/", secure_url)

        parsed = urlparse(secure_url)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_admissions_file")
        query = parse_qs(parsed.query)
        self.assertEqual((query.get("file") or [None])[0], file_doc.name)
        self.assertEqual((query.get("context_doctype") or [None])[0], "Student Applicant")
        self.assertEqual((query.get("context_name") or [None])[0], applicant.name)

    def test_repeatable_required_document_accepts_requirement_override_for_readiness(self):
        code = f"repeatable_doc_{frappe.generate_hash(length=6)}"
        doc_type = self._create_applicant_document_type(
            code=code,
            is_required=1,
            is_repeatable=1,
            min_items_required=2,
        )
        applicant = self._create_student_applicant()

        frappe.set_user("Administrator")
        try:
            applicant_doc = frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": applicant.name,
                    "document_type": doc_type,
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.set_user(self.staff_user.name)
        self._created.append(("Applicant Document", applicant_doc.name))
        applicant.set_document_requirement_override(
            applicant_document=applicant_doc.name,
            requirement_override="Waived",
            override_reason="School accepted formal waiver.",
        )

        payload = applicant.has_required_documents()
        self.assertTrue(payload.get("ok"))
        self.assertNotIn(code, payload.get("missing") or [])
        self.assertNotIn(code, payload.get("unapproved") or [])

        required_rows = payload.get("required_rows") or []
        row = next((item for item in required_rows if item.get("document_type") == doc_type), None)
        self.assertIsNotNone(row)
        self.assertEqual(row.get("review_status"), "Waived")
        self.assertEqual(int(row.get("approved_count") or 0), 0)
        self.assertEqual(int(row.get("required_count") or 0), 2)

    def test_uploaded_rows_include_each_uploaded_document_item(self):
        code = f"uploaded_rows_doc_{frappe.generate_hash(length=6)}"
        doc_type = self._create_applicant_document_type(
            code=code,
            is_required=1,
            is_repeatable=1,
            min_items_required=2,
        )
        applicant = self._create_student_applicant()

        frappe.set_user("Administrator")
        try:
            applicant_doc = frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": applicant.name,
                    "document_type": doc_type,
                    "review_status": "Pending",
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.set_user(self.staff_user.name)
        self._created.append(("Applicant Document", applicant_doc.name))

        created_item_labels = []
        for index in (1, 2):
            item_label = f"Transcript Variant {index}"
            item = frappe.get_doc(
                {
                    "doctype": "Applicant Document Item",
                    "applicant_document": applicant_doc.name,
                    "item_key": f"uploaded_variant_{index}",
                    "item_label": item_label,
                    "review_status": "Pending",
                }
            ).insert(ignore_permissions=True)
            self._created.append(("Applicant Document Item", item.name))

            file_doc = frappe.get_doc(
                {
                    "doctype": "File",
                    "attached_to_doctype": "Applicant Document Item",
                    "attached_to_name": item.name,
                    "file_name": f"uploaded-variant-{index}.txt",
                    "is_private": 1,
                    "content": f"uploaded-variant-{index}".encode(),
                }
            ).insert(ignore_permissions=True)
            self._created.append(("File", file_doc.name))
            created_item_labels.append(item_label)

        payload = applicant.has_required_documents()
        uploaded_rows = payload.get("uploaded_rows") or []
        target_rows = [row for row in uploaded_rows if row.get("document_type") == doc_type]
        self.assertEqual(len(target_rows), 2)

        labels = {row.get("item_label") for row in target_rows}
        self.assertEqual(labels, set(created_item_labels))
        self.assertTrue(all((row.get("file_url") or "").strip() for row in target_rows))

    def test_review_document_submission_updates_item_and_cancels_open_assignments(self):
        code = f"review_submission_doc_{frappe.generate_hash(length=6)}"
        doc_type = self._create_applicant_document_type(code=code, is_required=1)
        applicant = self._create_student_applicant()

        frappe.set_user("Administrator")
        try:
            applicant_document = frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": applicant.name,
                    "document_type": doc_type,
                    "review_status": "Pending",
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.set_user(self.staff_user.name)
        self._created.append(("Applicant Document", applicant_document.name))

        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_document.name,
                "item_key": "passport_primary",
                "item_label": "Passport PDF",
                "review_status": "Pending",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", item.name))

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": item.name,
                "file_name": "passport.txt",
                "is_private": 1,
                "content": b"passport",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        assignment_one = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "target_type": "Applicant Document Item",
                "target_name": item.name,
                "student_applicant": applicant.name,
                "assigned_to_user": self.staff_user.name,
                "status": "Open",
                "source_event": "document_uploaded",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment_one.name))
        assignment_two = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "target_type": "Applicant Document Item",
                "target_name": item.name,
                "student_applicant": applicant.name,
                "assigned_to_role": "Admission Manager",
                "status": "Open",
                "source_event": "document_uploaded",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment_two.name))

        result = applicant.review_document_submission(
            applicant_document_item=item.name,
            decision="Approved",
        )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("decision"), "Approved")

        item.reload()
        self.assertEqual(item.review_status, "Approved")
        self.assertEqual((item.reviewed_by or "").strip(), self.staff_user.name)
        self.assertTrue(bool(item.reviewed_on))

        applicant_document.reload()
        self.assertEqual(applicant_document.review_status, "Approved")

        assignment_one.reload()
        assignment_two.reload()
        self.assertEqual(assignment_one.status, "Cancelled")
        self.assertEqual(assignment_two.status, "Cancelled")
        self.assertEqual((assignment_one.decided_by or "").strip(), self.staff_user.name)

        documents_payload = result.get("documents") or {}
        uploaded_rows = documents_payload.get("uploaded_rows") or []
        target_row = next((row for row in uploaded_rows if row.get("applicant_document_item") == item.name), None)
        self.assertIsNotNone(target_row)
        self.assertEqual(target_row.get("review_status"), "Approved")

    def test_review_document_submission_requires_notes_for_follow_up_and_rejection(self):
        code = f"review_note_doc_{frappe.generate_hash(length=6)}"
        doc_type = self._create_applicant_document_type(code=code, is_required=1)
        applicant = self._create_student_applicant()

        frappe.set_user("Administrator")
        try:
            applicant_document = frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": applicant.name,
                    "document_type": doc_type,
                    "review_status": "Pending",
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.set_user(self.staff_user.name)
        self._created.append(("Applicant Document", applicant_document.name))

        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_document.name,
                "item_key": "transcript_primary",
                "item_label": "Transcript PDF",
                "review_status": "Pending",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", item.name))

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": item.name,
                "file_name": "transcript.txt",
                "is_private": 1,
                "content": b"transcript",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        with self.assertRaises(frappe.ValidationError):
            applicant.review_document_submission(
                applicant_document_item=item.name,
                decision="Needs Follow-Up",
            )

        with self.assertRaises(frappe.ValidationError):
            applicant.review_document_submission(
                applicant_document_item=item.name,
                decision="Rejected",
            )

    def test_profile_information_reports_missing_required_fields(self):
        applicant = self._create_student_applicant()
        payload = applicant.has_required_profile_information()
        self.assertFalse(payload.get("ok"))
        self.assertIn("Date of Birth", payload.get("missing") or [])
        self.assertIn("First Language", payload.get("missing") or [])
        self.assertIn("Nationality", payload.get("missing") or [])
        self.assertNotIn("Joining Date", payload.get("missing") or [])

    def test_readiness_snapshot_does_not_block_on_health_when_school_setting_disabled(self):
        applicant = self._create_student_applicant()
        frappe.db.set_value(
            "School",
            applicant.school,
            "require_health_profile_for_approval",
            0,
            update_modified=False,
        )
        frappe.clear_cache()

        with (
            patch.object(
                applicant, "has_required_policies", return_value={"ok": True, "missing": [], "required": [], "rows": []}
            ),
            patch.object(
                applicant,
                "has_required_documents",
                return_value={
                    "ok": True,
                    "missing": [],
                    "unapproved": [],
                    "required": [],
                    "required_rows": [],
                    "uploaded_rows": [],
                },
            ),
            patch.object(
                applicant,
                "health_review_complete",
                return_value={
                    "ok": False,
                    "status": "missing",
                    "profile_name": None,
                    "review_status": None,
                    "reviewed_by": None,
                    "reviewed_on": None,
                    "declared_complete": False,
                    "declared_by": None,
                    "declared_on": None,
                },
            ),
            patch.object(applicant, "has_required_interviews", return_value={"ok": False, "count": 0, "items": []}),
            patch.object(
                applicant,
                "has_required_profile_information",
                return_value={"ok": True, "missing": [], "required": [], "fields": {}},
            ),
            patch.object(
                applicant,
                "has_required_recommendations",
                return_value={
                    "ok": True,
                    "required_total": 0,
                    "received_total": 0,
                    "requested_total": 0,
                    "missing": [],
                    "rows": [],
                    "state": "optional",
                    "counts": {},
                },
            ),
            patch.object(applicant, "get_review_assignments_summary", return_value={}),
        ):
            snapshot = applicant.get_readiness_snapshot()

        self.assertTrue(snapshot.get("ready"))
        self.assertFalse((snapshot.get("health") or {}).get("required_for_approval"))
        self.assertFalse(
            any("Health profile is missing or not cleared." in str(item) for item in (snapshot.get("issues") or []))
        )

    def test_readiness_snapshot_blocks_on_health_when_school_setting_enabled(self):
        applicant = self._create_student_applicant()
        frappe.db.set_value(
            "School",
            applicant.school,
            "require_health_profile_for_approval",
            1,
            update_modified=False,
        )
        frappe.clear_cache()

        with (
            patch.object(
                applicant, "has_required_policies", return_value={"ok": True, "missing": [], "required": [], "rows": []}
            ),
            patch.object(
                applicant,
                "has_required_documents",
                return_value={
                    "ok": True,
                    "missing": [],
                    "unapproved": [],
                    "required": [],
                    "required_rows": [],
                    "uploaded_rows": [],
                },
            ),
            patch.object(
                applicant,
                "health_review_complete",
                return_value={
                    "ok": False,
                    "status": "missing",
                    "profile_name": None,
                    "review_status": None,
                    "reviewed_by": None,
                    "reviewed_on": None,
                    "declared_complete": False,
                    "declared_by": None,
                    "declared_on": None,
                },
            ),
            patch.object(applicant, "has_required_interviews", return_value={"ok": False, "count": 0, "items": []}),
            patch.object(
                applicant,
                "has_required_profile_information",
                return_value={"ok": True, "missing": [], "required": [], "fields": {}},
            ),
            patch.object(
                applicant,
                "has_required_recommendations",
                return_value={
                    "ok": True,
                    "required_total": 0,
                    "received_total": 0,
                    "requested_total": 0,
                    "missing": [],
                    "rows": [],
                    "state": "optional",
                    "counts": {},
                },
            ),
            patch.object(applicant, "get_review_assignments_summary", return_value={}),
        ):
            snapshot = applicant.get_readiness_snapshot()

        self.assertFalse(snapshot.get("ready"))
        self.assertTrue((snapshot.get("health") or {}).get("required_for_approval"))
        self.assertTrue(
            any("Health profile is missing or not cleared." in str(item) for item in (snapshot.get("issues") or []))
        )

    def test_promotion_requires_joining_date(self):
        applicant = self._create_student_applicant()
        self._create_applicant_health_profile(applicant.name)

        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        with self.assertRaises(frappe.ValidationError):
            applicant.promote_to_student()

    def test_promotion_copies_profile_information_to_student(self):
        language = self._get_or_create_language_xtra()
        country = self._get_any_country()
        if not country:
            self.skipTest("Country records are required for this profile mapping test.")
        cohort = self._create_student_cohort()
        student_house = self._create_student_house()

        applicant = self._create_student_applicant(
            student_preferred_name="Ada",
            student_date_of_birth="2014-01-01",
            student_gender="Female",
            student_mobile_number="+14155550199",
            student_joining_date=frappe.utils.nowdate(),
            student_first_language=language,
            student_second_language=language,
            student_nationality=country,
            student_second_nationality=country,
            residency_status="Local Resident",
            cohort=cohort,
            student_house=student_house,
        )
        self._create_applicant_health_profile(applicant.name)

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))
        student = frappe.get_doc("Student", student_name)
        self.assertEqual(student.student_preferred_name, "Ada")
        self.assertEqual(str(student.student_date_of_birth), "2014-01-01")
        self.assertEqual(student.student_gender, "Female")
        self.assertEqual(student.student_mobile_number, "+14155550199")
        self.assertEqual(str(student.student_joining_date), str(applicant.student_joining_date))
        self.assertEqual(student.student_first_language, language)
        self.assertEqual(student.student_second_language, language)
        self.assertEqual(student.student_nationality, country)
        self.assertEqual(student.student_second_nationality, country)
        self.assertEqual(student.residency_status, "Local Resident")
        self.assertEqual(student.cohort, cohort)
        self.assertEqual(student.student_house, student_house)
        self.assertEqual(student.anchor_school, applicant.school)

    def test_misconfigured_required_document_type_is_still_required_in_readiness(self):
        code = f"misconfigured_req_{frappe.generate_hash(length=6)}"
        doc_type = self._create_applicant_document_type(
            code=code,
            school=self.parent_school,
            is_required=1,
            is_active=1,
        )
        frappe.db.set_value("Applicant Document Type", doc_type, "classification_slot", "", update_modified=False)

        applicant = self._create_student_applicant()
        payload = applicant.has_required_documents()
        self.assertFalse(payload.get("ok"))
        self.assertIn(code, payload.get("required") or [])
        self.assertIn(code, payload.get("missing") or [])

    def test_promotion_copies_health_profile_to_student_patient(self):
        applicant = self._create_student_applicant(student_joining_date=frappe.utils.nowdate())
        self._create_applicant_health_profile(
            applicant.name,
            blood_group="O Positive",
            allergies=1,
            food_allergies="Peanuts",
            asthma="Mild",
            vaccinations=[
                {
                    "vaccine_name": "MMR",
                    "date": frappe.utils.nowdate(),
                    "vaccination_proof": "/files/mmr-proof.png",
                    "additional_notes": "Dose 1",
                }
            ],
        )

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        student_patient_name = frappe.db.get_value("Student Patient", {"student": student_name}, "name")
        self.assertTrue(student_patient_name)
        self._created.append(("Student Patient", student_patient_name))

        student_patient = frappe.get_doc("Student Patient", student_patient_name)
        self.assertEqual(student_patient.blood_group, "O Positive")
        self.assertEqual(int(student_patient.allergies or 0), 1)
        self.assertEqual(student_patient.food_allergies, "Peanuts")
        self.assertEqual(student_patient.asthma, "Mild")
        self.assertEqual(len(student_patient.vaccinations or []), 1)
        self.assertEqual(student_patient.vaccinations[0].vaccine_name, "MMR")
        self.assertEqual(str(student_patient.vaccinations[0].date), frappe.utils.nowdate())

    def test_upgrade_identity_requires_active_enrollment(self):
        applicant = self._create_student_applicant(student_joining_date=frappe.utils.nowdate())
        self._create_applicant_health_profile(applicant.name)

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        with self.assertRaises(frappe.ValidationError):
            applicant.upgrade_identity()

    def test_program_enrollment_creation_auto_upgrades_identity_for_promoted_applicant(self):
        offer_context = self._create_offer_context()
        applicant_user = self._create_user("Applicant", "Auto Upgrade", add_role="Admissions Applicant")
        applicant = self._create_student_applicant(
            student_joining_date=frappe.utils.nowdate(),
            academic_year=self.visible_ay,
            program=offer_context["program"].name,
            program_offering=offer_context["offering"].name,
        )
        self._create_applicant_health_profile(applicant.name)

        applicant.flags.from_applicant_invite = True
        applicant.flags.from_contact_sync = True
        applicant.applicant_user = applicant_user.name
        applicant.applicant_email = applicant_user.name
        applicant.portal_account_email = applicant_user.name
        applicant.save(ignore_permissions=True)

        self._advance_applicant_to_approved(applicant)

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        roles_before = set(
            frappe.get_all(
                "Has Role",
                filters={"parent": applicant_user.name, "parenttype": "User"},
                pluck="role",
            )
        )
        self.assertIn("Admissions Applicant", roles_before)
        self.assertNotIn("Student", roles_before)

        enrollment = frappe.get_doc(
            {
                "doctype": "Program Enrollment",
                "student": student_name,
                "program": offer_context["program"].name,
                "program_offering": offer_context["offering"].name,
                "academic_year": self.visible_ay,
                "enrollment_date": frappe.utils.nowdate(),
                "enrollment_source": "Admin",
                "enrollment_override_reason": "Auto identity upgrade test",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program Enrollment", enrollment.name))

        roles_after = set(
            frappe.get_all(
                "Has Role",
                filters={"parent": applicant_user.name, "parenttype": "User"},
                pluck="role",
            )
        )
        self.assertIn("Student", roles_after)
        self.assertNotIn("Admissions Applicant", roles_after)

    def test_upgrade_identity_is_idempotent_and_provisions_roles(self):
        applicant_user = self._create_user("Applicant", "Portal", add_role="Admissions Applicant")
        guardian_user = self._create_user("Guardian", "Portal")
        applicant = self._create_student_applicant(student_joining_date=frappe.utils.nowdate())
        self._create_applicant_health_profile(applicant.name)

        guardian = self._create_guardian(
            first_name="Parent",
            last_name="One",
            email=guardian_user.name,
            mobile="+14155550123",
            user=guardian_user.name,
        )
        applicant.append(
            "guardians",
            {
                "guardian": guardian.name,
                "relationship": "Mother",
                "is_primary": 1,
                "can_consent": 1,
            },
        )
        applicant.flags.from_applicant_invite = True
        applicant.flags.from_contact_sync = True
        applicant.applicant_user = applicant_user.name
        applicant.applicant_email = applicant_user.name
        applicant.portal_account_email = applicant_user.name
        applicant.save(ignore_permissions=True)

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        original_exists = frappe.db.exists

        def exists_with_enrollment(doctype, filters=None, *args, **kwargs):
            if doctype == "Program Enrollment" and isinstance(filters, dict):
                if filters.get("student") == student_name and int(filters.get("archived") or 0) == 0:
                    return "PE-MOCK-0001"
            return original_exists(doctype, filters, *args, **kwargs)

        with patch.object(frappe.db, "exists", side_effect=exists_with_enrollment):
            first = applicant.upgrade_identity()
            second = applicant.upgrade_identity()

        self.assertTrue(first.get("ok"))
        self.assertEqual(second.get("guardians_added"), 0)

        student = frappe.get_doc("Student", student_name)
        guardian_links = [row.guardian for row in (student.get("guardians") or []) if row.guardian == guardian.name]
        self.assertEqual(len(guardian_links), 1)
        consent_values = [
            int(row.can_consent or 0) for row in (student.get("guardians") or []) if row.guardian == guardian.name
        ]
        self.assertEqual(consent_values, [1])

        user = frappe.get_doc("User", applicant_user.name)
        self.assertEqual(int(user.enabled or 0), 1)
        role_names = set(
            frappe.get_all(
                "Has Role",
                filters={"parent": applicant_user.name, "parenttype": "User"},
                pluck="role",
            )
        )
        self.assertIn("Student", role_names)
        self.assertNotIn("Admissions Applicant", role_names)
        self.assertNotIn("Guardian", role_names)

        guardian_role_names = set(
            frappe.get_all(
                "Has Role",
                filters={"parent": guardian_user.name, "parenttype": "User"},
                pluck="role",
            )
        )
        self.assertIn("Guardian", guardian_role_names)

    def test_upgrade_identity_keeps_applicant_user_as_student_when_no_guardians_exist(self):
        applicant_user = self._create_user("Applicant", "Only", add_role="Admissions Applicant")
        applicant = self._create_student_applicant(student_joining_date=frappe.utils.nowdate())
        self._create_applicant_health_profile(applicant.name)

        applicant.flags.from_applicant_invite = True
        applicant.flags.from_contact_sync = True
        applicant.applicant_user = applicant_user.name
        applicant.applicant_email = applicant_user.name
        applicant.portal_account_email = applicant_user.name
        applicant.save(ignore_permissions=True)

        self._advance_applicant_to_approved(applicant)

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        original_exists = frappe.db.exists

        def exists_with_enrollment(doctype, filters=None, *args, **kwargs):
            if doctype == "Program Enrollment" and isinstance(filters, dict):
                if filters.get("student") == student_name and int(filters.get("archived") or 0) == 0:
                    return "PE-MOCK-0003"
            return original_exists(doctype, filters, *args, **kwargs)

        with patch.object(frappe.db, "exists", side_effect=exists_with_enrollment):
            result = applicant.upgrade_identity()

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("guardians_linked") or [], [])

        student = frappe.get_doc("Student", student_name)
        self.assertEqual(len(student.get("guardians") or []), 0)

        role_names = set(
            frappe.get_all(
                "Has Role",
                filters={"parent": applicant_user.name, "parenttype": "User"},
                pluck="role",
            )
        )
        self.assertIn("Student", role_names)
        self.assertNotIn("Admissions Applicant", role_names)
        self.assertNotIn("Guardian", role_names)

    def test_upgrade_identity_creates_guardian_from_applicant_guardian_profile_row(self):
        applicant = self._create_student_applicant(student_joining_date=frappe.utils.nowdate())
        self._create_applicant_health_profile(applicant.name)

        guardian_email = f"guardian-{frappe.generate_hash(length=8)}@example.com"
        applicant.append(
            "guardians",
            {
                "relationship": "Father",
                "can_consent": 1,
                "guardian_first_name": "Profile",
                "guardian_last_name": "Guardian",
                "guardian_email": guardian_email,
                "guardian_mobile_phone": "+14155550155",
                "guardian_gender": "Male",
            },
        )
        applicant.save(ignore_permissions=True)

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        original_exists = frappe.db.exists

        def exists_with_enrollment(doctype, filters=None, *args, **kwargs):
            if doctype == "Program Enrollment" and isinstance(filters, dict):
                if filters.get("student") == student_name and int(filters.get("archived") or 0) == 0:
                    return "PE-MOCK-0002"
            return original_exists(doctype, filters, *args, **kwargs)

        with patch.object(frappe.db, "exists", side_effect=exists_with_enrollment):
            result = applicant.upgrade_identity()

        self.assertTrue(result.get("ok"))
        self.assertEqual(len(result.get("guardians_linked") or []), 1)

        guardian_name = frappe.db.get_value("Guardian", {"guardian_email": guardian_email}, "name")
        self.assertTrue(bool(guardian_name))
        self._created.append(("Guardian", guardian_name))

        student = frappe.get_doc("Student", student_name)
        linked_guardians = [row.guardian for row in (student.get("guardians") or [])]
        self.assertIn(guardian_name, linked_guardians)
        consent_values = [
            int(row.can_consent or 0) for row in (student.get("guardians") or []) if row.guardian == guardian_name
        ]
        self.assertEqual(consent_values, [1])

        contact_name = frappe.db.get_value("Contact Email", {"email_id": guardian_email}, "parent")
        self.assertTrue(bool(contact_name))
        self.assertTrue(
            bool(
                frappe.db.exists(
                    "Dynamic Link",
                    {
                        "parenttype": "Contact",
                        "parentfield": "links",
                        "parent": contact_name,
                        "link_doctype": "Student",
                        "link_name": student_name,
                    },
                )
            )
        )

    def test_promote_to_student_carries_non_signing_guardian_authority(self):
        guardian = self._create_guardian(
            first_name="Emergency",
            last_name="Guardian",
            email=f"emergency-{frappe.generate_hash(length=8)}@example.com",
            mobile="+14155550156",
        )
        applicant = self._create_student_applicant(student_joining_date=frappe.utils.nowdate())
        self._create_applicant_health_profile(applicant.name)
        applicant.append(
            "guardians",
            {
                "guardian": guardian.name,
                "relationship": "Aunt",
                "can_consent": 0,
            },
        )
        applicant.save(ignore_permissions=True)
        self._advance_applicant_to_approved(applicant)

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        student = frappe.get_doc("Student", student_name)
        consent_values = [
            int(row.can_consent or 0) for row in (student.get("guardians") or []) if row.guardian == guardian.name
        ]
        self.assertEqual(consent_values, [0])

    def test_promote_to_student_links_siblings_from_shared_guardian(self):
        shared_guardian = self._create_guardian(
            first_name="Shared",
            last_name="Guardian",
            email=f"shared-{frappe.generate_hash(length=8)}@example.com",
            mobile="+14155550124",
        )
        first_applicant = self._create_student_applicant(student_joining_date=frappe.utils.nowdate())
        second_applicant = self._create_student_applicant(student_joining_date=frappe.utils.nowdate())
        self._create_applicant_health_profile(first_applicant.name)
        self._create_applicant_health_profile(second_applicant.name)

        for applicant in (first_applicant, second_applicant):
            applicant.append(
                "guardians",
                {
                    "guardian": shared_guardian.name,
                    "relationship": "Mother",
                    "is_primary": 1,
                    "can_consent": 1,
                },
            )
            applicant.save(ignore_permissions=True)
            self._advance_applicant_to_approved(applicant)

        first_student_name = first_applicant.promote_to_student()
        second_student_name = second_applicant.promote_to_student()
        self._created.append(("Student", first_student_name))
        self._created.append(("Student", second_student_name))

        first_student = frappe.get_doc("Student", first_student_name)
        second_student = frappe.get_doc("Student", second_student_name)

        self.assertIn(second_student_name, [row.sibling for row in (first_student.get("siblings") or [])])
        self.assertIn(first_student_name, [row.sibling for row in (second_student.get("siblings") or [])])

    def test_promote_blocks_when_latest_enrollment_plan_is_not_accepted(self):
        offer_context = self._create_offer_context()
        applicant = self._create_student_applicant(
            student_joining_date=frappe.utils.nowdate(),
            academic_year=self.visible_ay,
            program=offer_context["program"].name,
            program_offering=offer_context["offering"].name,
        )
        self._create_applicant_health_profile(applicant.name)
        self._advance_applicant_to_approved(applicant)

        plan = frappe.get_doc(
            {
                "doctype": "Applicant Enrollment Plan",
                "student_applicant": applicant.name,
                "academic_year": self.visible_ay,
                "program": offer_context["program"].name,
                "program_offering": offer_context["offering"].name,
                "status": "Offer Declined",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Enrollment Plan", plan.name))

        with self.assertRaises(frappe.ValidationError):
            applicant.promote_to_student()

    def test_promote_auto_hydrates_request_from_accepted_enrollment_plan(self):
        offer_context = self._create_offer_context()
        applicant = self._create_student_applicant(
            student_joining_date=frappe.utils.nowdate(),
            academic_year=self.visible_ay,
            program=offer_context["program"].name,
            program_offering=offer_context["offering"].name,
        )
        self._create_applicant_health_profile(applicant.name)
        self._advance_applicant_to_approved(applicant)

        plan = frappe.get_doc(
            {
                "doctype": "Applicant Enrollment Plan",
                "student_applicant": applicant.name,
                "academic_year": self.visible_ay,
                "program": offer_context["program"].name,
                "program_offering": offer_context["offering"].name,
                "status": "Offer Accepted",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Enrollment Plan", plan.name))

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        plan.reload()
        self.assertEqual(plan.status, "Hydrated")
        self.assertEqual(plan.student, student_name)
        self.assertTrue(bool(plan.program_enrollment_request))

        request = frappe.get_doc("Program Enrollment Request", plan.program_enrollment_request)
        self._created.append(("Program Enrollment Request", request.name))

        self.assertEqual(request.student, student_name)
        self.assertEqual(request.program_offering, offer_context["offering"].name)
        self.assertEqual(request.source_student_applicant, applicant.name)
        self.assertEqual(request.source_applicant_enrollment_plan, plan.name)
        self.assertEqual([row.course for row in request.get("courses") or []], [offer_context["required_course"].name])

    def test_promote_auto_hydrates_request_appending_required_courses_after_explicit_optional_choices(self):
        offer_context = self._create_offer_context(include_optional_course=True)
        applicant = self._create_student_applicant(
            student_joining_date=frappe.utils.nowdate(),
            academic_year=self.visible_ay,
            program=offer_context["program"].name,
            program_offering=offer_context["offering"].name,
        )
        self._create_applicant_health_profile(applicant.name)
        self._advance_applicant_to_approved(applicant)

        plan = frappe.get_doc(
            {
                "doctype": "Applicant Enrollment Plan",
                "student_applicant": applicant.name,
                "academic_year": self.visible_ay,
                "program": offer_context["program"].name,
                "program_offering": offer_context["offering"].name,
                "status": "Offer Accepted",
                "courses": [
                    {
                        "course": offer_context["optional_course"].name,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Enrollment Plan", plan.name))

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        plan.reload()
        self.assertTrue(bool(plan.program_enrollment_request))
        request = frappe.get_doc("Program Enrollment Request", plan.program_enrollment_request)
        self._created.append(("Program Enrollment Request", request.name))

        self.assertEqual(
            [row.course for row in request.get("courses") or []],
            [offer_context["optional_course"].name, offer_context["required_course"].name],
        )

    def _ensure_admissions_role(self, user, role):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
            self._created.append(("Role", role))
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
        frappe.clear_cache(user=user)

    def _ensure_role(self, role):
        if frappe.db.exists("Role", role):
            return
        frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
        self._created.append(("Role", role))

    def _ensure_gender(self, gender_name: str):
        if frappe.db.exists("Gender", gender_name):
            return
        now = frappe.utils.now()
        frappe.db.sql(
            """
            INSERT INTO `tabGender` (`name`, `creation`, `modified`, `modified_by`, `owner`, `docstatus`, `idx`)
            VALUES (%s, %s, %s, %s, %s, 0, 0)
            """,
            (gender_name, now, now, "Administrator", "Administrator"),
        )
        self._created.append(("Gender", gender_name))

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
        start_year, end_year = academic_year_name.split("-", 1)
        doc = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": academic_year_name,
                "school": school,
                "year_start_date": f"{start_year}-08-01",
                "year_end_date": f"{end_year}-06-30",
                "archived": archived,
                "visible_to_admission": visible,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Academic Year", doc.name))
        return doc.name

    def _create_student_applicant(self, **overrides):
        seed = frappe.generate_hash(length=6)
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Test",
                "last_name": f"Applicant {seed}",
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
        frappe.clear_cache(user=user.name)
        return user

    def _create_employee_for_user(self, user: str, *, first_name: str, last_name: str, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": first_name,
                "employee_last_name": last_name,
                "employee_professional_email": user,
                "organization": organization,
                "school": school,
                "user_id": user,
                "date_of_joining": frappe.utils.nowdate(),
                "employment_status": "Active",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", doc.name))
        return doc

    def _create_guardian(self, *, first_name, last_name, email, mobile, user=None):
        doc = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": first_name,
                "guardian_last_name": last_name,
                "guardian_email": email,
                "guardian_mobile_phone": mobile,
                "user": user,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Guardian", doc.name))
        return doc

    def _create_student_cohort(self):
        name = f"Cohort {frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Student Cohort",
                "cohort_name": name,
                "cohort_abbreviation": name[:8],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Cohort", doc.name))
        return doc.name

    def _create_student_house(self):
        name = f"House {frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Student House",
                "house_name": name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student House", doc.name))
        return doc.name

    def _create_applicant_document_type(
        self,
        *,
        code,
        school=None,
        organization=None,
        is_required=0,
        is_active=1,
        is_repeatable=0,
        min_items_required=1,
    ):
        existing = frappe.db.get_value("Applicant Document Type", {"code": code}, "name")
        if existing:
            return existing
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": f"Type {code}",
                "organization": organization or self.org,
                "school": school or self.leaf_school,
                "is_active": is_active,
                "is_required": is_required,
                "is_repeatable": is_repeatable,
                "min_items_required": min_items_required,
                "classification_slot": f"admissions_{frappe.scrub(code)}",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name

    def _get_or_create_language_xtra(self) -> str:
        existing = frappe.get_all("Language Xtra", filters={"enabled": 1}, fields=["name"], limit=1)
        if existing:
            return existing[0]["name"]

        code = f"lng_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Language Xtra",
                "language_name": f"Language {code}",
                "language_code": code,
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Language Xtra", doc.name))
        return doc.name

    def _get_any_country(self) -> str | None:
        existing = frappe.get_all("Country", fields=["name"], limit=1, order_by="name asc")
        if not existing:
            return None
        return existing[0]["name"]

    def _create_applicant_health_profile(self, applicant_name, **overrides):
        frappe.set_user(self.staff_user.name)
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": applicant_name,
                "review_status": "Cleared",
                **overrides,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Health Profile", doc.name))
        return doc

    def _advance_applicant_to_approved(self, applicant):
        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()
        return applicant

    def _create_offer_context(self, include_optional_course=False):
        grade_scale = frappe.get_doc(
            {
                "doctype": "Grade Scale",
                "grade_scale_name": f"Scale {frappe.generate_hash(length=6)}",
                "boundaries": [
                    {"grade_code": "B-", "boundary_interval": 70},
                    {"grade_code": "C", "boundary_interval": 60},
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Grade Scale", grade_scale.name))

        required_course = frappe.get_doc(
            {
                "doctype": "Course",
                "course_name": f"Required {frappe.generate_hash(length=6)}",
                "status": "Active",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Course", required_course.name))

        optional_course = None
        if include_optional_course:
            optional_course = frappe.get_doc(
                {
                    "doctype": "Course",
                    "course_name": f"Optional {frappe.generate_hash(length=6)}",
                    "status": "Active",
                }
            ).insert(ignore_permissions=True)
            self._created.append(("Course", optional_course.name))

        program = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Program {frappe.generate_hash(length=6)}",
                "grade_scale": grade_scale.name,
                "courses": [
                    {"course": required_course.name, "level": "None"},
                    *([{"course": optional_course.name, "level": "None"}] if optional_course else []),
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program", program.name))

        offering = frappe.get_doc(
            {
                "doctype": "Program Offering",
                "program": program.name,
                "school": self.leaf_school,
                "offering_title": f"Offering {frappe.generate_hash(length=6)}",
                "offering_academic_years": [{"academic_year": self.visible_ay}],
                "offering_courses": [
                    {
                        "course": required_course.name,
                        "course_name": required_course.course_name,
                        "required": 1,
                        "start_academic_year": self.visible_ay,
                        "end_academic_year": self.visible_ay,
                    },
                    *(
                        [
                            {
                                "course": optional_course.name,
                                "course_name": optional_course.course_name,
                                "required": 0,
                                "start_academic_year": self.visible_ay,
                                "end_academic_year": self.visible_ay,
                            }
                        ]
                        if optional_course
                        else []
                    ),
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program Offering", offering.name))

        return {
            "grade_scale": grade_scale,
            "required_course": required_course,
            "optional_course": optional_course,
            "program": program,
            "offering": offering,
        }
