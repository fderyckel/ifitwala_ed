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


def _insert_user_without_notifications(user):
    # User field values can shadow same-named methods on the document instance.
    with (
        patch.object(user, "send_password_notification"),
        patch.object(user, "send_welcome_mail_to_user"),
        patch("frappe.core.doctype.user.user.User.send_password_notification"),
        patch("frappe.core.doctype.user.user.User.send_welcome_mail_to_user"),
    ):
        return user.insert(ignore_permissions=True)


def _admission_settings_has_field(fieldname: str) -> bool:
    try:
        return bool(frappe.get_meta("Admission Settings").has_field(fieldname))
    except Exception:
        return False


class TestAdmissionsDocumentItems(FrappeTestCase):
    def setUp(self):
        self._welcome_mail_patcher = patch("frappe.core.doctype.user.user.User.send_welcome_mail_to_user")
        self._welcome_mail_patcher.start()
        self._password_notification_patcher = patch("frappe.core.doctype.user.user.User.send_password_notification")
        self._password_notification_patcher.start()
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Admissions Applicant")
        self._ensure_role("Admissions Family")

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
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("file_name"), "aisl-2019.txt")
        self.assertTrue(payload.get("open_url"))
        self.assertEqual(payload.get("attachment_preview", {}).get("owner_doctype"), "Student Applicant")
        self.assertEqual(payload.get("attachment_preview", {}).get("owner_name"), self.applicant.name)
        self.assertEqual(payload.get("attachment_preview", {}).get("open_url"), payload.get("open_url"))
        self.assertEqual(payload.get("attachment_preview", {}).get("preview_url"), payload.get("preview_url"))

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

    def test_list_applicant_documents_batches_drive_preview_metadata(self):
        frappe.set_user(self.applicant_user)
        with self._patched_drive_admissions_bridge():
            first_upload = upload_applicant_document(
                student_applicant=self.applicant.name,
                document_type=self.document_type,
                item_key="aisl_2019",
                item_label="AISL transcript 2019",
                file_name="aisl-2019.pdf",
                content=self._tiny_file_base64(),
            )
            second_upload = upload_applicant_document(
                student_applicant=self.applicant.name,
                document_type=self.document_type,
                item_key="isl_2020",
                item_label="ISL transcript 2020",
                file_name="isl-2020.pdf",
                content=self._tiny_file_base64(),
            )

        item_names = [
            first_upload.get("applicant_document_item"),
            second_upload.get("applicant_document_item"),
        ]
        drive_queries: list[dict] = []
        thumbnail_queries: list[list[str]] = []
        version_queries: list[list[str]] = []

        def fake_current_drive_files_for_attachments(*, attached_doctype, attached_names, fields, statuses):
            drive_queries.append(
                {
                    "attached_doctype": attached_doctype,
                    "attached_names": list(attached_names or []),
                    "fields": list(fields or []),
                    "statuses": tuple(statuses or ()),
                }
            )
            return [
                {
                    "name": "DRV-ADM-DOC-1",
                    "attached_name": item_names[0],
                    "file": "FILE-ADM-DOC-1",
                    "canonical_ref": f"drv:{self.organization}:DRV-ADM-DOC-1",
                    "display_name": "aisl-2019.pdf",
                    "preview_status": "ready",
                    "current_version": "VER-ADM-DOC-1",
                    "creation": "2026-04-27 08:00:00",
                },
                {
                    "name": "DRV-ADM-DOC-2",
                    "attached_name": item_names[1],
                    "file": "FILE-ADM-DOC-2",
                    "canonical_ref": f"drv:{self.organization}:DRV-ADM-DOC-2",
                    "display_name": "isl-2020.pdf",
                    "preview_status": "processing",
                    "current_version": "VER-ADM-DOC-2",
                    "creation": "2026-04-27 08:01:00",
                },
            ]

        def fake_thumbnail_ready_map(drive_file_ids):
            thumbnail_queries.append(list(drive_file_ids or []))
            return {"DRV-ADM-DOC-1": True, "DRV-ADM-DOC-2": False}

        def fake_version_mime_map(version_ids):
            version_queries.append(list(version_ids or []))
            return {"VER-ADM-DOC-1": "application/pdf", "VER-ADM-DOC-2": "application/pdf"}

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.get_current_drive_files_for_attachments",
                side_effect=fake_current_drive_files_for_attachments,
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.get_drive_file_thumbnail_ready_map",
                side_effect=fake_thumbnail_ready_map,
            ),
            patch(
                "ifitwala_ed.api.admissions_portal._load_drive_version_mime_map",
                side_effect=fake_version_mime_map,
            ),
        ):
            payload = list_applicant_documents(student_applicant=self.applicant.name)

        self.assertEqual(len(drive_queries), 1)
        self.assertEqual(drive_queries[0]["attached_doctype"], "Applicant Document Item")
        self.assertCountEqual(drive_queries[0]["attached_names"], item_names)
        self.assertIn("current_version", drive_queries[0]["fields"])
        self.assertEqual(drive_queries[0]["statuses"], ("active", "processing", "blocked"))
        self.assertEqual(thumbnail_queries, [["DRV-ADM-DOC-1", "DRV-ADM-DOC-2"]])
        self.assertEqual(version_queries, [["VER-ADM-DOC-1", "VER-ADM-DOC-2"]])

        documents = payload.get("documents") or []
        self.assertEqual(len(documents), 1)
        items_by_name = {row.get("name"): row for row in documents[0].get("items") or []}
        self.assertIn("thumbnail_admissions_file", str(items_by_name[item_names[0]].get("thumbnail_url") or ""))
        self.assertIn("preview_admissions_file", str(items_by_name[item_names[0]].get("preview_url") or ""))
        self.assertIsNone(items_by_name[item_names[1]].get("thumbnail_url"))
        self.assertIsNone(items_by_name[item_names[1]].get("preview_url"))

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

    def test_family_workspace_user_can_upload_applicant_document_without_doctype_docperm(self):
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")

        previous_mode = frappe.db.get_single_value("Admission Settings", "admissions_access_mode")
        family_user = self._create_family_user()
        self._link_family_user_to_applicant(family_user)
        frappe.db.set_single_value("Admission Settings", "admissions_access_mode", "Family Workspace")

        try:
            frappe.set_user(family_user)
            with self._patched_drive_admissions_bridge():
                payload = upload_applicant_document(
                    student_applicant=self.applicant.name,
                    document_type=self.document_type,
                    item_key="family_transcript",
                    item_label="Family uploaded transcript",
                    file_name="family-transcript.txt",
                    content=self._tiny_file_base64(),
                )
        finally:
            frappe.set_user("Administrator")
            frappe.db.set_single_value(
                "Admission Settings",
                "admissions_access_mode",
                previous_mode or "Single Applicant Workspace",
            )

        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("applicant_document"))
        self.assertTrue(payload.get("applicant_document_item"))

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
                "roles": [{"role": "Admissions Applicant"}],
            }
        )
        user.flags.no_welcome_mail = True
        user = _insert_user_without_notifications(user)
        self._created.append(("User", user.name))
        frappe.clear_cache(user=user.name)
        return user.name

    def _create_family_user(self) -> str:
        email = f"portal-family-doc-item-{frappe.generate_hash(length=8)}@example.com"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Portal",
                "last_name": "Family",
                "enabled": 1,
                "send_welcome_email": 0,
                "roles": [{"role": "Admissions Family"}],
            }
        )
        user.flags.no_welcome_mail = True
        user = _insert_user_without_notifications(user)
        self._created.append(("User", user.name))
        frappe.clear_cache(user=user.name)
        return user.name

    def _link_family_user_to_applicant(self, family_user: str) -> None:
        self.applicant.append(
            "guardians",
            {
                "user": family_user,
                "relationship": "Parent",
                "can_consent": 1,
                "is_primary": 1,
                "is_primary_guardian": 1,
                "guardian_first_name": "Portal",
                "guardian_last_name": "Family",
                "guardian_email": family_user,
            },
        )
        self.applicant.save(ignore_permissions=True)

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
