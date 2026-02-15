# ifitwala_ed/admission/doctype/inquiry/test_inquiry.py
# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.doctype.inquiry.inquiry import _normalize_inquiry_state


class TestInquiry(FrappeTestCase):
	def test_normalize_legacy_new_inquiry_state(self):
		self.assertEqual(_normalize_inquiry_state("New Inquiry"), "New")

	def test_insert_legacy_new_inquiry_state_is_canonicalized(self):
		doc = frappe.get_doc(
			{
				"doctype": "Inquiry",
				"first_name": "Legacy",
				"workflow_state": "New Inquiry",
			}
		)
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.workflow_state, "New")
		self.assertEqual(frappe.db.get_value("Inquiry", doc.name, "workflow_state"), "New")
