import frappe

from ifitwala_ed.accounting.test_support import AccountingTestMixin
from ifitwala_ed.tests.base import IfitwalaEdTestSuite


class TestBillableOffering(AccountingTestMixin, IfitwalaEdTestSuite):
    def test_autoname_generates_unique_sequence_for_same_type_and_organization(self):
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
        self.assertTrue(first.name.startswith(f"Program-{org.name}-"))
        self.assertTrue(second.name.startswith(f"Program-{org.name}-"))
        self.assertTrue(frappe.db.exists("Billable Offering", first.name))
        self.assertTrue(frappe.db.exists("Billable Offering", second.name))
