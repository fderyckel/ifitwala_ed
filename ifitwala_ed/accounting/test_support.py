# ifitwala_ed/accounting/test_support.py

import frappe
from frappe.utils import nowdate


class AccountingTestMixin:
    def make_organization(self, prefix="Org"):
        org = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=4)}",
            }
        )
        org.insert()
        return org

    def make_school(self, organization, prefix="School"):
        school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        )
        school.insert()
        return school

    def make_account(
        self,
        organization,
        root_type,
        account_type=None,
        is_group=0,
        parent_account=None,
        prefix="Account",
    ):
        doc = {
            "doctype": "Account",
            "organization": organization,
            "account_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "root_type": root_type,
            "is_group": 1 if is_group else 0,
        }
        if account_type:
            doc["account_type"] = account_type
        if parent_account:
            doc["parent_account"] = parent_account

        account = frappe.get_doc(doc)
        account.insert()
        return account

    def make_accounts_settings(
        self,
        organization,
        receivable_account,
        advance_account,
        cash_account=None,
        bank_account=None,
        tax_payable_account=None,
    ):
        if frappe.db.exists("Accounts Settings", organization):
            settings = frappe.get_doc("Accounts Settings", organization)
        else:
            settings = frappe.new_doc("Accounts Settings")
            settings.organization = organization

        settings.default_receivable_account = receivable_account
        settings.default_advance_account = advance_account
        settings.default_cash_account = cash_account
        settings.default_bank_account = bank_account
        settings.default_tax_payable_account = tax_payable_account
        settings.save()
        return settings

    def make_fiscal_year(
        self,
        organization,
        year=None,
        year_start_date=None,
        year_end_date=None,
        is_short_year=0,
    ):
        posting_year = str(year or frappe.utils.getdate(nowdate()).year)
        start_date = year_start_date or f"{posting_year}-01-01"
        end_date = year_end_date or f"{posting_year}-12-31"

        existing = frappe.get_all(
            "Fiscal Year Organization",
            filters={"organization": organization},
            fields=["parent"],
            limit=100,
        )
        for row in existing:
            fiscal_year = frappe.get_doc("Fiscal Year", row.parent)
            if str(fiscal_year.year_start_date) == start_date and str(fiscal_year.year_end_date) == end_date:
                return fiscal_year

        doc = frappe.get_doc(
            {
                "doctype": "Fiscal Year",
                "year": f"{organization}-{posting_year}-{frappe.generate_hash(length=4)}",
                "year_start_date": start_date,
                "year_end_date": end_date,
                "is_short_year": is_short_year,
                "organizations": [{"organization": organization}],
            }
        )
        doc.insert()
        return doc

    def make_account_holder(self, organization, holder_type="Individual", prefix="Account Holder"):
        account_holder = frappe.get_doc(
            {
                "doctype": "Account Holder",
                "organization": organization,
                "account_holder_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "account_holder_type": holder_type,
            }
        )
        account_holder.insert()
        return account_holder

    def make_billable_offering(self, organization, income_account, offering_type="One-off Fee", pricing_mode="Fixed"):
        offering = frappe.get_doc(
            {
                "doctype": "Billable Offering",
                "organization": organization,
                "offering_type": offering_type,
                "income_account": income_account,
                "pricing_mode": pricing_mode,
            }
        )
        offering.insert()
        return offering

    def make_student(self, organization, account_holder, school=None, prefix="Student"):
        school_name = school or self.make_school(organization).name
        student = frappe.get_doc(
            {
                "doctype": "Student",
                "student_first_name": prefix,
                "student_last_name": frappe.generate_hash(length=6),
                "student_email": f"{frappe.generate_hash(length=8)}@example.com",
                "anchor_school": school_name,
                "account_holder": account_holder,
            }
        )
        previous_in_migration = bool(getattr(frappe.flags, "in_migration", False))
        frappe.flags.in_migration = True
        try:
            student.insert()
        finally:
            frappe.flags.in_migration = previous_in_migration
        return student

    def make_program_offering(self, organization, school=None):
        school_name = school or self.make_school(organization).name
        academic_year = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
                "school": school_name,
                "year_start_date": "2025-08-01",
                "year_end_date": "2026-06-30",
                "archived": 0,
                "visible_to_admission": 1,
            }
        )
        academic_year.insert()

        program = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Program {frappe.generate_hash(length=6)}",
            }
        )
        program.insert()

        offering = frappe.get_doc(
            {
                "doctype": "Program Offering",
                "program": program.name,
                "school": school_name,
                "offering_title": f"Offering {frappe.generate_hash(length=6)}",
                "offering_academic_years": [{"academic_year": academic_year.name}],
            }
        )
        offering.insert()
        return offering

    def make_payment_terms_template(self, organization, title=None):
        doc = frappe.get_doc(
            {
                "doctype": "Payment Terms Template",
                "title": title or f"Terms {frappe.generate_hash(length=6)}",
                "organization": organization,
                "terms": [
                    {"term_name": "Deposit", "invoice_portion": 50, "due_days": 0},
                    {"term_name": "Final", "invoice_portion": 50, "due_days": 30},
                ],
            }
        )
        doc.insert()
        return doc

    def make_sales_invoice(
        self,
        organization,
        account_holder,
        billable_offering,
        income_account,
        student=None,
        qty=1,
        rate=100,
        program_offering=None,
        posting_date=None,
        payment_terms_template=None,
    ):
        invoice_posting_date = posting_date or nowdate()
        self.make_fiscal_year(organization, year=frappe.utils.getdate(invoice_posting_date).year)
        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "account_holder": account_holder,
                "organization": organization,
                "program_offering": program_offering,
                "posting_date": invoice_posting_date,
                "payment_terms_template": payment_terms_template,
                "items": [
                    {
                        "billable_offering": billable_offering,
                        "student": student,
                        "qty": qty,
                        "rate": rate,
                        "charge_source": "Program Offering" if program_offering else "Extra",
                        "income_account": income_account,
                    }
                ],
            }
        )
        invoice.insert()
        return invoice
