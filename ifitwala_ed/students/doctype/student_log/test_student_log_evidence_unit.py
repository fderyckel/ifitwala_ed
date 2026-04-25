from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeStudentLogDoc:
    def __init__(self):
        self.name = "SLOG-0001"
        self.student = "STU-0001"
        self.school = "SCH-0001"
        self.owner = "teacher@example.com"
        self.follow_up_person = None
        self.follow_up_status = "Open"
        self.visible_to_student = 1
        self.visible_to_guardians = 0
        self.docstatus = 1
        self.evidence_attachments = [
            SimpleNamespace(
                name="row-visible",
                title="Visible photo",
                description="Shared with student",
                external_url="https://example.test/evidence",
                file=None,
                file_name=None,
                file_size=None,
                visible_to_student=1,
                visible_to_guardians=0,
                is_removed=0,
            ),
            SimpleNamespace(
                name="row-staff-only",
                title="Staff-only note",
                description=None,
                external_url="https://example.test/private-evidence",
                file=None,
                file_name=None,
                file_size=None,
                visible_to_student=0,
                visible_to_guardians=0,
                is_removed=0,
            ),
        ]

    def is_new(self):
        return False

    def get(self, fieldname):
        return getattr(self, fieldname, None)


class TestStudentLogEvidenceUnit(TestCase):
    def test_upload_contract_uses_student_log_context_and_row_slot(self):
        with stubbed_frappe() as frappe:
            sys.modules["frappe.utils"].cint = lambda value=0: int(value or 0)
            frappe.db.get_value = lambda doctype, name, fieldname=None, **kwargs: (
                "ORG-0001" if doctype == "School" and name == "SCH-0001" and fieldname == "organization" else None
            )
            evidence = import_fresh("ifitwala_ed.students.doctype.student_log.evidence")

            contract = evidence.build_student_log_evidence_upload_contract(
                _FakeStudentLogDoc(),
                row_name="row-001",
            )

        self.assertEqual(contract["owner_doctype"], "Student Log")
        self.assertEqual(contract["owner_name"], "SLOG-0001")
        self.assertEqual(contract["attached_doctype"], "Student Log")
        self.assertEqual(contract["primary_subject_type"], "Student")
        self.assertEqual(contract["primary_subject_id"], "STU-0001")
        self.assertEqual(contract["organization"], "ORG-0001")
        self.assertEqual(contract["school"], "SCH-0001")
        self.assertEqual(contract["purpose"], "student_log_evidence")
        self.assertEqual(contract["slot"], "student_log_evidence__row-001")

    def test_student_portal_visibility_requires_parent_and_row_flags(self):
        doc = _FakeStudentLogDoc()

        with stubbed_frappe() as frappe:
            sys.modules["frappe.utils"].cint = lambda value=0: int(value or 0)
            frappe.session.user = "student@example.com"
            frappe.db.exists = lambda doctype, name=None, **kwargs: doctype == "Student Log" and name == "SLOG-0001"

            def fake_get_value(doctype, filters, fieldname=None, **kwargs):
                if doctype == "User" and filters == "student@example.com" and fieldname == "email":
                    return "student@example.com"
                if doctype == "Student" and filters == {"student_email": "student@example.com"}:
                    return "STU-0001"
                return None

            frappe.db.get_value = fake_get_value
            frappe.get_doc = lambda doctype, name=None: doc
            frappe.has_permission = lambda *args, **kwargs: False
            evidence = import_fresh("ifitwala_ed.students.doctype.student_log.evidence")

            rows = evidence.get_visible_student_log_evidence_attachments("SLOG-0001", audience="student")

        self.assertEqual([row["row_name"] for row in rows], ["row-visible"])
        self.assertEqual(rows[0]["attachment_preview"]["link_url"], "https://example.test/evidence")

    def test_workflow_registry_exposes_student_log_alias(self):
        with stubbed_frappe():
            workflow_specs = import_fresh("ifitwala_ed.integrations.drive.workflow_specs")
            spec = workflow_specs.get_upload_spec("student_log_evidence_attachment")

        self.assertEqual(spec.workflow_id, "student_log.evidence_attachment")
        self.assertTrue(spec.is_private)
