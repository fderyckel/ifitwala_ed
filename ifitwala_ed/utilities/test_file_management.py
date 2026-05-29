# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.utilities import file_management


def _new_file_doc(**overrides):
    doc = frappe._dict(
        is_folder=0,
        attached_to_doctype="Expense Claim",
        attached_to_field=None,
        flags=frappe._dict(),
    )
    doc.update(overrides)
    doc.is_new = lambda: True
    return doc


class TestFileManagement(FrappeTestCase):
    def test_expense_claim_raw_file_insert_requires_governed_receipt_upload(self):
        doc = _new_file_doc()

        with self.assertRaises(frappe.ValidationError) as raised:
            file_management.validate_admissions_attachment(doc)

        self.assertIn("Governed upload required for Expense Claim", str(raised.exception))
        self.assertIn("Upload Receipt", str(raised.exception))

    def test_expense_claim_governed_file_projection_is_allowed(self):
        doc = _new_file_doc(flags=frappe._dict(governed_upload=True))

        file_management.validate_admissions_attachment(doc)
