from __future__ import annotations

import ast
import json
from datetime import datetime
from pathlib import Path
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeDoc:
    def __init__(self, **values):
        self.__dict__.update(values)
        self.name = values.get("name") or "CER-1"
        self.flags = values.get("flags") or {}
        self.inserted = False
        self.saved = False

    def get(self, fieldname, default=None):
        return getattr(self, fieldname, default)

    def insert(self, ignore_permissions=True):
        self.inserted = True
        return self

    def save(self, ignore_permissions=True):
        self.saved = True
        return self


def _import_export_module():
    contact_audit = import_fresh("ifitwala_ed.contacts.contact_audit")
    contact_export = import_fresh("ifitwala_ed.contacts.contact_export")
    return contact_export, contact_audit


def _install_get_doc(frappe, request_doc=None, created_requests=None, logs=None):
    created_requests = created_requests if created_requests is not None else []
    logs = logs if logs is not None else []

    def get_doc(*args, **kwargs):
        if args and isinstance(args[0], dict):
            payload = dict(args[0])
            if payload.get("doctype") == "Contact Access Log":
                doc = _FakeDoc(**payload, name=f"CAL-{len(logs) + 1}")
                logs.append(payload)
                return doc
            if payload.get("doctype") == "Contact Export Request":
                doc = _FakeDoc(**payload, name=f"CER-{len(created_requests) + 1}")
                created_requests.append(doc)
                return doc
        if len(args) == 2 and args[0] == "Contact Export Request" and request_doc is not None:
            return request_doc
        raise AssertionError(f"Unexpected get_doc call: {args!r} {kwargs!r}")

    frappe.get_doc = get_doc
    return created_requests, logs


def _request_doc(**overrides):
    values = {
        "name": "CER-1",
        "requester": "unit.test@example.com",
        "organization": "ORG-1",
        "school": None,
        "scope_type": "Admissions Applicants",
        "scope_name": None,
        "purpose": "admissions_followup_export",
        "legal_basis": "consent",
        "fields_requested": '["display_name","primary_email"]',
        "estimated_row_count": 12,
        "status": "Submitted",
        "approved_by": None,
        "approved_on": None,
        "expires_on": None,
        "rejection_reason": None,
    }
    values.update(overrides)
    return _FakeDoc(**values)


class TestContactExportRequestController(TestCase):
    def test_manual_insert_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh("ifitwala_ed.governance.doctype.contact_export_request.contact_export_request")
            doc = module.ContactExportRequest.__new__(module.ContactExportRequest)
            doc.flags = {}

            with self.assertRaises(frappe.PermissionError):
                doc.before_insert()

    def test_global_scope_is_rejected_by_controller(self):
        with stubbed_frappe() as frappe:
            module = import_fresh("ifitwala_ed.governance.doctype.contact_export_request.contact_export_request")
            doc = module.ContactExportRequest.__new__(module.ContactExportRequest)
            doc.flags = {"from_contact_export_service": True}
            doc.requester = "unit.test@example.com"
            doc.purpose = "bulk_export"
            doc.legal_basis = "consent"
            doc.scope_type = "All Contacts"
            doc.scope_name = None
            doc.organization = "ORG-1"
            doc.school = None
            doc.status = "Draft"

            with self.assertRaises(frappe.ValidationError):
                doc.validate()


