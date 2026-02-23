# ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate


class TestSalesInvoice(FrappeTestCase):
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

    def _base_context(self):
        org = self.make_organization("SI")
        school = self.make_school(org.name, "SI School")

        receivable = self.make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Receivable",
            prefix="A/R",
        )
        advance = self.make_account(
            organization=org.name,
            root_type="Liability",
            prefix="Advance",
        )
        income = self.make_account(
            organization=org.name,
            root_type="Income",
            prefix="Income",
        )
        tax = self.make_account(
            organization=org.name,
            root_type="Liability",
            account_type="Tax",
            prefix="Tax",
        )

        self.make_accounts_settings(
            organization=org.name,
            receivable_account=receivable.name,
            advance_account=advance.name,
        )

        ah_primary = self.make_account_holder(org.name, prefix="Primary")
        ah_other = self.make_account_holder(org.name, prefix="Other")

        return {
            "org": org,
            "school": school,
            "receivable": receivable,
            "advance": advance,
            "income": income,
            "tax": tax,
            "ah_primary": ah_primary,
            "ah_other": ah_other,
        }

    def test_student_account_holder_must_match_invoice_account_holder(self):
        ctx = self._base_context()

        student = self.make_student(
            organization=ctx["org"].name,
            account_holder=ctx["ah_other"].name,
            school=ctx["school"].name,
            prefix="Mismatch",
        )
        offering = self.make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="Program",
            pricing_mode="Fixed",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Sales Invoice",
                    "organization": ctx["org"].name,
                    "account_holder": ctx["ah_primary"].name,
                    "posting_date": nowdate(),
                    "items": [
                        {
                            "billable_offering": offering.name,
                            "charge_source": "Program Offering",
                            "student": student.name,
                            "qty": 1,
                            "rate": 100,
                            "income_account": ctx["income"].name,
                        }
                    ],
                }
            ).insert()

    def test_program_charge_requires_program_offering_context(self):
        ctx = self._base_context()
        offering = self.make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="Program",
            pricing_mode="Fixed",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Sales Invoice",
                    "organization": ctx["org"].name,
                    "account_holder": ctx["ah_primary"].name,
                    "posting_date": nowdate(),
                    "items": [
                        {
                            "billable_offering": offering.name,
                            "charge_source": "Program Offering",
                            "qty": 1,
                            "rate": 100,
                            "income_account": ctx["income"].name,
                        }
                    ],
                }
            ).insert()

    def test_submit_posts_balanced_double_entry_gl(self):
        ctx = self._base_context()
        offering = self.make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "organization": ctx["org"].name,
                "account_holder": ctx["ah_primary"].name,
                "posting_date": nowdate(),
                "items": [
                    {
                        "billable_offering": offering.name,
                        "charge_source": "Extra",
                        "qty": 2,
                        "rate": 50,
                        "income_account": ctx["income"].name,
                    }
                ],
                "taxes": [
                    {
                        "account_head": ctx["tax"].name,
                        "rate": 10,
                        "included_in_print_rate": 0,
                    }
                ],
            }
        )
        invoice.insert()
        invoice.submit()

        self.assertEqual(flt(invoice.total), 100)
        self.assertEqual(flt(invoice.total_taxes), 10)
        self.assertEqual(flt(invoice.grand_total), 110)

        gl_rows = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Sales Invoice", "voucher_no": invoice.name, "is_cancelled": 0},
            fields=["account", "debit", "credit", "party", "party_type"],
        )

        self.assertEqual(sum(flt(row.debit) for row in gl_rows), sum(flt(row.credit) for row in gl_rows))
        self.assertTrue(
            any(
                row.account == ctx["receivable"].name
                and row.party_type == "Account Holder"
                and row.party == ctx["ah_primary"].name
                and flt(row.debit) == 110
                for row in gl_rows
            )
        )

    def test_inclusive_tax_keeps_grand_total_constant_and_balanced(self):
        ctx = self._base_context()
        offering = self.make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "organization": ctx["org"].name,
                "account_holder": ctx["ah_primary"].name,
                "posting_date": nowdate(),
                "items": [
                    {
                        "billable_offering": offering.name,
                        "charge_source": "Extra",
                        "qty": 1,
                        "rate": 100,
                        "income_account": ctx["income"].name,
                    }
                ],
                "taxes": [
                    {
                        "account_head": ctx["tax"].name,
                        "rate": 10,
                        "included_in_print_rate": 1,
                    }
                ],
            }
        )
        invoice.insert()
        invoice.submit()

        self.assertAlmostEqual(flt(invoice.grand_total), 100, places=6)
        self.assertAlmostEqual(flt(invoice.total_taxes), 100 - (100 / 1.1), places=6)

        gl_rows = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Sales Invoice", "voucher_no": invoice.name, "is_cancelled": 0},
            fields=["debit", "credit"],
        )
        self.assertEqual(sum(flt(row.debit) for row in gl_rows), sum(flt(row.credit) for row in gl_rows))

    def test_submitted_invoice_is_immutable_for_amount_lines(self):
        ctx = self._base_context()
        offering = self.make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "organization": ctx["org"].name,
                "account_holder": ctx["ah_primary"].name,
                "posting_date": nowdate(),
                "items": [
                    {
                        "billable_offering": offering.name,
                        "charge_source": "Extra",
                        "qty": 1,
                        "rate": 100,
                        "income_account": ctx["income"].name,
                    }
                ],
            }
        )
        invoice.insert()
        invoice.submit()

        invoice.reload()
        invoice.items[0].rate = 120
        with self.assertRaises(frappe.ValidationError):
            invoice.save()

    def test_invoice_gl_never_uses_student_as_ledger_party(self):
        ctx = self._base_context()
        student = self.make_student(
            organization=ctx["org"].name,
            account_holder=ctx["ah_primary"].name,
            school=ctx["school"].name,
            prefix="Analytic",
        )
        offering = self.make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="Program",
            pricing_mode="Fixed",
        )
        program_offering = self.make_program_offering(ctx["org"].name, school=ctx["school"].name)

        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "organization": ctx["org"].name,
                "account_holder": ctx["ah_primary"].name,
                "posting_date": nowdate(),
                "program_offering": program_offering.name,
                "items": [
                    {
                        "billable_offering": offering.name,
                        "charge_source": "Program Offering",
                        "program_offering": program_offering.name,
                        "student": student.name,
                        "qty": 1,
                        "rate": 100,
                        "income_account": ctx["income"].name,
                    }
                ],
            }
        )
        invoice.insert()
        invoice.submit()

        gl_rows = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Sales Invoice", "voucher_no": invoice.name, "is_cancelled": 0},
            fields=["account", "party_type", "party", "debit", "credit"],
        )

        self.assertTrue(
            any(
                row.account == ctx["receivable"].name
                and row.party_type == "Account Holder"
                and row.party == ctx["ah_primary"].name
                and flt(row.debit) == 100
                for row in gl_rows
            )
        )
        self.assertFalse(any(row.party_type == "Student" for row in gl_rows))
        self.assertFalse(any(row.party == student.name for row in gl_rows))

    def test_cross_organization_billable_offering_is_rejected(self):
        ctx = self._base_context()
        other_org = self.make_organization("SI Other")
        other_income = self.make_account(
            organization=other_org.name,
            root_type="Income",
            prefix="Other Income",
        )
        other_offering = self.make_billable_offering(
            organization=other_org.name,
            income_account=other_income.name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Sales Invoice",
                    "organization": ctx["org"].name,
                    "account_holder": ctx["ah_primary"].name,
                    "posting_date": nowdate(),
                    "items": [
                        {
                            "billable_offering": other_offering.name,
                            "charge_source": "Extra",
                            "qty": 1,
                            "rate": 10,
                            "income_account": ctx["income"].name,
                        }
                    ],
                }
            ).insert()
