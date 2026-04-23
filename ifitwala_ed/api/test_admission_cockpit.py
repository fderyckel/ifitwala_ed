# ifitwala_ed/api/test_admission_cockpit.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

import base64
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.admission_cockpit import (
    get_admissions_cockpit_data,
    hydrate_admissions_cockpit_request,
    send_admissions_cockpit_offer,
)
from ifitwala_ed.api.admissions_portal import upload_applicant_document
from ifitwala_ed.api.admissions_review import (
    review_applicant_document_submission,
    set_document_requirement_override,
)


class TestAdmissionCockpit(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self._password_notification_patcher = patch("frappe.core.doctype.user.user.User.send_password_notification")
        self._password_notification_patcher.start()
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Admission Manager")
        self._ensure_role("Admissions Applicant")
        self._ensure_gender("Male")

        self.staff_user = self._create_user("staff", ["Admission Manager"])
        self.applicant_user = self._create_user("applicant", ["Admissions Applicant"])

        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self._create_employee(self.staff_user.name, self.organization, self.school)
        self.applicant = self._create_applicant(self.organization, self.school, self.applicant_user.name)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        self._password_notification_patcher.stop()
        super().tearDown()

    def test_invalid_school_scope_reuses_single_organization_lookup(self):
        class _CacheStub:
            def __init__(self):
                self.values = {}

            def get_value(self, key):
                return self.values.get(key)

            def set_value(self, key, value, expires_in_sec=None):
                self.values[key] = value

        cache = _CacheStub()
        sql_calls = []

        def fake_sql(query, params=None, as_list=False, as_dict=False):
            if "FROM `tabOrganization`" in query:
                sql_calls.append(query)
                self.assertTrue(as_list)
                return [("ORG-1",), ("ORG-2",)]
            self.fail(f"Unexpected SQL query: {query}")

        with (
            patch("ifitwala_ed.api.admission_cockpit._ensure_cockpit_access", return_value=self.staff_user.name),
            patch("ifitwala_ed.api.admission_cockpit._get_roles_for_user", return_value={"Admission Manager"}),
            patch("ifitwala_ed.api.admission_cockpit.get_descendant_schools", return_value=[]),
            patch("ifitwala_ed.api.admission_cockpit.frappe.parse_json", return_value={"school": "MISSING-SCHOOL"}),
            patch("ifitwala_ed.api.admission_cockpit.frappe.cache", return_value=cache),
            patch("ifitwala_ed.api.admission_cockpit.frappe.as_json", side_effect=lambda value: value),
            patch("ifitwala_ed.api.admission_cockpit.frappe.db.sql", side_effect=fake_sql),
            patch("ifitwala_ed.api.admission_cockpit.frappe.get_all") as get_all_mock,
        ):
            payload = get_admissions_cockpit_data(filters={"school": "MISSING-SCHOOL"})

        get_all_mock.assert_not_called()
        self.assertEqual(len(sql_calls), 1)
        self.assertEqual(payload["config"]["organizations"], ["ORG-1", "ORG-2"])
        self.assertEqual(payload["config"]["schools"], [])

    def test_missing_requirement_blocker_targets_applicant_workspace(self):
        document_type = self._create_document_type(
            organization=self.organization,
            school=self.school,
            is_repeatable=0,
            min_items_required=1,
        )

        card = self._get_cockpit_card(self.applicant.name)
        self.assertFalse(bool((card.get("readiness") or {}).get("documents_ok")))

        blocker = self._get_blocker(card, "missing_documents")
        self.assertEqual(blocker.get("label"), "Requirements awaiting submission: 1")
        self.assertEqual(blocker.get("target_doctype"), "Student Applicant")
        self.assertEqual(blocker.get("target_name"), self.applicant.name)
        self.assertEqual(blocker.get("target_label"), "Open requirement")
        self.assertEqual(blocker.get("workspace_mode"), "applicant")
        self.assertEqual(blocker.get("workspace_student_applicant"), self.applicant.name)
        self.assertEqual(blocker.get("workspace_document_type"), document_type)
        self.assertFalse(blocker.get("workspace_applicant_document"))
        self.assertFalse(blocker.get("workspace_document_item"))
        self.assertIn("/desk/student-applicant/", blocker.get("target_url") or "")
        self.assertNotIn("/desk/applicant-document/", blocker.get("target_url") or "")

    def test_pending_submission_blocker_targets_submission_review_anchor(self):
        document_type = self._create_document_type(
            organization=self.organization,
            school=self.school,
            is_repeatable=0,
            min_items_required=1,
        )
        upload = self._upload_submission(document_type=document_type, item_key="passport_scan")

        card = self._get_cockpit_card(self.applicant.name)
        self.assertFalse(bool((card.get("readiness") or {}).get("documents_ok")))

        blocker = self._get_blocker(card, "documents_unapproved")
        self.assertEqual(blocker.get("label"), "Submitted files awaiting review: 1")
        self.assertEqual(blocker.get("target_doctype"), "Student Applicant")
        self.assertEqual(blocker.get("target_name"), self.applicant.name)
        self.assertEqual(blocker.get("target_label"), "Open submission review")
        self.assertEqual(blocker.get("workspace_mode"), "applicant")
        self.assertEqual(blocker.get("workspace_student_applicant"), self.applicant.name)
        self.assertEqual(blocker.get("workspace_document_type"), document_type)
        self.assertEqual(blocker.get("workspace_applicant_document"), upload.get("applicant_document"))
        self.assertEqual(blocker.get("workspace_document_item"), upload.get("applicant_document_item"))

    def test_rejected_submission_blocker_targets_requirement_anchor_for_resubmission(self):
        document_type = self._create_document_type(
            organization=self.organization,
            school=self.school,
            is_repeatable=0,
            min_items_required=1,
        )
        upload = self._upload_submission(document_type=document_type, item_key="passport_scan")
        self._review_submission(
            applicant_document_item=upload.get("applicant_document_item"),
            decision="Rejected",
            notes="The upload is unreadable.",
        )

        card = self._get_cockpit_card(self.applicant.name)
        self.assertFalse(bool((card.get("readiness") or {}).get("documents_ok")))

        blocker = self._get_blocker(card, "documents_unapproved")
        self.assertEqual(blocker.get("label"), "Requirements awaiting resubmission: 1")
        self.assertEqual(blocker.get("target_label"), "Open requirement")
        self.assertEqual(blocker.get("workspace_document_type"), document_type)
        self.assertEqual(blocker.get("workspace_applicant_document"), upload.get("applicant_document"))
        self.assertFalse(blocker.get("workspace_document_item"))

    def test_repeatable_requirement_override_marks_documents_ready_in_cockpit(self):
        document_type = self._create_document_type(
            organization=self.organization,
            school=self.school,
            is_repeatable=1,
            min_items_required=2,
        )

        frappe.set_user(self.staff_user.name)
        set_document_requirement_override(
            student_applicant=self.applicant.name,
            document_type=document_type,
            requirement_override="Waived",
            override_reason="School approved a waiver for this applicant.",
            client_request_id=f"waive-{frappe.generate_hash(length=8)}",
        )

        card = self._get_cockpit_card(self.applicant.name)
        self.assertTrue(bool((card.get("readiness") or {}).get("documents_ok")))
        self.assertFalse(
            any(
                (blocker or {}).get("kind") in {"missing_documents", "documents_unapproved"}
                for blocker in (card.get("blockers") or [])
            )
        )

    def test_cockpit_card_exposes_committee_approved_enrollment_plan_state(self):
        context = self._create_offer_plan(status="Committee Approved")

        card = self._get_cockpit_card(self.applicant.name)
        aep = card.get("aep") or {}

        self.assertTrue(bool(aep.get("has_plan")))
        self.assertEqual(aep.get("name"), context["plan"].name)
        self.assertEqual(aep.get("status"), "Committee Approved")
        self.assertTrue(bool(aep.get("open_url")))
        self.assertTrue(bool(aep.get("can_send_offer")))
        self.assertFalse(bool(aep.get("can_hydrate_request")))
        self.assertFalse(aep.get("program_enrollment_request"))

    def test_send_admissions_cockpit_offer_advances_plan_status(self):
        context = self._create_offer_plan(status="Committee Approved")

        frappe.set_user(self.staff_user.name)
        with patch("ifitwala_ed.api.admission_cockpit.invalidate_admissions_cockpit_cache") as invalidate_mock:
            result = send_admissions_cockpit_offer(context["plan"].name)

        context["plan"].reload()

        self.assertTrue(bool(result.get("ok")))
        self.assertEqual(result.get("applicant_enrollment_plan"), context["plan"].name)
        self.assertEqual(result.get("status"), "Offer Sent")
        self.assertEqual(context["plan"].status, "Offer Sent")
        invalidate_mock.assert_called_once()

    def test_hydrate_admissions_cockpit_request_returns_request_link(self):
        context = self._create_offer_plan(status="Offer Accepted")
        expected_request = f"PER-COCKPIT-{frappe.generate_hash(length=6)}"

        def _fake_hydrate(plan_name: str):
            self.assertEqual(plan_name, context["plan"].name)
            frappe.db.set_value(
                "Applicant Enrollment Plan",
                plan_name,
                {
                    "status": "Hydrated",
                    "program_enrollment_request": expected_request,
                },
                update_modified=False,
            )
            return {"name": expected_request, "created": True}

        frappe.set_user(self.staff_user.name)
        with (
            patch(
                "ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan.hydrate_program_enrollment_request_from_applicant_plan",
                side_effect=_fake_hydrate,
            ) as hydrate_mock,
            patch("ifitwala_ed.api.admission_cockpit.invalidate_admissions_cockpit_cache") as invalidate_mock,
        ):
            result = hydrate_admissions_cockpit_request(context["plan"].name)

        self.assertTrue(bool(result.get("ok")))
        self.assertEqual(result.get("applicant_enrollment_plan"), context["plan"].name)
        self.assertEqual(result.get("status"), "Hydrated")
        self.assertEqual(result.get("program_enrollment_request"), expected_request)
        self.assertIn("/desk/program-enrollment-request/", result.get("program_enrollment_request_url") or "")
        self.assertTrue(bool(result.get("created")))
        hydrate_mock.assert_called_once_with(context["plan"].name)
        invalidate_mock.assert_called_once()

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

    def _ensure_gender(self, gender_name: str):
        if frappe.db.exists("Gender", gender_name):
            return
        gender = frappe.get_doc({"doctype": "Gender", "gender": gender_name}).insert(ignore_permissions=True)
        self._created.append(("Gender", gender.name))

    def _create_user(self, prefix: str, roles: list[str]):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"cockpit-{prefix}-{frappe.generate_hash(length=6)}@example.com",
                "first_name": "Cockpit",
                "last_name": prefix.title(),
                "enabled": 1,
                "send_welcome_email": 0,
                "send_password_notification": 0,
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
                "employee_first_name": "Cockpit",
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
                "organization_name": f"Cockpit Org {frappe.generate_hash(length=6)}",
                "abbr": f"CO{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", organization.name))
        return organization.name

    def _create_school(self, organization: str) -> str:
        school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"Cockpit School {frappe.generate_hash(length=6)}",
                "abbr": f"CS{frappe.generate_hash(length=3)}",
                "organization": organization,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", school.name))
        return school.name

    def _create_applicant(self, organization: str, school: str, applicant_user: str):
        applicant = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Cockpit",
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

    def _create_document_type(
        self,
        *,
        organization: str,
        school: str,
        is_repeatable: int,
        min_items_required: int,
    ) -> str:
        code = f"cockpit_doc_{frappe.generate_hash(length=6)}"
        document_type = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": f"Cockpit Doc {code}",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "is_required": 1,
                "is_repeatable": is_repeatable,
                "min_items_required": min_items_required,
                "classification_slot": f"admissions_{frappe.scrub(code)}",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", document_type.name))
        return document_type.name

    def _create_offer_plan(self, *, status: str):
        academic_year = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
                "school": self.school,
                "year_start_date": "2025-08-01",
                "year_end_date": "2026-06-30",
                "archived": 0,
                "visible_to_admission": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Academic Year", academic_year.name))

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
                "course_name": f"Offer Course {frappe.generate_hash(length=6)}",
                "status": "Active",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Course", required_course.name))

        program = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Program {frappe.generate_hash(length=6)}",
                "grade_scale": grade_scale.name,
                "courses": [{"course": required_course.name, "level": "None"}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program", program.name))

        offering = frappe.get_doc(
            {
                "doctype": "Program Offering",
                "program": program.name,
                "school": self.school,
                "offering_title": f"Offering {frappe.generate_hash(length=6)}",
                "offering_academic_years": [{"academic_year": academic_year.name}],
                "offering_courses": [
                    {
                        "course": required_course.name,
                        "course_name": required_course.course_name,
                        "required": 1,
                        "start_academic_year": academic_year.name,
                        "end_academic_year": academic_year.name,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program Offering", offering.name))

        self.applicant.db_set("application_status", "Approved", update_modified=False)
        self.applicant.db_set("academic_year", academic_year.name, update_modified=False)
        self.applicant.db_set("program", program.name, update_modified=False)
        self.applicant.db_set("program_offering", offering.name, update_modified=False)
        self.applicant.reload()

        plan = frappe.get_doc(
            {
                "doctype": "Applicant Enrollment Plan",
                "student_applicant": self.applicant.name,
                "academic_year": academic_year.name,
                "program": program.name,
                "program_offering": offering.name,
                "status": status,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Enrollment Plan", plan.name))
        return {
            "plan": plan,
            "academic_year": academic_year,
            "program": program,
            "offering": offering,
            "required_course": required_course,
        }

    def _upload_submission(self, *, document_type: str, item_key: str) -> dict:
        frappe.set_user(self.applicant_user.name)
        with self._patched_drive_admissions_bridge():
            payload = upload_applicant_document(
                student_applicant=self.applicant.name,
                document_type=document_type,
                item_key=item_key,
                item_label=f"{item_key.title()} Submission",
                file_name=f"{item_key}.txt",
                content=self._tiny_file_base64(),
            )
        frappe.set_user("Administrator")
        return payload

    def _review_submission(
        self,
        *,
        applicant_document_item: str | None,
        decision: str,
        notes: str,
    ):
        frappe.set_user(self.staff_user.name)
        review_applicant_document_submission(
            student_applicant=self.applicant.name,
            applicant_document_item=applicant_document_item,
            decision=decision,
            notes=notes,
            client_request_id=f"review-{frappe.generate_hash(length=8)}",
        )

    def _get_cockpit_card(self, applicant_name: str) -> dict:
        frappe.set_user(self.staff_user.name)
        payload = get_admissions_cockpit_data(filters={"assigned_to_me": 0, "limit": 20})
        for column in payload.get("columns") or []:
            for card in column.get("items") or []:
                if card.get("name") == applicant_name:
                    return card
        self.fail(f"Admissions cockpit card not found for {applicant_name}.")

    def _get_blocker(self, card: dict, kind: str) -> dict:
        for blocker in card.get("blockers") or []:
            if blocker.get("kind") == kind:
                return blocker
        self.fail(f"Blocker {kind} not found on cockpit card {card.get('name')}.")

    def _tiny_file_base64(self) -> str:
        return base64.b64encode(b"cockpit-file").decode()

    @contextmanager
    def _patched_drive_admissions_bridge(self):
        from ifitwala_drive.services.files.creation import create_drive_file_artifacts

        from ifitwala_ed.integrations.drive.admissions import get_applicant_document_context

        fake_drive_admissions = type("FakeDriveAdmissions", (), {"upload_applicant_document": object()})()

        def _fake_drive_upload_and_finalize(*, create_session_callable, payload, content):
            self.assertIs(create_session_callable, fake_drive_admissions.upload_applicant_document)
            context = get_applicant_document_context(
                {
                    "student_applicant": self.applicant.name,
                    "document_type": payload["document_type"],
                    "applicant_document": payload["applicant_document"],
                    "applicant_document_item": payload["applicant_document_item"],
                    "item_key": payload["item_key"],
                    "item_label": payload["item_label"],
                    "filename_original": payload["filename_original"],
                }
            )
            storage_artifact = {
                "object_key": f"files/admissions/{frappe.generate_hash(length=12)}",
                "storage_backend": "local",
                "mime_type": "text/plain",
                "size_bytes": len(content),
                "content_hash": frappe.generate_hash(length=12),
            }
            file_doc = frappe.get_doc(
                {
                    "doctype": "File",
                    "attached_to_doctype": "Applicant Document Item",
                    "attached_to_name": payload["applicant_document_item"],
                    "file_name": payload["filename_original"],
                    "content": content,
                    "is_private": 1,
                }
            )
            file_doc.flags.governed_upload = True
            file_doc.flags.drive_compat_projection = True
            file_doc = file_doc.insert(ignore_permissions=True)
            self._created.append(("File", file_doc.name))
            session_doc = frappe.get_doc(
                {
                    "doctype": "Drive Upload Session",
                    "session_key": f"cockpit-doc-{frappe.generate_hash(length=12)}",
                    "status": "completed",
                    "upload_source": "SPA",
                    "created_by_user": "Administrator",
                    "owner_doctype": context["owner_doctype"],
                    "owner_name": context["owner_name"],
                    "attached_doctype": context["attached_doctype"],
                    "attached_name": context["attached_name"],
                    "organization": context["organization"],
                    "school": context["school"],
                    "intended_primary_subject_type": context["primary_subject_type"],
                    "intended_primary_subject_id": context["primary_subject_id"],
                    "intended_data_class": context["data_class"],
                    "intended_purpose": context["purpose"],
                    "intended_retention_policy": context["retention_policy"],
                    "intended_slot": context["slot"],
                    "filename_original": payload["filename_original"],
                    "mime_type_hint": storage_artifact["mime_type"],
                    "received_size_bytes": storage_artifact["size_bytes"],
                    "content_hash": storage_artifact["content_hash"],
                    "is_private": 1,
                    "storage_backend": storage_artifact["storage_backend"],
                    "tmp_object_key": f"tmp/admissions/{frappe.generate_hash(length=12)}",
                    "upload_token": frappe.generate_hash(length=16),
                }
            ).insert(ignore_permissions=True)
            self._created.append(("Drive Upload Session", session_doc.name))
            artifacts = create_drive_file_artifacts(
                upload_session_doc=session_doc,
                file_id=file_doc.name,
                storage_artifact=storage_artifact,
                binding_role="applicant_document",
            )
            self._created.append(("Drive File", artifacts["drive_file_id"]))
            if artifacts.get("drive_file_version_id"):
                self._created.append(("Drive File Version", artifacts["drive_file_version_id"]))
            if artifacts.get("drive_binding_id"):
                self._created.append(("Drive Binding", artifacts["drive_binding_id"]))
            for doctype in ("Drive File Derivative", "Drive Processing Job"):
                for name in frappe.get_all(
                    doctype,
                    filters={"drive_file": artifacts["drive_file_id"]},
                    pluck="name",
                ):
                    self._created.append((doctype, name))
            return (
                {"upload_session_id": "DUS-TEST"},
                {
                    "file_id": file_doc.name,
                    "file_url": file_doc.file_url,
                    "drive_file_id": artifacts["drive_file_id"],
                    "canonical_ref": artifacts["canonical_ref"],
                    "applicant_document": payload["applicant_document"],
                    "applicant_document_item": payload["applicant_document_item"],
                    "item_key": payload["item_key"],
                    "item_label": payload["item_label"],
                },
                file_doc,
            )

        with (
            patch(
                "ifitwala_drive.api.admissions.upload_applicant_document",
                new=fake_drive_admissions.upload_applicant_document,
            ),
            patch(
                "ifitwala_ed.admission.admissions_portal._drive_upload_and_finalize",
                side_effect=_fake_drive_upload_and_finalize,
            ),
        ):
            yield
