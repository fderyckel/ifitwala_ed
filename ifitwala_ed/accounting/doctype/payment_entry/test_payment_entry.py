# ifitwala_ed/accounting/doctype/payment_entry/test_payment_entry.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate


class TestPaymentEntry(FrappeTestCase):
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

    def make_sales_invoice(
        self,
        organization,
        account_holder,
        items,
        posting_date=None,
        taxes=None,
        taxes_and_charges=None,
        program_offering=None,
    ):
        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "organization": organization,
                "account_holder": account_holder,
                "posting_date": posting_date or nowdate(),
                "items": items,
                "taxes": taxes or [],
                "taxes_and_charges": taxes_and_charges,
                "program_offering": program_offering,
            }
        )
        invoice.insert()
        return invoice

    def _base_context(self):
        org = self.make_organization("PE")
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
        bank = self.make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Bank",
            prefix="Bank",
        )
        income = self.make_account(
            organization=org.name,
            root_type="Income",
            prefix="Income",
        )

        self.make_accounts_settings(
            organization=org.name,
            receivable_account=receivable.name,
            advance_account=advance.name,
            bank_account=bank.name,
        )

        account_holder = self.make_account_holder(org.name)
        offering = self.make_billable_offering(
            organization=org.name,
            income_account=income.name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        invoice = self.make_sales_invoice(
            organization=org.name,
            account_holder=account_holder.name,
            posting_date=nowdate(),
            items=[
                {
                    "billable_offering": offering.name,
                    "charge_source": "Extra",
                    "qty": 1,
                    "rate": 120,
                    "income_account": income.name,
                }
            ],
        )
        invoice.submit()

        return {
            "org": org,
            "receivable": receivable,
            "advance": advance,
            "bank": bank,
            "income": income,
            "account_holder": account_holder,
            "invoice": invoice,
        }

    def test_allocated_amount_cannot_exceed_invoice_outstanding(self):
        ctx = self._base_context()

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Payment Entry",
                    "payment_type": "Receive",
                    "party_type": "Account Holder",
                    "party": ctx["account_holder"].name,
                    "organization": ctx["org"].name,
                    "posting_date": nowdate(),
                    "paid_to": ctx["bank"].name,
                    "paid_amount": 100,
                    "references": [
                        {
                            "reference_doctype": "Sales Invoice",
                            "reference_name": ctx["invoice"].name,
                            "allocated_amount": 121,
                        }
                    ],
                }
            ).insert()

    def test_unallocated_amount_posts_to_advance_liability(self):
        ctx = self._base_context()

        pe = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "payment_type": "Receive",
                "party_type": "Account Holder",
                "party": ctx["account_holder"].name,
                "organization": ctx["org"].name,
                "posting_date": nowdate(),
                "paid_to": ctx["bank"].name,
                "paid_amount": 200,
                "references": [
                    {
                        "reference_doctype": "Sales Invoice",
                        "reference_name": ctx["invoice"].name,
                        "allocated_amount": 120,
                    }
                ],
            }
        )
        pe.insert()
        pe.submit()

        self.assertEqual(flt(pe.unallocated_amount), 80)

        gl_rows = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Payment Entry", "voucher_no": pe.name, "is_cancelled": 0},
            fields=["account", "party", "debit", "credit"],
        )

        self.assertEqual(sum(flt(row.debit) for row in gl_rows), sum(flt(row.credit) for row in gl_rows))
        self.assertEqual(
            sum(flt(row.credit) for row in gl_rows if row.account == ctx["receivable"].name),
            120,
        )
        self.assertTrue(
            any(
                row.account == ctx["advance"].name and row.party == ctx["account_holder"].name and flt(row.credit) == 80
                for row in gl_rows
            )
        )

        outstanding = frappe.db.get_value("Sales Invoice", ctx["invoice"].name, "outstanding_amount")
        self.assertEqual(flt(outstanding), 0)

    def test_payment_reference_must_match_payment_account_holder(self):
        ctx = self._base_context()
        other_holder = self.make_account_holder(ctx["org"].name, prefix="Other")
        offering = self.make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="Product",
            pricing_mode="Fixed",
        )
        other_invoice = self.make_sales_invoice(
            organization=ctx["org"].name,
            account_holder=other_holder.name,
            posting_date=nowdate(),
            items=[
                {
                    "billable_offering": offering.name,
                    "charge_source": "Extra",
                    "qty": 1,
                    "rate": 30,
                    "income_account": ctx["income"].name,
                }
            ],
        )
        other_invoice.submit()

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Payment Entry",
                    "payment_type": "Receive",
                    "party_type": "Account Holder",
                    "party": ctx["account_holder"].name,
                    "organization": ctx["org"].name,
                    "posting_date": nowdate(),
                    "paid_to": ctx["bank"].name,
                    "paid_amount": 30,
                    "references": [
                        {
                            "reference_doctype": "Sales Invoice",
                            "reference_name": other_invoice.name,
                            "allocated_amount": 30,
                        }
                    ],
                }
            ).insert()
