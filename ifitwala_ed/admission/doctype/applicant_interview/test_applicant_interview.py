# ifitwala_ed/admission/doctype/applicant_interview/test_applicant_interview.py

from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.doctype.applicant_interview.applicant_interview import (
    get_applicant_workspace,
    get_interview_workspace,
    save_my_interview_feedback,
    schedule_applicant_interview,
)
from ifitwala_ed.api.file_access import download_admissions_file
from ifitwala_ed.api.recommendation_intake import (
    create_recommendation_request,
    get_recommendation_review_payload,
    submit_recommendation,
)
from ifitwala_ed.utilities.employee_booking import upsert_employee_booking


class TestApplicantInterview(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.transfer_school = self._create_school(self.organization)
        self.applicant = self._create_applicant(self.organization, self.school)

    def tearDown(self):
        frappe.set_user("Administrator")
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
        self.assertIn("/desk/applicant-interview/", payload)

    def test_insert_creates_only_recorded_comment(self):
        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": frappe.utils.nowdate(),
                "interview_type": "Student",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        comments = self._comments_for_interview(interview.name)
        recorded = [row for row in comments if "Interview recorded:" in (row.get("content") or "")]
        updated = [row for row in comments if "Interview updated:" in (row.get("content") or "")]

        self.assertEqual(len(recorded), 1)
        self.assertEqual(len(updated), 0)

    def test_save_after_insert_creates_updated_comment(self):
        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": frappe.utils.nowdate(),
                "interview_type": "Student",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        comments_before = self._comments_for_interview(interview.name)
        self.assertEqual(
            len([row for row in comments_before if "Interview recorded:" in (row.get("content") or "")]), 1
        )
        self.assertEqual(len([row for row in comments_before if "Interview updated:" in (row.get("content") or "")]), 0)

        interview.notes = "Updated notes"
        interview.save(ignore_permissions=True)

        comments_after = self._comments_for_interview(interview.name)
        self.assertEqual(len([row for row in comments_after if "Interview recorded:" in (row.get("content") or "")]), 1)
        self.assertEqual(len([row for row in comments_after if "Interview updated:" in (row.get("content") or "")]), 1)

    def test_schedule_applicant_interview_creates_linked_school_event(self):
        interviewer = self._create_user("scheduler")
        employee = self._create_employee(interviewer, first_name="Case", last_name="Scheduler")

        payload = schedule_applicant_interview(
            student_applicant=self.applicant.name,
            interview_start="2030-05-01 10:00:00",
            duration_minutes=45,
            primary_interviewer=interviewer.name,
            interviewer_users=[interviewer.name],
            interview_type="Student",
            mode="In Person",
            confidentiality_level="Admissions Team",
            notes="Bring all prior records.",
        )

        self.assertTrue(payload.get("ok"))
        interview_name = payload.get("interview")
        school_event_name = payload.get("school_event")
        self.assertTrue(interview_name)
        self.assertTrue(school_event_name)
        self._created.append(("School Event", school_event_name))
        self._created.append(("Applicant Interview", interview_name))

        interview = frappe.get_doc("Applicant Interview", interview_name)
        self.assertEqual(interview.school_event, school_event_name)
        self.assertEqual(interview.interview_start.strftime("%H:%M:%S"), "10:00:00")
        self.assertEqual(interview.interview_end.strftime("%H:%M:%S"), "10:45:00")
        self.assertEqual(interview.interview_date.isoformat(), "2030-05-01")
        self.assertEqual(interview.interviewers[0].interviewer, interviewer.name)

        school_event = frappe.get_doc("School Event", school_event_name)
        self.assertEqual(school_event.reference_type, "Applicant Interview")
        self.assertEqual(school_event.reference_name, interview_name)
        self.assertEqual(school_event.event_category, "Appointment")
        self.assertEqual(len(school_event.participants), 1)
        self.assertEqual(school_event.participants[0].participant, interviewer.name)
        self.assertEqual(len(school_event.audience), 1)
        self.assertEqual(school_event.audience[0].audience_type, "Custom Users")

        self.assertEqual(employee.user_id, interviewer.name)

    def test_schedule_applicant_interview_returns_conflicts_with_suggestions(self):
        interviewer = self._create_user("conflict")
        employee = self._create_employee(interviewer, first_name="Case", last_name="Conflict")

        booking_name = upsert_employee_booking(
            employee=employee.name,
            start="2030-05-02 09:00:00",
            end="2030-05-02 10:00:00",
            source_doctype="Student Applicant",
            source_name=self.applicant.name,
            booking_type="Other",
            blocks_availability=1,
            school=self.school,
        )
        if booking_name:
            self._created.append(("Employee Booking", booking_name))

        before_count = frappe.db.count("Applicant Interview", {"student_applicant": self.applicant.name})
        payload = schedule_applicant_interview(
            student_applicant=self.applicant.name,
            interview_start="2030-05-02 09:15:00",
            duration_minutes=30,
            primary_interviewer=interviewer.name,
            interviewer_users=[interviewer.name],
            suggestion_window_start_time="08:00:00",
            suggestion_window_end_time="12:00:00",
        )
        after_count = frappe.db.count("Applicant Interview", {"student_applicant": self.applicant.name})

        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "EMPLOYEE_CONFLICT")
        self.assertGreaterEqual(len(payload.get("conflicts") or []), 1)
        self.assertGreaterEqual(len(payload.get("suggestions") or []), 1)
        self.assertEqual(before_count, after_count)

    def test_assigned_interviewer_without_admissions_role_can_access_but_not_edit_parent(self):
        interviewer = self._create_user("interviewer_access")
        self._create_employee(interviewer, first_name="Case", last_name="Interviewer")

        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": "2030-06-01",
                "interview_start": "2030-06-01 09:00:00",
                "interview_end": "2030-06-01 09:30:00",
                "interview_type": "Student",
                "interviewers": [{"interviewer": interviewer.name}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))
        self._ensure_interviewer_assignment(interview.name, interviewer.name)

        frappe.set_user(interviewer.name)
        interviewer_roles = set(frappe.get_roles(interviewer.name))
        self.assertFalse(
            interviewer_roles & {"Admission Officer", "Admission Manager", "Academic Admin", "System Manager"}
        )

        self.assertTrue(
            frappe.has_permission("Applicant Interview", ptype="read", doc=interview.name, user=interviewer.name)
        )
        self.assertFalse(
            frappe.has_permission("Applicant Interview", ptype="write", doc=interview.name, user=interviewer.name)
        )
        self.assertFalse(frappe.has_permission("Applicant Interview", ptype="create", user=interviewer.name))

        rows = frappe.get_list("Applicant Interview", fields=["name"], filters={"name": interview.name})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("name"), interview.name)

        loaded = frappe.get_doc("Applicant Interview", interview.name)
        loaded.notes = "Operational context update"
        with self.assertRaises(frappe.PermissionError):
            loaded.save()

        loaded = frappe.get_doc("Applicant Interview", interview.name)
        loaded.mode = "Online"
        with self.assertRaises(frappe.PermissionError):
            loaded.save()

    def test_non_interviewer_cannot_access_interview(self):
        interviewer = self._create_user("listed_interviewer")
        self._create_employee(interviewer, first_name="Listed", last_name="Interviewer")
        outsider = self._create_user("not_listed")
        self._create_employee(outsider, first_name="Not", last_name="Listed")

        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": "2030-06-02",
                "interview_start": "2030-06-02 11:00:00",
                "interview_end": "2030-06-02 11:30:00",
                "interview_type": "Student",
                "interviewers": [{"interviewer": interviewer.name}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))
        self._ensure_interviewer_assignment(interview.name, interviewer.name)

        frappe.set_user(outsider.name)
        self.assertFalse(
            frappe.has_permission("Applicant Interview", ptype="read", doc=interview.name, user=outsider.name)
        )
        self.assertFalse(
            frappe.has_permission("Applicant Interview", ptype="write", doc=interview.name, user=outsider.name)
        )
        with self.assertRaises(frappe.PermissionError):
            frappe.get_list("Applicant Interview", fields=["name"], filters={"name": interview.name})

    def test_workspace_returns_guardians_for_assigned_interviewer(self):
        interviewer = self._create_user("workspace")
        self._create_employee(interviewer, first_name="Work", last_name="Space")

        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": "2030-06-05",
                "interview_start": "2030-06-05 13:00:00",
                "interview_end": "2030-06-05 13:30:00",
                "interview_type": "Joint",
                "interviewers": [{"interviewer": interviewer.name}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        applicant_doc = frappe.get_doc("Student Applicant", self.applicant.name)
        applicant_doc.append(
            "guardians",
            {
                "relationship": "Mother",
                "guardian_first_name": "Ada",
                "guardian_last_name": "Lovelace",
                "guardian_gender": "Female",
                "guardian_email": "ada@example.com",
                "guardian_mobile_phone": "+33101010101",
                "guardian_work_email": "ada.work@example.com",
                "guardian_work_phone": "+33101010102",
                "guardian_designation": "Mathematician",
                "employment_sector": "Education",
                "work_place": "Analytical Engine School",
                "is_primary": 1,
                "can_consent": 0,
                "use_applicant_contact": 1,
            },
        )
        applicant_doc.save(ignore_permissions=True)

        frappe.set_user(interviewer.name)
        payload = get_interview_workspace(interview=interview.name)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("interview", {}).get("name"), interview.name)
        self.assertEqual(payload.get("applicant", {}).get("name"), self.applicant.name)
        guardians = payload.get("applicant", {}).get("guardians") or []
        self.assertGreaterEqual(len(guardians), 1)
        self.assertEqual((guardians[0] or {}).get("first_name"), "Ada")
        self.assertEqual((guardians[0] or {}).get("last_name"), "Lovelace")
        self.assertEqual((guardians[0] or {}).get("gender"), "Female")
        self.assertEqual((guardians[0] or {}).get("employment_sector"), "Education")
        self.assertEqual((guardians[0] or {}).get("work_place"), "Analytical Engine School")
        self.assertEqual((guardians[0] or {}).get("designation"), "Mathematician")
        self.assertTrue(bool((guardians[0] or {}).get("use_applicant_contact")))
        self.assertFalse(bool((guardians[0] or {}).get("can_consent")))
        self.assertEqual(payload.get("feedback", {}).get("my_feedback", {}).get("interviewer_user"), interviewer.name)
        self.assertTrue(bool(payload.get("feedback", {}).get("can_edit")))

    def test_workspace_document_links_use_secure_download_endpoint_for_interviewer(self):
        interviewer = self._create_user("workspace_docs")
        outsider = self._create_user("workspace_docs_out")
        self._create_employee(interviewer, first_name="Doc", last_name="Viewer")

        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": "2030-06-15",
                "interview_start": "2030-06-15 10:00:00",
                "interview_end": "2030-06-15 10:30:00",
                "interview_type": "Student",
                "interviewers": [{"interviewer": interviewer.name}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        doc_type = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": f"workspace_doc_{frappe.generate_hash(length=6)}",
                "document_type_name": "Workspace Doc",
                "organization": self.organization,
                "school": self.school,
                "is_active": 1,
                "classification_slot": "admissions_workspace_doc",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc_type.name))

        applicant_document = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": self.applicant.name,
                "document_type": doc_type.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", applicant_document.name))

        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_document.name,
                "item_key": "proof",
                "item_label": "Proof",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", item.name))

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": item.name,
                "file_name": "workspace-proof.txt",
                "is_private": 1,
                "content": b"workspace-file",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        frappe.set_user(interviewer.name)
        payload = get_interview_workspace(interview=interview.name)
        rows = (payload.get("documents") or {}).get("rows") or []
        self.assertTrue(rows)
        items = rows[0].get("items") or []
        self.assertTrue(items)
        secure_url = (items[0].get("file_url") or "").strip()

        self.assertTrue(secure_url)
        self.assertNotIn("/private/files/", secure_url)

        parsed = urlparse(secure_url)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_admissions_file")
        query = parse_qs(parsed.query)
        self.assertEqual((query.get("file") or [None])[0], file_doc.name)
        self.assertEqual((query.get("context_doctype") or [None])[0], "Applicant Interview")
        self.assertEqual((query.get("context_name") or [None])[0], interview.name)

        frappe.local.response = {}
        download_admissions_file(
            file=file_doc.name,
            context_doctype="Applicant Interview",
            context_name=interview.name,
        )
        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), file_doc.file_name)
        self.assertEqual(frappe.local.response.get("filecontent"), b"workspace-file")

        frappe.set_user(outsider.name)
        with self.assertRaises(frappe.PermissionError):
            download_admissions_file(
                file=file_doc.name,
                context_doctype="Applicant Interview",
                context_name=interview.name,
            )

    def test_save_my_feedback_upserts_single_row(self):
        interviewer = self._create_user("feedback_upsert")
        self._create_employee(interviewer, first_name="Feed", last_name="Back")

        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": "2030-06-06",
                "interview_start": "2030-06-06 09:00:00",
                "interview_end": "2030-06-06 09:30:00",
                "interview_type": "Student",
                "interviewers": [{"interviewer": interviewer.name}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        frappe.set_user(interviewer.name)
        first = save_my_interview_feedback(
            interview=interview.name,
            strengths="Strong curiosity",
            feedback_status="Draft",
        )
        self.assertTrue(first.get("ok"))

        second = save_my_interview_feedback(
            interview=interview.name,
            strengths="Strong curiosity and ownership",
            concerns="Needs mentoring plan",
            feedback_status="Submitted",
        )
        self.assertTrue(second.get("ok"))
        self.assertEqual(second.get("feedback_status"), "Submitted")

        rows = frappe.get_all(
            "Applicant Interview Feedback",
            filters={
                "applicant_interview": interview.name,
                "interviewer_user": interviewer.name,
            },
            fields=["name", "feedback_status", "submitted_on", "strengths", "concerns"],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("feedback_status"), "Submitted")
        self.assertTrue(bool(rows[0].get("submitted_on")))
        self.assertIn("ownership", rows[0].get("strengths") or "")

        self._created.append(("Applicant Interview Feedback", rows[0].get("name")))

    def test_workspace_blocks_non_assigned_user(self):
        interviewer = self._create_user("workspace_allow")
        self._create_employee(interviewer, first_name="Allow", last_name="User")
        outsider = self._create_user("workspace_block")
        self._create_employee(outsider, first_name="Block", last_name="User")

        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": "2030-06-07",
                "interview_start": "2030-06-07 15:00:00",
                "interview_end": "2030-06-07 15:30:00",
                "interview_type": "Family",
                "interviewers": [{"interviewer": interviewer.name}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        frappe.set_user(outsider.name)
        with self.assertRaises(frappe.PermissionError):
            get_interview_workspace(interview=interview.name)
        with self.assertRaises(frappe.PermissionError):
            save_my_interview_feedback(interview=interview.name, strengths="Not allowed", feedback_status="Draft")

    def test_transfer_school_academic_admin_can_read_interview_workspace(self):
        academic_admin = self._create_user("transfer_admin", roles=["Academic Admin"])
        self._create_employee(academic_admin, first_name="Transfer", last_name="Admin", school=self.transfer_school)

        self._link_applicant_to_student(anchor_school=self.transfer_school)
        interview = self._create_interview_for_applicant(
            date="2030-06-08",
            start="2030-06-08 10:00:00",
            end="2030-06-08 10:30:00",
            interview_type="Student",
        )

        frappe.set_user(academic_admin.name)
        self.assertTrue(
            frappe.has_permission("Applicant Interview", ptype="read", doc=interview.name, user=academic_admin.name)
        )

        payload = get_interview_workspace(interview=interview.name)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("applicant", {}).get("name"), self.applicant.name)

    def test_transfer_school_non_privileged_staff_cannot_read_interview_workspace(self):
        staff_user = self._create_user("transfer_staff", roles=["Academic Assistant"])
        self._create_employee(staff_user, first_name="Transfer", last_name="Staff", school=self.transfer_school)

        self._link_applicant_to_student(anchor_school=self.transfer_school)
        interview = self._create_interview_for_applicant(
            date="2030-06-09",
            start="2030-06-09 11:00:00",
            end="2030-06-09 11:30:00",
            interview_type="Student",
        )

        frappe.set_user(staff_user.name)
        self.assertFalse(
            frappe.has_permission("Applicant Interview", ptype="read", doc=interview.name, user=staff_user.name)
        )
        with self.assertRaises(frappe.PermissionError):
            get_interview_workspace(interview=interview.name)

    def test_transfer_school_academic_admin_can_read_applicant_workspace(self):
        academic_admin = self._create_user("transfer_file_admin", roles=["Academic Admin"])
        self._create_employee(
            academic_admin,
            first_name="Transfer",
            last_name="FileAdmin",
            school=self.transfer_school,
        )

        self._link_applicant_to_student(anchor_school=self.transfer_school)
        self._create_interview_for_applicant(
            date="2030-06-10",
            start="2030-06-10 10:00:00",
            end="2030-06-10 10:30:00",
            interview_type="Student",
        )

        frappe.set_user(academic_admin.name)
        payload = get_applicant_workspace(student_applicant=self.applicant.name)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("applicant", {}).get("name"), self.applicant.name)
        self.assertGreaterEqual(len(payload.get("interviews") or []), 1)
        self.assertIn("document_review", payload)
        self.assertIn("required_rows", payload.get("document_review") or {})
        self.assertTrue(payload.get("document_review", {}).get("can_review_submissions"))
        self.assertTrue(payload.get("document_review", {}).get("can_manage_overrides"))

    def test_applicant_workspace_interview_rows_include_feedback_completion(self):
        manager = self._create_user("workspace_feedback_manager", roles=["Admission Manager"])
        self._create_employee(manager, first_name="Feedback", last_name="Manager")

        interviewer_one = self._create_user("workspace_feedback_one")
        interviewer_two = self._create_user("workspace_feedback_two")
        self._create_employee(interviewer_one, first_name="Panel", last_name="One")
        self._create_employee(interviewer_two, first_name="Panel", last_name="Two")

        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": "2030-06-12",
                "interview_start": "2030-06-12 09:00:00",
                "interview_end": "2030-06-12 09:30:00",
                "interview_type": "Joint",
                "interviewers": [
                    {"interviewer": interviewer_one.name},
                    {"interviewer": interviewer_two.name},
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        frappe.set_user(interviewer_one.name)
        feedback_payload = save_my_interview_feedback(
            interview=interview.name,
            strengths="Clear and thoughtful answers.",
            feedback_status="Submitted",
        )
        if feedback_payload.get("feedback_name"):
            self._created.append(("Applicant Interview Feedback", feedback_payload.get("feedback_name")))

        frappe.set_user(manager.name)
        payload = get_applicant_workspace(student_applicant=self.applicant.name)
        interviews = payload.get("interviews") or []

        self.assertEqual(len(interviews), 1)
        self.assertEqual((interviews[0] or {}).get("name"), interview.name)
        self.assertEqual(int((interviews[0] or {}).get("feedback_submitted_count") or 0), 1)
        self.assertEqual(int((interviews[0] or {}).get("feedback_expected_count") or 0), 2)
        self.assertFalse(bool((interviews[0] or {}).get("feedback_complete")))
        self.assertEqual((interviews[0] or {}).get("feedback_status_label"), "1/2 submitted")

    def test_transfer_school_non_privileged_staff_cannot_read_applicant_workspace(self):
        staff_user = self._create_user("transfer_file_staff", roles=["Academic Assistant"])
        self._create_employee(staff_user, first_name="Transfer", last_name="FileStaff", school=self.transfer_school)

        self._link_applicant_to_student(anchor_school=self.transfer_school)
        frappe.set_user(staff_user.name)

        with self.assertRaises(frappe.PermissionError):
            get_applicant_workspace(student_applicant=self.applicant.name)

    def test_assigned_overall_reviewer_can_read_applicant_workspace_and_download_files(self):
        reviewer = self._create_user("overall_review_delegate")

        doc_type = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": f"overall_review_doc_{frappe.generate_hash(length=6)}",
                "document_type_name": "Overall Review Packet",
                "organization": self.organization,
                "school": self.school,
                "is_active": 1,
                "is_required": 1,
                "classification_slot": "admissions_workspace_doc",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc_type.name))

        applicant_document = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": self.applicant.name,
                "document_type": doc_type.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", applicant_document.name))

        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_document.name,
                "item_key": "final_packet",
                "item_label": "Final packet",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", item.name))

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": item.name,
                "file_name": "overall-review.txt",
                "is_private": 1,
                "content": b"overall-review-file",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        assignment = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "target_type": "Student Applicant",
                "target_name": self.applicant.name,
                "student_applicant": self.applicant.name,
                "assigned_to_user": reviewer.name,
                "status": "Open",
                "source_event": "application_submitted",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment.name))

        frappe.set_user(reviewer.name)
        payload = get_applicant_workspace(student_applicant=self.applicant.name)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("applicant", {}).get("name"), self.applicant.name)
        self.assertFalse(payload.get("document_review", {}).get("can_review_submissions"))

        uploaded_rows = payload.get("document_review", {}).get("uploaded_rows") or []
        self.assertTrue(uploaded_rows)
        secure_url = (uploaded_rows[0].get("file_url") or "").strip()
        self.assertTrue(secure_url)

        parsed = urlparse(secure_url)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_admissions_file")
        query = parse_qs(parsed.query)
        self.assertEqual((query.get("file") or [None])[0], file_doc.name)
        self.assertEqual((query.get("context_doctype") or [None])[0], "Student Applicant")
        self.assertEqual((query.get("context_name") or [None])[0], self.applicant.name)

        frappe.local.response = {}
        download_admissions_file(
            file=file_doc.name,
            context_doctype="Student Applicant",
            context_name=self.applicant.name,
        )
        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), file_doc.file_name)
        self.assertEqual(frappe.local.response.get("filecontent"), b"overall-review-file")

    def test_assigned_health_reviewer_can_read_applicant_workspace_and_download_files(self):
        reviewer = self._create_user("health_review_delegate")

        health_profile = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": self.applicant.name,
                "review_status": "Pending",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Health Profile", health_profile.name))

        doc_type = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": f"health_review_doc_{frappe.generate_hash(length=6)}",
                "document_type_name": "Health Review Packet",
                "organization": self.organization,
                "school": self.school,
                "is_active": 1,
                "is_required": 1,
                "classification_slot": "admissions_workspace_doc",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc_type.name))

        applicant_document = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": self.applicant.name,
                "document_type": doc_type.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", applicant_document.name))

        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_document.name,
                "item_key": "health_packet",
                "item_label": "Health packet",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", item.name))

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": item.name,
                "file_name": "health-review.txt",
                "is_private": 1,
                "content": b"health-review-file",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        assignment = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "target_type": "Applicant Health Profile",
                "target_name": health_profile.name,
                "student_applicant": self.applicant.name,
                "assigned_to_user": reviewer.name,
                "status": "Open",
                "source_event": "health_declared_complete",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment.name))

        frappe.set_user(reviewer.name)
        payload = get_applicant_workspace(student_applicant=self.applicant.name)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("applicant", {}).get("name"), self.applicant.name)
        self.assertFalse(payload.get("document_review", {}).get("can_review_submissions"))
        self.assertTrue(
            frappe.has_permission("Student Applicant", ptype="read", doc=self.applicant.name, user=reviewer.name)
        )
        self.assertTrue(
            frappe.has_permission(
                "Applicant Health Profile",
                ptype="read",
                doc=health_profile.name,
                user=reviewer.name,
            )
        )

        uploaded_rows = payload.get("document_review", {}).get("uploaded_rows") or []
        self.assertTrue(uploaded_rows)
        secure_url = (uploaded_rows[0].get("file_url") or "").strip()
        self.assertTrue(secure_url)

        parsed = urlparse(secure_url)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_admissions_file")
        query = parse_qs(parsed.query)
        self.assertEqual((query.get("file") or [None])[0], file_doc.name)
        self.assertEqual((query.get("context_doctype") or [None])[0], "Student Applicant")
        self.assertEqual((query.get("context_name") or [None])[0], self.applicant.name)

        frappe.local.response = {}
        download_admissions_file(
            file=file_doc.name,
            context_doctype="Student Applicant",
            context_name=self.applicant.name,
        )
        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), file_doc.file_name)
        self.assertEqual(frappe.local.response.get("filecontent"), b"health-review-file")

    def test_assigned_overall_reviewer_can_read_interview_workspace_and_download_files(self):
        reviewer = self._create_user("overall_review_interview_delegate")

        interview = self._create_interview_for_applicant(
            date="2030-06-11",
            start="2030-06-11 10:00:00",
            end="2030-06-11 10:30:00",
            interview_type="Student",
        )

        doc_type = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": f"overall_review_interview_doc_{frappe.generate_hash(length=6)}",
                "document_type_name": "Overall Interview Packet",
                "organization": self.organization,
                "school": self.school,
                "is_active": 1,
                "classification_slot": "admissions_workspace_doc",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc_type.name))

        applicant_document = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": self.applicant.name,
                "document_type": doc_type.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", applicant_document.name))

        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": applicant_document.name,
                "item_key": "interview_packet",
                "item_label": "Interview packet",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", item.name))

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": item.name,
                "file_name": "overall-interview-review.txt",
                "is_private": 1,
                "content": b"overall-interview-review-file",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        assignment = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "target_type": "Student Applicant",
                "target_name": self.applicant.name,
                "student_applicant": self.applicant.name,
                "assigned_to_user": reviewer.name,
                "status": "Open",
                "source_event": "application_submitted",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment.name))

        frappe.set_user(reviewer.name)
        self.assertFalse(
            frappe.has_permission("Applicant Interview", ptype="read", doc=interview.name, user=reviewer.name)
        )

        payload = get_interview_workspace(interview=interview.name)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("interview", {}).get("name"), interview.name)
        self.assertEqual(payload.get("applicant", {}).get("name"), self.applicant.name)
        self.assertFalse(bool(payload.get("feedback", {}).get("can_edit")))

        rows = (payload.get("documents") or {}).get("rows") or []
        self.assertTrue(rows)
        items = rows[0].get("items") or []
        self.assertTrue(items)
        secure_url = (items[0].get("file_url") or "").strip()
        self.assertTrue(secure_url)

        parsed = urlparse(secure_url)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_admissions_file")
        query = parse_qs(parsed.query)
        self.assertEqual((query.get("file") or [None])[0], file_doc.name)
        self.assertEqual((query.get("context_doctype") or [None])[0], "Applicant Interview")
        self.assertEqual((query.get("context_name") or [None])[0], interview.name)

        frappe.local.response = {}
        download_admissions_file(
            file=file_doc.name,
            context_doctype="Applicant Interview",
            context_name=interview.name,
        )
        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), file_doc.file_name)
        self.assertEqual(frappe.local.response.get("filecontent"), b"overall-interview-review-file")

    def test_assigned_overall_reviewer_can_open_recommendation_review_payload(self):
        if not self._recommendation_feature_tables_ready():
            self.skipTest("Recommendation intake DocTypes are not migrated on this site.")

        admissions_user = self._create_user("overall_review_staff", roles=["Admission Manager"])
        self._create_employee(admissions_user, first_name="Overall", last_name="Staff")
        reviewer = self._create_user("overall_review_recommendation_delegate")

        document_type = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": f"overall_review_recommendation_{frappe.generate_hash(length=6)}",
                "document_type_name": "Recommendation Letter",
                "organization": self.organization,
                "school": self.school,
                "is_active": 1,
                "is_required": 0,
                "is_repeatable": 1,
                "min_items_required": 1,
                "classification_slot": "recommendation_letter",
                "classification_data_class": "academic",
                "classification_purpose": "academic_report",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", document_type.name))

        template = frappe.get_doc(
            {
                "doctype": "Recommendation Template",
                "template_name": f"Overall Review Recommendation {frappe.generate_hash(length=5)}",
                "is_active": 1,
                "organization": self.organization,
                "school": self.school,
                "target_document_type": document_type.name,
                "minimum_required": 1,
                "maximum_allowed": 2,
                "allow_file_upload": 0,
                "file_upload_required": 0,
                "otp_enforced": 0,
                "applicant_can_view_status": 1,
                "template_fields": [
                    {
                        "field_key": "recommendation_summary",
                        "label": "Recommendation Summary",
                        "field_type": "Long Text",
                        "is_required": 1,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Template", template.name))

        assignment = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "target_type": "Student Applicant",
                "target_name": self.applicant.name,
                "student_applicant": self.applicant.name,
                "assigned_to_user": reviewer.name,
                "status": "Open",
                "source_event": "application_submitted",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment.name))

        frappe.set_user(admissions_user.name)
        created = create_recommendation_request(
            student_applicant=self.applicant.name,
            recommendation_template=template.name,
            recommender_name="Ms Mentor",
            recommender_email=f"mentor-{frappe.generate_hash(length=6)}@example.com",
            recommender_relationship="Teacher",
            send_email=0,
            client_request_id=f"overall-review-{frappe.generate_hash(length=6)}",
        )
        recommendation_request = created.get("recommendation_request")
        self.assertTrue(bool(recommendation_request))

        frappe.set_user("Guest")
        submit_recommendation(
            token=self._token_from_intake_url(created.get("intake_url")),
            answers={"recommendation_summary": "Strong and consistent performance."},
            attestation_confirmed=1,
            client_request_id=f"overall-review-submit-{frappe.generate_hash(length=6)}",
        )

        frappe.set_user(reviewer.name)
        payload = get_recommendation_review_payload(
            student_applicant=self.applicant.name,
            recommendation_request=recommendation_request,
        )

        self.assertTrue(payload.get("ok"))
        recommendation = payload.get("recommendation") or {}
        self.assertEqual(recommendation.get("recommendation_request"), recommendation_request)
        self.assertEqual(recommendation.get("student_applicant"), self.applicant.name)
        self.assertEqual(recommendation.get("review_status"), "Pending")
        answers = recommendation.get("answers") or []
        self.assertEqual(len(answers), 1)
        self.assertEqual((answers[0] or {}).get("display_value"), "Strong and consistent performance.")

    def test_assigned_health_reviewer_can_open_recommendation_review_payload(self):
        if not self._recommendation_feature_tables_ready():
            self.skipTest("Recommendation intake DocTypes are not migrated on this site.")

        admissions_user = self._create_user("health_review_staff", roles=["Admission Manager"])
        self._create_employee(admissions_user, first_name="Health", last_name="Staff")
        reviewer = self._create_user("health_review_recommendation_delegate")

        health_profile = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": self.applicant.name,
                "review_status": "Pending",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Health Profile", health_profile.name))

        document_type = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": f"health_review_recommendation_{frappe.generate_hash(length=6)}",
                "document_type_name": "Recommendation Letter",
                "organization": self.organization,
                "school": self.school,
                "is_active": 1,
                "is_required": 0,
                "is_repeatable": 1,
                "min_items_required": 1,
                "classification_slot": "recommendation_letter",
                "classification_data_class": "academic",
                "classification_purpose": "academic_report",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", document_type.name))

        template = frappe.get_doc(
            {
                "doctype": "Recommendation Template",
                "template_name": f"Health Review Recommendation {frappe.generate_hash(length=5)}",
                "is_active": 1,
                "organization": self.organization,
                "school": self.school,
                "target_document_type": document_type.name,
                "minimum_required": 1,
                "maximum_allowed": 2,
                "allow_file_upload": 0,
                "file_upload_required": 0,
                "otp_enforced": 0,
                "applicant_can_view_status": 1,
                "template_fields": [
                    {
                        "field_key": "recommendation_summary",
                        "label": "Recommendation Summary",
                        "field_type": "Long Text",
                        "is_required": 1,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Template", template.name))

        assignment = frappe.get_doc(
            {
                "doctype": "Applicant Review Assignment",
                "target_type": "Applicant Health Profile",
                "target_name": health_profile.name,
                "student_applicant": self.applicant.name,
                "assigned_to_user": reviewer.name,
                "status": "Open",
                "source_event": "health_declared_complete",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Review Assignment", assignment.name))

        frappe.set_user(admissions_user.name)
        created = create_recommendation_request(
            student_applicant=self.applicant.name,
            recommendation_template=template.name,
            recommender_name="Ms Health Mentor",
            recommender_email=f"health-mentor-{frappe.generate_hash(length=6)}@example.com",
            recommender_relationship="Teacher",
            send_email=0,
            client_request_id=f"health-review-{frappe.generate_hash(length=6)}",
        )
        recommendation_request = created.get("recommendation_request")
        self.assertTrue(bool(recommendation_request))

        frappe.set_user("Guest")
        submit_recommendation(
            token=self._token_from_intake_url(created.get("intake_url")),
            answers={"recommendation_summary": "Health reviewer can inspect this full applicant file."},
            attestation_confirmed=1,
            client_request_id=f"health-review-submit-{frappe.generate_hash(length=6)}",
        )

        frappe.set_user(reviewer.name)
        payload = get_recommendation_review_payload(
            student_applicant=self.applicant.name,
            recommendation_request=recommendation_request,
        )

        self.assertTrue(payload.get("ok"))
        recommendation = payload.get("recommendation") or {}
        self.assertEqual(recommendation.get("recommendation_request"), recommendation_request)
        self.assertEqual(recommendation.get("student_applicant"), self.applicant.name)
        self.assertEqual(recommendation.get("review_status"), "Pending")
        answers = recommendation.get("answers") or []
        self.assertEqual(len(answers), 1)
        self.assertEqual(
            (answers[0] or {}).get("display_value"),
            "Health reviewer can inspect this full applicant file.",
        )

    def _comments_for_interview(self, interview_name: str):
        comments = frappe.get_all(
            "Comment",
            filters={
                "reference_doctype": "Student Applicant",
                "reference_name": self.applicant.name,
            },
            fields=["content"],
            order_by="creation asc",
            limit_page_length=50,
        )
        marker = f"/desk/applicant-interview/{interview_name}"
        return [row for row in comments if marker in (row.get("content") or "")]

    def _ensure_interviewer_assignment(self, interview_name: str, interviewer_user: str):
        interview_name = (interview_name or "").strip()
        interviewer_user = (interviewer_user or "").strip()
        if not interview_name or not interviewer_user:
            return

        rows = frappe.get_all(
            "Applicant Interviewer",
            filters={"parent": interview_name},
            fields=["name", "interviewer"],
            limit_page_length=20,
        )
        if not rows:
            interview = frappe.get_doc("Applicant Interview", interview_name)
            interview.append("interviewers", {"interviewer": interviewer_user})
            interview.save(ignore_permissions=True)
            rows = frappe.get_all(
                "Applicant Interviewer",
                filters={"parent": interview_name},
                fields=["name", "interviewer"],
                limit_page_length=20,
            )

        for row in rows:
            row_name = (row.get("name") or "").strip()
            if not row_name:
                continue
            if frappe.db.table_exists("Applicant Interviewer") and frappe.db.has_column(
                "Applicant Interviewer", "interviewer"
            ):
                frappe.db.set_value(
                    "Applicant Interviewer",
                    row_name,
                    "interviewer",
                    interviewer_user,
                    update_modified=False,
                )
            if frappe.db.table_exists("Applicant Interviewer") and frappe.db.has_column(
                "Applicant Interviewer", "interviewer_user"
            ):
                frappe.db.set_value(
                    "Applicant Interviewer",
                    row_name,
                    "interviewer_user",
                    interviewer_user,
                    update_modified=False,
                )

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

    def _create_user(self, label: str, roles: list[str] | None = None):
        doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"{label}-{frappe.generate_hash(length=8)}@example.com",
                "first_name": "Interview",
                "last_name": "User",
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", doc.name))
        if roles:
            doc.add_roles(*roles)
        return doc

    def _create_employee(self, user, *, first_name: str, last_name: str, school: str | None = None):
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
                "school": school or self.school,
                "user_id": user.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", doc.name))
        return doc

    def _link_applicant_to_student(self, *, anchor_school: str):
        student = frappe.get_doc(
            {
                "doctype": "Student",
                "student_first_name": "Transfer",
                "student_last_name": f"Student-{frappe.generate_hash(length=6)}",
                "student_email": f"transfer-{frappe.generate_hash(length=8)}@example.com",
                "student_applicant": self.applicant.name,
                "anchor_school": anchor_school,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student", student.name))
        self.applicant.db_set("student", student.name, update_modified=False)
        return student

    def _create_interview_for_applicant(self, *, date: str, start: str, end: str, interview_type: str):
        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_date": date,
                "interview_start": start,
                "interview_end": end,
                "interview_type": interview_type,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))
        return interview

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

    def _recommendation_feature_tables_ready(self) -> bool:
        required = (
            "Recommendation Template",
            "Recommendation Template Field",
            "Recommendation Request",
            "Recommendation Submission",
        )
        for doctype in required:
            if not frappe.db.table_exists(doctype):
                return False
        return True

    def _token_from_intake_url(self, intake_url: str | None) -> str:
        text = str(intake_url or "").strip()
        self.assertTrue(bool(text))
        parsed = urlparse(text)
        path = parsed.path.rstrip("/")
        token = (path.split("/")[-1] or "").strip()
        self.assertTrue(bool(token))
        return token
