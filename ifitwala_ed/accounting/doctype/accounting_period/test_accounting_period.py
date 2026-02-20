# ifitwala_ed/accounting/doctype/accounting_period/test_accounting_period.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.tests.factories import make_organization


class TestAccountingPeriod(FrappeTestCase):
    def test_overlapping_periods_blocked_within_same_organization(self):
        org = make_organization("Period")

        frappe.get_doc(
            {
                "doctype": "Accounting Period",
                "organization": org.name,
                "period_name": f"Period A {frappe.generate_hash(length=6)}",
                "start_date": "2026-01-01",
                "end_date": "2026-03-31",
            }
        ).insert()

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Accounting Period",
                    "organization": org.name,
                    "period_name": f"Period B {frappe.generate_hash(length=6)}",
                    "start_date": "2026-03-01",
                    "end_date": "2026-06-30",
                }
            ).insert()

    def test_overlapping_periods_allowed_across_different_organizations(self):
        org_a = make_organization("Period A")
        org_b = make_organization("Period B")

        frappe.get_doc(
            {
                "doctype": "Accounting Period",
                "organization": org_a.name,
                "period_name": f"OrgA Period {frappe.generate_hash(length=6)}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            }
        ).insert()

        # Same date window in a different organization is valid.
        doc = frappe.get_doc(
            {
                "doctype": "Accounting Period",
                "organization": org_b.name,
                "period_name": f"OrgB Period {frappe.generate_hash(length=6)}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            }
        )
        doc.insert()
        self.assertEqual(doc.organization, org_b.name)
