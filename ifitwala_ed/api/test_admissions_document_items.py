# ifitwala_ed/api/test_admissions_document_items.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

import base64
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.admissions_portal import _resolve_applicant_document
from ifitwala_ed.api.admissions_portal import (
    list_applicant_document_types,
    list_applicant_documents,
    upload_applicant_document,
)


class TestAdmissionsDocumentItems(FrappeTestCase):
    def setUp(self):
        self._welcome_mail_patcher = patch("frappe.core.doctype.user.user.User.send_welcome_mail_to_user")
        self._welcome_mail_patcher.start()
        self._password_notification_patcher = patch("frappe.core.doctype.user.user.User.send_password_notification")
        self._password_notification_patcher.start()
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Admissions Applicant")

        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant_user = self._create_applicant_user()
        self.applicant = self._create_applicant(self.organization, self.school, self.applicant_user)
        self.document_type = self._create_document_type(self.organization, self.school)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        self._password_notification_patcher.stop()
        self._welcome_mail_patcher.stop()

    def test_upload_creates_item_and_returns_item_metadata(self):
        frappe.set_user(self.applicant_user)
        with self._patched_drive_admissions_bridge():
            payload = upload_applicant_document(
                student_applicant=self.applicant.name,
                document_type=self.document_type,
                item_key="aisl_2019",
                item_label="AISL transcript 2019",
                file_name="aisl-2019.txt",
                content=self._tiny_file_base64(),
            )

        self.assertTrue(bool(payload.get("applicant_document")))
        self.assertTrue(bool(payload.get("applicant_document_item")))
        self.assertEqual(payload.get("item_key"), "aisl_2019")
        self.assertEqual(payload.get("item_label"), "AISL transcript 2019")

        row = frappe.db.get_value(
            "Applicant Document Item",
            payload.get("applicant_document_item"),
            ["applicant_document", "item_key", "item_label"],
            as_dict=True,
        )
        self.assertTrue(bool(row))
        self.assertEqual(row.get("item_key"), "aisl_2019")
        self.assertEqual(row.get("item_label"), "AISL transcript 2019")

    def test_upload_reads_flat_form_payload_when_request_binding_omits_kwargs(self):
        frappe.set_user(self.applicant_user)
        with self._patched_form_dict(
            {
                "student_applicant": self.applicant.name,
                "document_type": self.document_type,
                "item_key": "passport",
                "item_label": "Passport",
                "client_request_id": f"upload_{frappe.generate_hash(length=8)}",
                "file_name": "passport.txt",
                "content": self._tiny_file_base64(),
            }
        ):
            with self._patched_drive_admissions_bridge():
                payload = upload_applicant_document()

        self.assertTrue(bool(payload.get("applicant_document")))
        self.assertTrue(bool(payload.get("applicant_document_item")))
        self.assertEqual(payload.get("item_key"), "passport")
        self.assertEqual(payload.get("item_label"), "Passport")

    def test_upload_reads_json_request_payload_when_bound_kwargs_are_blank_strings(self):
        frappe.set_user(self.applicant_user)
        request_payload = {
            "student_applicant": self.applicant.name,
            "document_type": self.document_type,
            "item_key": "passport",
            "item_label": "Passport",
            "client_request_id": f"upload_{frappe.generate_hash(length=8)}",
            "file_name": "passport.txt",
            "content": self._tiny_file_base64(),
        }
        with self._patched_form_dict({}), self._patched_request_json(request_payload):
            with self._patched_drive_admissions_bridge():
                payload = upload_applicant_document(
                    student_applicant="",
                    document_type="",
                    file_name="",
                    content="",
                )

        self.assertTrue(bool(payload.get("applicant_document")))
        self.assertTrue(bool(payload.get("applicant_document_item")))
        self.assertEqual(payload.get("item_key"), "passport")
        self.assertEqual(payload.get("item_label"), "Passport")

    def test_repeatable_upload_keeps_multiple_items(self):
        frappe.set_user(self.applicant_user)
        with self._patched_drive_admissions_bridge():
            upload_applicant_document(
                student_applicant=self.applicant.name,
                document_type=self.document_type,
                item_key="aisl_2019",
                item_label="AISL transcript 2019",
                file_name="aisl-2019.txt",
                content=self._tiny_file_base64(),
            )
            upload_applicant_document(
                student_applicant=self.applicant.name,
                document_type=self.document_type,
                item_key="isl_2020",
                item_label="ISL transcript 2020",
                file_name="isl-2020.txt",
                content=self._tiny_file_base64(),
            )

        payload = list_applicant_documents(student_applicant=self.applicant.name)
        documents = payload.get("documents") or []
        self.assertEqual(len(documents), 1)

        items = documents[0].get("items") or []
        self.assertEqual(len(items), 2)
        labels = {row.get("item_label") for row in items}
        self.assertIn("AISL transcript 2019", labels)
        self.assertIn("ISL transcript 2020", labels)

    def test_upload_without_item_description_uses_server_generated_submission_label(self):
        frappe.set_user(self.applicant_user)
        with self._patched_drive_admissions_bridge():
            payload = upload_applicant_document(
                student_applicant=self.applicant.name,
                document_type=self.document_type,
                file_name="unknown.txt",
                content=self._tiny_file_base64(),
            )

        row = frappe.db.get_value(
            "Applicant Document Item",
            payload.get("applicant_document_item"),
            ["item_key", "item_label"],
            as_dict=True,
        )
        self.assertTrue(bool(row))
        self.assertTrue(bool(row.get("item_key")))
        self.assertTrue(bool(row.get("item_label")))

    def test_resolve_applicant_document_from_item_without_document_type(self):
        frappe.set_user(self.applicant_user)
        with self._patched_drive_admissions_bridge():
            payload = upload_applicant_document(
                student_applicant=self.applicant.name,
                document_type=self.document_type,
                item_label="Passport",
                file_name="passport.txt",
                content=self._tiny_file_base64(),
            )

        doc = _resolve_applicant_document(
            student_applicant=self.applicant.name,
            applicant_document_item=payload.get("applicant_document_item"),
        )

        self.assertEqual(doc.name, payload.get("applicant_document"))
        self.assertEqual(doc.student_applicant, self.applicant.name)
        self.assertEqual(doc.document_type, self.document_type)

    def test_recommendation_target_document_types_are_hidden_from_documents_and_uploads(self):
        recommendation_document_type = self._create_recommendation_document_type(
            self.organization,
            self.school,
        )
        self._create_recommendation_template(
            organization=self.organization,
            school=self.school,
            target_document_type=recommendation_document_type,
        )
        self._create_applicant_document(
            student_applicant=self.applicant.name,
            document_type=recommendation_document_type,
        )

        frappe.set_user(self.applicant_user)
        documents_payload = list_applicant_documents(student_applicant=self.applicant.name)
        self.assertFalse(
            any(
                row.get("document_type") == recommendation_document_type
                for row in documents_payload.get("documents") or []
            )
        )

        types_payload = list_applicant_document_types(student_applicant=self.applicant.name)
        self.assertFalse(
            any(row.get("name") == recommendation_document_type for row in types_payload.get("document_types") or [])
        )

        with self.assertRaises(frappe.ValidationError):
            with self._patched_drive_admissions_bridge():
                upload_applicant_document(
                    student_applicant=self.applicant.name,
                    document_type=recommendation_document_type,
                    file_name="recommendation.txt",
                    content=self._tiny_file_base64(),
                )

    @contextmanager
    def _patched_drive_admissions_bridge(self):
        fake_drive_admissions = type("FakeDriveAdmissions", (), {"upload_applicant_document": object()})()

        def _fake_drive_upload_and_finalize(*, create_session_callable, payload, content):
            self.assertIs(create_session_callable, fake_drive_admissions.upload_applicant_document)
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
            file_doc.insert(ignore_permissions=True)
            self._created.append(("File", file_doc.name))
            drive_file_id = f"DRV-{file_doc.name}"
            return (
                {"upload_session_id": "DUS-TEST"},
                {
                    "file_id": file_doc.name,
                    "file_url": file_doc.file_url,
                    "drive_file_id": drive_file_id,
                    "canonical_ref": f"drv:{self.organization}:{drive_file_id}",
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

    @contextmanager
    def _patched_form_dict(self, payload: dict):
        original_form_dict = getattr(frappe, "form_dict", None)
        frappe.form_dict = frappe._dict(payload)
        try:
            yield
        finally:
            if original_form_dict is None:
                try:
                    del frappe.form_dict
                except AttributeError:
                    pass
            else:
                frappe.form_dict = original_form_dict

    @contextmanager
    def _patched_request_json(self, payload: dict):
        original_request = getattr(frappe, "request", None)
        frappe.request = SimpleNamespace(
            get_json=lambda silent=True: payload,
            data=frappe.as_json(payload),
            files=None,
            mimetype="application/json",
        )
        try:
            yield
        finally:
            if original_request is None:
                try:
                    del frappe.request
                except AttributeError:
                    pass
            else:
                frappe.request = original_request

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

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

    def _create_applicant_user(self) -> str:
        email = f"portal-doc-item-{frappe.generate_hash(length=8)}@example.com"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Portal",
                "last_name": "Applicant",
                "enabled": 1,
                "send_welcome_email": 0,
                "send_password_notification": 0,
                "roles": [{"role": "Admissions Applicant"}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        frappe.clear_cache(user=user.name)
        return user.name

    def _create_applicant(self, organization: str, school: str, applicant_user: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Portal",
                "last_name": f"Docs-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        doc.db_set("applicant_user", applicant_user, update_modified=False)
        doc.db_set("application_status", "Invited", update_modified=False)
        doc.reload()
        self._created.append(("Student Applicant", doc.name))
        return doc

    def _create_document_type(self, organization: str, school: str) -> str:
        code = f"transcript_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": "Transcript",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "is_required": 1,
                "is_repeatable": 1,
                "min_items_required": 2,
                "classification_slot": "prior_transcript",
                "classification_data_class": "academic",
                "classification_purpose": "academic_report",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name

    def _create_recommendation_document_type(self, organization: str, school: str) -> str:
        code = f"recommendation_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
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
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name

    def _create_recommendation_template(self, *, organization: str, school: str, target_document_type: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Recommendation Template",
                "template_name": f"Teacher Recommendation {frappe.generate_hash(length=5)}",
                "is_active": 1,
                "organization": organization,
                "school": school,
                "target_document_type": target_document_type,
                "minimum_required": 1,
                "maximum_allowed": 3,
                "allow_file_upload": 1,
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
        self._created.append(("Recommendation Template", doc.name))
        return doc.name

    def _create_applicant_document(self, *, student_applicant: str, document_type: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": student_applicant,
                "document_type": document_type,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", doc.name))
        return doc.name

    def _tiny_file_base64(self) -> str:
        return base64.b64encode(b"test-file-content").decode("ascii")
