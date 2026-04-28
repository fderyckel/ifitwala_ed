# ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.accounting.receivables import money
from ifitwala_ed.admission.admission_utils import has_scoped_staff_access_to_student_applicant
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_descendants_including_self,
    get_school_ancestors_including_self,
    get_school_descendants_including_self,
)
from ifitwala_ed.schedule.basket_group_utils import get_offering_course_semantics
from ifitwala_ed.schedule.enrollment_engine import evaluate_basket_selection

STAFF_ROLES = {
    "Admission Manager",
    "Admission Officer",
    "Academic Admin",
    "Curriculum Coordinator",
    "System Manager",
    "Administrator",
}
PORTAL_ROLE = "Admissions Applicant"
DEPOSIT_INVOICE_ROLES = {
    "Admission Manager",
    "System Manager",
    "Administrator",
}
ACCOUNT_HOLDER_CREATE_ROLES = {
    "Admission Manager",
    "Admission Officer",
    "System Manager",
    "Administrator",
}
DEPOSIT_ACADEMIC_APPROVER_ROLES = {"Academic Admin", "System Manager", "Administrator"}
DEPOSIT_FINANCE_APPROVER_ROLES = {"Accounts Manager", "System Manager", "Administrator"}
STATUS_OPTIONS = {
    "Draft",
    "Ready for Committee",
    "Committee Approved",
    "Offer Sent",
    "Offer Accepted",
    "Offer Declined",
    "Offer Expired",
    "Hydrated",
    "Cancelled",
    "Superseded",
}
TERMINAL_STATUSES = {"Offer Declined", "Offer Expired", "Hydrated", "Cancelled", "Superseded"}
PAID_DEPOSIT_STATUSES = {"Paid", "Credited"}


def _normalize_choice_rank(value) -> int | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        rank = int(text)
    except (TypeError, ValueError):
        frappe.throw(_("Choice Rank must be a positive whole number."))

    # Frappe Int child-table fields round-trip blank values as 0.
    if rank == 0:
        return None

    if rank < 0:
        frappe.throw(_("Choice Rank must be a positive whole number."))

    return rank


def _normalize_plan_rows(rows) -> list[dict]:
    normalized = []
    seen = set()

    for row in rows or []:
        course = (getattr(row, "course", None) or (row or {}).get("course") or "").strip()
        if not course or course in seen:
            continue

        seen.add(course)
        normalized.append(
            {
                "course": course,
                "required": 1 if int(getattr(row, "required", None) or (row or {}).get("required") or 0) == 1 else 0,
                "applied_basket_group": (
                    getattr(row, "applied_basket_group", None) or (row or {}).get("applied_basket_group") or ""
                ).strip(),
                "choice_rank": _normalize_choice_rank(
                    getattr(row, "choice_rank", None) if hasattr(row, "choice_rank") else (row or {}).get("choice_rank")
                ),
            }
        )

    return normalized


def _get_required_offering_basket_groups(program_offering: str) -> list[str]:
    if not program_offering:
        return []

    rows = frappe.get_all(
        "Program Offering Enrollment Rule",
        filters={
            "parent": program_offering,
            "parenttype": "Program Offering",
            "rule_type": "REQUIRE_GROUP_COVERAGE",
        },
        fields=["basket_group"],
        order_by="idx asc",
    )

    required_groups: list[str] = []
    seen = set()
    for row in rows or []:
        basket_group = (row.get("basket_group") or "").strip()
        if not basket_group or basket_group in seen:
            continue
        seen.add(basket_group)
        required_groups.append(basket_group)
    return required_groups


def _as_clean_text(value) -> str:
    return str(value or "").strip()


def _as_money(value) -> float:
    return money(flt(value or 0))


def _as_date_text(value) -> str:
    if not value:
        return ""
    return str(getdate(value))


def _deposit_terms_signature_from_plan(plan) -> dict:
    return {
        "deposit_required": 1 if cint(getattr(plan, "deposit_required", 0) or 0) else 0,
        "deposit_amount": _as_money(getattr(plan, "deposit_amount", 0)),
        "deposit_due_date": _as_date_text(getattr(plan, "deposit_due_date", None)),
        "deposit_billable_offering": _as_clean_text(getattr(plan, "deposit_billable_offering", "")),
    }


def _get_deposit_default_rows() -> list[dict]:
    try:
        settings = frappe.get_single("Admission Settings")
    except Exception:
        return []

    out: list[dict] = []
    for row in settings.get("deposit_defaults") or []:
        if not cint(row.get("enabled") or 0):
            continue
        organization = _as_clean_text(row.get("organization"))
        if not organization:
            continue
        out.append(
            {
                "organization": organization,
                "school": _as_clean_text(row.get("school")),
                "deposit_required": 1 if cint(row.get("deposit_required") or 0) else 0,
                "deposit_amount": _as_money(row.get("deposit_amount")),
                "deposit_due_days": cint(row.get("deposit_due_days") or 0),
                "deposit_billable_offering": _as_clean_text(row.get("deposit_billable_offering")),
                "payment_instructions": _as_clean_text(row.get("payment_instructions")),
                "idx": cint(row.get("idx") or 0),
            }
        )
    return out


def get_deposit_default_for_plan(plan) -> dict | None:
    organization = _as_clean_text(getattr(plan, "organization", ""))
    school = _as_clean_text(getattr(plan, "school", ""))
    if not organization:
        return None

    school_scope = []
    if school:
        school_scope = get_school_ancestors_including_self(school) or [school]
    school_rank = {school_name: idx for idx, school_name in enumerate(school_scope)}

    candidates = []
    for row in _get_deposit_default_rows():
        if row.get("organization") != organization:
            continue
        row_school = _as_clean_text(row.get("school"))
        if row_school and row_school not in school_rank:
            continue
        candidates.append(row)

    if not candidates:
        return None

    candidates.sort(
        key=lambda row: (
            school_rank.get(_as_clean_text(row.get("school")), 9999),
            cint(row.get("idx") or 0),
        )
    )
    return candidates[0]


def _default_deposit_due_date(plan, default_row: dict | None) -> str:
    if not default_row or not cint(default_row.get("deposit_required") or 0):
        return ""

    accepted_on = getattr(plan, "offer_accepted_on", None)
    if not accepted_on:
        return ""

    return str(add_days(getdate(accepted_on), cint(default_row.get("deposit_due_days") or 0)))


def _deposit_terms_signature_from_default(plan, default_row: dict | None) -> dict | None:
    if not default_row:
        return None
    return {
        "deposit_required": 1 if cint(default_row.get("deposit_required") or 0) else 0,
        "deposit_amount": _as_money(default_row.get("deposit_amount")),
        "deposit_due_date": _default_deposit_due_date(plan, default_row),
        "deposit_billable_offering": _as_clean_text(default_row.get("deposit_billable_offering")),
    }


