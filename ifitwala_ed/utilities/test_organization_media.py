# ifitwala_ed/utilities/test_organization_media.py

from __future__ import annotations

import base64
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.utilities.governed_file_contract import (
    ORGANIZATION_MEDIA_PURPOSE,
    ORGANIZATION_MEDIA_RETENTION_POLICY,
)
from ifitwala_ed.utilities.governed_uploads import (
    upload_organization_logo,
    upload_organization_media_asset,
)
from ifitwala_ed.utilities.organization_media import (
    build_organization_logo_slot,
    build_organization_media_classification,
    build_organization_media_slot,
    build_school_gallery_slot,
    build_school_logo_slot,
    get_visible_organization_media_for_school,
    list_owned_media_for_organization,
    list_visible_media_for_school,
)


class TestOrganizationMedia(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self.root_org = self._create_org("Org Media Root", "OMR", is_group=1)
        self.child_org = self._create_org("Org Media Child", "OMC", parent=self.root_org, is_group=1)
        self.sibling_org = self._create_org("Org Media Sibling", "OMS", parent=self.root_org, is_group=1)
        self.root_school = self._create_school("Org Media School Root", "OMSR", self.child_org, is_group=1)
        self.leaf_school = self._create_school(
            "Org Media School Leaf",
            "OMSL",
            self.child_org,
            parent=self.root_school,
            is_group=0,
        )
        self.branch_school = self._create_school(
            "Org Media School Branch",
            "OMSB",
            self.child_org,
            parent=self.root_school,
            is_group=0,
        )
        self.sibling_org_school = self._create_school(
            "Org Media Sibling Org School",
            "OMSO",
            self.sibling_org,
            is_group=0,
        )
        frappe.cache().delete_value(f"policy_scope:ancestors:{self.root_org}")
        frappe.cache().delete_value(f"policy_scope:ancestors:{self.child_org}")
        frappe.cache().delete_value(f"policy_scope:ancestors:{self.sibling_org}")
        frappe.cache().delete_value(f"policy_scope:ancestors:{self.leaf_school}")
        frappe.cache().delete_value(f"policy_scope:ancestors:{self.root_school}")
        frappe.cache().delete_value(f"policy_scope:ancestors:{self.branch_school}")

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_governed_org_media_file_carries_drive_authority(self):
        slot = build_school_logo_slot(school=self.leaf_school)
        file_doc = self._create_org_media_file(
            organization=self.child_org,
            school=self.leaf_school,
            slot=slot,
            file_name="school-logo.png",
        )

        drive_row = frappe.db.get_value(
            "Drive File",
            {"file": file_doc.name},
            [
                "primary_subject_type",
                "primary_subject_id",
                "purpose",
                "retention_policy",
                "organization",
                "school",
                "slot",
                "attached_doctype",
                "attached_name",
                "owner_doctype",
                "owner_name",
            ],
            as_dict=True,
        )
        self.assertEqual(drive_row.get("primary_subject_type"), "Organization")
        self.assertEqual(drive_row.get("primary_subject_id"), self.child_org)
        self.assertEqual(drive_row.get("purpose"), ORGANIZATION_MEDIA_PURPOSE)
        self.assertEqual(drive_row.get("retention_policy"), ORGANIZATION_MEDIA_RETENTION_POLICY)
        self.assertEqual(drive_row.get("organization"), self.child_org)
        self.assertEqual(drive_row.get("school"), self.leaf_school)
        self.assertEqual(drive_row.get("slot"), slot)
        self.assertEqual(drive_row.get("attached_doctype"), "Organization")
        self.assertEqual(drive_row.get("attached_name"), self.child_org)
        self.assertEqual(drive_row.get("owner_doctype"), "Organization")
        self.assertEqual(drive_row.get("owner_name"), self.child_org)

    def test_visible_media_for_school_respects_org_and_school_ancestry(self):
        exact_school_file = self._create_org_media_file(
            organization=self.child_org,
            school=self.leaf_school,
            slot=build_organization_media_slot(media_key="leaf-hero"),
        )
        ancestor_school_file = self._create_org_media_file(
            organization=self.child_org,
            school=self.root_school,
            slot=build_organization_media_slot(media_key="root-hero"),
        )
        current_org_file = self._create_org_media_file(
            organization=self.child_org,
            school=None,
            slot=build_organization_media_slot(media_key="child-shared"),
        )
        ancestor_org_file = self._create_org_media_file(
            organization=self.root_org,
            school=None,
            slot=build_organization_media_slot(media_key="root-shared"),
        )
        hidden_branch_file = self._create_org_media_file(
            organization=self.child_org,
            school=self.branch_school,
            slot=build_organization_media_slot(media_key="branch-hidden"),
        )
        hidden_sibling_org_file = self._create_org_media_file(
            organization=self.sibling_org,
            school=None,
            slot=build_organization_media_slot(media_key="sibling-org-hidden"),
        )

        rows = get_visible_organization_media_for_school(school=self.leaf_school)
        visible_files = [row.get("file") for row in rows]

        self.assertEqual(
            visible_files,
            [
                exact_school_file.name,
                ancestor_school_file.name,
                current_org_file.name,
                ancestor_org_file.name,
            ],
        )
        self.assertNotIn(hidden_branch_file.name, visible_files)
        self.assertNotIn(hidden_sibling_org_file.name, visible_files)

    def test_school_save_syncs_governed_logo_and_gallery_rows(self):
        logo_file = self._create_org_media_file(
            organization=self.child_org,
            school=self.leaf_school,
            slot=build_school_logo_slot(school=self.leaf_school),
            file_name="leaf-logo.png",
        )
        gallery_file = self._create_org_media_file(
            organization=self.child_org,
            school=self.root_school,
            slot=build_school_gallery_slot(row_name="gallery-row-001"),
            file_name="gallery-root.png",
        )

        school_doc = frappe.get_doc("School", self.leaf_school)
        school_doc.school_logo = ""
        school_doc.school_logo_file = logo_file.name
        school_doc.append(
            "gallery_image",
            {
                "governed_file": gallery_file.name,
                "school_image": "",
                "caption": "Ancestor Media",
            },
        )
        school_doc.save(ignore_permissions=True)
        school_doc.reload()

        self.assertEqual(school_doc.school_logo, logo_file.file_url)
        self.assertEqual(school_doc.school_logo_file, logo_file.name)
        self.assertEqual((school_doc.gallery_image or [])[0].school_image, gallery_file.file_url)
        self.assertEqual((school_doc.gallery_image or [])[0].governed_file, gallery_file.name)

    def test_list_visible_media_for_school_serializes_scope_metadata(self):
        exact_school_file = self._create_org_media_file(
            organization=self.child_org,
            school=self.leaf_school,
            slot=build_organization_media_slot(media_key="leaf-card"),
            file_name="leaf-card.png",
        )
        shared_org_file = self._create_org_media_file(
            organization=self.child_org,
            school=None,
            slot=build_organization_media_slot(media_key="shared-card"),
            file_name="shared-card.png",
        )

        payload = list_visible_media_for_school(self.leaf_school, limit=10)

        self.assertEqual(payload["organization"], self.child_org)
        self.assertEqual([item["file"] for item in payload["items"]], [exact_school_file.name, shared_org_file.name])
        self.assertEqual(payload["items"][0]["scope_type"], "school")
        self.assertEqual(payload["items"][0]["school"], self.leaf_school)
        self.assertEqual(payload["items"][1]["scope_type"], "organization")
        self.assertIsNone(payload["items"][1]["school"])

    def test_list_owned_media_for_organization_returns_items_and_school_filters(self):
        school_file = self._create_org_media_file(
            organization=self.child_org,
            school=self.leaf_school,
            slot=build_organization_media_slot(media_key="leaf-banner"),
            file_name="leaf-banner.png",
        )
        org_file = self._create_org_media_file(
            organization=self.child_org,
            school=None,
            slot=build_organization_media_slot(media_key="shared-banner"),
            file_name="shared-banner.png",
        )

        payload = list_owned_media_for_organization(self.child_org, limit=10)

        self.assertEqual(payload["organization"], self.child_org)
        self.assertEqual({item["file"] for item in payload["items"]}, {school_file.name, org_file.name})
        self.assertTrue(any(item["scope_type"] == "school" for item in payload["items"]))
        self.assertTrue(any(item["scope_type"] == "organization" for item in payload["items"]))
        self.assertIn(self.leaf_school, {row["name"] for row in payload["schools"]})

    def test_upload_organization_media_asset_creates_governed_drive_file(self):
        with (
            self._patched_drive_media_bridge(),
            patch(
                "ifitwala_ed.utilities.governed_uploads._get_uploaded_file",
                return_value=("homepage-hero.png", base64.b64decode(self._tiny_png_base64())),
            ),
        ):
            payload = upload_organization_media_asset(
                organization=self.child_org,
                school=self.leaf_school,
                scope="school",
                media_key="homepage-hero",
            )

        self.assertEqual(payload["organization"], self.child_org)
        self.assertEqual(payload["school"], self.leaf_school)
        self.assertEqual(payload["scope"], "school")
        self.assertEqual(payload["slot"], "organization_media__homepage_hero")

        drive_row = frappe.db.get_value(
            "Drive File",
            {"file": payload["file"]},
            ["organization", "school", "purpose", "slot"],
            as_dict=True,
        )
        self.assertEqual(drive_row["organization"], self.child_org)
        self.assertEqual(drive_row["school"], self.leaf_school)
        self.assertEqual(drive_row["purpose"], ORGANIZATION_MEDIA_PURPOSE)
        self.assertEqual(drive_row["slot"], "organization_media__homepage_hero")

    def test_upload_organization_logo_updates_org_with_governed_file(self):
        with (
            self._patched_drive_media_bridge(),
            patch(
                "ifitwala_ed.utilities.governed_uploads._get_uploaded_file",
                return_value=("org-logo.png", base64.b64decode(self._tiny_png_base64())),
            ),
        ):
            payload = upload_organization_logo(organization=self.child_org)

        organization_doc = frappe.get_doc("Organization", self.child_org)
        self.assertEqual(organization_doc.organization_logo_file, payload["file"])
        self.assertEqual(organization_doc.organization_logo, payload["file_url"])

        drive_row = frappe.db.get_value(
            "Drive File",
            {"file": payload["file"]},
            ["organization", "school", "slot"],
            as_dict=True,
        )
        self.assertEqual(drive_row["organization"], self.child_org)
        self.assertFalse(drive_row["school"])
        self.assertEqual(drive_row["slot"], build_organization_logo_slot(organization=self.child_org))

    def test_school_save_rejects_legacy_url_only_media(self):
        logo_file = self._create_org_media_file(
            organization=self.child_org,
            school=self.leaf_school,
            slot=build_school_logo_slot(school=self.leaf_school),
            file_name="existing-logo.png",
        )
        school_doc = frappe.get_doc("School", self.leaf_school)
        school_doc.school_logo = logo_file.file_url
        school_doc.school_logo_file = None

        with self.assertRaisesRegex(frappe.ValidationError, "School Logo must use governed Organization Media"):
            school_doc.save(ignore_permissions=True)

        school_doc.reload()
        gallery_file = self._create_org_media_file(
            organization=self.child_org,
            school=self.leaf_school,
            slot=build_school_gallery_slot(row_name="gallery-row-legacy"),
            file_name="existing-gallery.png",
        )
        school_doc.append(
            "gallery_image",
            {
                "school_image": gallery_file.file_url,
                "caption": "Legacy",
            },
        )

        with self.assertRaisesRegex(
            frappe.ValidationError,
            "Gallery Image rows must use governed Organization Media",
        ):
            school_doc.save(ignore_permissions=True)

    def test_organization_save_rejects_legacy_url_only_logo(self):
        logo_file = self._create_org_media_file(
            organization=self.child_org,
            school=None,
            slot=build_organization_logo_slot(organization=self.child_org),
            file_name="existing-org-logo.png",
        )
        organization_doc = frappe.get_doc("Organization", self.child_org)
        organization_doc.organization_logo = logo_file.file_url
        organization_doc.organization_logo_file = None

        with self.assertRaisesRegex(
            frappe.ValidationError,
            "Organization Logo must use governed Organization Media",
        ):
            organization_doc.save(ignore_permissions=True)

    def _create_org_media_file(
        self,
        *,
        organization: str,
        school: str | None,
        slot: str,
        file_name: str | None = None,
        upload_source: str = "Desk",
    ):
        from ifitwala_drive.services.files.creation import create_drive_file_artifacts

        classification = build_organization_media_classification(
            organization=organization,
            school=school,
            slot=slot,
            upload_source=upload_source,
        )
        content = base64.b64decode(self._tiny_png_base64())
        storage_artifact = {
            "object_key": f"files/organization-media/{frappe.generate_hash(length=12)}",
            "storage_backend": "local",
            "mime_type": "image/png",
            "size_bytes": len(content),
            "content_hash": frappe.generate_hash(length=12),
        }
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Organization",
                "attached_to_name": organization,
                "file_name": file_name or f"{slot}.png",
                "content": content,
                "is_private": 0,
            }
        )
        file_doc.flags.governed_upload = True
        file_doc.flags.drive_compat_projection = True
        file_doc = file_doc.insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        session_doc = frappe.get_doc(
            {
                "doctype": "Drive Upload Session",
                "session_key": f"org-media-{frappe.generate_hash(length=12)}",
                "status": "completed",
                "upload_source": upload_source,
                "created_by_user": "Administrator",
                "attached_doctype": "Organization",
                "attached_name": organization,
                "owner_doctype": "Organization",
                "owner_name": organization,
                "organization": organization,
                "school": school,
                "intended_primary_subject_type": classification["primary_subject_type"],
                "intended_primary_subject_id": classification["primary_subject_id"],
                "intended_data_class": classification["data_class"],
                "intended_purpose": classification["purpose"],
                "intended_retention_policy": classification["retention_policy"],
                "intended_slot": classification["slot"],
                "filename_original": file_doc.file_name,
                "mime_type_hint": storage_artifact["mime_type"],
                "received_size_bytes": storage_artifact["size_bytes"],
                "content_hash": storage_artifact["content_hash"],
                "is_private": int(file_doc.is_private or 0),
                "storage_backend": "local",
                "tmp_object_key": f"tmp/org-media/{frappe.generate_hash(length=12)}",
                "upload_token": frappe.generate_hash(length=16),
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Drive Upload Session", session_doc.name))
        artifacts = create_drive_file_artifacts(
            upload_session_doc=session_doc,
            file_id=file_doc.name,
            storage_artifact=storage_artifact,
            binding_role="organization_media",
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
        return file_doc

    @contextmanager
    def _patched_drive_media_bridge(self):
        fake_drive_media = type(
            "FakeDriveMedia",
            (),
            {
                "upload_organization_media_asset": object(),
                "upload_organization_logo": object(),
                "upload_school_logo": object(),
                "upload_school_gallery_image": object(),
            },
        )()

        def _fake_drive_upload_and_finalize(*, create_session_callable, payload, content):
            if create_session_callable is fake_drive_media.upload_organization_logo:
                slot = build_organization_logo_slot(organization=payload["organization"])
                school = None
            elif create_session_callable is fake_drive_media.upload_school_logo:
                slot = build_school_logo_slot(school=payload["school"])
                school = payload["school"]
            elif create_session_callable is fake_drive_media.upload_school_gallery_image:
                row_name = payload.get("row_name") or frappe.generate_hash(length=10)
                slot = build_school_gallery_slot(row_name=row_name)
                school = payload["school"]
            else:
                slot = build_organization_media_slot(media_key=payload["media_key"])
                school = payload.get("school")

            file_doc = self._create_org_media_file(
                organization=payload["organization"],
                school=school,
                slot=slot,
                file_name=payload["filename_original"],
                upload_source=payload.get("upload_source") or "Desk",
            )

            finalize_response = {
                "file_id": file_doc.name,
                "file_url": file_doc.file_url,
            }
            return {"upload_session_id": "DUS-TEST"}, finalize_response, file_doc

        with (
            patch(
                "ifitwala_drive.api.media.upload_organization_media_asset",
                new=fake_drive_media.upload_organization_media_asset,
            ),
            patch("ifitwala_drive.api.media.upload_organization_logo", new=fake_drive_media.upload_organization_logo),
            patch("ifitwala_drive.api.media.upload_school_logo", new=fake_drive_media.upload_school_logo),
            patch(
                "ifitwala_drive.api.media.upload_school_gallery_image", new=fake_drive_media.upload_school_gallery_image
            ),
            patch(
                "ifitwala_ed.utilities.governed_uploads._drive_upload_and_finalize",
                side_effect=_fake_drive_upload_and_finalize,
            ),
            patch(
                "ifitwala_ed.utilities.governed_uploads._ensure_file_on_disk",
                return_value=None,
            ),
        ):
            yield

    def _create_org(self, organization_name: str, abbr: str, parent: str | None = None, is_group: int = 0) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": organization_name,
                "abbr": abbr,
                "is_group": is_group,
                "parent_organization": parent,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(
        self,
        school_name: str,
        abbr: str,
        organization: str,
        parent: str | None = None,
        is_group: int = 0,
    ) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": school_name,
                "abbr": abbr,
                "organization": organization,
                "parent_school": parent,
                "is_group": is_group,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name

    def _tiny_png_base64(self) -> str:
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+tmxoAAAAASUVORK5CYII="
