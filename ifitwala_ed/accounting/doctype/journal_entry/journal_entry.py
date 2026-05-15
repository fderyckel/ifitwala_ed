import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.accounting.ledger_utils import cancel_gl_entries, make_gl_entries, validate_posting_date
from ifitwala_ed.accounting.receivables import is_zero, money


class JournalEntry(Document):
    def validate(self):
        self.validate_accounts()
        self.set_totals()
        validate_posting_date(self.organization, self.posting_date)

    def validate_accounts(self):
        if not self.accounts:
            frappe.throw(_("Accounts table is required"))
        for row in self.accounts:
            if not row.account:
                frappe.throw(_("Account is required for each row"))
            account = frappe.db.get_value("Account", row.account, ["organization", "is_group"], as_dict=True)
            if not account:
                frappe.throw(_("Account not found"))
            if account.organization != self.organization:
                frappe.throw(_("Account must belong to the same Organization"))
            if account.is_group:
                frappe.throw(_("Cannot post to a group account"))

            row_debit = money(row.debit)
            row_credit = money(row.credit)
            if row_debit and row_credit:
                frappe.throw(_("Debit and Credit cannot both be non-zero on the same row"))
            if is_zero(row_debit) and is_zero(row_credit):
                frappe.throw(_("Either Debit or Credit is required on each row"))

    def set_totals(self):
        self.total_debit = money(sum(money(row.debit) for row in self.accounts))
        self.total_credit = money(sum(money(row.credit) for row in self.accounts))
        if not is_zero(self.total_debit - self.total_credit):
            frappe.throw(_("Total Debit must equal Total Credit"))

    def on_submit(self):
        entries = []
        for row in self.accounts:
            entries.append(
                {
                    "organization": self.organization,
                    "posting_date": self.posting_date,
                    "account": row.account,
                    "party_type": row.party_type,
                    "party": row.party,
                    "against": None,
                    "remarks": self.remark,
                    "debit": row.debit,
                    "credit": row.credit,
                    "school": row.school,
                    "program": row.program,
                    "program_offering": row.program_offering,
                    "student": row.student,
                }
            )
        make_gl_entries(entries, "Journal Entry", self.name)

    def on_cancel(self):
        cancel_gl_entries("Journal Entry", self.name)
