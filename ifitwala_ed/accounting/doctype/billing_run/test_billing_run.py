import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.billing.invoice_generation import generate_draft_invoices_for_run
from ifitwala_ed.accounting.billing.schedule_generation import sync_billing_schedules_for_plan
from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestBillingRun(AccountingTestMixin, FrappeTestCase):
    def test_bulk_run_groups_students_by_account_holder_and_cancel_resets_rows(self):
        org = self.make_organization("Run")
        receivable = self.make_account(org.name, "Asset", account_type="Receivable", prefix="A/R")
        advance = self.make_account(org.name, "Liability", prefix="Advance")
        income = self.make_account(org.name, "Income", prefix="Income")
        self.make_accounts_settings(org.name, receivable.name, advance.name)
        account_holder = self.make_account_holder(org.name)
        offering = self.make_program_offering(org.name)
        academic_year = self.get_program_offering_academic_year(offering.name)
        school = frappe.db.get_value("Program Offering", offering.name, "school")
        student_a = self.make_student(org.name, account_holder.name, school=school, prefix="Student A")
        student_b = self.make_student(org.name, account_holder.name, school=school, prefix="Student B")
        self.make_program_enrollment(
            organization=org.name,
            account_holder=account_holder.name,
            program_offering=offering.name,
            student=student_a.name,
            academic_year=academic_year,
        )
        self.make_program_enrollment(
            organization=org.name,
            account_holder=account_holder.name,
            program_offering=offering.name,
            student=student_b.name,
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
                    "default_rate": 150,
                    "requires_student": 1,
                }
            ],
        )
        sync_billing_schedules_for_plan(plan.name)
        self.make_fiscal_year(org.name, year=2025, year_start_date="2025-01-01", year_end_date="2025-12-31")

        run = frappe.get_doc(
            {
                "doctype": "Billing Run",
                "organization": org.name,
                "program_offering": offering.name,
                "academic_year": academic_year,
                "posting_date": "2025-08-01",
                "due_date_from": "2025-08-01",
                "due_date_to": "2025-08-01",
            }
        )
        run.insert()

        result = generate_draft_invoices_for_run(run.name)

        self.assertEqual(result["invoice_count"], 1)
        invoice = frappe.get_doc("Sales Invoice", result["invoice_names"][0])
        self.assertEqual(invoice.account_holder, account_holder.name)
        self.assertEqual(invoice.docstatus, 0)
        self.assertEqual(len(invoice.items), 2)
        self.assertEqual({row.student for row in invoice.items}, {student_a.name, student_b.name})

        schedules = frappe.get_all(
            "Billing Schedule",
            filters={"billing_plan": plan.name},
            fields=["name"],
            order_by="name asc",
            limit=10,
        )
        self.assertEqual(len(schedules), 2)
        for row in schedules:
            schedule = frappe.get_doc("Billing Schedule", row.name)
            self.assertEqual(schedule.status, "Invoiced")
            self.assertEqual(schedule.rows[0].sales_invoice, invoice.name)

        invoice.submit()
        invoice.reload()
        invoice.cancel()

        for row in schedules:
            schedule = frappe.get_doc("Billing Schedule", row.name)
            self.assertEqual(schedule.status, "Pending")
            self.assertEqual(schedule.rows[0].status, "Pending")
            self.assertFalse(schedule.rows[0].sales_invoice)

        run.reload()
        self.assertEqual(run.status, "Draft")
        self.assertFalse(run.processed_on)
        self.assertEqual(run.items, [])
