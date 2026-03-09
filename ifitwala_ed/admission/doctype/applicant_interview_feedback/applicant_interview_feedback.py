# ifitwala_ed/admission/doctype/applicant_interview_feedback/applicant_interview_feedback.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.admission.admission_utils import (
    READ_LIKE_PERMISSION_TYPES,
    build_admissions_file_scope_exists_sql,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
)

ALLOWED_FEEDBACK_STATUS = {"Draft", "Submitted"}


class ApplicantInterviewFeedback(Document):
    def validate(self):
        self._validate_parent_interview()
        self._validate_status()
        self._validate_permissions()

    def _validate_parent_interview(self):
        interview_name = (self.applicant_interview or "").strip()
        if not interview_name:
            frappe.throw(_("Applicant Interview is required."), title=_("Missing Interview"))

        interview_row = frappe.db.get_value(
            "Applicant Interview",
            interview_name,
            ["name", "student_applicant"],
            as_dict=True,
        )
        if not interview_row:
            frappe.throw(
                _("Applicant Interview {0} was not found.").format(interview_name),
                frappe.DoesNotExistError,
            )

        student_applicant = interview_row.get("student_applicant")
        if not student_applicant:
            frappe.throw(_("The linked interview is missing a Student Applicant."), title=_("Invalid Interview"))

        if self.student_applicant and self.student_applicant != student_applicant:
            frappe.throw(_("Student Applicant must match the linked interview."), title=_("Invalid Applicant"))
        self.student_applicant = student_applicant

        if not self.interviewer_user:
            self.interviewer_user = frappe.session.user

    def _validate_status(self):
        resolved = (self.feedback_status or "Draft").strip() or "Draft"
        if resolved not in ALLOWED_FEEDBACK_STATUS:
            frappe.throw(
                _("Feedback Status must be one of: {0}.").format(", ".join(sorted(ALLOWED_FEEDBACK_STATUS))),
                title=_("Invalid Feedback Status"),
            )

        self.feedback_status = resolved

        before = self.get_doc_before_save()
        if (
            before
            and before.feedback_status == "Submitted"
            and resolved == "Draft"
            and not _is_feedback_privileged_user(frappe.session.user)
        ):
            self.feedback_status = "Submitted"

        if self.feedback_status == "Submitted":
            if not self.submitted_on:
                self.submitted_on = now_datetime()

    def _validate_permissions(self):
        current_user = (frappe.session.user or "").strip()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Please sign in to continue."), frappe.PermissionError)

        if _is_feedback_privileged_user(current_user):
            if not has_scoped_staff_access_to_student_applicant(
                user=current_user,
                student_applicant=self.student_applicant,
            ):
                frappe.throw(_("You do not have permission to edit this interview feedback."), frappe.PermissionError)
            return

        if (self.interviewer_user or "").strip() != current_user:
            frappe.throw(_("You can only edit your own interview feedback."), frappe.PermissionError)

        if not _is_interviewer_on_interview(user=current_user, interview_name=self.applicant_interview):
            frappe.throw(_("You are not assigned as an interviewer for this interview."), frappe.PermissionError)

        before = self.get_doc_before_save()
        if before and before.applicant_interview != self.applicant_interview:
            frappe.throw(_("Applicant Interview cannot be changed."), frappe.PermissionError)

        if before and before.interviewer_user != self.interviewer_user:
            frappe.throw(_("Interviewer cannot be changed."), frappe.PermissionError)


def on_doctype_update():
    frappe.db.add_unique("Applicant Interview Feedback", ["applicant_interview", "interviewer_user"])
    frappe.db.add_index("Applicant Interview Feedback", ["interviewer_user", "feedback_status"])


