import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.billing.schedule_generation import sync_billing_schedules_for_plan
from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestBillingSchedule(AccountingTestMixin, FrappeTestCase):
    def test_generate_annual_schedule_from_program_enrollment(self):
        org = self.make_organization("Sched")
        income = self.make_account(org.name, "Income", prefix="Income")
        account_holder = self.make_account_holder(org.name)
        offering = self.make_program_offering(org.name)
        academic_year = self.get_program_offering_academic_year(offering.name)
        school = frappe.db.get_value("Program Offering", offering.name, "school")
        student = self.make_student(org.name, account_holder.name, school=school)
        enrollment = self.make_program_enrollment(
            organization=org.name,
            account_holder=account_holder.name,
            program_offering=offering.name,
            student=student.name,
            academic_year=academic_year,
        )
        billable_offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Program",
            pricing_mode="Fixed",
        )
        plan = self.make_program_billing_plan(
            organization=org.name,
            program_offering=offering.name,
            academic_year=academic_year,
            components=[
                {
                    "billable_offering": billable_offering.name,
                    "qty": 1,
                    "default_rate": 200,
                    "requires_student": 1,
                }
            ],
        )

        result = sync_billing_schedules_for_plan(plan.name)

        self.assertEqual(result["created_count"], 1)
        schedule = frappe.get_doc("Billing Schedule", result["schedule_names"][0])
        self.assertEqual(schedule.program_enrollment, enrollment.name)
        self.assertEqual(schedule.account_holder, account_holder.name)
        self.assertEqual(len(schedule.rows), 1)
        self.assertEqual(schedule.rows[0].expected_amount, 200)
        self.assertEqual(str(schedule.rows[0].due_date), "2025-08-01")

    def test_generate_term_schedule_uses_academic_terms(self):
        org = self.make_organization("Term")
        income = self.make_account(org.name, "Income", prefix="Income")
        account_holder = self.make_account_holder(org.name)
        offering = self.make_program_offering(org.name)
        academic_year = self.get_program_offering_academic_year(offering.name)
        school = frappe.db.get_value("Program Offering", offering.name, "school")
        self.make_term(academic_year, school=school, term_name="Term 1", start_date="2025-08-01", end_date="2025-12-15")
        self.make_term(academic_year, school=school, term_name="Term 2", start_date="2026-01-10", end_date="2026-06-30")
        student = self.make_student(org.name, account_holder.name, school=school)
        self.make_program_enrollment(
            organization=org.name,
            account_holder=account_holder.name,
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
            billing_cadence="Term",
            components=[
                {
                    "billable_offering": billable_offering.name,
                    "qty": 1,
                    "default_rate": 300,
                    "requires_student": 1,
                }
            ],
        )

        result = sync_billing_schedules_for_plan(plan.name)
        schedule = frappe.get_doc("Billing Schedule", result["schedule_names"][0])

        self.assertEqual(len(schedule.rows), 2)
        self.assertEqual([row.period_label for row in schedule.rows], ["Term 1", "Term 2"])