def _deposit_terms_match_default(plan, default_row: dict | None) -> bool:
    default_signature = _deposit_terms_signature_from_default(plan, default_row)
    if default_signature is None:
        return False
    return _deposit_terms_signature_from_plan(plan) == default_signature


def _deposit_terms_changed_since_previous(plan) -> bool:
    before = plan.get_doc_before_save() if getattr(plan, "name", None) else None
    if not before:
        return True
    return _deposit_terms_signature_from_plan(plan) != _deposit_terms_signature_from_plan(before)


def _invoice_summary_from_row(row: dict | None, *, fallback_due_date=None, fallback_amount=0) -> dict:
    if not row:
        due_date = _as_date_text(fallback_due_date)
        return {
            "invoice": None,
            "invoice_status": None,
            "docstatus": None,
            "amount": _as_money(fallback_amount),
            "paid_amount": 0,
            "outstanding_amount": _as_money(fallback_amount),
            "due_date": due_date,
            "is_overdue": bool(due_date and getdate(due_date) < getdate(nowdate())),
            "is_paid": False,
        }

    status = _as_clean_text(row.get("status"))
    outstanding = _as_money(row.get("outstanding_amount"))
    due_date = _as_date_text(row.get("due_date"))
    docstatus = cint(row.get("docstatus") or 0)
    is_paid = bool(docstatus == 1 and (status in PAID_DEPOSIT_STATUSES or outstanding <= 0))
    return {
        "invoice": _as_clean_text(row.get("name")) or None,
        "invoice_status": status or None,
        "docstatus": docstatus,
        "amount": _as_money(row.get("grand_total")),
        "paid_amount": _as_money(row.get("paid_amount")),
        "outstanding_amount": outstanding,
        "due_date": due_date,
        "is_overdue": bool(outstanding > 0 and due_date and getdate(due_date) < getdate(nowdate())),
        "is_paid": is_paid,
    }


def _deposit_blocker_label(summary: dict) -> str | None:
    if not summary.get("deposit_required"):
        return None
    if summary.get("requires_override_approval"):
        return _("Deposit terms need academic and finance approval")
    if not summary.get("invoice"):
        return _("Deposit not generated")
    if summary.get("invoice_status") == "Draft":
        return _("Deposit invoice pending finance review")
    if summary.get("is_paid"):
        return _("Deposit paid")
    if summary.get("is_overdue"):
        return _("Deposit overdue")
    if flt(summary.get("outstanding_amount") or 0) > 0:
        return _("Deposit unpaid")
    return None


def get_deposit_invoice_status_for_plan(plan_or_name) -> dict:
    plan = frappe.get_doc("Applicant Enrollment Plan", plan_or_name) if isinstance(plan_or_name, str) else plan_or_name
    default_row = get_deposit_default_for_plan(plan)
    invoice_name = _as_clean_text(getattr(plan, "deposit_invoice", ""))

    invoice_row = None
    if invoice_name:
        invoice_row = frappe.db.get_value(
            "Sales Invoice",
            invoice_name,
            ["name", "docstatus", "status", "grand_total", "paid_amount", "outstanding_amount", "due_date"],
            as_dict=True,
        )

    invoice_summary = _invoice_summary_from_row(
        invoice_row,
        fallback_due_date=getattr(plan, "deposit_due_date", None),
        fallback_amount=getattr(plan, "deposit_amount", 0),
    )
    terms_source = _as_clean_text(getattr(plan, "deposit_terms_source", "")) or "School Default"
    override_status = _as_clean_text(getattr(plan, "deposit_override_status", "")) or "Not Required"
    requires_override = bool(
        cint(getattr(plan, "deposit_required", 0) or 0)
        and (terms_source == "Manual Override")
        and override_status != "Approved"
    )

    summary = {
        "deposit_required": bool(cint(getattr(plan, "deposit_required", 0) or 0)),
        "deposit_amount": _as_money(getattr(plan, "deposit_amount", 0)),
        "deposit_due_date": _as_date_text(getattr(plan, "deposit_due_date", None)) or None,
        "deposit_billable_offering": _as_clean_text(getattr(plan, "deposit_billable_offering", "")) or None,
        "terms_source": terms_source,
        "override_status": override_status,
        "requires_override_approval": requires_override,
        "academic_approved": bool(_as_clean_text(getattr(plan, "deposit_academic_approved_by", ""))),
        "finance_approved": bool(_as_clean_text(getattr(plan, "deposit_finance_approved_by", ""))),
        "payment_instructions": _as_clean_text((default_row or {}).get("payment_instructions")) or None,
        **invoice_summary,
    }
    summary["blocker_label"] = _deposit_blocker_label(summary)
    return summary


def get_effective_applicant_enrollment_plan_rows(plan: "ApplicantEnrollmentPlan") -> list[dict]:
    explicit_rows = _normalize_plan_rows(plan.get("courses") or [])
    offering_semantics = get_offering_course_semantics((plan.program_offering or "").strip())
    effective_rows = []
    seen = set()

    for row in explicit_rows:
        course = row.get("course")
        if not course or course in seen:
            continue
        if offering_semantics and course not in offering_semantics:
            continue
        seen.add(course)

        semantics = offering_semantics.get(course) or {}
        effective_rows.append(
            {
                "course": course,
                "required": 1 if semantics.get("required") else 0,
                "applied_basket_group": (row.get("applied_basket_group") or "").strip(),
                "choice_rank": _normalize_choice_rank(row.get("choice_rank")),
            }
        )

    for course, semantics in offering_semantics.items():
        if not semantics.get("required") or course in seen:
            continue
        effective_rows.append(
            {
                "course": course,
                "required": 1,
                "applied_basket_group": "",
                "choice_rank": None,
            }
        )

    return effective_rows


