from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeDoc:
    _counter = 0

    def __init__(self, payload, store):
        self._store = store
        for key, value in payload.items():
            setattr(self, key, value)

    def insert(self, ignore_permissions=False):
        del ignore_permissions
        if not getattr(self, "name", None):
            _FakeDoc._counter += 1
            prefix = {
                "Drive Upload Session": "DUS",
                "Drive File": "DF",
            }.get(getattr(self, "doctype", ""), "DOC")
            self.name = f"{prefix}-{_FakeDoc._counter:04d}"
        self._store[(self.doctype, self.name)] = self
        return self

    def save(self, ignore_permissions=False):
        del ignore_permissions
        self._store[(self.doctype, self.name)] = self
        return self


@contextmanager
def _patch_module():
    docs: dict[tuple[str, str], _FakeDoc] = {}
    _FakeDoc._counter = 0

    with stubbed_frappe() as frappe:

        def get_doc(arg1, arg2=None):
            if isinstance(arg1, dict):
                return _FakeDoc(arg1, docs)
            return docs[(arg1, arg2)]

        frappe.get_doc = get_doc
        frappe.db = SimpleNamespace()
        frappe.db.table_exists = lambda doctype: True
        frappe.db.exists = lambda doctype, value=None: doctype == "User" and str(value or "").strip() == "Administrator"
        frappe.db.get_value = lambda doctype, filters=None, fieldname=None, as_dict=False: None
        frappe.session = SimpleNamespace(user="Administrator")
        frappe.get_traceback = lambda: "traceback"
        yield import_fresh("ifitwala_ed.patches.backfill_drive_authority_for_classified_files"), frappe, docs


