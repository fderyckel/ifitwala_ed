# ifitwala_ed/admission/api/test_portal_profile_images.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt


import base64
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.api.portal.profile import (
    get_applicant_profile_impl as get_applicant_profile,
)
from ifitwala_ed.admission.api.portal.profile import (
    update_applicant_profile_impl as update_applicant_profile,
)
from ifitwala_ed.admission.api.portal.profile_images import (
    upload_applicant_guardian_image_impl as upload_applicant_guardian_image,
)
from ifitwala_ed.admission.api.portal.profile_images import (
    upload_applicant_profile_image_impl as upload_applicant_profile_image,
)
from ifitwala_ed.admission.api.portal_test_helpers import (
    AdmissionsPortalScenarioMixin,
)


class TestPortalProfileImages(AdmissionsPortalScenarioMixin, FrappeTestCase):
    def test_update_applicant_profile_rejects_invalid_guardian_email(self):
        self._set_guardians_section_setting(1)

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "relationship": "Mother",
                        "guardian_first_name": "Mina",
                        "guardian_last_name": "Portal",
                        "guardian_email": "not-an-email",
                        "guardian_mobile_phone": "+14155550102",
                        "guardian_image": "/private/files/guardian.png",
                    }
                ],
            )

    def test_update_applicant_profile_rejects_invalid_guardian_phone(self):
        self._set_guardians_section_setting(1)

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "relationship": "Father",
                        "guardian_first_name": "Jean",
                        "guardian_last_name": "Portal",
                        "guardian_email": f"guardian-{frappe.generate_hash(length=8)}@example.com",
                        "guardian_mobile_phone": "bad-phone",
                        "guardian_image": "/private/files/guardian.png",
                    }
                ],
            )

    def test_update_applicant_profile_rejects_missing_guardian_image(self):
        self._set_guardians_section_setting(1)

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "relationship": "Mother",
                        "guardian_first_name": "Mina",
                        "guardian_last_name": "Portal",
                        "guardian_email": f"guardian-{frappe.generate_hash(length=8)}@example.com",
                        "guardian_mobile_phone": "+14155550102",
                        "guardian_image": "",
                    }
                ],
            )

    def test_update_applicant_profile_preserves_existing_guardian_image_when_thumbnail_pending(self):
        self._set_guardians_section_setting(1)
        guardian_email = f"guardian-thumbnail-{frappe.generate_hash(length=8)}@example.com"
        persisted_image = "/private/files/guardian-thumbnail-pending.jpg"
        guardian_row = self.applicant.append(
            "guardians",
            {
                "relationship": "Mother",
                "can_consent": 1,
                "is_primary": 1,
                "is_primary_guardian": 1,
                "guardian_first_name": "Mina",
                "guardian_last_name": "Portal",
                "guardian_email": guardian_email,
                "guardian_mobile_phone": "+14155550101",
                "guardian_image": persisted_image,
            },
        )
        self.applicant.save(ignore_permissions=True)
        guardian_row_name = guardian_row.name

        frappe.set_user(self.applicant_user)
        payload = update_applicant_profile(
            student_applicant=self.applicant.name,
            guardians=[
                {
                    "name": guardian_row_name,
                    "relationship": "Mother",
                    "can_consent": 1,
                    "is_primary": 1,
                    "is_primary_guardian": 1,
                    "guardian_first_name": "Mina",
                    "guardian_last_name": "Portal",
                    "guardian_email": guardian_email,
                    "guardian_mobile_phone": "+14155550101",
                    "guardian_image": "",
                }
            ],
        )

        self.assertTrue(payload.get("ok"))
        self.applicant.reload()
        rows = self.applicant.get("guardians") or []
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].guardian_image, persisted_image)

    def test_update_applicant_profile_preserves_guardian_image_attachment_scope_on_guardian_row(self):
        self._set_guardians_section_setting(1)

        contact = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": "Applicant",
                "last_name": "Contact",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Contact", contact.name))
        self.applicant.db_set("applicant_contact", contact.name, update_modified=False)
        self.applicant.reload()

        guardian_email = f"guardian-{frappe.generate_hash(length=8)}@example.com"
        guardian_row = self.applicant.append(
            "guardians",
            {
                "relationship": "Mother",
                "use_applicant_contact": 1,
                "can_consent": 1,
                "is_primary": 1,
                "is_primary_guardian": 1,
                "guardian_first_name": "Mina",
                "guardian_last_name": "Portal",
                "guardian_email": guardian_email,
                "guardian_mobile_phone": "+14155550101",
            },
        )
        self.applicant.save(ignore_permissions=True)
        guardian_row_name = guardian_row.name

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Student Applicant Guardian",
                "attached_to_name": guardian_row_name,
                "attached_to_field": "guardian_image",
                "file_name": "guardian.png",
                "content": base64.b64decode(self._tiny_png_base64()),
                "is_private": 1,
            }
        )
        file_doc.flags.governed_upload = True
        file_doc.insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.admission.doctype.student_applicant.student_applicant.ensure_guardian_profile_image",
                return_value=file_doc.file_url,
            ),
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.get_drive_file_for_file",
                return_value={
                    "name": "DRV-GUARDIAN-1",
                    "file": file_doc.name,
                    "canonical_ref": f"drv:{self.organization}:DRV-GUARDIAN-1",
                    "primary_subject_type": "Student Applicant",
                    "primary_subject_id": self.applicant.name,
                },
            ),
            patch(
                "ifitwala_ed.admission.api.portal.profile.get_drive_file_thumbnail_ready_map",
                return_value={"DRV-GUARDIAN-1": True},
            ),
        ):
            payload = update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "name": guardian_row_name,
                        "relationship": "Mother",
                        "use_applicant_contact": 1,
                        "can_consent": 1,
                        "is_primary": 1,
                        "is_primary_guardian": 1,
                        "guardian_first_name": "Mina",
                        "guardian_last_name": "Portal",
                        "guardian_email": guardian_email,
                        "guardian_mobile_phone": "+14155550101",
                        "guardian_image": file_doc.file_url,
                    }
                ],
            )

        self.assertTrue(payload.get("ok"))
        guardian_payload = (payload.get("guardians") or [{}])[0]
        self.assertIn("thumbnail_admissions_file", guardian_payload.get("guardian_image") or "")
        self.assertIn("download_admissions_file", guardian_payload.get("guardian_image_open_url") or "")
        file_row = frappe.db.get_value(
            "File",
            file_doc.name,
            ["attached_to_doctype", "attached_to_name", "attached_to_field"],
            as_dict=True,
        )
        self.assertEqual(file_row.get("attached_to_doctype"), "Student Applicant Guardian")
        self.assertEqual(file_row.get("attached_to_name"), guardian_row_name)
        self.assertEqual((file_row.get("attached_to_field") or "").strip(), "guardian_image")

    def test_get_applicant_profile_includes_applicant_image(self):
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Student Applicant",
                "attached_to_name": self.applicant.name,
                "attached_to_field": "applicant_image",
                "file_name": f"applicant-{frappe.generate_hash(length=6)}.png",
                "is_private": 1,
                "content": base64.b64decode(self._tiny_png_base64()),
            }
        )
        file_doc.flags.governed_upload = True
        file_doc.insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))
        self.applicant.db_set("applicant_image", file_doc.file_url, update_modified=False)
        self.applicant.reload()

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.get_drive_file_for_file",
                return_value={
                    "name": "DRV-APP-1",
                    "file": file_doc.name,
                    "canonical_ref": f"drv:{self.organization}:DRV-APP-1",
                    "primary_subject_type": "Student Applicant",
                    "primary_subject_id": self.applicant.name,
                },
            ),
            patch(
                "ifitwala_ed.admission.api.portal.profile.get_drive_file_thumbnail_ready_map",
                return_value={"DRV-APP-1": True},
            ),
        ):
            profile_payload = get_applicant_profile(student_applicant=self.applicant.name)
        secure_url = str(profile_payload.get("applicant_image") or "").strip()
        self.assertTrue(secure_url)
        self.assertNotIn("/private/files/", secure_url)
        self.assertIn("thumbnail_admissions_file", secure_url)
        self.assertIn(f"file={file_doc.name}", secure_url)
        self.assertIn(
            "download_admissions_file",
            str(profile_payload.get("applicant_image_open_url") or ""),
        )

    def test_upload_applicant_profile_image_denies_other_applicant(self):
        other = self._create_applicant(self.organization, self.school, applicant_user="")

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.PermissionError):
            upload_applicant_profile_image(
                student_applicant=other.name,
                file_name="student.png",
                content=self._tiny_png_base64(),
            )

    def test_upload_applicant_profile_image_denies_read_only_status(self):
        self.applicant.db_set("application_status", "Submitted", update_modified=False)
        self.applicant.reload()

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.PermissionError):
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.png",
                content=self._tiny_png_base64(),
            )

    def test_upload_applicant_profile_image_creates_governed_file(self):
        captured: dict = {}
        drive_file_id = "DRV-FILE-0001"
        canonical_ref = f"drv:{self.organization}:{drive_file_id}"

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            return {
                "file": "FILE-UP-APP-1",
                "file_url": f"/private/files/applicant-{frappe.generate_hash(length=6)}.jpg",
                "drive_file_id": drive_file_id,
                "canonical_ref": canonical_ref,
                "student_applicant": kwargs.get("student_applicant"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.admission_api.upload_applicant_profile_image",
                side_effect=_capture_drive_upload,
            ),
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.get_drive_file_thumbnail_ready_map",
                return_value={drive_file_id: True},
            ),
        ):
            payload = upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.png",
                content=self._tiny_png_base64(),
            )

        self.assertTrue(payload.get("ok"))
        self.assertIn("thumbnail_admissions_file", str(payload.get("image_url") or ""))
        self.assertIn("download_admissions_file", str(payload.get("open_url") or ""))
        self.assertEqual(str(payload.get("drive_file_id") or ""), drive_file_id)
        self.assertEqual(str(payload.get("canonical_ref") or ""), canonical_ref)
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["upload_source"], "SPA")
        self.assertTrue(captured["file_name"].startswith("applicant_profile_image_"))
        self.assertTrue(captured["file_name"].endswith(".jpg"))
        self.assertTrue(captured["content"].startswith(b"\xff\xd8\xff"))

    def test_upload_applicant_profile_image_reads_json_request_payload_when_bound_kwargs_are_blank_strings(self):
        captured: dict = {}
        drive_file_id = "DRV-FILE-JSON-1"
        canonical_ref = f"drv:{self.organization}:{drive_file_id}"
        request_payload = {
            "student_applicant": self.applicant.name,
            "file_name": "student.png",
            "content": self._tiny_png_base64(),
        }

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            return {
                "file": "FILE-UP-APP-JSON-1",
                "file_url": f"/private/files/applicant-{frappe.generate_hash(length=6)}.jpg",
                "drive_file_id": drive_file_id,
                "canonical_ref": canonical_ref,
                "student_applicant": kwargs.get("student_applicant"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch.object(frappe, "form_dict", frappe._dict(), create=True),
            patch.object(
                frappe,
                "request",
                SimpleNamespace(
                    get_json=lambda silent=True: request_payload,
                    data=frappe.as_json(request_payload),
                    files=None,
                    mimetype="application/json",
                ),
                create=True,
            ),
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.admission_api.upload_applicant_profile_image",
                side_effect=_capture_drive_upload,
            ),
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.get_drive_file_thumbnail_ready_map",
                return_value={drive_file_id: True},
            ),
        ):
            payload = upload_applicant_profile_image(
                student_applicant="",
                file_name="",
                content="",
            )

        self.assertTrue(payload.get("ok"))
        self.assertEqual(str(payload.get("drive_file_id") or ""), drive_file_id)
        self.assertEqual(str(payload.get("canonical_ref") or ""), canonical_ref)
        self.assertIn("thumbnail_admissions_file", str(payload.get("image_url") or ""))
        self.assertIn("download_admissions_file", str(payload.get("open_url") or ""))
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["upload_source"], "SPA")
        self.assertTrue(captured["file_name"].startswith("applicant_profile_image_"))
        self.assertTrue(captured["content"].startswith(b"\xff\xd8\xff"))

    def test_upload_applicant_profile_image_rejects_heic_extension(self):
        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError) as error_context:
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="IMG_1157.HEIC",
                content=self._tiny_png_base64(),
            )

        self.assertIn("Only JPG, JPEG, PNG image files are accepted", str(error_context.exception))

    def test_upload_applicant_profile_image_rejects_extension_content_mismatch(self):
        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError) as error_context:
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.jpg",
                content=self._tiny_png_base64(),
            )

        self.assertIn("extension does not match", str(error_context.exception))

    def test_upload_applicant_profile_image_rejects_files_larger_than_limit(self):
        oversized_content = base64.b64encode(b"\xff\xd8\xff" + b"a" * (11 * 1024 * 1024)).decode()

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError) as error_context:
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.jpg",
                content=oversized_content,
            )

        self.assertIn("Max file size is 10 MB", str(error_context.exception))

    def test_upload_applicant_profile_image_rejects_images_over_pixel_limit(self):
        frappe.set_user(self.applicant_user)
        with (
            patch("ifitwala_ed.admission.api.portal.profile_images.PROFILE_IMAGE_MAX_PIXELS", 0),
            self.assertRaises(frappe.ValidationError) as error_context,
        ):
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.png",
                content=self._tiny_png_base64(),
            )

        self.assertIn("Max image size is", str(error_context.exception))

    def test_upload_applicant_guardian_image_creates_governed_file(self):
        guardian_row = self.applicant.append(
            "guardians",
            {
                "relationship": "Mother",
                "guardian_first_name": "Mina",
                "guardian_last_name": "Guardian",
                "guardian_email": f"guardian-{frappe.generate_hash(length=6)}@example.com",
                "guardian_mobile_phone": "+14155550121",
            },
        )
        self.applicant.save(ignore_permissions=True)
        guardian_row_name = guardian_row.name

        captured: dict = {}
        drive_file_id = "DRV-GUARDIAN-UP-1"
        canonical_ref = f"drv:{self.organization}:{drive_file_id}"

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            return {
                "file": "FILE-UP-GUARDIAN-1",
                "file_url": f"/private/files/guardian-{frappe.generate_hash(length=6)}.jpg",
                "drive_file_id": drive_file_id,
                "canonical_ref": canonical_ref,
                "student_applicant": kwargs.get("student_applicant"),
                "guardian_row_name": kwargs.get("guardian_row_name"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.admission_api.upload_applicant_guardian_image",
                side_effect=_capture_drive_upload,
            ),
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.get_drive_file_thumbnail_ready_map",
                return_value={drive_file_id: True},
            ),
        ):
            payload = upload_applicant_guardian_image(
                student_applicant=self.applicant.name,
                guardian_row_name=guardian_row_name,
                file_name="guardian.png",
                content=self._tiny_png_base64(),
            )

        self.assertTrue(payload.get("ok"))
        self.assertIn("thumbnail_admissions_file", str(payload.get("image_url") or ""))
        self.assertIn("download_admissions_file", str(payload.get("open_url") or ""))
        self.assertEqual(str(payload.get("drive_file_id") or ""), drive_file_id)
        self.assertEqual(str(payload.get("canonical_ref") or ""), canonical_ref)
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["guardian_row_name"], guardian_row_name)
        self.assertEqual(captured["upload_source"], "SPA")
        self.assertTrue(captured["file_name"].startswith("guardian_profile_image_"))
        self.assertTrue(captured["file_name"].endswith(".jpg"))
        self.assertTrue(captured["content"].startswith(b"\xff\xd8\xff"))

    def test_upload_applicant_guardian_image_reads_json_request_payload_when_bound_kwargs_are_blank_strings(self):
        guardian_row = self.applicant.append(
            "guardians",
            {
                "relationship": "Mother",
                "guardian_first_name": "Mina",
                "guardian_last_name": "Guardian",
                "guardian_email": f"guardian-{frappe.generate_hash(length=6)}@example.com",
                "guardian_mobile_phone": "+14155550121",
            },
        )
        self.applicant.save(ignore_permissions=True)
        guardian_row_name = guardian_row.name

        captured: dict = {}
        drive_file_id = "DRV-GUARDIAN-JSON-1"
        canonical_ref = f"drv:{self.organization}:{drive_file_id}"
        request_payload = {
            "student_applicant": self.applicant.name,
            "guardian_row_name": guardian_row_name,
            "file_name": "guardian.png",
            "content": self._tiny_png_base64(),
        }

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            return {
                "file": "FILE-UP-GUARDIAN-JSON-1",
                "file_url": f"/private/files/guardian-{frappe.generate_hash(length=6)}.jpg",
                "drive_file_id": drive_file_id,
                "canonical_ref": canonical_ref,
                "student_applicant": kwargs.get("student_applicant"),
                "guardian_row_name": kwargs.get("guardian_row_name"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch.object(frappe, "form_dict", frappe._dict(), create=True),
            patch.object(
                frappe,
                "request",
                SimpleNamespace(
                    get_json=lambda silent=True: request_payload,
                    data=frappe.as_json(request_payload),
                    files=None,
                    mimetype="application/json",
                ),
                create=True,
            ),
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.admission_api.upload_applicant_guardian_image",
                side_effect=_capture_drive_upload,
            ),
            patch(
                "ifitwala_ed.admission.api.portal.profile_images.get_drive_file_thumbnail_ready_map",
                return_value={drive_file_id: True},
            ),
        ):
            payload = upload_applicant_guardian_image(
                student_applicant="",
                guardian_row_name="",
                file_name="",
                content="",
            )

        self.assertTrue(payload.get("ok"))
        self.assertEqual(str(payload.get("drive_file_id") or ""), drive_file_id)
        self.assertEqual(str(payload.get("canonical_ref") or ""), canonical_ref)
        self.assertIn("thumbnail_admissions_file", str(payload.get("image_url") or ""))
        self.assertIn("download_admissions_file", str(payload.get("open_url") or ""))
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["guardian_row_name"], guardian_row_name)
        self.assertEqual(captured["upload_source"], "SPA")
        self.assertTrue(captured["file_name"].startswith("guardian_profile_image_"))
        self.assertTrue(captured["content"].startswith(b"\xff\xd8\xff"))
