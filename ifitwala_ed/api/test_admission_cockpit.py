# ifitwala_ed/api/test_admission_cockpit.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

import base64
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.admission_utils import get_applicant_document_slot_spec
from ifitwala_ed.api.admission_cockpit import get_admissions_cockpit_data
from ifitwala_ed.api.admissions_portal import upload_applicant_document
from ifitwala_ed.api.admissions_review import (
    review_applicant_document_submission,
    set_document_requirement_override,
)
from ifitwala_ed.utilities import file_dispatcher


class TestAdmissionCockpit(FrappeTestCase):
    def setUp(self):
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
        fake_drive_admissions = type("FakeDriveAdmissions", (), {"upload_applicant_document": object()})()

        def _fake_drive_upload_and_finalize(*, create_session_callable, payload, content):
            self.assertIs(create_session_callable, fake_drive_admissions.upload_applicant_document)
            slot_spec = get_applicant_document_slot_spec(document_type=payload["document_type"])
            item_slot_key = f"{slot_spec['slot']}_{frappe.scrub(payload['item_key'])[:80]}"
            file_doc = file_dispatcher.create_and_classify_file(
                file_kwargs={
                    "attached_to_doctype": "Applicant Document Item",
                    "attached_to_name": payload["applicant_document_item"],
                    "file_name": payload["filename_original"],
                    "content": content,
                    "is_private": 1,
                },
                classification={
                    "primary_subject_type": "Student Applicant",
                    "primary_subject_id": payload["student_applicant"],
                    "data_class": slot_spec["data_class"],
                    "purpose": slot_spec["purpose"],
                    "retention_policy": slot_spec["retention_policy"],
                    "slot": item_slot_key,
                    "organization": self.organization,
                    "school": self.school,
                    "upload_source": payload.get("upload_source") or "SPA",
                },
            )
            classification_name = frappe.db.get_value("File Classification", {"file": file_doc.name}, "name")
            return (
                {"upload_session_id": "DUS-TEST"},
                {
                    "file_id": file_doc.name,
                    "file_url": file_doc.file_url,
                    "classification": classification_name,
                    "applicant_document": payload["applicant_document"],
                    "applicant_document_item": payload["applicant_document_item"],
                    "item_key": payload["item_key"],
                    "item_label": payload["item_label"],
                },
                file_doc,
            )

        with (
            patch(
                "ifitwala_ed.admission.admissions_portal._load_drive_module",
                return_value=fake_drive_admissions,
            ),
            patch(
                "ifitwala_ed.admission.admissions_portal._drive_upload_and_finalize",
                side_effect=_fake_drive_upload_and_finalize,
            ),
        ):
            yield
