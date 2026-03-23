# ifitwala_ed/api/test_recommendation_intake.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from urllib.parse import urlparse

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.doctype.applicant_interview.applicant_interview import (
    get_applicant_workspace,
    save_my_interview_feedback,
)
from ifitwala_ed.api.admission_cockpit import get_admissions_cockpit_data
from ifitwala_ed.api.admissions_review import review_applicant_document_submission
from ifitwala_ed.api.recommendation_intake import (
    create_recommendation_request,
    get_recommendation_intake_payload,
    get_recommendation_review_payload,
    get_recommendation_status_for_applicant,
    list_recommendation_requests,
    submit_recommendation,
)


class TestRecommendationIntake(FrappeTestCase):
    def setUp(self):
        if not self._feature_tables_ready():
            self.skipTest("Recommendation intake DocTypes are not migrated on this site.")

        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []

        self._ensure_role("Admission Manager")
        self._ensure_role("Admissions Applicant")

        self.staff_user = self._create_user("staff", ["Admission Manager"])
        self.applicant_user = self._create_user("applicant", ["Admissions Applicant"])

        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self._create_employee(self.staff_user.name, self.organization, self.school)
        self.applicant = self._create_applicant(self.organization, self.school, self.applicant_user.name)

        self.document_type = self._create_document_type(self.organization, self.school)
        self.template = self._create_template(
            organization=self.organization,
            school=self.school,
            target_document_type=self.document_type,
            minimum_required=1,
            maximum_allowed=2,
            allow_file_upload=0,
            otp_enforced=0,
            applicant_can_view_status=1,
        )

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_create_and_submit_recommendation_request(self):
        frappe.set_user(self.staff_user.name)
        created = create_recommendation_request(
            student_applicant=self.applicant.name,
            recommendation_template=self.template.name,
            recommender_name="Ms Mentor",
            recommender_email=f"mentor-{frappe.generate_hash(length=6)}@example.com",
            recommender_relationship="Teacher",
            send_email=0,
            client_request_id="create-1",
        )
        self._track_recommendation_artifacts(created.get("recommendation_request"))

        self.assertTrue(bool(created.get("ok")))
        self.assertEqual(created.get("status"), "processed")
        request_name = created.get("recommendation_request")
        self.assertTrue(bool(request_name))

        request_row = frappe.db.get_value(
            "Recommendation Request",
            request_name,
            [
                "name",
                "request_status",
                "token_hash",
                "item_key",
                "applicant_document",
                "applicant_document_item",
            ],
            as_dict=True,
        )
        self.assertEqual(request_row.get("request_status"), "Sent")
        self.assertTrue(bool(request_row.get("token_hash")))
        self.assertTrue(bool(request_row.get("item_key")))
        self.assertTrue(bool(request_row.get("applicant_document")))
        self.assertTrue(bool(request_row.get("applicant_document_item")))

        token = self._token_from_intake_url(created.get("intake_url"))

        frappe.set_user("Guest")
        intake_payload = get_recommendation_intake_payload(token=token)
        self.assertEqual(intake_payload.get("status"), "open")

        submit_payload = submit_recommendation(
            token=token,
            answers={"recommendation_summary": "Strong and consistent performance."},
            attestation_confirmed=1,
            client_request_id="submit-1",
        )
        self.assertTrue(bool(submit_payload.get("ok")))
        self.assertEqual(submit_payload.get("status"), "processed")

        frappe.set_user(self.staff_user.name)
        request_row = frappe.db.get_value(
            "Recommendation Request",
            request_name,
            ["request_status", "submission"],
            as_dict=True,
        )
        self.assertEqual(request_row.get("request_status"), "Submitted")
        self.assertTrue(bool(request_row.get("submission")))
        self._track_recommendation_artifacts(request_name)

        status_payload = get_recommendation_status_for_applicant(
            student_applicant=self.applicant.name, include_confidential=True
        )
        self.assertTrue(bool(status_payload.get("ok")))
        self.assertEqual(int(status_payload.get("required_total") or 0), 1)
        self.assertEqual(int(status_payload.get("received_total") or 0), 1)

    def test_template_maximum_allowed_blocks_extra_requests(self):
        frappe.set_user(self.staff_user.name)
        first = create_recommendation_request(
            student_applicant=self.applicant.name,
            recommendation_template=self.template.name,
            recommender_name="Recommender 1",
            recommender_email=f"r1-{frappe.generate_hash(length=6)}@example.com",
            send_email=0,
            client_request_id="max-1",
        )
        self._track_recommendation_artifacts(first.get("recommendation_request"))
        second = create_recommendation_request(
            student_applicant=self.applicant.name,
            recommendation_template=self.template.name,
            recommender_name="Recommender 2",
            recommender_email=f"r2-{frappe.generate_hash(length=6)}@example.com",
            send_email=0,
            client_request_id="max-2",
        )
        self._track_recommendation_artifacts(second.get("recommendation_request"))

        self.assertNotEqual(first.get("item_key"), second.get("item_key"))

        with self.assertRaises(frappe.ValidationError):
            create_recommendation_request(
                student_applicant=self.applicant.name,
                recommendation_template=self.template.name,
                recommender_name="Recommender 3",
                recommender_email=f"r3-{frappe.generate_hash(length=6)}@example.com",
                send_email=0,
                client_request_id="max-3",
            )

    def test_applicant_list_hides_recommender_identity(self):
        frappe.set_user(self.staff_user.name)
        create_recommendation_request(
            student_applicant=self.applicant.name,
            recommendation_template=self.template.name,
            recommender_name="Identity Hidden",
            recommender_email=f"hidden-{frappe.generate_hash(length=6)}@example.com",
            send_email=0,
            client_request_id="hidden-1",
        )
        self._track_recommendation_artifacts(
            frappe.db.get_value(
                "Recommendation Request",
                {
                    "student_applicant": self.applicant.name,
                    "recommendation_template": self.template.name,
                    "recommender_name": "Identity Hidden",
                },
                "name",
            )
        )

        frappe.set_user(self.applicant_user.name)
        payload = list_recommendation_requests()
        rows = payload.get("requests") or []
        self.assertEqual(len(rows), 1)
        self.assertNotIn("recommender_email", rows[0])
        self.assertNotIn("recommender_name", rows[0])
        self.assertEqual((payload.get("summary") or {}).get("state"), "pending")

    def test_staff_review_payload_exposes_answers_and_review_target(self):
        submitted = self._create_submitted_recommendation()

        frappe.set_user(self.staff_user.name)
        payload = get_recommendation_review_payload(
            student_applicant=self.applicant.name,
            recommendation_request=submitted["recommendation_request"],
        )

        self.assertTrue(bool(payload.get("ok")))
        recommendation = payload.get("recommendation") or {}
        self.assertEqual(recommendation.get("recommendation_request"), submitted["recommendation_request"])
        self.assertEqual(recommendation.get("recommendation_submission"), submitted["recommendation_submission"])
        self.assertEqual(recommendation.get("applicant_document_item"), submitted["applicant_document_item"])
        self.assertEqual(recommendation.get("review_status"), "Pending")
        self.assertTrue(bool(recommendation.get("can_review")))

        answers = recommendation.get("answers") or []
        self.assertEqual(len(answers), 1)
        self.assertEqual((answers[0] or {}).get("label"), "Recommendation Summary")
        self.assertEqual((answers[0] or {}).get("display_value"), "Strong and consistent performance.")

    def test_applicant_cannot_access_staff_review_payload(self):
        submitted = self._create_submitted_recommendation()

        frappe.set_user(self.applicant_user.name)
        with self.assertRaises(frappe.PermissionError):
            get_recommendation_review_payload(
                student_applicant=self.applicant.name,
                recommendation_request=submitted["recommendation_request"],
            )

    def test_cockpit_payload_includes_pending_recommendation_review_target(self):
        submitted = self._create_submitted_recommendation()

        frappe.set_user(self.staff_user.name)
        payload = get_admissions_cockpit_data(filters={"assigned_to_me": 0, "limit": 20})
        columns = payload.get("columns") or []
        cards = [
            card
            for column in columns
            for card in (column.get("items") or [])
            if card.get("name") == self.applicant.name
        ]

        self.assertEqual(len(cards), 1)
        recommendations = (cards[0] or {}).get("recommendations") or {}
        self.assertEqual(int(recommendations.get("received_total") or 0), 1)
        self.assertEqual(int(recommendations.get("pending_review_count") or 0), 1)
        self.assertEqual(
            (recommendations.get("first_pending_review") or {}).get("recommendation_request"),
            submitted["recommendation_request"],
        )
        self.assertEqual(
            (recommendations.get("first_pending_review") or {}).get("applicant_document_item"),
            submitted["applicant_document_item"],
        )

    def test_cockpit_payload_includes_latest_interview_feedback_summary(self):
        if not frappe.db.table_exists("Applicant Interview Feedback"):
            self.skipTest("Applicant Interview Feedback DocType is not migrated on this site.")

        self._ensure_role("Employee")
        panel_user = self._create_user("panel", ["Employee"])
        interview = self._create_interview([self.staff_user.name, panel_user.name])
        self._submit_interview_feedback(interview.name, self.staff_user.name)

        frappe.set_user(self.staff_user.name)
        payload = get_admissions_cockpit_data(filters={"assigned_to_me": 0, "limit": 20})
        columns = payload.get("columns") or []
        cards = [
            card
            for column in columns
            for card in (column.get("items") or [])
            if card.get("name") == self.applicant.name
        ]

        self.assertEqual(len(cards), 1)
        interviews = (cards[0] or {}).get("interviews") or {}
        latest = interviews.get("latest") or {}

        self.assertEqual(int(interviews.get("count") or 0), 1)
        self.assertEqual(latest.get("name"), interview.name)
        self.assertEqual(latest.get("interview_type"), "Family")
        self.assertEqual(latest.get("mode"), "In Person")
        self.assertEqual(int(latest.get("feedback_submitted_count") or 0), 1)
        self.assertEqual(int(latest.get("feedback_expected_count") or 0), 2)
        self.assertEqual(latest.get("feedback_status_label"), "1/2 submitted")
        self.assertEqual(
            set(latest.get("interviewer_labels") or []),
            {"Recommendation Staff", "Recommendation Panel"},
        )
        self.assertEqual(latest.get("open_url"), f"/desk/applicant-interview/{interview.name}")

    def test_applicant_workspace_includes_recommendation_review_rows(self):
        submitted = self._create_submitted_recommendation()

        frappe.set_user(self.staff_user.name)
        payload = get_applicant_workspace(student_applicant=self.applicant.name)
        review_rows = (payload.get("recommendations") or {}).get("review_rows") or []

        self.assertEqual(len(review_rows), 1)
        self.assertEqual((review_rows[0] or {}).get("recommendation_request"), submitted["recommendation_request"])
        self.assertEqual((review_rows[0] or {}).get("applicant_document_item"), submitted["applicant_document_item"])

    def test_form_only_recommendations_satisfy_required_document_counts(self):
        frappe.db.set_value(
            "Applicant Document Type",
            self.document_type,
            "min_items_required",
            2,
            update_modified=False,
        )

        first = self._create_submitted_recommendation()
        second = self._create_submitted_recommendation()

        frappe.set_user(self.staff_user.name)
        review_applicant_document_submission(
            student_applicant=self.applicant.name,
            applicant_document_item=first["applicant_document_item"],
            decision="Approved",
            client_request_id=f"review-{frappe.generate_hash(length=6)}",
        )
        review_applicant_document_submission(
            student_applicant=self.applicant.name,
            applicant_document_item=second["applicant_document_item"],
            decision="Approved",
            client_request_id=f"review-{frappe.generate_hash(length=6)}",
        )

        applicant_doc = frappe.get_doc("Student Applicant", self.applicant.name)
        documents = applicant_doc.has_required_documents()
        recommendation_rows = [
            row for row in (documents.get("uploaded_rows") or []) if row.get("document_type") == self.document_type
        ]

        self.assertEqual(len(recommendation_rows), 2)
        self.assertTrue(all(row.get("review_status") == "Approved" for row in recommendation_rows))
        self.assertTrue(all(int(row.get("uploaded_count") or 0) == 2 for row in recommendation_rows))
        self.assertTrue(all(int(row.get("approved_count") or 0) == 2 for row in recommendation_rows))
        self.assertTrue(all(bool(row.get("uploaded_at")) for row in recommendation_rows))
        self.assertFalse(documents.get("missing"))
        self.assertFalse(documents.get("unapproved"))

    def _feature_tables_ready(self) -> bool:
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

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

    def _create_user(self, prefix: str, roles: list[str]):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"recommendation-{prefix}-{frappe.generate_hash(length=6)}@example.com",
                "first_name": "Recommendation",
                "last_name": prefix.title(),
                "enabled": 1,
                "roles": [{"role": role} for role in roles],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        frappe.clear_cache(user=user.name)
        return user

    def _create_employee(self, user: str, organization: str, school: str):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Recommendation",
                "employee_last_name": "Staff",
                "employee_gender": "Male",
                "employee_professional_email": user,
                "date_of_joining": "2025-01-01",
                "employment_status": "Active",
                "organization": organization,
                "school": school,
                "user_id": user,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", employee.name))
        frappe.clear_cache(user=user)
        return employee

    def _create_organization(self) -> str:
        organization = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Rec Org {frappe.generate_hash(length=6)}",
                "abbr": f"RO{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", organization.name))
        return organization.name

    def _create_school(self, organization: str) -> str:
        school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"Rec School {frappe.generate_hash(length=6)}",
                "abbr": f"RS{frappe.generate_hash(length=3)}",
                "organization": organization,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", school.name))
        return school.name

    def _create_applicant(self, organization: str, school: str, applicant_user: str):
        applicant = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Rec",
                "last_name": f"Applicant-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        applicant.db_set("applicant_user", applicant_user, update_modified=False)
        applicant.db_set("application_status", "In Progress", update_modified=False)
        applicant.reload()
        self._created.append(("Student Applicant", applicant.name))
        return applicant

    def _create_document_type(self, organization: str, school: str) -> str:
        code = f"recommendation_{frappe.generate_hash(length=6)}"
        document_type = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": "Recommendation Letter",
                "organization": organization,
                "school": school,
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
        return document_type.name

    def _create_interview(self, interviewer_users: list[str]):
        frappe.set_user(self.staff_user.name)
        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": self.applicant.name,
                "interview_type": "Family",
                "interview_date": "2026-03-12",
                "interview_start": "2026-03-12 09:00:00",
                "interview_end": "2026-03-12 09:30:00",
                "mode": "In Person",
                "interviewers": [{"interviewer": user} for user in interviewer_users],
            }
        ).insert()
        self._created.append(("Applicant Interview", interview.name))
        return interview

    def _submit_interview_feedback(self, interview_name: str, user: str):
        frappe.set_user(user)
        payload = save_my_interview_feedback(
            interview=interview_name,
            strengths="Strong applicant communication.",
            feedback_status="Submitted",
        )
        feedback_name = payload.get("feedback_name")
        if feedback_name:
            self._created.append(("Applicant Interview Feedback", feedback_name))
        return payload

    def _create_template(
        self,
        *,
        organization: str,
        school: str,
        target_document_type: str,
        minimum_required: int,
        maximum_allowed: int,
        allow_file_upload: int,
        otp_enforced: int,
        applicant_can_view_status: int,
    ):
        template = frappe.get_doc(
            {
                "doctype": "Recommendation Template",
                "template_name": f"Teacher Recommendation {frappe.generate_hash(length=5)}",
                "is_active": 1,
                "organization": organization,
                "school": school,
                "target_document_type": target_document_type,
                "minimum_required": minimum_required,
                "maximum_allowed": maximum_allowed,
                "allow_file_upload": allow_file_upload,
                "file_upload_required": 0,
                "otp_enforced": otp_enforced,
                "applicant_can_view_status": applicant_can_view_status,
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
        return template

    def _token_from_intake_url(self, intake_url: str | None) -> str:
        text = str(intake_url or "").strip()
        self.assertTrue(bool(text))
        parsed = urlparse(text)
        path = parsed.path.rstrip("/")
        token = (path.split("/")[-1] or "").strip()
        self.assertTrue(bool(token))
        return token

    def _create_submitted_recommendation(self) -> dict[str, str]:
        frappe.set_user(self.staff_user.name)
        created = create_recommendation_request(
            student_applicant=self.applicant.name,
            recommendation_template=self.template.name,
            recommender_name="Ms Mentor",
            recommender_email=f"mentor-{frappe.generate_hash(length=6)}@example.com",
            recommender_relationship="Teacher",
            send_email=0,
            client_request_id=f"submitted-{frappe.generate_hash(length=6)}",
        )

        recommendation_request = created.get("recommendation_request")
        self.assertTrue(bool(recommendation_request))
        self._track_recommendation_artifacts(recommendation_request)
        token = self._token_from_intake_url(created.get("intake_url"))

        frappe.set_user("Guest")
        submit_recommendation(
            token=token,
            answers={"recommendation_summary": "Strong and consistent performance."},
            attestation_confirmed=1,
            client_request_id=f"submit-{frappe.generate_hash(length=6)}",
        )

        frappe.set_user(self.staff_user.name)
        request_row = frappe.db.get_value(
            "Recommendation Request",
            recommendation_request,
            ["submission", "applicant_document_item"],
            as_dict=True,
        )
        self.assertTrue(bool(request_row.get("submission")))
        self.assertTrue(bool(request_row.get("applicant_document_item")))
        self._track_recommendation_artifacts(recommendation_request)
        return {
            "recommendation_request": recommendation_request,
            "recommendation_submission": request_row.get("submission"),
            "applicant_document_item": request_row.get("applicant_document_item"),
        }

    def _track_recommendation_artifacts(self, recommendation_request: str | None):
        def _append_once(doctype: str, name: str | None):
            docname = str(name or "").strip()
            if not docname:
                return
            key = (doctype, docname)
            if key not in self._created:
                self._created.append(key)

        request_name = str(recommendation_request or "").strip()
        if not request_name:
            return

        request_row = frappe.db.get_value(
            "Recommendation Request",
            request_name,
            ["name", "submission", "applicant_document", "applicant_document_item"],
            as_dict=True,
        )
        if not request_row:
            return

        applicant_document = request_row.get("applicant_document")
        applicant_document_item = request_row.get("applicant_document_item")
        submission = request_row.get("submission")

        _append_once("Applicant Document", applicant_document)
        _append_once("Applicant Document Item", applicant_document_item)
        _append_once("Recommendation Request", request_name)
        _append_once("Recommendation Submission", submission)
