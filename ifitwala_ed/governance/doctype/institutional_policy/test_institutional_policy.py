# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.governance.policy_utils import ensure_policy_applies_to_column
from ifitwala_ed.tests.factories.organization import make_organization


class TestInstitutionalPolicy(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.created: list[tuple[str, str]] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self.created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def test_insert_normalizes_multi_audience_applies_to(self):
        organization = make_organization(prefix="IP Multi")
        self.created.append(("Organization", organization.name))

        policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"multi_audience_{frappe.generate_hash(length=6)}",
                "policy_title": f"Multi Audience {frappe.generate_hash(length=6)}",
                "policy_category": "Admissions",
                "applies_to": "Guardian, Student",
                "organization": organization.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", policy.name))

        self.assertEqual(policy.applies_to, "Guardian\nStudent")

    def test_insert_rejects_unknown_applies_to_values(self):
        organization = make_organization(prefix="IP Invalid")
        self.created.append(("Organization", organization.name))

        policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"invalid_audience_{frappe.generate_hash(length=6)}",
                "policy_title": f"Invalid Audience {frappe.generate_hash(length=6)}",
                "policy_category": "Admissions",
                "applies_to": "Guardian\nUnknown",
                "organization": organization.name,
                "is_active": 1,
            }
        )

        with self.assertRaises(frappe.ValidationError):
            policy.insert(ignore_permissions=True)

    def test_schema_check_rejects_missing_db_column_even_when_meta_has_field(self):
        with (
            patch("ifitwala_ed.governance.policy_utils.frappe.db.has_column", return_value=False),
            patch(
                "ifitwala_ed.governance.policy_utils.frappe.get_meta",
                return_value=type("Meta", (), {"has_field": lambda self, fieldname: fieldname == "applies_to"})(),
            ),
        ):
            result = ensure_policy_applies_to_column(caller="test")

        self.assertFalse(result.get("ok"))
        self.assertIn("missing", (result.get("message") or "").lower())