def get_applicant_enrollment_choice_state(plan: "ApplicantEnrollmentPlan") -> dict:
    offering_name = (plan.program_offering or "").strip()
    offering_semantics = get_offering_course_semantics(offering_name) if offering_name else {}
    explicit_rows = _normalize_plan_rows(plan.get("courses") or [])
    explicit_by_course = {row["course"]: row for row in explicit_rows}
    effective_rows = get_effective_applicant_enrollment_plan_rows(plan)
    effective_by_course = {row["course"]: row for row in effective_rows}
    required_basket_groups = _get_required_offering_basket_groups(offering_name)
    basket_result = (
        evaluate_basket_selection(program_offering=offering_name, requested_courses=effective_rows)
        if offering_name
        else {
            "status": None,
            "override_required": False,
            "reasons": [],
            "violations": [],
            "missing_required_courses": [],
            "ambiguous_courses": [],
            "group_summary": {},
        }
    )

    courses = []
    required_count = 0
    optional_count = 0
    selected_optional_count = 0

    for course, semantics in offering_semantics.items():
        effective_row = effective_by_course.get(course) or {}
        basket_groups = list(semantics.get("basket_groups") or [])
        required = bool(semantics.get("required"))
        is_selected = required or course in explicit_by_course
        applied_basket_group = (effective_row.get("applied_basket_group") or "").strip()
        choice_rank = effective_row.get("choice_rank")

        if required:
            required_count += 1
        else:
            optional_count += 1
            if course in explicit_by_course:
                selected_optional_count += 1

        courses.append(
            {
                "course": course,
                "course_name": (semantics.get("course_name") or "").strip() or course,
                "required": required,
                "basket_groups": basket_groups,
                "applied_basket_group": applied_basket_group or None,
                "choice_rank": choice_rank,
                "is_selected": bool(is_selected),
                "requires_basket_group_selection": bool(
                    is_selected and len(basket_groups) > 1 and not applied_basket_group
                ),
                "is_explicit_choice": bool(course in explicit_by_course),
                "has_choice_rank": choice_rank is not None,
            }
        )

    basket_status = (basket_result.get("status") or "").strip() or None
    ready_for_offer_response = basket_status in {"ok", "not_configured"}
    can_edit_choices = (plan.status or "").strip() == "Offer Sent"

    return {
        "plan": {
            "name": plan.name,
            "status": (plan.status or "").strip(),
            "academic_year": (plan.academic_year or "").strip(),
            "term": (plan.term or "").strip(),
            "program": (plan.program or "").strip(),
            "program_offering": offering_name,
            "offer_expires_on": plan.offer_expires_on,
            "can_edit_choices": can_edit_choices,
            "can_respond_to_offer": can_edit_choices,
        },
        "summary": {
            "has_plan": True,
            "has_courses": bool(courses),
            "has_selectable_courses": any(not bool(row.get("required")) for row in courses),
            "can_edit_choices": can_edit_choices,
            "ready_for_offer_response": ready_for_offer_response,
            "required_course_count": required_count,
            "optional_course_count": optional_count,
            "selected_optional_count": selected_optional_count,
        },
        "validation": {
            "status": basket_status,
            "ready_for_offer_response": ready_for_offer_response,
            "reasons": list(basket_result.get("reasons") or []),
            "violations": list(basket_result.get("violations") or []),
            "missing_required_courses": list(basket_result.get("missing_required_courses") or []),
            "ambiguous_courses": list(basket_result.get("ambiguous_courses") or []),
            "group_summary": dict(basket_result.get("group_summary") or {}),
        },
        "required_basket_groups": required_basket_groups,
        "courses": courses,
    }


