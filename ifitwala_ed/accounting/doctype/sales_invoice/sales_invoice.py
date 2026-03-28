# ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.accounting.ledger_utils import cancel_gl_entries, make_gl_entries, validate_posting_date
from ifitwala_ed.accounting.receivables import (
    apply_invoice_dimensions,
    clamp_money,
    compute_cash_paid_amount,
    get_submitted_credit_note_total,
    is_zero,
    money,
    persist_submitted_invoice_runtime_state,
    resolve_program_offering_dimensions,
    resolve_student_school,
    set_payment_schedule_from_template,
    sync_dunning_notices_for_invoice,
    sync_invoice_runtime_state,
    sync_payment_requests_for_invoice,
)


class SalesInvoice(Document):
    def validate(self):
        self.validate_account_holder()
        self.validate_adjustment_context()
        self.validate_items()
        self.set_item_amounts()
        self.apply_tax_template_if_needed()
        self.validate_taxes()
        self.set_totals()
        self.validate_adjustment_amount()
        set_payment_schedule_from_template(self)
        apply_invoice_dimensions(self)
        sync_invoice_runtime_state(self)
        self.credit_note_total = get_submitted_credit_note_total(self.name) if self.name else 0
        self.paid_amount = compute_cash_paid_amount(self) if self.name else 0
        validate_posting_date(self.organization, self.posting_date)

    def validate_account_holder(self):
        account_holder_org = frappe.db.get_value("Account Holder", self.account_holder, "organization")
        if account_holder_org and account_holder_org != self.organization:
            frappe.throw(_("Account Holder must belong to the same Organization"))

    def validate_adjustment_context(self):
        if self.against_sales_invoice and not self.adjustment_type:
            frappe.throw(_("Adjustment Type is required when Against Sales Invoice is set."))
        if self.adjustment_type and not self.against_sales_invoice:
            frappe.throw(_("Against Sales Invoice is required when Adjustment Type is set."))

        if not self.against_sales_invoice:
            return

        invoice = frappe.db.get_value(
            "Sales Invoice",
            self.against_sales_invoice,
            ["organization", "account_holder", "docstatus", "adjustment_type", "outstanding_amount"],
            as_dict=True,
        )
        if not invoice:
            frappe.throw(
                _("Against Sales Invoice {sales_invoice} not found.").format(sales_invoice=self.against_sales_invoice)
            )
        if invoice.docstatus != 1:
            frappe.throw(_("Against Sales Invoice must be submitted."))
        if invoice.organization != self.organization:
            frappe.throw(_("Against Sales Invoice must belong to the same Organization."))
        if invoice.account_holder != self.account_holder:
            frappe.throw(_("Against Sales Invoice must belong to the same Account Holder."))
        if invoice.adjustment_type == "Credit Note":
            frappe.throw(_("You cannot create an adjustment against a credit note."))

    def validate_items(self):
        if not self.items:
            frappe.throw(_("At least one item is required"))

        is_credit_note = self.adjustment_type == "Credit Note"
        header_program_offering = self.program_offering
        if header_program_offering:
            header_dimensions = resolve_program_offering_dimensions(header_program_offering)
            header_program_org = self._get_program_offering_org(header_program_offering)
            if header_program_org and header_program_org != self.organization:
                frappe.throw(_("Program Offering must belong to the same Organization"))
            self.school = header_dimensions.school
            self.program = header_dimensions.program

        offering_cache = {}
        program_org_cache = {}
        student_cache = {}

        for idx, row in enumerate(self.items, start=1):
            qty = flt(row.qty)
            if is_zero(qty):
                frappe.throw(_("Row {row_number}: Qty cannot be zero").format(row_number=idx))
            if is_credit_note and qty >= 0:
                frappe.throw(_("Row {row_number}: Credit note rows must use negative Qty").format(row_number=idx))
            if not is_credit_note and qty <= 0:
                frappe.throw(_("Row {row_number}: Qty must be greater than zero").format(row_number=idx))

            if row.rate is None:
                frappe.throw(_("Row {row_number}: Rate is required").format(row_number=idx))
            if flt(row.rate) < 0:
                frappe.throw(_("Row {row_number}: Rate cannot be negative").format(row_number=idx))

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
                frappe.throw(
                    _("Row {row_number}: Program Offering must match the invoice header").format(row_number=idx)
                )

            if row.charge_source == "Program Offering" and not row.program_offering:
                frappe.throw(
                    _("Row {row_number}: Program Offering is required for Program Offering charges").format(
                        row_number=idx
                    )
                )

            if row.program_offering:
                program_org = program_org_cache.get(row.program_offering)
                if program_org is None:
                    program_org = self._get_program_offering_org(row.program_offering)
                    program_org_cache[row.program_offering] = program_org
                if program_org and program_org != self.organization:
                    frappe.throw(
                        _("Row {row_number}: Program Offering must belong to the same Organization").format(
                            row_number=idx
                        )
                    )
                dimensions = resolve_program_offering_dimensions(row.program_offering)
                row.school = dimensions.school
                row.program = dimensions.program

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
                        frappe.throw(_("Row {row_number}: Billable Offering not found").format(row_number=idx))
                    offering_cache[row.billable_offering] = offering
                if offering.disabled:
                    frappe.throw(_("Row {row_number}: Billable Offering is disabled").format(row_number=idx))
                if offering.organization != self.organization:
                    frappe.throw(
                        _("Row {row_number}: Billable Offering must belong to the same Organization").format(
                            row_number=idx
                        )
                    )
                if not row.income_account:
                    row.income_account = offering.income_account
                if offering.offering_type == "Program" and not row.student:
                    frappe.throw(
                        _("Row {row_number}: Student is required for Program tuition lines").format(row_number=idx)
                    )
            else:
                if row.charge_source != "Manual":
                    frappe.throw(
                        _("Row {row_number}: Billable Offering is required unless Charge Source is Manual").format(
                            row_number=idx
                        )
                    )
                if not row.income_account:
                    frappe.throw(
                        _("Row {row_number}: Income Account is required for manual lines").format(row_number=idx)
                    )

            if is_zero(flt(row.rate)) and not row.description:
                frappe.throw(_("Row {row_number}: Description is required for zero-rate lines").format(row_number=idx))

            account = frappe.db.get_value(
                "Account", row.income_account, ["organization", "is_group", "root_type"], as_dict=True
            )
            if not account:
                frappe.throw(_("Row {row_number}: Income account not found").format(row_number=idx))
            if account.organization != self.organization:
                frappe.throw(
                    _("Row {row_number}: Income account must belong to the same Organization").format(row_number=idx)
                )
            if account.is_group:
                frappe.throw(_("Row {row_number}: Cannot post to a group income account").format(row_number=idx))
            if account.root_type != "Income":
                frappe.throw(_("Row {row_number}: Income account must have Root Type 'Income'").format(row_number=idx))

            if row.student:
                student = student_cache.get(row.student)
                if not student:
                    student = frappe.db.get_value(
                        "Student", row.student, ["anchor_school", "account_holder"], as_dict=True
                    )
                    if not student:
                        frappe.throw(_("Row {row_number}: Student not found").format(row_number=idx))
                    student_cache[row.student] = student
                if not student.anchor_school:
                    frappe.throw(
                        _("Row {row_number}: Student is missing Anchor School for organization validation").format(
                            row_number=idx
                        )
                    )
                student_org = get_school_organization(student.anchor_school)
                if student_org and student_org != self.organization:
                    frappe.throw(
                        _("Row {row_number}: Student must belong to the same Organization").format(row_number=idx)
                    )
                if not student.account_holder:
                    frappe.throw(_("Row {row_number}: Student is missing an Account Holder").format(row_number=idx))
                if student.account_holder != self.account_holder:
                    frappe.throw(
                        _("Row {row_number}: Student Account Holder must match the invoice Account Holder").format(
                            row_number=idx
                        )
                    )
                if not row.school:
                    row.school = resolve_student_school(row.student)

    def _get_program_offering_org(self, program_offering):
        school = frappe.db.get_value("Program Offering", program_offering, "school")
        if not school:
            frappe.throw(
                _("Program Offering {program_offering} is missing School").format(program_offering=program_offering)
            )
        return get_school_organization(school)

    def set_item_amounts(self):
        for row in self.items:
            row.amount = money(flt(row.qty) * flt(row.rate))

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
        self.total = money(sum(flt(row.amount) for row in self.items))
        if is_zero(self.total):
            frappe.throw(_("Invoice total cannot be zero"))

        total_taxes = 0.0
        inclusive_taxes = 0.0
        sign = -1 if self.total < 0 else 1
        total_abs = abs(self.total)
        for tax in self.taxes:
            rate = flt(tax.rate)
            if is_zero(rate):
                tax.tax_amount = 0
                continue
            if tax.included_in_print_rate:
                tax_amount_abs = total_abs - (total_abs / (1 + rate / 100))
                tax_amount = money(sign * tax_amount_abs)
                inclusive_taxes = money(inclusive_taxes + tax_amount)
            else:
                tax_amount = money(self.total * (rate / 100))
            tax.tax_amount = tax_amount
            total_taxes = money(total_taxes + tax_amount)

        self.total_taxes = total_taxes
        if abs(inclusive_taxes) > abs(self.total):
            frappe.throw(_("Inclusive tax exceeds invoice total"))
        self.grand_total = money(self.total + (total_taxes - inclusive_taxes))

        if self.docstatus == 0:
            if self.adjustment_type == "Credit Note" or self.grand_total < 0:
                self.outstanding_amount = 0
            else:
                self.outstanding_amount = money(self.grand_total)

    def validate_adjustment_amount(self):
        if self.adjustment_type == "Credit Note":
            if self.grand_total >= 0:
                frappe.throw(_("Credit notes must result in a negative grand total."))
            if self.payment_terms_template:
                frappe.throw(_("Credit notes cannot use a Payment Terms Template."))
            source_outstanding = money(
                frappe.db.get_value("Sales Invoice", self.against_sales_invoice, "outstanding_amount") or 0
            )
            if abs(self.grand_total) > source_outstanding and not is_zero(abs(self.grand_total) - source_outstanding):
                frappe.throw(_("Credit note amount cannot exceed the outstanding amount on the source invoice."))
        elif self.adjustment_type == "Debit Note" and self.grand_total <= 0:
            frappe.throw(_("Debit notes must result in a positive grand total."))

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
                "against": ", ".join(sorted({row.income_account for row in self.items if row.income_account})),
                "remarks": self.remarks,
                "debit": money(self.grand_total) if self.grand_total > 0 else 0,
                "credit": abs(money(self.grand_total)) if self.grand_total < 0 else 0,
                "school": self.school,
                "program": self.program,
                "program_offering": self.program_offering,
            }
        ]

        inclusive_tax_total = money(sum(flt(tax.tax_amount) for tax in self.taxes if tax.included_in_print_rate))
        income_total = money(self.total - inclusive_tax_total)

        if not is_zero(inclusive_tax_total):
            allocated_income = 0.0
            base_total = abs(self.total)
            item_count = len(self.items)
            for index, row in enumerate(self.items):
                if index == item_count - 1:
                    signed_income_amount = money(income_total - allocated_income)
                else:
                    proportion = abs(flt(row.amount)) / base_total if base_total else 0
                    signed_income_amount = money(income_total * proportion)
                    allocated_income = money(allocated_income + signed_income_amount)

                if is_zero(signed_income_amount):
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
                        "debit": abs(signed_income_amount) if signed_income_amount < 0 else 0,
                        "credit": signed_income_amount if signed_income_amount > 0 else 0,
                        "school": row.school,
                        "program": row.program,
                        "program_offering": row.program_offering,
                        "student": row.student,
                    }
                )
        else:
            for row in self.items:
                signed_amount = money(row.amount)
                entries.append(
                    {
                        "organization": self.organization,
                        "posting_date": self.posting_date,
                        "account": row.income_account,
                        "party_type": None,
                        "party": None,
                        "against": ar_account,
                        "remarks": self.remarks,
                        "debit": abs(signed_amount) if signed_amount < 0 else 0,
                        "credit": signed_amount if signed_amount > 0 else 0,
                        "school": row.school,
                        "program": row.program,
                        "program_offering": row.program_offering,
                        "student": row.student,
                    }
                )

        for tax in self.taxes:
            signed_amount = money(tax.tax_amount)
            if is_zero(signed_amount):
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
                    "debit": abs(signed_amount) if signed_amount < 0 else 0,
                    "credit": signed_amount if signed_amount > 0 else 0,
                    "school": self.school,
                    "program": self.program,
                    "program_offering": self.program_offering,
                }
            )

        make_gl_entries(entries, "Sales Invoice", self.name)

        if self.adjustment_type == "Credit Note":
            self._apply_credit_note_to_source()

        persist_submitted_invoice_runtime_state(self.name)
        if self.against_sales_invoice:
            persist_submitted_invoice_runtime_state(self.against_sales_invoice)

    def on_cancel(self):
        self._validate_no_settlements_before_cancel()
        cancel_gl_entries("Sales Invoice", self.name)

        if self.adjustment_type == "Credit Note" and self.against_sales_invoice:
            source_outstanding = money(
                frappe.db.get_value("Sales Invoice", self.against_sales_invoice, "outstanding_amount") or 0
            )
            restored_outstanding = money(source_outstanding + abs(self.grand_total))
            frappe.db.set_value("Sales Invoice", self.against_sales_invoice, "outstanding_amount", restored_outstanding)
            persist_submitted_invoice_runtime_state(self.against_sales_invoice)

        frappe.db.set_value(
            "Sales Invoice",
            self.name,
            {
                "outstanding_amount": 0,
                "paid_amount": 0,
                "status": "Cancelled",
            },
        )
        sync_payment_requests_for_invoice(self.name)
        sync_dunning_notices_for_invoice(self.name)

    def _apply_credit_note_to_source(self):
        if not self.against_sales_invoice:
            return
        source_outstanding = money(
            frappe.db.get_value("Sales Invoice", self.against_sales_invoice, "outstanding_amount") or 0
        )
        new_outstanding = clamp_money(source_outstanding - abs(self.grand_total))
        frappe.db.set_value("Sales Invoice", self.against_sales_invoice, "outstanding_amount", new_outstanding)

    def _validate_no_settlements_before_cancel(self):
        payment_refs = frappe.db.sql(
            """
            select per.reference_name
            from `tabPayment Entry Reference` per
            join `tabPayment Entry` pe on pe.name = per.parent
            where pe.docstatus = 1
              and per.reference_doctype = 'Sales Invoice'
              and per.reference_name = %s
              and per.allocated_amount > 0
            limit 1
            """,
            (self.name,),
        )
        if payment_refs:
            frappe.throw(_("Cancel linked Payment Entries before cancelling this invoice."))

        recon_refs = frappe.db.sql(
            """
            select pra.sales_invoice
            from `tabPayment Reconciliation Allocation` pra
            join `tabPayment Reconciliation` pr on pr.name = pra.parent
            where pr.docstatus = 1
              and pra.sales_invoice = %s
            limit 1
            """,
            (self.name,),
        )
        if recon_refs:
            frappe.throw(_("Cancel linked Payment Reconciliations before cancelling this invoice."))


