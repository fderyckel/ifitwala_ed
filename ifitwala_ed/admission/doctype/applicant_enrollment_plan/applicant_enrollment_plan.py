# ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate

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

    if rank <= 0:
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