class ApplicantEnrollmentPlan(Document):
    def validate(self):
        applicant_row = self._get_applicant_row()
        self._sync_from_applicant(applicant_row)
        self._normalize_courses()
        self._sync_course_semantics_from_offering()
        self._validate_course_rows()
        self._validate_status()
        self._validate_single_active_plan()
        self._validate_offer_expiry()
        self._validate_deposit_terms()

    def _get_applicant_row(self) -> dict:
        if not self.student_applicant:
            frappe.throw(_("Student Applicant is required."))

        applicant_row = frappe.db.get_value(
            "Student Applicant",
            self.student_applicant,
            [
                "name",
                "organization",
                "school",
                "academic_year",
                "term",
                "program",
                "program_offering",
                "student",
                "application_status",
                "applicant_user",
            ],
            as_dict=True,
        )
        if not applicant_row:
            frappe.throw(_("Student Applicant {0} does not exist.").format(self.student_applicant))
        return applicant_row

    def _sync_from_applicant(self, applicant_row: dict):
        self.organization = applicant_row.get("organization")
        self.school = applicant_row.get("school")
        self.student = applicant_row.get("student") or None

        if not self.academic_year and applicant_row.get("academic_year"):
            self.academic_year = applicant_row.get("academic_year")
        if not self.term and applicant_row.get("term"):
            self.term = applicant_row.get("term")
        if not self.program and applicant_row.get("program"):
            self.program = applicant_row.get("program")
        if not self.program_offering and applicant_row.get("program_offering"):
            self.program_offering = applicant_row.get("program_offering")

        if self.program_offering:
            offering = frappe.db.get_value(
                "Program Offering",
                self.program_offering,
                ["program", "school"],
                as_dict=True,
            )
            if not offering:
                frappe.throw(_("Program Offering {0} does not exist.").format(self.program_offering))
            self.program = offering.get("program")
            if self.school and offering.get("school") and self.school != offering.get("school"):
                frappe.throw(_("Program Offering school must match the applicant school."))

    def _normalize_courses(self):
        current_rows = self.get("courses") or []
        normalized = _normalize_plan_rows(current_rows)
        current_normalized = [
            {
                "course": (row.course or "").strip(),
                "required": 1 if int(row.required or 0) == 1 else 0,
                "applied_basket_group": (row.applied_basket_group or "").strip(),
                "choice_rank": _normalize_choice_rank(row.choice_rank),
            }
            for row in current_rows
            if (row.course or "").strip()
        ]
        if normalized == current_normalized:
            return
        self.set("courses", normalized)

    def _sync_course_semantics_from_offering(self):
        if not self.program_offering or not getattr(self, "courses", None):
            return

        offering_semantics = get_offering_course_semantics(self.program_offering)
        for row in self.get("courses") or []:
            course = (row.course or "").strip()
            if not course:
                continue
            row.required = 1 if (offering_semantics.get(course) or {}).get("required") else 0

    def _validate_course_rows(self):
        if not getattr(self, "courses", None):
            return

        offering_semantics = get_offering_course_semantics(self.program_offering) if self.program_offering else {}
        gate_statuses = {"Offer Accepted", "Hydrated"}
        seen = set()

        for idx, row in enumerate(self.get("courses") or [], start=1):
            course = (row.course or "").strip()
            if not course:
                frappe.throw(_("Planned Course row {0}: Course is required.").format(idx))
            if course in seen:
                frappe.throw(_("Planned Course row {0}: duplicate course {1}.").format(idx, course))
            seen.add(course)

            semantics = offering_semantics.get(course) or {}
            if self.program_offering and not semantics:
                frappe.throw(
                    _("Planned Course row {0}: Course {1} is not part of Program Offering {2}.").format(
                        idx, course, self.program_offering
                    )
                )
            allowed_groups = list(semantics.get("basket_groups") or [])
            applied_group = (row.applied_basket_group or "").strip()

            if applied_group and applied_group not in allowed_groups:
                frappe.throw(
                    _("Planned Course row {0}: Basket Group {1} is not allowed for course {2}.").format(
                        idx, applied_group, course
                    )
                )

            if not applied_group and len(allowed_groups) == 1 and not int(row.required or 0):
                row.applied_basket_group = allowed_groups[0]
                applied_group = allowed_groups[0]

            if row.choice_rank and not applied_group:
                frappe.throw(_("Planned Course row {0}: Choice Rank requires an Applied Basket Group.").format(idx))

            if (self.status or "").strip() in gate_statuses and len(allowed_groups) > 1 and not applied_group:
                frappe.throw(
                    _("Planned Course row {0}: select an Applied Basket Group for course {1}.").format(idx, course)
                )

    def _validate_status(self):
        status = (self.status or "Draft").strip() or "Draft"
        if status not in STATUS_OPTIONS:
            frappe.throw(_("Invalid Applicant Enrollment Plan status: {0}.").format(status))
        self.status = status

        if status in {"Ready for Committee", "Committee Approved", "Offer Sent", "Offer Accepted", "Hydrated"}:
            if not self.academic_year:
                frappe.throw(_("Academic Year is required before the plan can advance to {0}.").format(status))
            if not self.program_offering:
                frappe.throw(_("Program Offering is required before the plan can advance to {0}.").format(status))

        applicant_status = frappe.db.get_value("Student Applicant", self.student_applicant, "application_status")
        if status in {"Committee Approved", "Offer Sent", "Offer Accepted", "Hydrated"}:
            if applicant_status != "Approved":
                frappe.throw(_("Student Applicant must be Approved before the plan can advance to {0}.").format(status))

        if status == "Hydrated" and not self.program_enrollment_request:
            frappe.throw(_("Program Enrollment Request is required before marking the plan as Hydrated."))

    def _validate_single_active_plan(self):
        if self.status in TERMINAL_STATUSES:
            return
        rows = frappe.get_all(
            "Applicant Enrollment Plan",
            filters={"student_applicant": self.student_applicant},
            fields=["name", "status"],
            order_by="creation desc",
        )
        for row in rows:
            if row.get("name") == self.name:
                continue
            if (row.get("status") or "").strip() in TERMINAL_STATUSES:
                continue
            frappe.throw(
                _("Student Applicant {0} already has an active Applicant Enrollment Plan ({1}).").format(
                    self.student_applicant, row.get("name")
                )
            )

    def _validate_offer_expiry(self):
        if not self.offer_expires_on:
            return
        if self.status == "Offer Sent" and getdate(self.offer_expires_on) < getdate(nowdate()):
            frappe.throw(_("Offer expiry cannot be in the past while the offer is still open."))

    def _apply_deposit_defaults_if_needed(self):
        default_row = get_deposit_default_for_plan(self)
        if not default_row or self.deposit_invoice:
            return

        before = self.get_doc_before_save() if self.name else None
        has_any_deposit_terms = bool(
            cint(self.deposit_required or 0)
            or flt(self.deposit_amount or 0)
            or _as_clean_text(self.deposit_due_date)
            or _as_clean_text(self.deposit_billable_offering)
        )

        if not before and not has_any_deposit_terms:
            self.deposit_required = 1 if cint(default_row.get("deposit_required") or 0) else 0
            self.deposit_amount = _as_money(default_row.get("deposit_amount"))
            self.deposit_billable_offering = _as_clean_text(default_row.get("deposit_billable_offering"))

        if not cint(self.deposit_required or 0):
            return

        if not flt(self.deposit_amount or 0) and cint(default_row.get("deposit_required") or 0):
            self.deposit_amount = _as_money(default_row.get("deposit_amount"))
        if not _as_clean_text(self.deposit_billable_offering):
            self.deposit_billable_offering = _as_clean_text(default_row.get("deposit_billable_offering"))
        if not self.deposit_due_date:
            due_date = _default_deposit_due_date(self, default_row)
            if due_date:
                self.deposit_due_date = due_date

    def _sync_deposit_override_state(self):
        default_row = get_deposit_default_for_plan(self)
        matches_default = _deposit_terms_match_default(self, default_row)
        default_required = bool(cint((default_row or {}).get("deposit_required") or 0))
        deposit_required = bool(cint(self.deposit_required or 0))

        if matches_default or (not deposit_required and not default_required):
            self.deposit_terms_source = "School Default"
            self.deposit_override_status = "Not Required"
            self.deposit_academic_approved_by = None
            self.deposit_academic_approved_on = None
            self.deposit_finance_approved_by = None
            self.deposit_finance_approved_on = None
            return

        self.deposit_terms_source = "Manual Override"
        terms_changed = _deposit_terms_changed_since_previous(self)
        if terms_changed:
            self.deposit_academic_approved_by = None
            self.deposit_academic_approved_on = None
            self.deposit_finance_approved_by = None
            self.deposit_finance_approved_on = None

        if (
            not terms_changed
            and (self.deposit_override_status or "").strip() == "Rejected"
            and not (self.deposit_academic_approved_by or self.deposit_finance_approved_by)
        ):
            return

        if self.deposit_academic_approved_by and self.deposit_finance_approved_by:
            self.deposit_override_status = "Approved"
        else:
            self.deposit_override_status = "Pending"

    def _validate_deposit_terms(self):
        self._apply_deposit_defaults_if_needed()
        self._sync_deposit_override_state()

        if not cint(self.deposit_required or 0):
            return

        if flt(self.deposit_amount or 0) <= 0:
            frappe.throw(_("Deposit Amount must be greater than zero when a deposit is required."))

        if not _as_clean_text(self.deposit_billable_offering):
            frappe.throw(_("Deposit Billable Offering is required when a deposit is required."))

        if (self.status or "").strip() in {"Offer Accepted", "Hydrated"} and not self.deposit_due_date:
            frappe.throw(_("Deposit Due Date is required once the offer is accepted."))

        offering = frappe.db.get_value(
            "Billable Offering",
            self.deposit_billable_offering,
            ["organization", "disabled", "offering_type"],
            as_dict=True,
        )
        if not offering:
            frappe.throw(_("Deposit Billable Offering {0} was not found.").format(self.deposit_billable_offering))
        if offering.get("organization") != self.organization:
            frappe.throw(_("Deposit Billable Offering must belong to the Applicant Enrollment Plan Organization."))
        if cint(offering.get("disabled") or 0):
            frappe.throw(_("Deposit Billable Offering is disabled."))
        if (offering.get("offering_type") or "").strip() == "Program":
            frappe.throw(_("Admissions deposit Billable Offering must be a one-off fee, not a Program offering."))

    def _ensure_deposit_override_pending(self):
        if not cint(self.deposit_required or 0):
            frappe.throw(_("No deposit override is required for this plan."))
        if (self.deposit_terms_source or "").strip() != "Manual Override":
            frappe.throw(_("Deposit terms match the school default and do not require override approval."))
        if (self.deposit_override_status or "").strip() == "Approved":
            frappe.throw(_("Deposit override is already approved."))
        if not _as_clean_text(self.deposit_override_reason):
            frappe.throw(_("Deposit Override Reason is required before approval."))

    def _ensure_deposit_approval_role(self, allowed_roles: set[str], message: str):
        user = _as_clean_text(frappe.session.user)
        roles = set(frappe.get_roles(user))
        if user == "Administrator" or "System Manager" in roles:
            return
        if not (roles & allowed_roles):
            frappe.throw(message, frappe.PermissionError)

        employee = frappe.db.get_value(
            "Employee",
            {"user_id": user, "employment_status": "Active"},
            ["organization", "school"],
            as_dict=True,
        )
        if not employee:
            frappe.throw(_("Your user must be linked to an active Employee profile."), frappe.PermissionError)

        org_scope = set(get_organization_descendants_including_self(employee.get("organization")) or [])
        if self.organization and (not org_scope or self.organization not in org_scope):
            frappe.throw(_("Your Organization scope does not cover this deposit override."), frappe.PermissionError)

        employee_school = _as_clean_text(employee.get("school"))
        if employee_school:
            school_scope = set(get_school_descendants_including_self(employee_school) or [])
            if self.school and school_scope and self.school not in school_scope:
                frappe.throw(_("Your School scope does not cover this deposit override."), frappe.PermissionError)

    def _ensure_staff_role(self):
        roles = set(frappe.get_roles(frappe.session.user))
        if roles & STAFF_ROLES:
            return
        frappe.throw(_("You do not have permission to manage Applicant Enrollment Plans."), frappe.PermissionError)

    def _ensure_portal_offer_actor(self, user: str):
        user = (user or "").strip()
        if not user:
            frappe.throw(_("You must be signed in to respond to an offer."), frappe.PermissionError)

        roles = set(frappe.get_roles(user))
        if PORTAL_ROLE not in roles:
            frappe.throw(_("You do not have permission to respond to this offer."), frappe.PermissionError)

        applicant_row = (
            frappe.db.get_value(
                "Student Applicant",
                self.student_applicant,
                ["applicant_user", "application_status"],
                as_dict=True,
            )
            or {}
        )
        if (applicant_row.get("applicant_user") or "").strip() != user:
            frappe.throw(_("You do not have permission to respond to this offer."), frappe.PermissionError)
        if (applicant_row.get("application_status") or "").strip() != "Approved":
            frappe.throw(_("The applicant must be Approved before the offer can be answered."))

    @frappe.whitelist()
    def mark_ready_for_committee(self):
        self._ensure_staff_role()
        if self.status != "Draft":
            frappe.throw(_("Only Draft plans can be marked Ready for Committee."))
        self.status = "Ready for Committee"
        self.save(ignore_permissions=True)
        return {"ok": True, "status": self.status}

    @frappe.whitelist()
    def approve_committee(self):
        self._ensure_staff_role()
        if self.status != "Ready for Committee":
            frappe.throw(_("Only Ready for Committee plans can be approved."))
        applicant_status = frappe.db.get_value("Student Applicant", self.student_applicant, "application_status")
        if applicant_status != "Approved":
            frappe.throw(_("Student Applicant must be Approved before committee approval can be recorded."))
        self.status = "Committee Approved"
        self.save(ignore_permissions=True)
        return {"ok": True, "status": self.status}

    @frappe.whitelist()
    def send_offer(self):
        self._ensure_staff_role()
        if self.status != "Committee Approved":
            frappe.throw(_("Only Committee Approved plans can send an offer."))
        self.status = "Offer Sent"
        self.offer_sent_on = now_datetime()
        self.offer_sent_by = frappe.session.user
        self.save(ignore_permissions=True)
        return {"ok": True, "status": self.status}

    def accept_offer(self, *, user: str):
        self._ensure_portal_offer_actor(user)
        if self.status == "Offer Accepted":
            return {"ok": True, "status": self.status}
        if self.status != "Offer Sent":
            frappe.throw(_("This offer is not open for acceptance."))
        if self.offer_expires_on and getdate(self.offer_expires_on) < getdate(nowdate()):
            frappe.throw(_("This offer has expired."))
        self._ensure_offer_response_ready()
        self.status = "Offer Accepted"
        self.offer_accepted_on = now_datetime()
        self.offer_accepted_by = user
        self.save(ignore_permissions=True)
        return {"ok": True, "status": self.status}

    def decline_offer(self, *, user: str):
        self._ensure_portal_offer_actor(user)
        if self.status == "Offer Declined":
            return {"ok": True, "status": self.status}
        if self.status != "Offer Sent":
            frappe.throw(_("This offer is not open for decline."))
        self.status = "Offer Declined"
        self.offer_declined_on = now_datetime()
        self.offer_declined_by = user
        self.save(ignore_permissions=True)
        return {"ok": True, "status": self.status}

    @frappe.whitelist()
    def hydrate_program_enrollment_request(self):
        self._ensure_staff_role()
        return hydrate_program_enrollment_request_from_applicant_plan(self.name)

    @frappe.whitelist()
    def approve_deposit_academic_override(self):
        self._ensure_deposit_approval_role(
            DEPOSIT_ACADEMIC_APPROVER_ROLES,
            _("Only Academic Admin or System Manager can approve the academic side of a deposit override."),
        )
        self._ensure_deposit_override_pending()
        self.deposit_academic_approved_by = frappe.session.user
        self.deposit_academic_approved_on = now_datetime()
        self.save(ignore_permissions=True)
        return {"ok": True, "deposit_override_status": self.deposit_override_status}

    @frappe.whitelist()
    def approve_deposit_finance_override(self):
        self._ensure_deposit_approval_role(
            DEPOSIT_FINANCE_APPROVER_ROLES,
            _("Only Accounts Manager or System Manager can approve the finance side of a deposit override."),
        )
        self._ensure_deposit_override_pending()
        self.deposit_finance_approved_by = frappe.session.user
        self.deposit_finance_approved_on = now_datetime()
        self.save(ignore_permissions=True)
        return {"ok": True, "deposit_override_status": self.deposit_override_status}

    @frappe.whitelist()
    def reject_deposit_override(self):
        self._ensure_deposit_approval_role(
            DEPOSIT_ACADEMIC_APPROVER_ROLES | DEPOSIT_FINANCE_APPROVER_ROLES,
            _("Only Academic Admin, Accounts Manager, or System Manager can reject a deposit override."),
        )
        if (self.deposit_terms_source or "").strip() != "Manual Override":
            frappe.throw(_("Only manual deposit overrides can be rejected."))
        self.deposit_override_status = "Rejected"
        self.deposit_academic_approved_by = None
        self.deposit_academic_approved_on = None
        self.deposit_finance_approved_by = None
        self.deposit_finance_approved_on = None
        self.save(ignore_permissions=True)
        return {"ok": True, "deposit_override_status": self.deposit_override_status}

    @frappe.whitelist()
    def generate_deposit_invoice(self):
        return generate_deposit_invoice_from_offer(self.name)

    def _ensure_offer_response_ready(self):
        choice_state = get_applicant_enrollment_choice_state(self)
        validation = choice_state.get("validation") or {}
        if validation.get("ready_for_offer_response"):
            return

        reasons = [reason for reason in (validation.get("reasons") or []) if reason]
        if not reasons:
            frappe.throw(_("Complete your course choices before accepting the offer."))

        reason_lines = "\n".join(f"- {reason}" for reason in reasons[:3])
        frappe.throw(_("Complete your course choices before accepting the offer.") + "\n" + reason_lines)

    def update_portal_choices(self, *, user: str, courses: list[dict] | None = None):
        self._ensure_portal_offer_actor(user)
        if (self.status or "").strip() != "Offer Sent":
            frappe.throw(_("Course choices can only be updated while the offer is open."))
        if not self.program_offering:
            frappe.throw(_("Program Offering is required before course choices can be updated."))

        seen_courses = set()
        duplicate_courses = set()
        for row in courses or []:
            course = ((row or {}).get("course") or "").strip()
            if not course:
                continue
            if course in seen_courses:
                duplicate_courses.add(course)
                continue
            seen_courses.add(course)
        if duplicate_courses:
            frappe.throw(
                _("Each selected course can only be submitted once: {0}.").format(", ".join(sorted(duplicate_courses)))
            )

        submitted_rows = _normalize_plan_rows(courses or [])
        submitted_by_course = {row["course"]: row for row in submitted_rows}
        offering_semantics = get_offering_course_semantics(self.program_offering)
        allowed_courses = set(offering_semantics.keys())
        unknown_courses = sorted(course for course in submitted_by_course if course not in allowed_courses)
        if unknown_courses:
            frappe.throw(
                _("One or more selected courses are not part of this Program Offering: {0}.").format(
                    ", ".join(unknown_courses)
                )
            )

        rows_to_store = []
        for course, semantics in offering_semantics.items():
            submitted = submitted_by_course.get(course)
            if semantics.get("required"):
                if not submitted:
                    continue
                if not (submitted.get("applied_basket_group") or submitted.get("choice_rank") is not None):
                    continue
                rows_to_store.append(
                    {
                        "course": course,
                        "applied_basket_group": submitted.get("applied_basket_group") or "",
                        "choice_rank": submitted.get("choice_rank"),
                    }
                )
                continue

            if not submitted:
                continue

            rows_to_store.append(
                {
                    "course": course,
                    "applied_basket_group": submitted.get("applied_basket_group") or "",
                    "choice_rank": submitted.get("choice_rank"),
                }
            )

        self.set("courses", rows_to_store)
        self.save(ignore_permissions=True)
        self.reload()
        return get_applicant_enrollment_choice_state(self)


