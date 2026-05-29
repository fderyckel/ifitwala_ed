from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, nowdate

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.accounting.receivables import money


class InitialEnrollmentBillingPackage(Document):
    def validate(self):
        self._validate_scope()
        self._validate_payment_terms_template()
        self._validate_items()

    def _validate_scope(self):
        if not (self.school or self.academic_year or self.program or self.program_offering):
            frappe.throw(
                _("Choose at least one School, Academic Year, Program, or Program Offering for the billing package.")
            )

        if self.school:
            school_organization = get_school_organization(self.school)
            if school_organization != self.organization:
                frappe.throw(_("School must belong to the same Organization as the billing package."))

        if self.program_offering:
            offering = frappe.db.get_value(
                "Program Offering",
                self.program_offering,
                ["school", "program"],
                as_dict=True,
            )
            if not offering:
                frappe.throw(
                    _("Program Offering {program_offering} was not found.").format(
                        program_offering=self.program_offering
                    )
                )
            if get_school_organization(offering.school) != self.organization:
                frappe.throw(_("Program Offering must belong to the same Organization as the billing package."))
            if self.school and offering.school != self.school:
                frappe.throw(_("Program Offering must belong to the selected School."))
            if self.program and offering.program != self.program:
                frappe.throw(_("Program Offering must belong to the selected Program."))
            if self.academic_year and not frappe.db.exists(
                "Program Offering Academic Year",
                {
                    "parent": self.program_offering,
                    "parenttype": "Program Offering",
                    "academic_year": self.academic_year,
                },
            ):
                frappe.throw(_("Academic Year must be part of the selected Program Offering."))

        if self.academic_year and self.school:
            academic_year_school = frappe.db.get_value("Academic Year", self.academic_year, "school")
            if academic_year_school and academic_year_school != self.school:
                frappe.throw(_("Academic Year must belong to the selected School."))

        if cint(self.default_due_days or 0) < 0:
            frappe.throw(_("Default Due Days cannot be negative."))

    def _validate_payment_terms_template(self):
        if not self.payment_terms_template:
            return

        template_organization = frappe.db.get_value(
            "Payment Terms Template",
            self.payment_terms_template,
            "organization",
        )
        if not template_organization:
            frappe.throw(
                _("Payment Terms Template {template} was not found.").format(template=self.payment_terms_template)
            )
        if template_organization != self.organization:
            frappe.throw(_("Payment Terms Template must belong to the same Organization as the billing package."))

    def _validate_items(self):
        if not self.items:
            frappe.throw(_("At least one billing package item is required."))

        seen_billable_offerings: set[str] = set()
        offering_cache = {}
        for idx, row in enumerate(self.items, start=1):
            if not row.billable_offering:
                frappe.throw(_("Row {row_number}: Billable Offering is required.").format(row_number=idx))
            if row.billable_offering in seen_billable_offerings:
                frappe.throw(
                    _("Row {row_number}: Billable Offering {billable_offering} is duplicated.").format(
                        row_number=idx,
                        billable_offering=row.billable_offering,
                    )
                )
            seen_billable_offerings.add(row.billable_offering)

            if flt(row.qty or 0) <= 0:
                frappe.throw(_("Row {row_number}: Qty must be greater than zero.").format(row_number=idx))
            if flt(row.default_rate or 0) < 0:
                frappe.throw(_("Row {row_number}: Default Rate cannot be negative.").format(row_number=idx))
            if flt(row.default_rate or 0) == 0 and not (row.description_override or "").strip():
                frappe.throw(
                    _("Row {row_number}: Description Override is required for zero-rate items.").format(row_number=idx)
                )

            offering = offering_cache.get(row.billable_offering)
            if not offering:
                offering = frappe.db.get_value(
                    "Billable Offering",
                    row.billable_offering,
                    ["organization", "disabled", "offering_type"],
                    as_dict=True,
                )
                if not offering:
                    frappe.throw(_("Row {row_number}: Billable Offering was not found.").format(row_number=idx))
                offering_cache[row.billable_offering] = offering

            if offering.organization != self.organization:
                frappe.throw(
                    _("Row {row_number}: Billable Offering must belong to the same Organization.").format(
                        row_number=idx
                    )
                )
            if cint(offering.disabled or 0):
                frappe.throw(_("Row {row_number}: Billable Offering is disabled.").format(row_number=idx))
            if (offering.offering_type or "").strip() == "Program":
                frappe.throw(
                    _(
                        "Row {row_number}: Initial enrollment packages cannot include Program billable offerings."
                    ).format(row_number=idx)
                )

    @frappe.whitelist()
    def generate_draft_invoices(self, posting_date: str | None = None, due_date: str | None = None):
        return generate_initial_enrollment_invoices(
            initial_enrollment_billing_package=self.name,
            posting_date=posting_date,
            due_date=due_date,
        )


