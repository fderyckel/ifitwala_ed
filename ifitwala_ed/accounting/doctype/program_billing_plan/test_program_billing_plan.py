import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.billing.rate_policies import AMOUNT_BASIS_CUSTOM_PERCENTAGES
from ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan import (
    generate_billing_schedules,
    get_program_offering_academic_years,
)
from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestProgramBillingPlan(AccountingTestMixin, FrappeTestCase):
    def test_single_offering_academic_year_is_resolved_when_empty(self):
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

        plan = self.make_program_billing_plan(
            organization=org.name,
            program_offering=offering.name,
            academic_year=None,
            components=[self._program_component(billable_offering.name, 100)],
        )

        self.assertEqual(plan.academic_year, academic_year)

    def test_multiple_offering_academic_years_require_explicit_selection(self):
        org = self.make_organization("Plan")
        income = self.make_account(org.name, "Income", prefix="Income")
        offering = self.make_program_offering(org.name)
        self._add_academic_year_to_offering(offering.name)
        billable_offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Program",
            pricing_mode="Per Term",
        )

        with self.assertRaisesRegex(frappe.ValidationError, "Please choose an Academic Year"):
            self.make_program_billing_plan(
                organization=org.name,
                program_offering=offering.name,
                academic_year=None,
                components=[self._program_component(billable_offering.name, 100)],
            )

    def test_academic_year_must_belong_to_program_offering(self):
        org = self.make_organization("Plan")
        income = self.make_account(org.name, "Income", prefix="Income")
        offering = self.make_program_offering(org.name)
        school = frappe.db.get_value("Program Offering", offering.name, "school")
        unlinked_academic_year = self._make_academic_year(school, "2026-08-01", "2027-06-30")
        billable_offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Program",
            pricing_mode="Per Term",
        )

        with self.assertRaisesRegex(frappe.ValidationError, "Academic Year must be part"):
            self.make_program_billing_plan(
                organization=org.name,
                program_offering=offering.name,
                academic_year=unlinked_academic_year.name,
                components=[self._program_component(billable_offering.name, 100)],
            )

    def test_program_offering_academic_year_helper_returns_linked_years_only(self):
        org = self.make_organization("Plan")
        offering = self.make_program_offering(org.name)
        first_academic_year = self.get_program_offering_academic_year(offering.name)
        second_academic_year = self._add_academic_year_to_offering(offering.name)

        rows = get_program_offering_academic_years(offering.name)

        self.assertEqual([row["academic_year"] for row in rows], [first_academic_year, second_academic_year.name])

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

    def test_generate_billing_schedules_returns_account_holder_tool_context(self):
        org = self.make_organization("Plan Missing AH")
        income = self.make_account(org.name, "Income", prefix="Income")
        offering = self.make_program_offering(org.name)
        academic_year = self.get_program_offering_academic_year(offering.name)
        school = frappe.db.get_value("Program Offering", offering.name, "school")
        student = self.make_student(org.name, "", school=school)
        self.make_program_enrollment(
            organization=org.name,
            program_offering=offering.name,
            student=student.name,
            academic_year=academic_year,
        )
        billable_offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Program",
            pricing_mode="Per Term",
        )
        plan = self.make_program_billing_plan(
            organization=org.name,
            program_offering=offering.name,
            academic_year=academic_year,
            components=[self._program_component(billable_offering.name, 100)],
        )

        result = generate_billing_schedules(plan.name)

        self.assertFalse(result["ok"])
        self.assertTrue(result["requires_account_holder_setup"])
        self.assertEqual(result["tool_doctype"], "Student Account Holder Tool")
        self.assertEqual(result["organization"], org.name)
        self.assertEqual(result["program_offering"], offering.name)
        self.assertEqual(result["academic_year"], academic_year)
        self.assertEqual(result["missing_students"][0]["student"], student.name)

    def test_custom_term_split_percentages_must_total_full_annual_fee(self):
        org = self.make_organization("Plan Split")
        income = self.make_account(org.name, "Income", prefix="Income")
        offering = self.make_program_offering(org.name)
        academic_year = self.get_program_offering_academic_year(offering.name)
        school = frappe.db.get_value("Program Offering", offering.name, "school")
        first_term = self.make_term(
            academic_year,
            school=school,
            term_name="Term 1",
            start_date="2025-08-01",
            end_date="2025-10-31",
        )
        second_term = self.make_term(
            academic_year,
            school=school,
            term_name="Term 2",
            start_date="2025-11-01",
            end_date="2026-01-31",
        )
        billable_offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Program",
            pricing_mode="Per Term",
        )

        with self.assertRaisesRegex(frappe.ValidationError, "must total 100%"):
            self.make_program_billing_plan(
                organization=org.name,
                program_offering=offering.name,
                academic_year=academic_year,
                billing_cadence="Term",
                term_splits=[
                    {"term": first_term.name, "term_label": "Term 1", "percentage": 40},
                    {"term": second_term.name, "term_label": "Term 2", "percentage": 50},
                ],
                components=[
                    {
                        "billable_offering": billable_offering.name,
                        "qty": 1,
                        "default_rate": 12000,
                        "amount_basis": AMOUNT_BASIS_CUSTOM_PERCENTAGES,
                        "requires_student": 1,
                    }
                ],
            )

    def _program_component(self, billable_offering, default_rate):
        return {
            "billable_offering": billable_offering,
            "qty": 1,
            "default_rate": default_rate,
            "requires_student": 1,
        }

    def _add_academic_year_to_offering(self, program_offering):
        school = frappe.db.get_value("Program Offering", program_offering, "school")
        academic_year = self._make_academic_year(school, "2026-08-01", "2027-06-30")
        offering = frappe.get_doc("Program Offering", program_offering)
        offering.append("offering_academic_years", {"academic_year": academic_year.name})
        offering.save()
        return academic_year

    def _make_academic_year(self, school, year_start_date, year_end_date):
        academic_year = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
                "school": school,
                "year_start_date": year_start_date,
                "year_end_date": year_end_date,
                "archived": 0,
                "visible_to_admission": 1,
            }
        )
        academic_year.insert()
        return academic_year