def get_permission_query_conditions(user: str | None = None) -> str | None:
    user = (user or frappe.session.user or "").strip()
    if not user or user == "Guest":
        return "1=0"

    conditions: list[str] = []
    if _is_feedback_privileged_user(user):
        staff_condition = build_admissions_file_scope_exists_sql(
            user=user,
            student_applicant_expr_sql="`tabApplicant Interview Feedback`.`student_applicant`",
        )
        if staff_condition is None:
            return None
        if staff_condition != "1=0":
            conditions.append(f"({staff_condition})")

    escaped_user = frappe.db.escape(user)
    interviewer_condition = (
        "(`tabApplicant Interview Feedback`.`interviewer_user` = {user} "
        "AND exists ("
        "select 1 from `tabApplicant Interviewer` ai "
        "where ai.parent = `tabApplicant Interview Feedback`.`applicant_interview` "
        "and ai.parenttype = 'Applicant Interview' "
        "and ai.parentfield = 'interviewers' "
        "and ai.interviewer = {user}"
        "))"
    ).format(user=escaped_user)
    conditions.append(f"({interviewer_condition})")
    return " OR ".join(conditions) if conditions else "1=0"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    user = (user or frappe.session.user or "").strip()
    op = (ptype or "read").lower()

    if not user or user == "Guest":
        return False
    if _is_feedback_privileged_user(user):
        valid_staff_ops = READ_LIKE_PERMISSION_TYPES | {"write", "create", "delete", "submit", "cancel", "amend"}
        if op not in valid_staff_ops:
            return False
        if op == "create":
            if not doc:
                return True
        if not doc:
            return True
        student_applicant = _resolve_feedback_student_applicant(doc)
        return has_scoped_staff_access_to_student_applicant(user=user, student_applicant=student_applicant)

    if op in {"delete", "submit", "cancel", "amend"}:
        return False

    if op == "create":
        if not doc:
            return bool(
                frappe.db.exists(
                    "Applicant Interviewer",
                    {
                        "parenttype": "Applicant Interview",
                        "parentfield": "interviewers",
                        "interviewer": user,
                    },
                )
            )

        if isinstance(doc, str):
            return False

        interview_name = _extract_doc_field(doc, "applicant_interview")
        interviewer_user = _extract_doc_field(doc, "interviewer_user") or user
        if interviewer_user != user:
            return False
        return _is_interviewer_on_interview(user=user, interview_name=interview_name)

    read_like = READ_LIKE_PERMISSION_TYPES | {"write"}
    if op not in read_like:
        return False

    if not doc:
        return bool(
            frappe.db.exists(
                "Applicant Interview Feedback",
                {
                    "interviewer_user": user,
                },
            )
        )

    if isinstance(doc, str):
        row = frappe.db.get_value(
            "Applicant Interview Feedback",
            doc,
            ["applicant_interview", "interviewer_user"],
            as_dict=True,
        )
        if not row:
            return False
        interview_name = (row.get("applicant_interview") or "").strip()
        interviewer_user = (row.get("interviewer_user") or "").strip()
    else:
        interview_name = _extract_doc_field(doc, "applicant_interview")
        interviewer_user = _extract_doc_field(doc, "interviewer_user")

    if interviewer_user != user:
        return False

    return _is_interviewer_on_interview(user=user, interview_name=interview_name)


def _extract_doc_field(doc, fieldname: str) -> str:
    if isinstance(doc, dict):
        return (doc.get(fieldname) or "").strip()
    return (getattr(doc, fieldname, None) or "").strip()


def _is_feedback_privileged_user(user: str) -> bool:
    return is_admissions_file_staff_user(user)


def _resolve_feedback_student_applicant(doc) -> str:
    if isinstance(doc, str):
        feedback_name = (doc or "").strip()
        if not feedback_name:
            return ""
        return (frappe.db.get_value("Applicant Interview Feedback", feedback_name, "student_applicant") or "").strip()

    student_applicant = _extract_doc_field(doc, "student_applicant")
    if student_applicant:
        return student_applicant

    interview_name = _extract_doc_field(doc, "applicant_interview")
    if interview_name:
        return (frappe.db.get_value("Applicant Interview", interview_name, "student_applicant") or "").strip()
    return ""


def _is_interviewer_on_interview(*, user: str, interview_name: str) -> bool:
    resolved_user = (user or "").strip()
    resolved_name = (interview_name or "").strip()
    if not resolved_user or not resolved_name:
        return False

    return bool(
        frappe.db.exists(
            "Applicant Interviewer",
            {
                "parent": resolved_name,
                "parenttype": "Applicant Interview",
                "parentfield": "interviewers",
                "interviewer": resolved_user,
            },
        )
    )
