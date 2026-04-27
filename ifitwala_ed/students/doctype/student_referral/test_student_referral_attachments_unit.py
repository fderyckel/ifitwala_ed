from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeReferralDoc:
    name = "SRF-2026-0001"
    student = "STU-0001"
    school = "SCH-0001"
    owner = "student@example.com"
    referrer = "student@example.com"
    referral_source = "Student (Self)"
    docstatus = 1

    def is_new(self):
        return False


class TestStudentReferralAttachmentsUnit(TestCase):
    def test_upload_contract_uses_self_referral_context_and_slot(self):
        with stubbed_frappe() as frappe:
            frappe.db.get_value = lambda doctype, name, fieldname=None, **kwargs: (
                "ORG-0001" if doctype == "School" and name == "SCH-0001" and fieldname == "organization" else None
            )
            attachments = import_fresh("ifitwala_ed.students.doctype.student_referral.attachments")

            contract = attachments.build_student_referral_attachment_upload_contract(
                _FakeReferralDoc(),
                slot="student_referral_attachment__abc123",
            )

        self.assertEqual(contract["owner_doctype"], "Student Referral")
        self.assertEqual(contract["owner_name"], "SRF-2026-0001")
        self.assertEqual(contract["attached_doctype"], "Student Referral")
        self.assertEqual(contract["primary_subject_type"], "Student")
        self.assertEqual(contract["primary_subject_id"], "STU-0001")
        self.assertEqual(contract["organization"], "ORG-0001")
        self.assertEqual(contract["school"], "SCH-0001")
        self.assertEqual(contract["purpose"], "safeguarding_evidence")
        self.assertEqual(contract["retention_policy"], "fixed_7y")
        self.assertEqual(contract["slot"], "student_referral_attachment__abc123")

    def test_upload_access_requires_current_student_self_referral(self):
        doc = _FakeReferralDoc()

        with stubbed_frappe() as frappe:
            frappe.session.user = "other@example.com"
            frappe.get_roles = lambda user: ["Student"]
            frappe.db.exists = lambda doctype, name=None, **kwargs: doctype == "Student Referral"
            frappe.get_doc = lambda doctype, name: doc

            def fake_get_value(doctype, filters, fieldname=None, **kwargs):
                if doctype == "Student" and filters == {"student_email": "other@example.com"}:
                    return "STU-0002"
                return None

            frappe.db.get_value = fake_get_value
            attachments = import_fresh("ifitwala_ed.students.doctype.student_referral.attachments")

            with self.assertRaises(frappe.PermissionError):
                attachments.assert_self_referral_attachment_upload_access("SRF-2026-0001")

    def test_finalize_context_rejects_stale_session_subject(self):
        doc = _FakeReferralDoc()
        upload_session = SimpleNamespace(
            owner_doctype="Student Referral",
            owner_name="SRF-2026-0001",
            attached_doctype="Student Referral",
            attached_name="SRF-2026-0001",
            organization="ORG-0001",
            school="SCH-0001",
            intended_primary_subject_type="Student",
            intended_primary_subject_id="STU-OTHER",
            intended_data_class="safeguarding",
            intended_purpose="safeguarding_evidence",
            intended_retention_policy="fixed_7y",
            intended_slot="student_referral_attachment__abc123",
        )

        with stubbed_frappe() as frappe:
            frappe.session.user = "student@example.com"
            frappe.get_roles = lambda user: ["Student"]
            frappe.db.exists = lambda doctype, name=None, **kwargs: doctype in {"Student Referral"}

            def fake_get_value(doctype, filters, fieldname=None, **kwargs):
                if doctype == "Student" and filters == {"student_email": "student@example.com"}:
                    return "STU-0001"
                if doctype == "School" and filters == "SCH-0001" and fieldname == "organization":
                    return "ORG-0001"
                return None

            frappe.db.get_value = fake_get_value
            frappe.get_doc = lambda doctype, name: doc
            attachments = import_fresh("ifitwala_ed.students.doctype.student_referral.attachments")

            with self.assertRaises(frappe.ValidationError):
                attachments.validate_student_referral_attachment_finalize_context(upload_session)

    def test_workflow_registry_exposes_student_referral_alias(self):
        with stubbed_frappe():
            workflow_specs = import_fresh("ifitwala_ed.integrations.drive.workflow_specs")
            spec = workflow_specs.get_upload_spec("student_referral_attachment")

        self.assertEqual(spec.workflow_id, "student_referral.attachment")
        self.assertTrue(spec.is_private)