def _require_sales_invoice_create_permission() -> None:
    if not frappe.has_permission("Sales Invoice", ptype="create"):
        frappe.throw(_("You do not have permission to create Sales Invoices."), frappe.PermissionError)


def _normalize_date(value):
    return getdate(value) if value else None


def _get_enrollment_context(program_enrollment: str) -> dict:
    row = frappe.db.get_value(
        "Program Enrollment",
        program_enrollment,
        ["name", "student", "program_offering", "academic_year", "program", "school", "enrollment_date"],
        as_dict=True,
    )
    if not row:
        frappe.throw(
            _("Program Enrollment {program_enrollment} was not found.").format(program_enrollment=program_enrollment)
        )
    if not row.student:
        frappe.throw(_("Program Enrollment is missing Student."))
    if not row.program_offering:
        frappe.throw(_("Program Enrollment is missing Program Offering."))
    if not row.school:
        frappe.throw(_("Program Enrollment is missing School."))

    student = frappe.db.get_value(
        "Student",
        row.student,
        ["account_holder", "anchor_school"],
        as_dict=True,
    )
    if not student:
        frappe.throw(_("Student {student} was not found.").format(student=row.student))
    if not student.account_holder:
        frappe.throw(_("Student is missing an Account Holder."))

    organization = get_school_organization(row.school)
    if not organization:
        frappe.throw(_("Program Enrollment School is missing Organization context."))

    account_holder_org = frappe.db.get_value("Account Holder", student.account_holder, "organization")
    if account_holder_org != organization:
        frappe.throw(_("Student Account Holder must belong to the same Organization as the enrollment."))

    row["organization"] = organization
    row["account_holder"] = student.account_holder
    return row


def _package_matches_context(package, context: dict) -> bool:
    if package.organization != context.get("organization"):
        return False
    if package.school and package.school != context.get("school"):
        return False
    if package.academic_year and package.academic_year != context.get("academic_year"):
        return False
    if package.program and package.program != context.get("program"):
        return False
    if package.program_offering and package.program_offering != context.get("program_offering"):
        return False
    return True


def _package_specificity(package) -> tuple[int, int, int, int]:
    return (
        1 if package.program_offering else 0,
        1 if package.program else 0,
        1 if package.academic_year else 0,
        1 if package.school else 0,
    )


def _get_active_package_for_context(context: dict, package_name: str | None = None):
    if package_name:
        package = frappe.get_doc("Initial Enrollment Billing Package", package_name)
        package.check_permission("read")
        if not cint(package.is_active or 0):
            frappe.throw(_("Initial Enrollment Billing Package must be active."))
        if not _package_matches_context(package, context):
            frappe.throw(_("Initial Enrollment Billing Package does not match this Program Enrollment."))
        return package

    rows = frappe.get_all(
        "Initial Enrollment Billing Package",
        filters={"organization": context.get("organization"), "is_active": 1},
        fields=["name"],
        limit=500,
    )
    candidates = []
    for row in rows:
        package = frappe.get_doc("Initial Enrollment Billing Package", row.name)
        if _package_matches_context(package, context):
            candidates.append(package)

    if not candidates:
        frappe.throw(_("No active Initial Enrollment Billing Package matches this Program Enrollment."))

    candidates.sort(key=_package_specificity, reverse=True)
    top_specificity = _package_specificity(candidates[0])
    tied = [package for package in candidates if _package_specificity(package) == top_specificity]
    if len(tied) > 1:
        frappe.throw(
            _("Multiple Initial Enrollment Billing Packages match this Program Enrollment: {packages}.").format(
                packages=", ".join(sorted(package.name for package in tied))
            )
        )
    candidates[0].check_permission("read")
    return candidates[0]


def _get_existing_initial_enrollment_invoice(program_enrollment: str, package_name: str) -> str | None:
    existing = frappe.get_all(
        "Sales Invoice",
        filters={
            "source_program_enrollment": program_enrollment,
            "initial_enrollment_billing_package": package_name,
            "docstatus": ["<", 2],
        },
        pluck="name",
        limit=1,
    )
    return existing[0] if existing else None


def _is_first_program_enrollment(context: dict) -> bool:
    rows = frappe.get_all(
        "Program Enrollment",
        filters={"student": context.get("student")},
        fields=["name", "enrollment_date", "creation"],
        order_by="enrollment_date asc, creation asc, name asc",
        limit=500,
    )
    return bool(rows and rows[0].get("name") == context.get("name"))


