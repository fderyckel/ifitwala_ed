import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from ifitwala_ed.accounting.doctype.initial_enrollment_billing_package.initial_enrollment_billing_package import (
    generate_initial_enrollment_invoice,
    generate_initial_enrollment_invoices,
)
from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestInitialEnrollmentBillingPackage(AccountingTestMixin, FrappeTestCase):
    def test_generate_draft_invoice_for_first_enrollment_once(self):
        ctx = self._make_context()

        first = generate_initial_enrollment_invoice(
            program_enrollment=ctx["enrollment"].name,
            initial_enrollment_billing_package=ctx["package"].name,
            posting_date="2025-08-01",
        )
        second = generate_initial_enrollment_invoice(
            program_enrollment=ctx["enrollment"].name,
            initial_enrollment_billing_package=ctx["package"].name,
            posting_date="2025-08-01",
        )

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["sales_invoice"], second["sales_invoice"])

        invoice = frappe.get_doc("Sales Invoice", first["sales_invoice"])
        self.assertEqual(invoice.docstatus, 0)
        self.assertEqual(invoice.account_holder, ctx["account_holder"].name)
        self.assertEqual(invoice.organization, ctx["organization"].name)
        self.assertEqual(invoice.program_offering, ctx["program_offering"].name)
        self.assertEqual(invoice.source_program_enrollment, ctx["enrollment"].name)
        self.assertEqual(invoice.initial_enrollment_billing_package, ctx["package"].name)
        self.assertEqual(len(invoice.items), 1)
        self.assertEqual(invoice.items[0].billable_offering, ctx["billable_offering"].name)
        self.assertEqual(invoice.items[0].student, ctx["student"].name)
        self.assertEqual(flt(invoice.grand_total), 375)

    def test_bulk_generation_skips_returning_student(self):
        ctx = self._make_context()
        old_offering = self.make_program_offering(
            ctx["organization"].name,
            school=ctx["school"],
            academic_year_start_date="2024-08-01",
            academic_year_end_date="2025-06-30",
        )
        old_academic_year = self.get_program_offering_academic_year(old_offering.name)
        self.make_program_enrollment(
            organization=ctx["organization"].name,
            account_holder=ctx["account_holder"].name,
            school=ctx["school"],
            program_offering=old_offering.name,
            student=ctx["student"].name,
            academic_year=old_academic_year,
            enrollment_date="2024-08-01",
        )

        result = generate_initial_enrollment_invoices(
            initial_enrollment_billing_package=ctx["package"].name,
            posting_date="2025-08-01",
        )

        self.assertEqual(result["created_count"], 0)
        self.assertEqual(result["existing_count"], 0)
        self.assertFalse(
            frappe.db.exists(
                "Sales Invoice",
                {
                    "source_program_enrollment": ctx["enrollment"].name,
                    "initial_enrollment_billing_package": ctx["package"].name,
                },
            )
        )

    def test_package_rejects_program_billable_offering(self):
        org = self.make_organization("Initial")
        income = self.make_account(org.name, "Income", prefix="Income")
        offering = self.make_program_offering(org.name)
        academic_year = self.get_program_offering_academic_year(offering.name)
        billable_offering = self.make_billable_offering(
            org.name,
            income.name,
            offering_type="Program",
            pricing_mode="Fixed",
        )

        with self.assertRaisesRegex(frappe.ValidationError, "cannot include Program billable offerings"):
            self.make_initial_enrollment_billing_package(
                organization=org.name,
                billable_offering=billable_offering.name,
                program_offering=offering.name,
                academic_year=academic_year,
                default_rate=100,
            )

    def _make_context(self):
        organization = self.make_organization("Initial")
        receivable = self.make_account(organization.name, "Asset", account_type="Receivable", prefix="A/R")
        advance = self.make_account(organization.name, "Liability", prefix="Advance")
        income = self.make_account(organization.name, "Income", prefix="Income")
        self.make_accounts_settings(organization.name, receivable.name, advance.name)
        self.make_fiscal_year(organization.name, year=2025, year_start_date="2025-01-01", year_end_date="2025-12-31")

        account_holder = self.make_account_holder(organization.name)
        program_offering = self.make_program_offering(organization.name)
        academic_year = self.get_program_offering_academic_year(program_offering.name)
        school = frappe.db.get_value("Program Offering", program_offering.name, "school")
        student = self.make_student(organization.name, account_holder.name, school=school, prefix="New Student")
        enrollment = self.make_program_enrollment(
            organization=organization.name,
            account_holder=account_holder.name,
            school=school,
            program_offering=program_offering.name,
            student=student.name,
            academic_year=academic_year,
            enrollment_date="2025-08-01",
        )
        billable_offering = self.make_billable_offering(
            organization.name,
            income.name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )
        package = self.make_initial_enrollment_billing_package(
            organization=organization.name,
            billable_offering=billable_offering.name,
            program_offering=program_offering.name,
            academic_year=academic_year,
            default_rate=375,
        )
        return {
            "organization": organization,
            "account_holder": account_holder,
            "program_offering": program_offering,
            "academic_year": academic_year,
            "school": school,
            "student": student,
            "enrollment": enrollment,
            "billable_offering": billable_offering,
            "package": package,
        }
