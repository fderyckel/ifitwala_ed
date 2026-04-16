from __future__ import annotations

from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeOrgCommunicationDoc:
    def __init__(self, *, name: str, organization: str, school: str, audiences: list[object]):
        self.name = name
        self.organization = organization
        self.school = school
        self.audiences = audiences
        self.activity_student_group = None
        self.attachments = [
            SimpleNamespace(
                name="row-001",
                file="/private/files/announcement.pdf",
                external_url=None,
                section_break_sbex="Announcement PDF",
                description=None,
                file_name="announcement.pdf",
                file_size=1024,
            )
        ]

    def check_permission(self, _permission_type=None):
        return None

    def get(self, fieldname):
        return getattr(self, fieldname, None)

    def reload(self):
        return self


class TestOrgCommunicationAttachmentsUnit(TestCase):
    def test_finalize_context_allows_generated_row_without_existing_attachment_row(self):
        with stubbed_frappe() as frappe:
            org_doc = _FakeOrgCommunicationDoc(
                name="COMM-0001",
                organization="ORG-1",
                school="SCH-1",
                audiences=[SimpleNamespace(target_mode="Student Group", student_group="SG-1")],
            )
            org_doc.attachments = []
            frappe.generate_hash = lambda length=10: "x" * length
            frappe.db.exists = lambda doctype, name=None: doctype == "Org Communication" and name == "COMM-0001"

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Student Group" and name == "SG-1" and fieldname == ["course", "school"] and as_dict:
                    return {"course": "COURSE-1", "school": "SCH-1"}
                return None

            frappe.db.get_value = fake_get_value
            frappe.get_doc = lambda doctype, name=None: org_doc

            attachments = import_fresh("ifitwala_ed.setup.doctype.org_communication.attachments")
            upload_session_doc = SimpleNamespace(
                owner_doctype="Org Communication",
                owner_name="COMM-0001",
                attached_doctype="Org Communication",
                attached_name="COMM-0001",
                organization="ORG-1",
                school="SCH-1",
                intended_primary_subject_type="Organization",
                intended_primary_subject_id="ORG-1",
                intended_data_class="administrative",
                intended_purpose="administrative",
                intended_retention_policy="fixed_7y",
                intended_slot="communication_attachment__row-001",
            )

            authoritative = attachments.validate_org_communication_attachment_finalize_context(upload_session_doc)

        self.assertEqual(authoritative["slot"], "communication_attachment__row-001")
        self.assertEqual(authoritative["student_group"], "SG-1")
        self.assertEqual(authoritative["course"], "COURSE-1")

    def test_context_override_uses_school_scope_path_for_single_school_audience(self):
        with stubbed_frappe() as frappe:
            org_doc = _FakeOrgCommunicationDoc(
                name="COMM-0002",
                organization="ORG-1",
                school="",
                audiences=[SimpleNamespace(target_mode="School Scope", school="SCH-2")],
            )
            frappe.db.exists = lambda doctype, name=None: doctype == "Org Communication" and name == "COMM-0002"

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "School" and name == "SCH-2" and fieldname == "organization":
                    return "ORG-1"
                return None

            frappe.db.get_value = fake_get_value
            frappe.get_doc = lambda doctype, name=None: org_doc

            attachments = import_fresh("ifitwala_ed.setup.doctype.org_communication.attachments")
            override = attachments.get_org_communication_context_override(
                "COMM-0002", "communication_attachment__row-1"
            )

        self.assertEqual(override["root_folder"], "Home/Organizations")
        self.assertEqual(override["subfolder"], "ORG-1/Schools/SCH-2/Communications/COMM-0002/Attachments")
        self.assertEqual(override["file_category"], "School Communication Attachment")

    def test_context_override_uses_organization_scope_path_without_school_context(self):
        with stubbed_frappe() as frappe:
            org_doc = _FakeOrgCommunicationDoc(
                name="COMM-0003",
                organization="ORG-ROOT",
                school="",
                audiences=[SimpleNamespace(target_mode="Organization")],
            )
            frappe.db.exists = lambda doctype, name=None: doctype == "Org Communication" and name == "COMM-0003"
            frappe.db.get_value = lambda *args, **kwargs: None
            frappe.get_doc = lambda doctype, name=None: org_doc

            attachments = import_fresh("ifitwala_ed.setup.doctype.org_communication.attachments")
            override = attachments.get_org_communication_context_override(
                "COMM-0003", "communication_attachment__row-1"
            )

        self.assertEqual(override["root_folder"], "Home/Organizations")
        self.assertEqual(override["subfolder"], "ORG-ROOT/Communications/COMM-0003/Attachments")
        self.assertEqual(override["file_category"], "Organization Communication Attachment")

    def test_upload_endpoint_unpacks_drive_tuple_and_uses_session_row_name(self):
        file_access = ModuleType("ifitwala_ed.api.file_access")
        file_access.build_org_communication_attachment_open_url = lambda *, org_communication, row_name: (
            f"/open/{org_communication}/{row_name}"
        )
        file_access.build_org_communication_attachment_preview_url = lambda *, org_communication, row_name: (
            f"/preview/{org_communication}/{row_name}"
        )

        attachments_bridge = ModuleType("ifitwala_ed.setup.doctype.org_communication.attachments")
        attachments_bridge.ORG_COMMUNICATION_ATTACHMENT_BINDING_ROLE = "communication_attachment"
        attachments_bridge.ORG_COMMUNICATION_ATTACHMENT_SLOT_PREFIX = "communication_attachment__"

        org_doc = _FakeOrgCommunicationDoc(
            name="COMM-0001",
            organization="ORG-1",
            school="SCH-1",
            audiences=[SimpleNamespace(target_mode="Student Group", student_group="SG-1")],
        )
        attachments_bridge.assert_org_communication_attachment_upload_access = (
            lambda org_communication, permission_type="write": org_doc
        )

        governed_uploads = ModuleType("ifitwala_ed.utilities.governed_uploads")
        governed_uploads._get_uploaded_file = lambda: ("announcement.pdf", b"file-bytes")
        governed_uploads._resolve_upload_mime_type_hint = lambda filename=None: "application/pdf"
        governed_uploads._drive_upload_and_finalize = lambda **kwargs: (
            {"upload_session_id": "DUS-0001", "row_name": "row-001"},
            {"file_id": "FILE-0001"},
            SimpleNamespace(name="FILE-0001"),
        )

        drive_root = ModuleType("ifitwala_drive")
        drive_api_pkg = ModuleType("ifitwala_drive.api")
        drive_api = ModuleType("ifitwala_drive.api.communications")
        drive_api.upload_org_communication_attachment = lambda **kwargs: {
            "upload_session_id": "DUS-0001",
            "row_name": "row-001",
        }

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.api.file_access": file_access,
                "ifitwala_ed.setup.doctype.org_communication.attachments": attachments_bridge,
                "ifitwala_ed.utilities.governed_uploads": governed_uploads,
                "ifitwala_drive": drive_root,
                "ifitwala_drive.api": drive_api_pkg,
                "ifitwala_drive.api.communications": drive_api,
            }
        ) as frappe:
            frappe.db.get_value = lambda *args, **kwargs: None
            module = import_fresh("ifitwala_ed.api.org_communication_attachments")
            response = module.upload_org_communication_attachment(org_communication="COMM-0001")

        self.assertEqual(response["org_communication"], "COMM-0001")
        self.assertEqual(response["attachment"]["row_name"], "row-001")
        self.assertEqual(response["attachment"]["file_name"], "announcement.pdf")
        self.assertEqual(response["attachment"]["open_url"], "/open/COMM-0001/row-001")

    def test_serialize_attachment_row_includes_preview_status_for_governed_file(self):
        file_access = ModuleType("ifitwala_ed.api.file_access")
        file_access.build_org_communication_attachment_open_url = lambda *, org_communication, row_name: (
            f"/open/{org_communication}/{row_name}"
        )
        file_access.build_org_communication_attachment_preview_url = lambda *, org_communication, row_name: (
            f"/preview/{org_communication}/{row_name}"
        )

        attachments_bridge = ModuleType("ifitwala_ed.setup.doctype.org_communication.attachments")
        attachments_bridge.ORG_COMMUNICATION_ATTACHMENT_BINDING_ROLE = "communication_attachment"
        attachments_bridge.ORG_COMMUNICATION_ATTACHMENT_SLOT_PREFIX = "communication_attachment__"
        attachments_bridge.assert_org_communication_attachment_upload_access = lambda *_args, **_kwargs: None

        governed_uploads = ModuleType("ifitwala_ed.utilities.governed_uploads")
        governed_uploads._get_uploaded_file = lambda: ("announcement.pdf", b"file-bytes")
        governed_uploads._resolve_upload_mime_type_hint = lambda filename=None: "application/pdf"
        governed_uploads._drive_upload_and_finalize = lambda **kwargs: ({}, {}, SimpleNamespace(name="FILE-1"))

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.api.file_access": file_access,
                "ifitwala_ed.setup.doctype.org_communication.attachments": attachments_bridge,
                "ifitwala_ed.utilities.governed_uploads": governed_uploads,
            }
        ) as frappe:

            def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
                if doctype == "Drive Binding":
                    return "DF-0001"
                if doctype == "Drive File" and filters == "DF-0001" and fieldname == "preview_status":
                    return "ready"
                return None

            frappe.db.get_value = fake_get_value
            module = import_fresh("ifitwala_ed.api.org_communication_attachments")
            payload = module.serialize_org_communication_attachment_row(
                "COMM-0001",
                SimpleNamespace(
                    name="row-001",
                    file="/private/files/announcement.pdf",
                    external_url=None,
                    section_break_sbex="Announcement PDF",
                    description=None,
                    file_name="announcement.pdf",
                    file_size=1024,
                ),
            )

        self.assertEqual(payload["preview_status"], "ready")
        self.assertEqual(payload["preview_url"], "/preview/COMM-0001/row-001")