def _get_package_enrollment_rows(package) -> list[dict]:
    filters = {
        "school": package.school,
        "academic_year": package.academic_year,
        "program": package.program,
        "program_offering": package.program_offering,
    }
    filters = {key: value for key, value in filters.items() if value}
    rows = frappe.get_all(
        "Program Enrollment",
        filters=filters,
        fields=["name", "student", "program_offering", "academic_year", "program", "school", "enrollment_date"],
        order_by="enrollment_date asc, name asc",
        limit=5000,
    )

    out = []
    for row in rows:
        context = _get_enrollment_context(row.name)
        if not _package_matches_context(package, context):
            continue
        if not _is_first_program_enrollment(context):
            continue
        out.append(context)
    return out


def _resolve_invoice_dates(package, posting_date=None, due_date=None) -> tuple:
    invoice_posting_date = getdate(posting_date or nowdate())
    if package.payment_terms_template:
        return invoice_posting_date, None
    invoice_due_date = (
        getdate(due_date) if due_date else add_days(invoice_posting_date, cint(package.default_due_days or 0))
    )
    return invoice_posting_date, invoice_due_date


def _create_initial_enrollment_invoice(context: dict, package, posting_date=None, due_date=None):
    invoice_posting_date, invoice_due_date = _resolve_invoice_dates(
        package,
        posting_date=posting_date,
        due_date=due_date,
    )
    invoice = frappe.new_doc("Sales Invoice")
    invoice.update(
        {
            "account_holder": context.get("account_holder"),
            "organization": context.get("organization"),
            "program_offering": context.get("program_offering"),
            "source_program_enrollment": context.get("name"),
            "initial_enrollment_billing_package": package.name,
            "posting_date": invoice_posting_date,
            "remarks": _("Initial enrollment invoice from package {package}.").format(package=package.name),
        }
    )
    if package.payment_terms_template:
        invoice.payment_terms_template = package.payment_terms_template
    else:
        invoice.due_date = invoice_due_date

    for row in package.items:
        invoice.append(
            "items",
            {
                "billable_offering": row.billable_offering,
                "program_offering": context.get("program_offering"),
                "charge_source": "Program Offering",
                "description": (row.description_override or "").strip()
                or _("Initial enrollment fee for {student}").format(student=context.get("student")),
                "student": context.get("student") if cint(row.requires_student or 0) else None,
                "qty": row.qty,
                "rate": money(flt(row.default_rate or 0)),
            },
        )

    invoice.insert()
    return invoice


@frappe.whitelist()
def generate_initial_enrollment_invoice(
    program_enrollment: str,
    initial_enrollment_billing_package: str | None = None,
    posting_date: str | None = None,
    due_date: str | None = None,
) -> dict:
    _require_sales_invoice_create_permission()
    context = _get_enrollment_context(program_enrollment)
    package = _get_active_package_for_context(context, package_name=initial_enrollment_billing_package)
    existing_invoice = _get_existing_initial_enrollment_invoice(context.get("name"), package.name)
    if existing_invoice:
        return {
            "ok": True,
            "created": False,
            "program_enrollment": context.get("name"),
            "initial_enrollment_billing_package": package.name,
            "sales_invoice": existing_invoice,
        }

    invoice = _create_initial_enrollment_invoice(
        context,
        package,
        posting_date=posting_date,
        due_date=due_date,
    )
    return {
        "ok": True,
        "created": True,
        "program_enrollment": context.get("name"),
        "initial_enrollment_billing_package": package.name,
        "sales_invoice": invoice.name,
    }


@frappe.whitelist()
def generate_initial_enrollment_invoices(
    initial_enrollment_billing_package: str,
    posting_date: str | None = None,
    due_date: str | None = None,
) -> dict:
    _require_sales_invoice_create_permission()
    package = frappe.get_doc("Initial Enrollment Billing Package", initial_enrollment_billing_package)
    package.check_permission("read")
    if not cint(package.is_active or 0):
        frappe.throw(_("Initial Enrollment Billing Package must be active."))

    created = []
    existing = []
    for context in _get_package_enrollment_rows(package):
        result = generate_initial_enrollment_invoice(
            program_enrollment=context.get("name"),
            initial_enrollment_billing_package=package.name,
            posting_date=posting_date,
            due_date=due_date,
        )
        if result.get("created"):
            created.append(result.get("sales_invoice"))
        else:
            existing.append(result.get("sales_invoice"))

    return {
        "ok": True,
        "initial_enrollment_billing_package": package.name,
        "created_invoice_names": created,
        "existing_invoice_names": existing,
        "created_count": len(created),
        "existing_count": len(existing),
    }
