# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestFileClassification(FrappeTestCase):
    def test_form_marks_system_managed_fields_read_only(self):
        meta = frappe.get_meta("File Classification")

        read_only_fields = (
            "file",
            "attached_doctype",
            "attached_name",
            "primary_subject_type",
            "primary_subject_id",
            "data_class",
            "purpose",
            "retention_policy",
            "retention_until",
            "slot",
            "organization",
            "school",
            "version_number",
            "is_current_version",
            "content_hash",
            "source_file",
            "upload_source",
            "ip_address",
        )

        editable_fields = (
            "legal_hold",
            "erasure_state",
            "secondary_subjects",
        )

        for fieldname in read_only_fields:
            with self.subTest(fieldname=fieldname):
                self.assertEqual(meta.get_field(fieldname).read_only, 1)

        for fieldname in editable_fields:
            with self.subTest(fieldname=fieldname):
                self.assertEqual(meta.get_field(fieldname).read_only, 0)
