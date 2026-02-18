# ifitwala_ed/admission/doctype/inquiry/test_inquiry.py
# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.admission_utils import _validate_admissions_assignee
from ifitwala_ed.admission.doctype.inquiry.inquiry import _normalize_inquiry_state
from ifitwala_ed.tests.factories.users import make_user


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

    def _ensure_role(self, user: str, role: str) -> None:
        if not frappe.db.exists("Role", role):
            self.skipTest(f"Missing Role '{role}' in this site.")
        if frappe.db.exists("Has Role", {"parent": user, "role": role}):
            return
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parent": user,
                "parenttype": "User",
                "parentfield": "roles",
                "role": role,
            }
        ).insert(ignore_permissions=True)

    def test_validate_admissions_assignee_allows_manager_or_officer(self):
        manager = make_user()
        self._ensure_role(manager.name, "Admission Manager")
        _validate_admissions_assignee(manager.name)

        officer = make_user()
        self._ensure_role(officer.name, "Admission Officer")
        _validate_admissions_assignee(officer.name)

    def test_validate_admissions_assignee_rejects_disabled_or_no_role(self):
        no_role = make_user()
        with self.assertRaises(frappe.ValidationError):
            _validate_admissions_assignee(no_role.name)

        disabled = make_user()
        self._ensure_role(disabled.name, "Admission Officer")
        frappe.db.set_value("User", disabled.name, "enabled", 0)
        with self.assertRaises(frappe.ValidationError):
            _validate_admissions_assignee(disabled.name)