class TestContactExportService(TestCase):
    def test_create_request_rejects_global_scope(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()

            with self.assertRaises(frappe.ValidationError):
                contact_export.create_contact_export_request(
                    {
                        "scope_type": "All Contacts",
                        "purpose": "unsafe bulk export",
                        "legal_basis": "consent",
                        "organization": "ORG-1",
                    }
                )

    def test_create_request_rejects_missing_purpose_and_legal_basis(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()

            with self.assertRaises(frappe.ValidationError):
                contact_export.create_contact_export_request(
                    {
                        "scope_type": "Admissions Applicants",
                        "organization": "ORG-1",
                    }
                )

            with self.assertRaises(frappe.ValidationError):
                contact_export.create_contact_export_request(
                    {
                        "scope_type": "Admissions Applicants",
                        "purpose": "admissions_followup_export",
                        "organization": "ORG-1",
                    }
                )

    def test_create_request_rejects_raw_values_in_fields_requested(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()

            with self.assertRaises(frappe.ValidationError):
                contact_export.create_contact_export_request(
                    {
                        "scope_type": "Admissions Applicants",
                        "purpose": "admissions_followup_export",
                        "legal_basis": "consent",
                        "organization": "ORG-1",
                        "fields_requested": ["display_name", "guardian@example.com"],
                    }
                )

    def test_create_request_stores_only_metadata(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            created_requests, _logs = _install_get_doc(frappe)

            name = contact_export.create_contact_export_request(
                {
                    "scope_type": "Admissions Applicants",
                    "purpose": "admissions_followup_export",
                    "legal_basis": "consent",
                    "organization": "ORG-1",
                    "fields_requested": ["display_name", "primary_email"],
                }
            )

        self.assertEqual(name, "CER-1")
        self.assertEqual(created_requests[0].status, "Draft")
        self.assertEqual(created_requests[0].requester, "unit.test@example.com")
        self.assertIn("primary_email", created_requests[0].fields_requested)
        self.assertNotIn("guardian@example.com", str(created_requests[0].__dict__))

    def test_estimate_sets_row_count_and_submits_request(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc(status="Draft", estimated_row_count=None)
            _created_requests, _logs = _install_get_doc(frappe, request_doc=request_doc)
            frappe.db.get_value = lambda doctype, name, fields, as_dict=False: {"lft": 1, "rgt": 2}
            frappe.get_all = lambda doctype, **kwargs: ["ORG-1"]
            frappe.db.count = lambda doctype, filters=None: 12

            count = contact_export.estimate_contact_export_rows("CER-1")

        self.assertEqual(count, 12)
        self.assertEqual(request_doc.estimated_row_count, 12)
        self.assertEqual(request_doc.status, "Submitted")
        self.assertTrue(request_doc.saved)

    def test_estimate_expands_parent_organization_and_school_scope(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc(organization="ORG-PARENT", school="SCHOOL-PARENT")
            _created_requests, _logs = _install_get_doc(frappe, request_doc=request_doc)
            captured_filters = []

            def get_value(doctype, name, fields, as_dict=False):
                if doctype == "Organization":
                    return {"lft": 1, "rgt": 6}
                if doctype == "School":
                    return {"lft": 10, "rgt": 14}
                return None

            def get_all(doctype, **kwargs):
                if doctype == "Organization":
                    return ["ORG-PARENT", "ORG-CHILD"]
                if doctype == "School":
                    return ["SCHOOL-PARENT", "SCHOOL-CHILD"]
                return []

            def count(doctype, filters=None):
                captured_filters.append(filters)
                return 22

            frappe.db.get_value = get_value
            frappe.get_all = get_all
            frappe.db.count = count

            row_count = contact_export.estimate_contact_export_rows("CER-1")

        self.assertEqual(row_count, 22)
        self.assertEqual(captured_filters[0]["organization"], ["in", ["ORG-PARENT", "ORG-CHILD"]])
        self.assertEqual(captured_filters[0]["school"], ["in", ["SCHOOL-PARENT", "SCHOOL-CHILD"]])

    def test_ordinary_user_cannot_approve_request(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc()
            _created_requests, logs = _install_get_doc(frappe, request_doc=request_doc)
            frappe.get_roles = lambda user=None: ["Admission Officer"]

            with self.assertRaises(frappe.PermissionError):
                contact_export.approve_contact_export_request("CER-1")

        self.assertEqual(logs[0]["access_type"], "export")
        self.assertEqual(logs[0]["result"], "denied")
        self.assertEqual(logs[0]["subject_name"], "CER-1")

    def test_system_manager_cannot_approve_without_privacy_role(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc()
            _created_requests, logs = _install_get_doc(frappe, request_doc=request_doc)
            frappe.get_roles = lambda user=None: ["System Manager"]

            with self.assertRaises(frappe.PermissionError):
                contact_export.approve_contact_export_request("CER-1")

        self.assertEqual(logs[0]["details"], '{"reason":"missing_privacy_approver_role"}')
        self.assertEqual(request_doc.status, "Submitted")

    def test_dpo_can_approve_scoped_request(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc()
            _created_requests, logs = _install_get_doc(frappe, request_doc=request_doc)
            frappe.get_roles = lambda user=None: ["Data Protection Officer"]
            contact_export.now_datetime = lambda: datetime(2026, 5, 19, 8, 0, 0)

            contact_export.approve_contact_export_request("CER-1")

        self.assertEqual(request_doc.status, "Approved")
        self.assertEqual(request_doc.approved_by, "unit.test@example.com")
        self.assertEqual(request_doc.expires_on, datetime(2026, 5, 20, 8, 0, 0))
        self.assertTrue(request_doc.saved)
        self.assertEqual(logs[0]["access_type"], "export")
        self.assertEqual(logs[0]["result"], "allowed")
        self.assertNotIn("guardian@example.com", str(logs[0]))

    def test_dpo_cannot_approve_without_estimated_row_count(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc(estimated_row_count=None)
            _created_requests, _logs = _install_get_doc(frappe, request_doc=request_doc)
            frappe.get_roles = lambda user=None: ["Data Protection Officer"]

            with self.assertRaises(frappe.ValidationError):
                contact_export.approve_contact_export_request("CER-1")

        self.assertEqual(request_doc.status, "Submitted")

    def test_reject_request_writes_denied_export_log(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc()
            _created_requests, logs = _install_get_doc(frappe, request_doc=request_doc)
            frappe.get_roles = lambda user=None: ["Data Protection Officer"]
            contact_export.now_datetime = lambda: datetime(2026, 5, 19, 8, 0, 0)

            contact_export.reject_contact_export_request("CER-1", "Scope is too broad for this purpose.")

        self.assertEqual(request_doc.status, "Rejected")
        self.assertEqual(request_doc.rejection_reason, "Scope is too broad for this purpose.")
        self.assertEqual(logs[0]["access_type"], "export")
        self.assertEqual(logs[0]["result"], "denied")

    def test_rejected_request_is_denied_by_export_assertion(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc(status="Rejected", rejection_reason="No")
            _created_requests, logs = _install_get_doc(frappe, request_doc=request_doc)

            with self.assertRaises(frappe.PermissionError):
                contact_export.assert_approved_contact_export(
                    "CER-1",
                    purpose="admissions_followup_export",
                    scope_type="Admissions Applicants",
                )

        self.assertEqual(logs[0]["access_type"], "export")
        self.assertEqual(logs[0]["result"], "denied")
        self.assertIn("not_approved", logs[0]["details"])

    def test_expired_approved_request_is_denied(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc(
                status="Approved",
                approved_by="dpo@example.com",
                approved_on=datetime(2026, 5, 18, 8, 0, 0),
                expires_on=datetime(2026, 5, 18, 9, 0, 0),
            )
            _created_requests, logs = _install_get_doc(frappe, request_doc=request_doc)
            contact_export.now_datetime = lambda: datetime(2026, 5, 19, 8, 0, 0)
            contact_export.get_datetime = lambda value: value

            with self.assertRaises(frappe.PermissionError):
                contact_export.assert_approved_contact_export(
                    "CER-1",
                    purpose="admissions_followup_export",
                    scope_type="Admissions Applicants",
                )

        self.assertEqual(request_doc.status, "Expired")
        self.assertTrue(request_doc.saved)
        self.assertEqual(logs[0]["result"], "denied")
        self.assertIn("expired", logs[0]["details"])

    def test_approved_unexpired_request_passes_export_assertion(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc(
                status="Approved",
                approved_by="dpo@example.com",
                approved_on=datetime(2026, 5, 19, 8, 0, 0),
                expires_on=datetime(2026, 5, 20, 8, 0, 0),
            )
            _created_requests, logs = _install_get_doc(frappe, request_doc=request_doc)
            contact_export.now_datetime = lambda: datetime(2026, 5, 19, 9, 0, 0)
            contact_export.get_datetime = lambda value: value

            contact_export.assert_approved_contact_export(
                "CER-1",
                purpose="admissions_followup_export",
                scope_type="Admissions Applicants",
            )

        self.assertEqual(logs[0]["access_type"], "export")
        self.assertEqual(logs[0]["result"], "allowed")
        self.assertIn("Admissions Applicants", logs[0]["details"])

    def test_approved_request_for_another_requester_is_denied(self):
        with stubbed_frappe() as frappe:
            contact_export, _contact_audit = _import_export_module()
            request_doc = _request_doc(
                requester="other.user@example.com",
                status="Approved",
                approved_by="dpo@example.com",
                approved_on=datetime(2026, 5, 19, 8, 0, 0),
                expires_on=datetime(2026, 5, 20, 8, 0, 0),
            )
            _created_requests, logs = _install_get_doc(frappe, request_doc=request_doc)
            contact_export.now_datetime = lambda: datetime(2026, 5, 19, 9, 0, 0)
            contact_export.get_datetime = lambda value: value
            frappe.get_roles = lambda user=None: []

            with self.assertRaises(frappe.PermissionError):
                contact_export.assert_approved_contact_export(
                    "CER-1",
                    purpose="admissions_followup_export",
                    scope_type="Admissions Applicants",
                )

        self.assertEqual(logs[0]["result"], "denied")
        self.assertIn("requester_mismatch", logs[0]["details"])


class TestContactExportStaticBoundary(TestCase):
    def _package_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _function_sources(self, relative_path: str):
        source = self._package_root().joinpath(relative_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield node.name, ast.get_source_segment(source, node) or ""

    def test_contact_privacy_doctypes_do_not_claim_core_contacts_module(self):
        package_root = self._package_root()
        modules = package_root.joinpath("modules.txt").read_text(encoding="utf-8").splitlines()
        self.assertNotIn("Contacts", modules)

        metadata_paths = [
            package_root.joinpath("governance/doctype/contact_access_log/contact_access_log.json"),
            package_root.joinpath("governance/doctype/contact_export_request/contact_export_request.json"),
        ]
        for metadata_path in metadata_paths:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["module"], "Governance")

    def test_contact_export_endpoints_must_use_approval_gate(self):
        targets = [
            "api/admissions_portal.py",
            "api/family_consent.py",
            "admission/doctype/inquiry/inquiry.py",
            "students/doctype/student/student.py",
            "students/doctype/guardian/guardian.py",
            "hr/doctype/employee/employee.py",
        ]
        sensitive_tokens = ("Contact", "Guardian", "Student Applicant", "Inquiry", "Employee")
        raw_tokens = ("email", "phone", "mobile", "address", "contact")
        violations: list[str] = []

        for relative_path in targets:
            for function_name, body in self._function_sources(relative_path):
                folded_body = body.casefold()
                if "export" not in function_name.casefold() and "export" not in folded_body:
                    continue
                if not any(token in body for token in sensitive_tokens):
                    continue
                if not any(token in folded_body for token in raw_tokens):
                    continue
                if "assert_approved_contact_export" not in body:
                    violations.append(f"{relative_path}::{function_name}")

        self.assertEqual(violations, [])