class TestBackfillDriveAuthorityForClassifiedFiles(TestCase):
    def test_execute_backfills_missing_drive_authority_for_current_row(self):
        with _patch_module() as (module, frappe, docs):
            classification_row = {
                "name": "FC-0001",
                "file": "FILE-0001",
                "attached_doctype": "Student",
                "attached_name": "STU-0001",
                "primary_subject_type": "Student",
                "primary_subject_id": "STU-0001",
                "data_class": "identity_image",
                "purpose": "student_profile_display",
                "retention_policy": "until_school_exit_plus_6m",
                "slot": "profile_image",
                "organization": "ORG-0001",
                "school": "SCH-0001",
                "is_current_version": 1,
                "legal_hold": 0,
                "erasure_state": "active",
                "upload_source": "Desk",
                "owner": "Administrator",
            }
            file_row = {
                "name": "FILE-0001",
                "file_url": "/private/files/student.png",
                "file_name": "student.png",
                "file_size": 123,
                "is_private": 1,
                "attached_to_doctype": "Student",
                "attached_to_name": "STU-0001",
                "owner": "Administrator",
            }

            module._load_classification_rows = lambda: [classification_row]
            module._load_file_rows = lambda file_names: {"FILE-0001": file_row}
            module._load_existing_drive_files = lambda file_names: set()
            module._read_file_bytes = lambda row: b"student-image"
            module._resolve_content_hash = lambda row, content: "sha256:abc123"

            written = {}

            class FakeStorage:
                backend_name = "local"

                def write_final_object(self, *, object_key, content, mime_type=None):
                    written["artifact"] = {
                        "object_key": object_key,
                        "content": content,
                        "mime_type": mime_type,
                    }
                    return {
                        "object_key": object_key,
                        "storage_backend": "local",
                        "file_url": f"/private/files/ifitwala_drive/{object_key}",
                    }

            def fake_create_drive_file_artifacts(*, upload_session_doc, file_id, storage_artifact, binding_role=None):
                del binding_role
                drive_file = _FakeDoc(
                    {
                        "doctype": "Drive File",
                        "name": "DF-0001",
                        "storage_backend": storage_artifact["storage_backend"],
                        "storage_object_key": storage_artifact["object_key"],
                        "content_hash": storage_artifact["content_hash"],
                    },
                    docs,
                )
                docs[("Drive File", "DF-0001")] = drive_file
                return {
                    "drive_file_id": "DF-0001",
                    "drive_file_version_id": "DFV-0001",
                    "canonical_ref": "drv:ORG-0001:DF-0001",
                }

            module._load_drive_dependencies = lambda: (
                fake_create_drive_file_artifacts,
                lambda: FakeStorage(),
                lambda **kwargs: "files/aa/bb/backfilled.png",
            )

            module.execute()

            drive_file = docs[("Drive File", "DF-0001")]
            upload_session = docs[("Drive Upload Session", "DUS-0001")]

            self.assertEqual(written["artifact"]["object_key"], "files/aa/bb/backfilled.png")
            self.assertEqual(written["artifact"]["content"], b"student-image")
            self.assertEqual(drive_file.status, "active")
            self.assertEqual(drive_file.erasure_state, "active")
            self.assertEqual(drive_file.legal_hold, 0)
            self.assertEqual(upload_session.status, "completed")
            self.assertEqual(upload_session.drive_file, "DF-0001")
            self.assertEqual(upload_session.drive_file_version, "DFV-0001")
            self.assertEqual(upload_session.canonical_ref, "drv:ORG-0001:DF-0001")

    def test_execute_marks_non_current_legacy_rows_superseded(self):
        with _patch_module() as (module, frappe, docs):
            classification_row = {
                "name": "FC-0002",
                "file": "FILE-0002",
                "attached_doctype": "Task Submission",
                "attached_name": "TSUB-0001",
                "primary_subject_type": "Student",
                "primary_subject_id": "STU-0001",
                "data_class": "assessment",
                "purpose": "assessment_submission",
                "retention_policy": "until_school_exit_plus_6m",
                "slot": "submission",
                "organization": "ORG-0001",
                "school": "SCH-0001",
                "is_current_version": 0,
                "legal_hold": 0,
                "erasure_state": "active",
                "upload_source": "SPA",
                "owner": "Administrator",
            }
            file_row = {
                "name": "FILE-0002",
                "file_url": "/private/files/submission.docx",
                "file_name": "submission.docx",
                "file_size": 456,
                "is_private": 1,
                "attached_to_doctype": "Task Submission",
                "attached_to_name": "TSUB-0001",
                "owner": "Administrator",
            }

            module._load_classification_rows = lambda: [classification_row]
            module._load_file_rows = lambda file_names: {"FILE-0002": file_row}
            module._load_existing_drive_files = lambda file_names: set()
            module._read_file_bytes = lambda row: b"submission"

            class FakeStorage:
                backend_name = "local"

                def write_final_object(self, *, object_key, content, mime_type=None):
                    del content, mime_type
                    return {
                        "object_key": object_key,
                        "storage_backend": "local",
                        "file_url": f"/private/files/ifitwala_drive/{object_key}",
                    }

            def fake_create_drive_file_artifacts(*, upload_session_doc, file_id, storage_artifact, binding_role=None):
                del upload_session_doc, file_id, binding_role
                docs[("Drive File", "DF-0002")] = _FakeDoc(
                    {
                        "doctype": "Drive File",
                        "name": "DF-0002",
                        "storage_backend": storage_artifact["storage_backend"],
                        "storage_object_key": storage_artifact["object_key"],
                    },
                    docs,
                )
                return {
                    "drive_file_id": "DF-0002",
                    "drive_file_version_id": "DFV-0002",
                    "canonical_ref": "drv:ORG-0001:DF-0002",
                }

            module._load_drive_dependencies = lambda: (
                fake_create_drive_file_artifacts,
                lambda: FakeStorage(),
                lambda **kwargs: "files/cc/dd/backfilled.docx",
            )

            module.execute()

            drive_file = docs[("Drive File", "DF-0002")]
            self.assertEqual(drive_file.status, "superseded")
