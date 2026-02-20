# ifitwala_ed/accounting/tests/factories.py

from __future__ import annotations

import frappe
from frappe.utils import nowdate


def make_organization(prefix: str = "Org"):
    org = frappe.get_doc(
        {
            "doctype": "Organization",
            "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "abbr": f"O{frappe.generate_hash(length=4)}",
        }
    )
    org.insert()
    return org


def make_school(organization: str, prefix: str = "School"):
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
    organization: str,
    root_type: str,
    account_type: str | None = None,
    is_group: int = 0,
    parent_account: str | None = None,
    prefix: str = "Account",
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
    organization: str,
    receivable_account: str,
    advance_account: str,
    cash_account: str | None = None,
    bank_account: str | None = None,
    tax_payable_account: str | None = None,
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


def make_account_holder(organization: str, holder_type: str = "Individual", prefix: str = "Account Holder"):
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


def make_billable_offering(
    organization: str,
    income_account: str,
    offering_type: str = "One-off Fee",
    pricing_mode: str = "Fixed",
):
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


def make_student(organization: str, account_holder: str, school: str | None = None, prefix: str = "Student"):
    school_name = school or make_school(organization).name
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


def make_program_offering(organization: str, school: str | None = None):
    school_name = school or make_school(organization).name
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
        }
    )
    offering.insert()
    return offering


def make_sales_invoice(
    organization: str,
    account_holder: str,
    items: list[dict],
    posting_date: str | None = None,
    taxes: list[dict] | None = None,
    taxes_and_charges: str | None = None,
    program_offering: str | None = None,
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
