# ifitwala_ed/accounting/doctype/fiscal_year/test_fiscal_year.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.fiscal_year_utils import (
    fill_date_range_from_fiscal_year,
    get_fiscal_year_date_range,
    resolve_fiscal_year,
)
from ifitwala_ed.accounting.ledger_utils import validate_posting_date


class TestFiscalYear(FrappeTestCase):
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

    def make_fiscal_year(
        self,
        organization,
        year="2026",
        year_start_date="2026-01-01",
        year_end_date="2026-12-31",
        is_short_year=0,
    ):
        doc = frappe.get_doc(
            {
                "doctype": "Fiscal Year",
                "year": year,
                "year_start_date": year_start_date,
                "year_end_date": year_end_date,
                "is_short_year": is_short_year,
                "organizations": [{"organization": organization}],
            }
        )
        doc.insert()
        return doc

    def test_requires_at_least_one_organization(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Fiscal Year",
                    "year": f"FY {frappe.generate_hash(length=4)}",
                    "year_start_date": "2026-01-01",
                    "year_end_date": "2026-12-31",
                }
            ).insert()

    def test_full_year_must_span_exact_year(self):
        org = self.make_organization("FY Dates")

        with self.assertRaises(frappe.ValidationError):
            self.make_fiscal_year(
                organization=org.name,
                year=f"FY {frappe.generate_hash(length=4)}",
                year_start_date="2026-01-01",
                year_end_date="2026-11-30",
            )

    def test_short_year_allows_non_standard_range(self):
        org = self.make_organization("FY Short")
        doc = self.make_fiscal_year(
            organization=org.name,
            year=f"FY {frappe.generate_hash(length=4)}",
            year_start_date="2026-01-01",
            year_end_date="2026-06-30",
            is_short_year=1,
        )
        self.assertEqual(doc.is_short_year, 1)

    def test_overlap_blocked_within_same_organization(self):
        org = self.make_organization("FY Overlap")
        self.make_fiscal_year(org.name, year=f"FY A {frappe.generate_hash(length=4)}")

        with self.assertRaises(frappe.ValidationError):
            self.make_fiscal_year(
                organization=org.name,
                year=f"FY B {frappe.generate_hash(length=4)}",
                year_start_date="2026-06-01",
                year_end_date="2027-05-31",
                is_short_year=1,
            )

    def test_overlap_allowed_across_different_organizations(self):
        org_a = self.make_organization("FY A")
        org_b = self.make_organization("FY B")
        self.make_fiscal_year(org_a.name, year=f"FY A {frappe.generate_hash(length=4)}")
        doc = self.make_fiscal_year(org_b.name, year=f"FY B {frappe.generate_hash(length=4)}")
        self.assertEqual(doc.organizations[0].organization, org_b.name)

    def test_resolve_fiscal_year_by_posting_date(self):
        org = self.make_organization("FY Resolve")
        fiscal_year = self.make_fiscal_year(org.name, year=f"FY {frappe.generate_hash(length=4)}")

        resolved = resolve_fiscal_year(org.name, "2026-04-10")
        self.assertEqual(resolved.get("name"), fiscal_year.name)

        date_range = get_fiscal_year_date_range(org.name, fiscal_year.name)
        self.assertEqual(str(date_range["from_date"]), "2026-01-01")
        self.assertEqual(str(date_range["to_date"]), "2026-12-31")

        filled_from_date, filled_to_date = fill_date_range_from_fiscal_year(
            {"organization": org.name, "fiscal_year": fiscal_year.name}
        )
        self.assertEqual(str(filled_from_date), "2026-01-01")
        self.assertEqual(str(filled_to_date), "2026-12-31")

        validate_posting_date(org.name, "2026-04-10")

    def test_missing_fiscal_year_blocks_resolution(self):
        org = self.make_organization("FY Missing")

        with self.assertRaises(frappe.ValidationError):
            resolve_fiscal_year(org.name, "2026-04-10")
