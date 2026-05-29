import frappe

from ifitwala_ed.accounting.test_support import AccountingTestMixin
from ifitwala_ed.tests.base import IfitwalaEdTestSuite


class TestBillableOffering(AccountingTestMixin, IfitwalaEdTestSuite):
    def test_autoname_uses_billable_offering_prefix_and_organization_abbreviation(self):
        org = self.make_organization("Billable")
        income = self.make_account(org.name, "Income", prefix="Income")

        first = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Program",
            pricing_mode="Fixed",
        )
        second = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Program",
            pricing_mode="Fixed",
        )

        self.assertNotEqual(first.name, second.name)
        self.assertNotIn("#", first.name)
        self.assertNotIn("#", second.name)
        self.assertTrue(first.name.startswith(f"BO-{org.abbr}-"))
        self.assertTrue(second.name.startswith(f"BO-{org.abbr}-"))
        self.assertNotIn(first.offering_type, first.name)
        self.assertNotIn(org.name, first.name)
        self.assertTrue(frappe.db.exists("Billable Offering", first.name))
        self.assertTrue(frappe.db.exists("Billable Offering", second.name))
