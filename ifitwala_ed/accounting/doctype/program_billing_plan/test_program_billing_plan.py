import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestProgramBillingPlan(AccountingTestMixin, FrappeTestCase):
    def test_only_one_active_plan_allowed_per_program_offering_and_academic_year(self):
        org = self.make_organization("Plan")
        income = self.make_account(org.name, "Income", prefix="Income")
        offering = self.make_program_offering(org.name)
        academic_year = self.get_program_offering_academic_year(offering.name)
        billable_offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Program",
            pricing_mode="Per Term",
        )

        self.make_program_billing_plan(
            organization=org.name,
            program_offering=offering.name,
            academic_year=academic_year,
            components=[
                {
                    "billable_offering": billable_offering.name,
                    "qty": 1,
                    "default_rate": 100,
                    "requires_student": 1,
                }
            ],
        )

        with self.assertRaises(frappe.ValidationError):
            self.make_program_billing_plan(
                organization=org.name,
                program_offering=offering.name,
                academic_year=academic_year,
                components=[
                    {
                        "billable_offering": billable_offering.name,
                        "qty": 1,
                        "default_rate": 125,
                        "requires_student": 1,
                    }
                ],
            )
