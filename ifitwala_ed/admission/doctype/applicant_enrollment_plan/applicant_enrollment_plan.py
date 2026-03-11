# ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate

from ifitwala_ed.schedule.basket_group_utils import get_offering_course_semantics

STAFF_ROLES = {
    "Admission Manager",
    "Admission Officer",
    "Academic Admin",
    "Curriculum Coordinator",
    "System Manager",
    "Administrator",
}
PORTAL_ROLE = "Admissions Applicant"
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
        normalized = []
        seen = set()
        for row in self.get("courses") or []:
            course = (row.course or "").strip()
            if not course or course in seen:
                continue
            seen.add(course)
            normalized.append(
                {
                    "course": course,
                    "required": 1 if int(row.required or 0) == 1 else 0,
                    "applied_basket_group": (row.applied_basket_group or "").strip(),
                    "choice_rank": row.choice_rank,
                }
            )
        if len(normalized) == len(self.get("courses") or []):
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
        limit_page_length=20,
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

    selected_courses = _get_unique_courses(plan.get("courses") or [])
    if not selected_courses:
        selected_courses = _get_required_offering_courses((plan.program_offering or "").strip())
    if not selected_courses:
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
                    "course": row.course,
                    "required": 1 if int(row.required or 0) == 1 else 0,
                    "applied_basket_group": (row.applied_basket_group or "").strip(),
                    "choice_rank": row.choice_rank,
                }
                for row in (plan.get("courses") or [])
                if (row.course or "").strip() in selected_courses
            ]
            or [{"course": course, "required": 1} for course in selected_courses],
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