def _get_unique_courses(rows) -> list[str]:
    output: list[str] = []
    seen = set()
    for row in rows or []:
        course = ((row or {}).get("course") or "").strip()
        if not course or course in seen:
            continue
        seen.add(course)
        output.append(course)
    return output


def _get_required_offering_courses(program_offering: str) -> list[str]:
    return _get_unique_courses(
        frappe.get_all(
            "Program Offering Course",
            filters={
                "parent": program_offering,
                "parenttype": "Program Offering",
                "required": 1,
            },
            fields=["course"],
            order_by="idx asc",
        )
    )


def get_active_applicant_enrollment_plan(student_applicant: str) -> ApplicantEnrollmentPlan | None:
    plan_name = get_active_applicant_enrollment_plan_name(student_applicant)
    if not plan_name:
        return None
    return frappe.get_doc("Applicant Enrollment Plan", plan_name)


def get_latest_applicant_enrollment_plan(
    student_applicant: str, statuses: set[str] | None = None
) -> ApplicantEnrollmentPlan | None:
    plan_name = get_latest_applicant_enrollment_plan_name(student_applicant, statuses=statuses)
    if not plan_name:
        return None
    return frappe.get_doc("Applicant Enrollment Plan", plan_name)


def get_latest_applicant_enrollment_plan_name(student_applicant: str, statuses: set[str] | None = None) -> str:
    return get_active_applicant_enrollment_plan_name(
        student_applicant,
        statuses=statuses,
        include_terminal=True,
    )


