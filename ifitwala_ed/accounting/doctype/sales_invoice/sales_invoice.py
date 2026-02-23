import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.accounting.ledger_utils import cancel_gl_entries, make_gl_entries, validate_posting_date


class SalesInvoice(Document):
    def validate(self):
        self.validate_account_holder()
        self.validate_items()
        self.set_item_amounts()
        self.apply_tax_template_if_needed()
        self.validate_taxes()
        self.set_totals()
        validate_posting_date(self.organization, self.posting_date)

    def validate_account_holder(self):
        account_holder_org = frappe.db.get_value("Account Holder", self.account_holder, "organization")
        if account_holder_org and account_holder_org != self.organization:
            frappe.throw(_("Account Holder must belong to the same Organization"))

    def validate_items(self):
        if not self.items:
            frappe.throw(_("At least one item is required"))

        header_program_offering = self.program_offering
        header_program_org = None
        if header_program_offering:
            header_program_org = self._get_program_offering_org(header_program_offering)
            if header_program_org and header_program_org != self.organization:
                frappe.throw(_("Program Offering must belong to the same Organization"))

        offering_cache = {}
        program_org_cache = {}
        student_cache = {}

        for idx, row in enumerate(self.items, start=1):
            if flt(row.qty) <= 0:
                frappe.throw(_("Row {0}: Qty must be greater than zero").format(idx))
            if row.rate is None:
                frappe.throw(_("Row {0}: Rate is required").format(idx))
            if flt(row.rate) < 0:
                frappe.throw(_("Row {0}: Rate cannot be negative").format(idx))

            if not row.charge_source:
                if not row.billable_offering:
                    row.charge_source = "Manual"
                elif row.program_offering or header_program_offering:
                    row.charge_source = "Program Offering"
                else:
                    row.charge_source = "Extra"

            if row.charge_source == "Program Offering" and not row.program_offering and header_program_offering:
                row.program_offering = header_program_offering

            if row.program_offering and header_program_offering and row.program_offering != header_program_offering:
                frappe.throw(_("Row {0}: Program Offering must match the invoice header").format(idx))

            if row.charge_source == "Program Offering" and not row.program_offering:
                frappe.throw(_("Row {0}: Program Offering is required for Program Offering charges").format(idx))

            if row.program_offering:
                program_org = program_org_cache.get(row.program_offering)
                if program_org is None:
                    program_org = self._get_program_offering_org(row.program_offering)
                    program_org_cache[row.program_offering] = program_org
                if program_org and program_org != self.organization:
                    frappe.throw(_("Row {0}: Program Offering must belong to the same Organization").format(idx))

            if row.billable_offering:
                offering = offering_cache.get(row.billable_offering)
                if not offering:
                    offering = frappe.db.get_value(
                        "Billable Offering",
                        row.billable_offering,
                        ["organization", "income_account", "disabled", "offering_type"],
                        as_dict=True,
                    )
                    if not offering:
                        frappe.throw(_("Row {0}: Billable Offering not found").format(idx))
                    offering_cache[row.billable_offering] = offering
                if offering.disabled:
                    frappe.throw(_("Row {0}: Billable Offering is disabled").format(idx))
                if offering.organization != self.organization:
                    frappe.throw(_("Row {0}: Billable Offering must belong to the same Organization").format(idx))
                if not row.income_account:
                    row.income_account = offering.income_account
                if offering.offering_type == "Program" and not row.student:
                    frappe.throw(_("Row {0}: Student is required for Program tuition lines").format(idx))
            else:
                if row.charge_source != "Manual":
                    frappe.throw(_("Row {0}: Billable Offering is required unless Charge Source is Manual").format(idx))
                if not row.income_account:
                    frappe.throw(_("Row {0}: Income Account is required for manual lines").format(idx))

            account = frappe.db.get_value(
                "Account", row.income_account, ["organization", "is_group", "root_type"], as_dict=True
            )
            if not account:
                frappe.throw(_("Row {0}: Income account not found").format(idx))
            if account.organization != self.organization:
                frappe.throw(_("Row {0}: Income account must belong to the same Organization").format(idx))
            if account.is_group:
                frappe.throw(_("Row {0}: Cannot post to a group income account").format(idx))
            if account.root_type != "Income":
                frappe.throw(_("Row {0}: Income account must have Root Type 'Income'").format(idx))

            if row.student:
                student = student_cache.get(row.student)
                if not student:
                    student = frappe.db.get_value(
                        "Student", row.student, ["anchor_school", "account_holder"], as_dict=True
                    )
                    if not student:
                        frappe.throw(_("Row {0}: Student not found").format(idx))
                    student_cache[row.student] = student
                if not student.anchor_school:
                    frappe.throw(_("Row {0}: Student is missing Anchor School for organization validation").format(idx))
                student_org = get_school_organization(student.anchor_school)
                if student_org and student_org != self.organization:
                    frappe.throw(_("Row {0}: Student must belong to the same Organization").format(idx))
                if not student.account_holder:
                    frappe.throw(_("Row {0}: Student is missing an Account Holder").format(idx))
                if student.account_holder != self.account_holder:
                    frappe.throw(_("Row {0}: Student Account Holder must match the invoice Account Holder").format(idx))

    def _get_program_offering_org(self, program_offering):
        school = frappe.db.get_value("Program Offering", program_offering, "school")
        if not school:
            frappe.throw(_("Program Offering {0} is missing School").format(program_offering))
        return get_school_organization(school)

    def set_item_amounts(self):
        for row in self.items:
            row.amount = flt(row.qty) * flt(row.rate)

    def validate_taxes(self):
        for tax in self.taxes:
            if not tax.account_head:
                frappe.throw(_("Tax account is required on each tax row"))
            account = frappe.db.get_value(
                "Account", tax.account_head, ["organization", "is_group", "root_type"], as_dict=True
            )
            if not account:
                frappe.throw(_("Tax account not found"))
            if account.organization != self.organization:
                frappe.throw(_("Tax account must belong to the same Organization"))
            if account.is_group:
                frappe.throw(_("Cannot post to a group tax account"))
            if account.root_type != "Liability":
                frappe.throw(_("Tax account must have Root Type 'Liability'"))

    def apply_tax_template_if_needed(self):
        if self.taxes:
            return
        if not self.taxes_and_charges:
            return

        template = frappe.get_doc("Sales Taxes and Charges Template", self.taxes_and_charges)
        if template.organization != self.organization:
            frappe.throw(_("Tax Template must belong to the same Organization"))
        self.taxes = []
        for row in template.taxes:
            self.append(
                "taxes",
                {
                    "description": row.description,
                    "account_head": row.account_head,
                    "rate": row.rate,
                    "included_in_print_rate": row.included_in_print_rate,
                },
            )

    def set_totals(self):
        self.total = sum(flt(row.amount) for row in self.items)
        if self.total <= 0:
            frappe.throw(_("Invoice total must be greater than zero"))

        total_taxes = 0
        inclusive_taxes = 0
        for tax in self.taxes:
            rate = flt(tax.rate)
            if rate == 0:
                tax.tax_amount = 0
                continue
            if tax.included_in_print_rate:
                tax_amount = self.total - (self.total / (1 + rate / 100))
                inclusive_taxes += tax_amount
            else:
                tax_amount = self.total * (rate / 100)
            tax.tax_amount = tax_amount
            total_taxes += tax_amount

        self.total_taxes = total_taxes
        if inclusive_taxes > self.total:
            frappe.throw(_("Inclusive tax exceeds invoice total"))
        self.grand_total = self.total + (total_taxes - inclusive_taxes)
        if self.docstatus == 0:
            self.outstanding_amount = self.grand_total

    def on_submit(self):
        settings = frappe.get_doc("Accounts Settings", self.organization)
        ar_account = settings.default_receivable_account
        if not ar_account:
            frappe.throw(_("Default Accounts Receivable account is required"))

        entries = [
            {
                "organization": self.organization,
                "posting_date": self.posting_date,
                "account": ar_account,
                "party_type": "Account Holder",
                "party": self.account_holder,
                "against": ", ".join({row.income_account for row in self.items}),
                "remarks": self.remarks,
                "debit": self.grand_total,
                "credit": 0,
            }
        ]

        inclusive_tax_total = sum(flt(tax.tax_amount) for tax in self.taxes if tax.included_in_print_rate)
        income_total = self.total - inclusive_tax_total

        if inclusive_tax_total:
            allocated_income = 0
            item_count = len(self.items)
            for index, row in enumerate(self.items):
                if index == item_count - 1:
                    income_credit = income_total - allocated_income
                else:
                    income_credit = flt(income_total * flt(row.amount) / self.total)
                    allocated_income += income_credit

                if flt(income_credit) == 0:
                    continue

                entries.append(
                    {
                        "organization": self.organization,
                        "posting_date": self.posting_date,
                        "account": row.income_account,
                        "party_type": None,
                        "party": None,
                        "against": ar_account,
                        "remarks": self.remarks,
                        "debit": 0,
                        "credit": income_credit,
                    }
                )
        else:
            for row in self.items:
                entries.append(
                    {
                        "organization": self.organization,
                        "posting_date": self.posting_date,
                        "account": row.income_account,
                        "party_type": None,
                        "party": None,
                        "against": ar_account,
                        "remarks": self.remarks,
                        "debit": 0,
                        "credit": row.amount,
                    }
                )

        for tax in self.taxes:
            if flt(tax.tax_amount) == 0:
                continue
            entries.append(
                {
                    "organization": self.organization,
                    "posting_date": self.posting_date,
                    "account": tax.account_head,
                    "party_type": None,
                    "party": None,
                    "against": ar_account,
                    "remarks": self.remarks,
                    "debit": 0,
                    "credit": tax.tax_amount,
                }
            )

        make_gl_entries(entries, "Sales Invoice", self.name)

    def on_cancel(self):
        cancel_gl_entries("Sales Invoice", self.name)
        self.outstanding_amount = 0