def _copy_tax_rows(source_doc):
    return [
        {
            "description": row.description,
            "account_head": row.account_head,
            "rate": row.rate,
            "included_in_print_rate": row.included_in_print_rate,
        }
        for row in (source_doc.taxes or [])
    ]


@frappe.whitelist()
def make_credit_note(source_invoice: str) -> str:
    source = frappe.get_doc("Sales Invoice", source_invoice)
    if source.docstatus != 1:
        frappe.throw(_("Only submitted invoices can be credited."))

    doc = frappe.new_doc("Sales Invoice")
    doc.update(
        {
            "account_holder": source.account_holder,
            "organization": source.organization,
            "program_offering": source.program_offering,
            "posting_date": frappe.utils.today(),
            "adjustment_type": "Credit Note",
            "against_sales_invoice": source.name,
            "remarks": _("Credit note against {source_invoice}").format(source_invoice=source.name),
        }
    )
    for row in source.items or []:
        doc.append(
            "items",
            {
                "billable_offering": row.billable_offering,
                "program_offering": row.program_offering,
                "charge_source": row.charge_source,
                "description": row.description,
                "student": row.student,
                "qty": -abs(flt(row.qty)),
                "rate": row.rate,
                "income_account": row.income_account,
                "school": getattr(row, "school", None),
                "program": getattr(row, "program", None),
            },
        )
    for tax in _copy_tax_rows(source):
        doc.append("taxes", tax)
    doc.insert()
    return doc.name


@frappe.whitelist()
def make_debit_note(source_invoice: str) -> str:
    source = frappe.get_doc("Sales Invoice", source_invoice)
    if source.docstatus != 1:
        frappe.throw(_("Only submitted invoices can be used to create a debit note."))

    doc = frappe.new_doc("Sales Invoice")
    doc.update(
        {
            "account_holder": source.account_holder,
            "organization": source.organization,
            "program_offering": source.program_offering,
            "posting_date": frappe.utils.today(),
            "adjustment_type": "Debit Note",
            "against_sales_invoice": source.name,
            "taxes_and_charges": source.taxes_and_charges,
            "remarks": _("Debit note against {source_invoice}").format(source_invoice=source.name),
        }
    )
    for row in source.items or []:
        doc.append(
            "items",
            {
                "billable_offering": row.billable_offering,
                "program_offering": row.program_offering,
                "charge_source": row.charge_source,
                "description": row.description,
                "student": row.student,
                "qty": abs(flt(row.qty)),
                "rate": row.rate,
                "income_account": row.income_account,
                "school": getattr(row, "school", None),
                "program": getattr(row, "program", None),
            },
        )
    for tax in _copy_tax_rows(source):
        doc.append("taxes", tax)
    doc.insert()
    return doc.name