def get_active_applicant_enrollment_plan_name(
    student_applicant: str,
    statuses: set[str] | None = None,
    include_terminal: bool = False,
) -> str:
    if not student_applicant:
        return ""

    rows = frappe.get_all(
        "Applicant Enrollment Plan",
        filters={"student_applicant": student_applicant},
        fields=["name", "status"],
        order_by="creation desc",
        limit=20,
    )
    for row in rows:
        status = (row.get("status") or "").strip()
        if statuses is not None and status not in statuses:
            continue
        if not include_terminal and statuses is None and status in TERMINAL_STATUSES:
            continue
        return (row.get("name") or "").strip()
    return ""


def ensure_applicant_enrollment_plan(student_applicant: str) -> ApplicantEnrollmentPlan:
    existing_name = get_active_applicant_enrollment_plan_name(student_applicant)
    if existing_name:
        return frappe.get_doc("Applicant Enrollment Plan", existing_name)

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    doc = frappe.get_doc(
        {
            "doctype": "Applicant Enrollment Plan",
            "student_applicant": applicant.name,
            "academic_year": applicant.academic_year,
            "term": applicant.term,
            "program": applicant.program,
            "program_offering": applicant.program_offering,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc


def _applicant_display_name(applicant) -> str:
    parts = [
        _as_clean_text(getattr(applicant, "first_name", "")),
        _as_clean_text(getattr(applicant, "middle_name", "")),
        _as_clean_text(getattr(applicant, "last_name", "")),
    ]
    return " ".join(part for part in parts if part).strip() or applicant.name


def _validate_account_holder_scope(account_holder: str, organization: str) -> dict:
    row = frappe.db.get_value(
        "Account Holder",
        account_holder,
        ["name", "organization", "status"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Account Holder {0} was not found.").format(account_holder))
    if row.get("organization") != organization:
        frappe.throw(_("Account Holder must belong to the same Organization as the applicant."))
    if (row.get("status") or "").strip() == "Inactive":
        frappe.throw(_("Account Holder is inactive."))
    return row


def _guardian_account_holder_seed(applicant) -> dict:
    rows = list(applicant.get("guardians") or [])
    rows.sort(
        key=lambda row: (
            0 if cint(row.get("is_financial_guardian") or 0) else 1,
            0 if cint(row.get("is_primary") or row.get("is_primary_guardian") or 0) else 1,
            row.idx or 0,
        )
    )

    for row in rows:
        if row.get("guardian"):
            guardian = frappe.db.get_value(
                "Guardian",
                row.get("guardian"),
                [
                    "guardian_full_name",
                    "guardian_first_name",
                    "guardian_last_name",
                    "guardian_email",
                    "guardian_mobile_phone",
                ],
                as_dict=True,
            )
            if guardian:
                name_parts = [
                    _as_clean_text(guardian.get("guardian_first_name")),
                    _as_clean_text(guardian.get("guardian_last_name")),
                ]
                return {
                    "name": _as_clean_text(guardian.get("guardian_full_name"))
                    or " ".join(part for part in name_parts if part).strip()
                    or _as_clean_text(row.get("guardian")),
                    "email": _as_clean_text(guardian.get("guardian_email")),
                    "phone": _as_clean_text(guardian.get("guardian_mobile_phone")),
                }

        row_name_parts = [
            _as_clean_text(row.get("guardian_first_name")),
            _as_clean_text(row.get("guardian_last_name")),
        ]
        row_name = (
            _as_clean_text(row.get("guardian_full_name")) or " ".join(part for part in row_name_parts if part).strip()
        )
        if row_name or row.get("guardian_email") or row.get("guardian_mobile_phone"):
            return {
                "name": row_name,
                "email": _as_clean_text(row.get("guardian_email")),
                "phone": _as_clean_text(row.get("guardian_mobile_phone")),
            }

    return {
        "name": "",
        "email": _as_clean_text(getattr(applicant, "applicant_email", "")),
        "phone": "",
    }


def get_or_create_account_holder_for_applicant(student_applicant) -> str:
    applicant = (
        frappe.get_doc("Student Applicant", student_applicant)
        if isinstance(student_applicant, str)
        else student_applicant
    )
    existing = _as_clean_text(getattr(applicant, "account_holder", ""))
    if existing:
        _validate_account_holder_scope(existing, applicant.organization)
        return existing

    seed = _guardian_account_holder_seed(applicant)
    holder_name = _as_clean_text(seed.get("name")) or _("{applicant_name} Family").format(
        applicant_name=_applicant_display_name(applicant)
    )
    account_holder = frappe.get_doc(
        {
            "doctype": "Account Holder",
            "organization": applicant.organization,
            "account_holder_name": holder_name,
            "account_holder_type": "Individual",
            "status": "Active",
            "primary_email": _as_clean_text(seed.get("email")),
            "primary_phone": _as_clean_text(seed.get("phone")),
            "notes": _("Created from Student Applicant {student_applicant}.").format(student_applicant=applicant.name),
        }
    )
    account_holder.insert(ignore_permissions=True)
    frappe.db.set_value("Student Applicant", applicant.name, "account_holder", account_holder.name)
    applicant.account_holder = account_holder.name
    return account_holder.name


def _account_holder_summary(account_holder: str) -> dict:
    row = frappe.db.get_value(
        "Account Holder",
        account_holder,
        [
            "name",
            "organization",
            "account_holder_name",
            "account_holder_type",
            "status",
            "primary_email",
            "primary_phone",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Account Holder {0} was not found.").format(account_holder))
    return dict(row)


def _ensure_account_holder_create_actor(applicant) -> None:
    user = _as_clean_text(frappe.session.user)
    roles = set(frappe.get_roles(user))
    if user == "Administrator" or roles & {"System Manager"}:
        return
    if not (roles & ACCOUNT_HOLDER_CREATE_ROLES):
        frappe.throw(
            _("You do not have permission to create Account Holders for applicants."),
            frappe.PermissionError,
        )
    if not has_scoped_staff_access_to_student_applicant(user=user, student_applicant=applicant.name):
        frappe.throw(
            _("You do not have permission to create an Account Holder for this applicant."),
            frappe.PermissionError,
        )


@frappe.whitelist()
def create_account_holder_for_applicant(student_applicant: str):
    applicant_name = _as_clean_text(student_applicant)
    if not applicant_name:
        frappe.throw(_("Student Applicant is required."))

    locked = frappe.db.sql(
        "select name from `tabStudent Applicant` where name = %s for update",
        (applicant_name,),
        as_dict=True,
    )
    if not locked:
        frappe.throw(_("Student Applicant {0} was not found.").format(applicant_name))

    applicant = frappe.get_doc("Student Applicant", applicant_name)
    _ensure_account_holder_create_actor(applicant)

    if _as_clean_text(getattr(applicant, "application_status", "")) in {"Rejected", "Withdrawn", "Promoted"}:
        frappe.throw(
            _("Account Holder cannot be created when the applicant is {0}.").format(applicant.application_status)
        )

    existing = _as_clean_text(getattr(applicant, "account_holder", ""))
    account_holder = get_or_create_account_holder_for_applicant(applicant)
    return {
        "ok": True,
        "created": not bool(existing),
        "student_applicant": applicant.name,
        "account_holder": _account_holder_summary(account_holder),
    }


def _ensure_deposit_invoice_actor(plan) -> None:
    user = _as_clean_text(frappe.session.user)
    roles = set(frappe.get_roles(user))
    if user == "Administrator" or roles & {"System Manager"}:
        return
    if not (roles & DEPOSIT_INVOICE_ROLES):
        frappe.throw(_("You do not have permission to generate deposit invoices."), frappe.PermissionError)
    if not has_scoped_staff_access_to_student_applicant(user=user, student_applicant=plan.student_applicant):
        frappe.throw(
            _("You do not have permission to generate a deposit invoice for this applicant."), frappe.PermissionError
        )


def _ensure_deposit_ready_for_invoice(plan) -> None:
    if (plan.status or "").strip() != "Offer Accepted":
        frappe.throw(_("Applicant Enrollment Plan must be Offer Accepted before generating a deposit invoice."))
    if not cint(plan.deposit_required or 0):
        frappe.throw(_("This offer does not require a deposit."))
    if flt(plan.deposit_amount or 0) <= 0:
        frappe.throw(_("Deposit Amount must be greater than zero."))
    if not _as_clean_text(plan.deposit_billable_offering):
        frappe.throw(_("Deposit Billable Offering is required."))
    if not plan.deposit_due_date:
        frappe.throw(_("Deposit Due Date is required."))
    if (plan.deposit_terms_source or "").strip() == "Manual Override" and (
        plan.deposit_override_status or ""
    ).strip() != "Approved":
        frappe.throw(_("Deposit override must be approved by Academic Admin and Accounts Manager before invoicing."))


def _sales_invoice_summary(invoice_name: str) -> dict:
    invoice = frappe.db.get_value(
        "Sales Invoice",
        invoice_name,
        [
            "name",
            "docstatus",
            "status",
            "grand_total",
            "paid_amount",
            "outstanding_amount",
            "due_date",
        ],
        as_dict=True,
    )
    if not invoice:
        frappe.throw(_("Linked deposit Sales Invoice {0} was not found.").format(invoice_name))
    return _invoice_summary_from_row(invoice)


@frappe.whitelist()
def generate_deposit_invoice_from_offer(applicant_enrollment_plan: str):
    plan_name = _as_clean_text(applicant_enrollment_plan)
    if not plan_name:
        frappe.throw(_("Applicant Enrollment Plan is required."))

    locked = frappe.db.sql(
        "select name from `tabApplicant Enrollment Plan` where name = %s for update",
        (plan_name,),
        as_dict=True,
    )
    if not locked:
        frappe.throw(_("Applicant Enrollment Plan {0} was not found.").format(plan_name))

    plan = frappe.get_doc("Applicant Enrollment Plan", plan_name)
    _ensure_deposit_invoice_actor(plan)
    plan.save(ignore_permissions=True)
    plan.reload()

    existing_invoice = _as_clean_text(plan.deposit_invoice)
    if existing_invoice:
        return {
            "ok": True,
            "created": False,
            "applicant_enrollment_plan": plan.name,
            "deposit": get_deposit_invoice_status_for_plan(plan),
            "invoice": _sales_invoice_summary(existing_invoice),
        }

    _ensure_deposit_ready_for_invoice(plan)

    applicant = frappe.get_doc("Student Applicant", plan.student_applicant)
    account_holder = get_or_create_account_holder_for_applicant(applicant)
    _validate_account_holder_scope(account_holder, plan.organization)

    program_offering = _as_clean_text(plan.program_offering)
    if program_offering:
        offering_school = _as_clean_text(frappe.db.get_value("Program Offering", program_offering, "school"))
        if offering_school and get_school_organization(offering_school) != plan.organization:
            frappe.throw(_("Program Offering must belong to the same Organization as the deposit invoice."))

    invoice = frappe.new_doc("Sales Invoice")
    invoice.update(
        {
            "account_holder": account_holder,
            "organization": plan.organization,
            "program_offering": program_offering or None,
            "posting_date": getdate(nowdate()),
            "due_date": getdate(plan.deposit_due_date),
            "remarks": _("Admissions deposit for {applicant_name} from Applicant Enrollment Plan {plan_name}.").format(
                applicant_name=_applicant_display_name(applicant),
                plan_name=plan.name,
            ),
        }
    )
    invoice.append(
        "items",
        {
            "billable_offering": plan.deposit_billable_offering,
            "program_offering": program_offering or None,
            "charge_source": "Program Offering" if program_offering else "Extra",
            "description": _("Admissions deposit for {applicant_name}").format(
                applicant_name=_applicant_display_name(applicant)
            ),
            "qty": 1,
            "rate": _as_money(plan.deposit_amount),
        },
    )
    invoice.insert(ignore_permissions=True)

    plan.deposit_invoice = invoice.name
    plan.save(ignore_permissions=True)
    plan.add_comment(
        "Comment",
        text=_("Deposit Sales Invoice {0} created.").format(frappe.bold(invoice.name)),
    )

    return {
        "ok": True,
        "created": True,
        "applicant_enrollment_plan": plan.name,
        "deposit": get_deposit_invoice_status_for_plan(plan),
        "invoice": _sales_invoice_summary(invoice.name),
    }


@frappe.whitelist()
def get_or_create_applicant_enrollment_plan(student_applicant: str):
    roles = set(frappe.get_roles(frappe.session.user))
    if not roles & STAFF_ROLES:
        frappe.throw(_("You do not have permission to manage Applicant Enrollment Plans."), frappe.PermissionError)
    plan = ensure_applicant_enrollment_plan(student_applicant)
    return {"name": plan.name, "status": plan.status}


@frappe.whitelist()
def hydrate_program_enrollment_request_from_applicant_plan(applicant_enrollment_plan: str):
    if not applicant_enrollment_plan:
        frappe.throw(_("Applicant Enrollment Plan is required."))
    roles = set(frappe.get_roles(frappe.session.user))
    if not roles & STAFF_ROLES:
        frappe.throw(_("You do not have permission to hydrate the enrollment request."), frappe.PermissionError)

    plan = frappe.get_doc("Applicant Enrollment Plan", applicant_enrollment_plan)
    if plan.program_enrollment_request and frappe.db.exists(
        "Program Enrollment Request", plan.program_enrollment_request
    ):
        return {"name": plan.program_enrollment_request, "created": False}

    if (plan.status or "").strip() != "Offer Accepted":
        frappe.throw(_("Applicant Enrollment Plan must be Offer Accepted before it can hydrate a request."))

    applicant = frappe.get_doc("Student Applicant", plan.student_applicant)
    student_name = (plan.student or applicant.student or "").strip()
    if not student_name:
        frappe.throw(_("Student Applicant must be promoted before the enrollment request can be hydrated."))

    effective_rows = get_effective_applicant_enrollment_plan_rows(plan)
    if not effective_rows:
        frappe.throw(
            _("Applicant Enrollment Plan has no planned courses and the Program Offering has no required courses.")
        )

    request = frappe.get_doc(
        {
            "doctype": "Program Enrollment Request",
            "student": student_name,
            "program_offering": plan.program_offering,
            "academic_year": plan.academic_year,
            "status": "Draft",
            "courses": [
                {
                    "course": row.get("course"),
                    "required": 1 if int(row.get("required") or 0) == 1 else 0,
                    "applied_basket_group": (row.get("applied_basket_group") or "").strip(),
                    "choice_rank": row.get("choice_rank"),
                }
                for row in effective_rows
            ]
            or [{"course": course, "required": 1} for course in _get_required_offering_courses(plan.program_offering)],
            "source_student_applicant": plan.student_applicant,
            "source_applicant_enrollment_plan": plan.name,
        }
    )
    request.insert(ignore_permissions=True)

    plan.status = "Hydrated"
    plan.student = student_name
    plan.program_enrollment_request = request.name
    plan.hydrated_on = now_datetime()
    plan.hydrated_by = frappe.session.user
    plan.save(ignore_permissions=True)

    return {"name": request.name, "created": True}
