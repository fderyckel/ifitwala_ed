# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import sys
import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe
from ifitwala_ed.utilities.governed_file_contract import is_allowed_file_purpose


class _Doc:
    def __init__(self, name: str):
        self.name = name
        self.status = "Draft"
        self.organization = "ORG-1"
        self.school = "SCH-1"
        self.employee = "EMP-1"
        self.receipts = [
            types.SimpleNamespace(
                name="ROW-1",
                file="/private/files/receipt.pdf",
                external_url="",
                section_break_sbex="Receipt",
                description="",
                file_name="receipt.pdf",
                file_size=128,
            )
        ]

    def get(self, key):
        return getattr(self, key)

    def reload(self):
        return self


def _expense_claim_receipt_stub_modules(captured_payloads: list[dict]):
    file_access = types.ModuleType("ifitwala_ed.api.file_access")
    file_access._resolve_drive_file_grant_target_url = lambda **kwargs: None
    file_access._respond_with_delivery_target = lambda **kwargs: False
    file_access._resolve_card_preview_derivative_role_for_drive_file = lambda drive_file_id: None
    file_access._resolve_cached_thumbnail_target_url = lambda **kwargs: None

    governed_uploads = types.ModuleType("ifitwala_ed.utilities.governed_uploads")

    def get_form_arg(key: str):
        frappe = sys.modules["frappe"]
        value = getattr(frappe, "form_dict", {}).get(key)
        if value:
            return value
        args = getattr(frappe, "form_dict", {}).get("args")
        if isinstance(args, str):
            args = json.loads(args)
        if isinstance(args, dict):
            return args.get(key)
        return None

    def drive_upload_and_finalize(*, create_session_callable, payload, content):
        del create_session_callable, content
        captured_payloads.append(dict(payload))
        return (
            {"workflow_result": {"row_name": "ROW-1"}},
            {"workflow_result": {"row_name": "ROW-1"}, "file_id": "FILE-1"},
            types.SimpleNamespace(name="FILE-1"),
        )

    governed_uploads._get_form_arg = get_form_arg
    governed_uploads._get_uploaded_file = lambda: ("receipt.pdf", b"receipt-bytes")
    governed_uploads._resolve_upload_mime_type_hint = lambda **kwargs: "application/pdf"
    governed_uploads._workflow_result_payload = lambda response: dict(response.get("workflow_result") or {})
    governed_uploads._drive_upload_and_finalize = drive_upload_and_finalize

    drive_uploads = types.ModuleType("ifitwala_drive.api.uploads")
    drive_uploads.create_upload_session = lambda **kwargs: {
        "upload_session_id": "DUS-1",
        "workflow_result": {"row_name": "ROW-1"},
    }
    drive_api = types.ModuleType("ifitwala_drive.api")
    drive_api.uploads = drive_uploads
    drive_root = types.ModuleType("ifitwala_drive")
    drive_root.api = drive_api

    return {
        "ifitwala_ed.api.file_access": file_access,
        "ifitwala_ed.utilities.governed_uploads": governed_uploads,
        "ifitwala_drive": drive_root,
        "ifitwala_drive.api": drive_api,
        "ifitwala_drive.api.uploads": drive_uploads,
    }


class TestExpenseClaimReceiptsUnit(TestCase):
    def test_expense_claim_receipt_contract_uses_allowed_drive_purpose(self):
        with stubbed_frappe(extra_modules=_expense_claim_receipt_stub_modules([])):
            module = import_fresh("ifitwala_ed.hr.doctype.expense_claim.receipts")

            contract = module.build_expense_claim_receipt_upload_contract(_Doc("EXC-2026-00001"), row_name="ROW-1")

        self.assertEqual(contract["purpose"], "administrative")
        self.assertTrue(is_allowed_file_purpose(contract["purpose"]))

    def test_upload_recovers_expense_claim_from_frappe_upload_args(self):
        captured_payloads = []
        with stubbed_frappe(extra_modules=_expense_claim_receipt_stub_modules(captured_payloads)) as frappe:
            doc = _Doc("EXC-2026-00001")
            frappe.form_dict = {
                "args": json.dumps({"expense_claim": doc.name, "row_name": "ROW-1"}),
            }
            frappe.db.exists = lambda doctype, name: doctype == "Expense Claim" and name == doc.name
            frappe.db.get_value = lambda *args, **kwargs: None
            frappe.get_doc = lambda doctype, name=None, **kwargs: doc
            frappe.has_permission = lambda doctype, doc=None, ptype=None, user=None: True
            frappe.get_roles = lambda user=None: ["Employee"]

            module = import_fresh("ifitwala_ed.api.expense_claim_receipts")
            response = module.upload_expense_claim_receipt()

        self.assertTrue(response["ok"])
        self.assertEqual(captured_payloads[0]["expense_claim"], "EXC-2026-00001")
        self.assertEqual(captured_payloads[0]["workflow_payload"]["expense_claim"], "EXC-2026-00001")

    def test_upload_uses_docname_as_fallback_for_frappe_uploads(self):
        captured_payloads = []
        with stubbed_frappe(extra_modules=_expense_claim_receipt_stub_modules(captured_payloads)) as frappe:
            doc = _Doc("EXC-2026-00002")
            frappe.form_dict = {"docname": doc.name}
            frappe.db.exists = lambda doctype, name: doctype == "Expense Claim" and name == doc.name
            frappe.db.get_value = lambda *args, **kwargs: None
            frappe.get_doc = lambda doctype, name=None, **kwargs: doc
            frappe.has_permission = lambda doctype, doc=None, ptype=None, user=None: True
            frappe.get_roles = lambda user=None: ["Employee"]

            module = import_fresh("ifitwala_ed.api.expense_claim_receipts")
            response = module.upload_expense_claim_receipt()

        self.assertTrue(response["ok"])
        self.assertEqual(captured_payloads[0]["expense_claim"], "EXC-2026-00002")

    def test_upload_without_saved_claim_name_has_actionable_error(self):
        with stubbed_frappe(extra_modules=_expense_claim_receipt_stub_modules([])) as frappe:
            frappe.form_dict = {}
            frappe.db.exists = lambda doctype, name: False
            frappe.db.get_value = lambda *args, **kwargs: None
            frappe.has_permission = lambda doctype, doc=None, ptype=None, user=None: True

            module = import_fresh("ifitwala_ed.api.expense_claim_receipts")
            with self.assertRaises(StubValidationError) as raised:
                module.upload_expense_claim_receipt()

        self.assertIn("Save the Expense Claim before attaching receipts", str(raised.exception))
