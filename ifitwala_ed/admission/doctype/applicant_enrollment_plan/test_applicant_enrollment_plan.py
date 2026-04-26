# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.utils import flt, getdate, now_datetime, nowdate

from ifitwala_ed.accounting.fiscal_year_utils import clear_fiscal_year_cache
from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
    generate_deposit_invoice_from_offer,
)
from ifitwala_ed.tests.base import IfitwalaEdTestSuite


class TestApplicantEnrollmentPlanDepositBridge(IfitwalaEdTestSuite):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        for role in ("Admission Manager", "Academic Admin", "Accounts Manager"):
            self._ensure_role(role)
        self._configure_admission_settings()

    def test_admission_manager_generates_default_draft_deposit_invoice_once(self):
        ctx = self._make_context()
        plan = self._make_plan(ctx, status="Offer Accepted")

        with self.set_user(ctx["admission_manager"].name):
            first = generate_deposit_invoice_from_offer(plan.name)
            second = generate_deposit_invoice_from_offer(plan.name)

        self.assertTrue(first.get("created"))
        self.assertFalse(second.get("created"))
        self.assertEqual(first.get("invoice", {}).get("invoice"), second.get("invoice", {}).get("invoice"))

        plan.reload()
        applicant = frappe.get_doc("Student Applicant", ctx["applicant"].name)
        invoice = frappe.get_doc("Sales Invoice", plan.deposit_invoice)
        self.assertEqual(invoice.docstatus, 0)
        self.assertEqual(invoice.status, "Draft")
        self.assertEqual(invoice.account_holder, applicant.account_holder)
        self.assertEqual(invoice.organization, ctx["organization"])
        self.assertEqual(flt(invoice.grand_total), 500)
        self.assertEqual(frappe.db.count("Sales Invoice", {"name": plan.deposit_invoice}), 1)

    def test_non_accepted_offer_cannot_generate_deposit_invoice(self):
        ctx = self._make_context()
        plan = self._make_plan(ctx, status="Offer Sent")

        with self.set_user(ctx["admission_manager"].name):
            with self.assertRaises(frappe.ValidationError):
                generate_deposit_invoice_from_offer(plan.name)

        plan.reload()
        self.assertFalse((plan.deposit_invoice or "").strip())

    def test_manual_deposit_override_requires_academic_and_finance_approval(self):
        ctx = self._make_context()
        plan = self._make_plan(ctx, status="Offer Accepted")
        plan.deposit_amount = 250
        plan.deposit_override_reason = "Sibling discount approved in principle."
        plan.save(ignore_permissions=True)
        self.assertEqual(plan.deposit_terms_source, "Manual Override")
        self.assertEqual(plan.deposit_override_status, "Pending")

        with self.set_user(ctx["admission_manager"].name):
            with self.assertRaises(frappe.ValidationError):
                generate_deposit_invoice_from_offer(plan.name)

        with self.set_user(ctx["academic_admin"].name):
            plan.approve_deposit_academic_override()
        plan.reload()
        self.assertEqual(plan.deposit_override_status, "Pending")

        with self.set_user(ctx["finance_manager"].name):
            plan.approve_deposit_finance_override()
        plan.reload()
        self.assertEqual(plan.deposit_override_status, "Approved")

        with self.set_user(ctx["admission_manager"].name):
            result = generate_deposit_invoice_from_offer(plan.name)

        self.assertTrue(result.get("created"))
        self.assertEqual(flt(result.get("invoice", {}).get("amount")), 250)

    def test_cross_school_finance_approval_is_blocked(self):
        ctx = self._make_context()
        plan = self._make_plan(ctx, status="Offer Accepted")
        plan.deposit_amount = 250
        plan.deposit_override_reason = "Manual discount."
        plan.save(ignore_permissions=True)

        out_of_scope = self._make_user("Finance", "Other", ["Accounts Manager"])
        other_school = self._make_school(ctx["organization"], prefix="Other Finance")
        self._make_employee(
            out_of_scope.name,
            organization=ctx["organization"],
            school=other_school.name,
            first_name="Finance",
            last_name="Other",
        )

        with self.set_user(out_of_scope.name):
            with self.assertRaises(frappe.PermissionError):
                plan.approve_deposit_finance_override()

    def test_promotion_is_blocked_until_required_deposit_invoice_is_paid(self):
        ctx = self._make_context()
        plan = self._make_plan(ctx, status="Offer Accepted")

        with self.set_user(ctx["admission_manager"].name):
            generate_deposit_invoice_from_offer(plan.name)

        student = self._make_existing_student(ctx)
        ctx["applicant"].db_set("student", student.name, update_modified=False)
        frappe.db.set_single_value("Admission Settings", "require_deposit_before_promotion", 1)

        applicant = frappe.get_doc("Student Applicant", ctx["applicant"].name)
        with self.set_user(ctx["admission_manager"].name):
            with self.assertRaises(frappe.ValidationError):
                applicant.promote_to_student()

        plan.reload()
        invoice = frappe.get_doc("Sales Invoice", plan.deposit_invoice)
        invoice.submit()
        self._pay_invoice(ctx, invoice)

        applicant.reload()
        with self.set_user(ctx["admission_manager"].name):
            promoted_student = applicant.promote_to_student()

        self.assertEqual(promoted_student, student.name)
        applicant.reload()
        self.assertEqual(applicant.application_status, "Promoted")

    def _make_context(self) -> dict:
        organization = self.bootstrap.organization
        school = self.bootstrap.child_school
        academic_year = self.bootstrap.academic_year
        self._ensure_accounting_context(organization)

        admission_manager = self._make_user("Admissions", "Manager", ["Admission Manager"])
        academic_admin = self._make_user("Academic", "Admin", ["Academic Admin"])
        finance_manager = self._make_user("Finance", "Manager", ["Accounts Manager"])
        for user in (admission_manager, academic_admin, finance_manager):
            self._make_employee(
                user.name,
                organization=organization,
                school=school,
                first_name=user.first_name,
                last_name=user.last_name,
            )

        program = self._make_program()
        program_offering = self._make_program_offering(program.name, school, academic_year)
        applicant = self._make_applicant(
            organization=organization,
            school=school,
            academic_year=academic_year,
            program=program.name,
            program_offering=program_offering.name,
        )
        billable_offering = self._make_billable_offering(organization, self.income_account.name)
        self._configure_admission_settings(
            organization=organization,
            school=school,
            billable_offering=billable_offering.name,
        )

        return {
            "organization": organization,
            "school": school,
            "academic_year": academic_year,
            "program": program,
            "program_offering": program_offering,
            "applicant": applicant,
            "billable_offering": billable_offering,
            "admission_manager": admission_manager,
            "academic_admin": academic_admin,
            "finance_manager": finance_manager,
        }

    def _make_plan(self, ctx: dict, *, status: str):
        plan = frappe.get_doc(
            {
                "doctype": "Applicant Enrollment Plan",
                "student_applicant": ctx["applicant"].name,
                "status": status,
                "academic_year": ctx["academic_year"],
                "program": ctx["program"].name,
                "program_offering": ctx["program_offering"].name,
                "offer_accepted_on": now_datetime() if status == "Offer Accepted" else None,
                "offer_accepted_by": ctx["admission_manager"].name if status == "Offer Accepted" else None,
            }
        )
        plan.insert(ignore_permissions=True)
        return plan

    def _make_applicant(self, *, organization, school, academic_year, program, program_offering):
        with self.set_user(self._make_user("Applicant", "Creator", ["Admission Manager"]).name):
            applicant = frappe.get_doc(
                {
                    "doctype": "Student Applicant",
                    "first_name": "Deposit",
                    "last_name": f"Applicant {frappe.generate_hash(length=6)}",
                    "organization": organization,
                    "school": school,
                    "academic_year": academic_year,
                    "program": program,
                    "program_offering": program_offering,
                    "application_status": "Draft",
                    "student_joining_date": "2026-08-15",
                }
            ).insert(ignore_permissions=True)
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()
        return applicant

    def _ensure_accounting_context(self, organization: str):
        self._ensure_fiscal_year(organization)
        self.receivable_account = self._make_account(organization, "Asset", "Receivable", "Deposit Receivable")
        self.cash_account = self._make_account(organization, "Asset", "Cash", "Deposit Cash")
        self.advance_account = self._make_account(organization, "Liability", None, "Deposit Advance")
        self.income_account = self._make_account(organization, "Income", None, "Deposit Income")

        settings = (
            frappe.get_doc("Accounts Settings", organization)
            if frappe.db.exists("Accounts Settings", organization)
            else frappe.new_doc("Accounts Settings")
        )
        settings.organization = organization
        settings.default_receivable_account = self.receivable_account.name
        settings.default_cash_account = self.cash_account.name
        settings.default_advance_account = self.advance_account.name
        settings.save(ignore_permissions=True)

    def _ensure_fiscal_year(self, organization: str):
        rows = frappe.get_all(
            "Fiscal Year Organization",
            filters={"organization": organization},
            fields=["parent"],
            limit=100,
        )
        today = getdate(nowdate())
        for row in rows:
            fiscal_year = frappe.db.get_value(
                "Fiscal Year",
                row.parent,
                ["year_start_date", "year_end_date", "disabled"],
                as_dict=True,
            )
            if (
                fiscal_year
                and not fiscal_year.get("disabled")
                and getdate(fiscal_year.get("year_start_date")) <= today <= getdate(fiscal_year.get("year_end_date"))
            ):
                return row.parent

        fiscal_year = frappe.get_doc(
            {
                "doctype": "Fiscal Year",
                "year": f"FY-{organization}-{frappe.generate_hash(length=6)}",
                "year_start_date": f"{today.year}-01-01",
                "year_end_date": f"{today.year}-12-31",
                "organizations": [{"organization": organization}],
            }
        )
        fiscal_year.insert(ignore_permissions=True)
        clear_fiscal_year_cache()
        return fiscal_year.name

    def _make_account(self, organization: str, root_type: str, account_type: str | None, prefix: str):
        account = frappe.get_doc(
            {
                "doctype": "Account",
                "organization": organization,
                "account_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "root_type": root_type,
                "account_type": account_type,
                "is_group": 0,
            }
        )
        account.insert(ignore_permissions=True)
        return account

    def _make_billable_offering(self, organization: str, income_account: str):
        offering = frappe.get_doc(
            {
                "doctype": "Billable Offering",
                "organization": organization,
                "offering_type": "One-off Fee",
                "income_account": income_account,
                "pricing_mode": "Fixed",
            }
        )
        offering.insert(ignore_permissions=True)
        return offering

    def _configure_admission_settings(
        self,
        *,
        organization: str | None = None,
        school: str | None = None,
        billable_offering: str | None = None,
    ):
        settings = frappe.get_single("Admission Settings")
        settings.auto_hydrate_enrollment_request_after_promotion = 0
        settings.require_deposit_before_promotion = 0
        settings.set("deposit_defaults", [])
        if organization and billable_offering:
            settings.append(
                "deposit_defaults",
                {
                    "enabled": 1,
                    "organization": organization,
                    "school": school,
                    "deposit_required": 1,
                    "deposit_amount": 500,
                    "deposit_due_days": 7,
                    "deposit_billable_offering": billable_offering,
                    "payment_instructions": "Transfer to the school admissions deposit account.",
                },
            )
        settings.save(ignore_permissions=True)

    def _make_program(self):
        program = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Deposit Program {frappe.generate_hash(length=8)}",
                "program_slug": f"deposit-program-{frappe.generate_hash(length=8)}",
            }
        )
        program.insert(ignore_permissions=True)
        return program

    def _make_program_offering(self, program: str, school: str, academic_year: str):
        offering = frappe.get_doc(
            {
                "doctype": "Program Offering",
                "program": program,
                "school": school,
                "offering_title": f"Deposit Offering {frappe.generate_hash(length=8)}",
                "offering_academic_years": [{"academic_year": academic_year}],
            }
        )
        offering.insert(ignore_permissions=True)
        return offering

    def _make_existing_student(self, ctx: dict):
        applicant = frappe.get_doc("Student Applicant", ctx["applicant"].name)
        student = frappe.get_doc(
            {
                "doctype": "Student",
                "student_first_name": applicant.first_name,
                "student_last_name": applicant.last_name,
                "student_email": f"student-{frappe.generate_hash(length=8)}@example.com",
                "student_date_of_birth": "2014-01-01",
                "student_joining_date": applicant.student_joining_date,
                "anchor_school": ctx["school"],
                "account_holder": applicant.account_holder,
                "student_applicant": applicant.name,
            }
        )
        previous = bool(getattr(frappe.flags, "from_applicant_promotion", False))
        frappe.flags.from_applicant_promotion = True
        try:
            student.insert(ignore_permissions=True)
        finally:
            frappe.flags.from_applicant_promotion = previous
        return student

    def _pay_invoice(self, ctx: dict, invoice):
        payment = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "payment_type": "Receive",
                "party_type": "Account Holder",
                "party": invoice.account_holder,
                "organization": ctx["organization"],
                "posting_date": nowdate(),
                "paid_to": self.cash_account.name,
                "paid_amount": invoice.grand_total,
                "references": [
                    {
                        "reference_doctype": "Sales Invoice",
                        "reference_name": invoice.name,
                        "allocated_amount": invoice.grand_total,
                    }
                ],
            }
        )
        payment.insert(ignore_permissions=True)
        payment.submit()
        return payment

    def _ensure_role(self, role: str):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)

    def _make_user(self, first_name: str, last_name: str, roles: list[str]):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"user-{frappe.generate_hash(length=10)}@example.com",
                "first_name": first_name,
                "last_name": last_name,
                "enabled": 1,
                "send_welcome_email": 0,
            }
        )
        for role in roles:
            self._ensure_role(role)
            user.append("roles", {"role": role})
        user.flags.no_welcome_mail = True
        user.flags.no_password_notification = True
        user.insert(ignore_permissions=True)
        frappe.clear_cache(user=user.name)
        return user

    def _make_employee(self, user: str, *, organization: str, school: str, first_name: str, last_name: str):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": first_name,
                "employee_last_name": last_name,
                "employee_gender": "Other",
                "employee_professional_email": user,
                "organization": organization,
                "school": school,
                "user_id": user,
                "date_of_joining": nowdate(),
                "employment_status": "Active",
            }
        )
        employee.insert(ignore_permissions=True)
        return employee

    def _make_school(self, organization: str, *, prefix: str):
        school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{prefix} {frappe.generate_hash(length=8)}",
                "abbr": f"S{frappe.generate_hash(length=5)}",
                "organization": organization,
                "parent_school": self.bootstrap.root_school,
                "is_group": 0,
            }
        )
        school.insert(ignore_permissions=True)
        return school
