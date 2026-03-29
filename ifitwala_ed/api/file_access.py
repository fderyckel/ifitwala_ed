# ifitwala_ed/api/file_access.py

from __future__ import annotations

import mimetypes
import os
from urllib.parse import urlencode

import frappe
from frappe import _

from ifitwala_ed.admission.access import (
    ADMISSIONS_APPLICANT_ROLE,
    ADMISSIONS_FAMILY_ROLE,
    user_can_access_student_applicant,
)
from ifitwala_ed.admission.admission_utils import (
    has_open_applicant_review_access,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
)
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org

ADMISSIONS_ATTACHMENT_DOCTYPES = {"Applicant Document Item", "Student Applicant", "Contact"}
CONTEXT_STUDENT_APPLICANT = "Student Applicant"
CONTEXT_APPLICANT_INTERVIEW = "Applicant Interview"
CONTEXT_TASK_SUBMISSION = "Task Submission"
CONTEXT_STUDENT_PORTFOLIO_ITEM = "Student Portfolio Item"
CONTEXT_STUDENT = "Student"
CONTEXT_GUARDIAN = "Guardian"
CONTEXT_EMPLOYEE = "Employee"


def build_admissions_file_open_url(
    *,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str:
    resolved_file = (file_name or "").strip()
    if not resolved_file:
        return ""

    params = {"file": resolved_file}
    if (context_doctype or "").strip():
        params["context_doctype"] = context_doctype.strip()
    if (context_name or "").strip():
        params["context_name"] = context_name.strip()
    return f"/api/method/ifitwala_ed.api.file_access.download_admissions_file?{urlencode(params)}"


def resolve_admissions_file_open_url(
    *,
    file_name: str | None,
    file_url: str | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if raw_url.startswith(("http://", "https://")):
        return raw_url

    resolved_name = (file_name or "").strip()
    if not resolved_name:
        return raw_url or None

    open_url = build_admissions_file_open_url(
        file_name=resolved_name,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    return open_url or raw_url or None


def build_academic_file_open_url(
    *,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
) -> str:
    resolved_file = (file_name or "").strip()
    if not resolved_file:
        return ""

    params = {"file": resolved_file}
    if (context_doctype or "").strip():
        params["context_doctype"] = context_doctype.strip()
    if (context_name or "").strip():
        params["context_name"] = context_name.strip()
    if (share_token or "").strip():
        params["share_token"] = share_token.strip()
    if (viewer_email or "").strip():
        params["viewer_email"] = viewer_email.strip()
    return f"/api/method/ifitwala_ed.api.file_access.download_academic_file?{urlencode(params)}"


def resolve_academic_file_open_url(
    *,
    file_name: str | None,
    file_url: str | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if raw_url.startswith(("http://", "https://")):
        return raw_url

    resolved_name = (file_name or "").strip()
    if not resolved_name:
        return raw_url or None

    open_url = build_academic_file_open_url(
        file_name=resolved_name,
        context_doctype=context_doctype,
        context_name=context_name,
        share_token=share_token,
        viewer_email=viewer_email,
    )
    return open_url or raw_url or None


def build_guardian_file_open_url(
    *,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str:
    resolved_file = (file_name or "").strip()
    if not resolved_file:
        return ""

    params = {"file": resolved_file}
    if (context_doctype or "").strip():
        params["context_doctype"] = context_doctype.strip()
    if (context_name or "").strip():
        params["context_name"] = context_name.strip()
    return f"/api/method/ifitwala_ed.api.file_access.download_guardian_file?{urlencode(params)}"


def resolve_guardian_file_open_url(
    *,
    file_name: str | None,
    file_url: str | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if raw_url.startswith(("http://", "https://")):
        return raw_url

    resolved_name = (file_name or "").strip()
    if not resolved_name:
        return raw_url or None

    open_url = build_guardian_file_open_url(
        file_name=resolved_name,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    return open_url or raw_url or None


def build_employee_file_open_url(
    *,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str:
    resolved_file = (file_name or "").strip()
    if not resolved_file:
        return ""

    params = {"file": resolved_file}
    if (context_doctype or "").strip():
        params["context_doctype"] = context_doctype.strip()
    if (context_name or "").strip():
        params["context_name"] = context_name.strip()
    return f"/api/method/ifitwala_ed.api.file_access.download_employee_file?{urlencode(params)}"


def resolve_employee_file_open_url(
    *,
    file_name: str | None,
    file_url: str | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if raw_url.startswith(("http://", "https://")):
        return raw_url

    resolved_name = (file_name or "").strip()
    if not resolved_name:
        return raw_url or None

    open_url = build_employee_file_open_url(
        file_name=resolved_name,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    return open_url or raw_url or None


def _require_authenticated_user() -> str:
    user = (frappe.session.user or "").strip()
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to access this file."), frappe.PermissionError)
    return user


def _is_adminish(user: str) -> bool:
    return user == "Administrator" or ("System Manager" in frappe.get_roles(user))


def _resolve_file_row(file_name: str) -> dict:
    row = frappe.db.get_value(
        "File",
        file_name,
        [
            "name",
            "file_url",
            "file_name",
            "is_private",
            "attached_to_doctype",
            "attached_to_name",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("File not found."), frappe.DoesNotExistError)
    if (row.get("attached_to_doctype") or "").strip() not in ADMISSIONS_ATTACHMENT_DOCTYPES:
        frappe.throw(_("Not permitted for this file."), frappe.PermissionError)
    return row


def _resolve_any_file_row(file_name: str) -> dict:
    row = frappe.db.get_value(
        "File",
        file_name,
        [
            "name",
            "file_url",
            "file_name",
            "is_private",
            "attached_to_doctype",
            "attached_to_name",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("File not found."), frappe.DoesNotExistError)
    return row


def _resolve_guardian_from_file(file_row: dict) -> str:
    file_name = (file_row.get("name") or "").strip()
    if file_name:
        classification = frappe.db.get_value(
            "File Classification",
            {"file": file_name},
            ["primary_subject_type", "primary_subject_id"],
            as_dict=True,
        )
        if classification and (classification.get("primary_subject_type") or "").strip() == CONTEXT_GUARDIAN:
            resolved = (classification.get("primary_subject_id") or "").strip()
            if resolved:
                return resolved

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    if attached_to_doctype == CONTEXT_GUARDIAN and attached_to_name:
        return attached_to_name

    frappe.throw(_("File is missing guardian ownership context."), frappe.ValidationError)


def _resolve_employee_from_file(file_row: dict) -> str:
    file_name = (file_row.get("name") or "").strip()
    if file_name:
        classification = frappe.db.get_value(
            "File Classification",
            {"file": file_name},
            ["primary_subject_type", "primary_subject_id"],
            as_dict=True,
        )
        if classification and (classification.get("primary_subject_type") or "").strip() == CONTEXT_EMPLOYEE:
            resolved = (classification.get("primary_subject_id") or "").strip()
            if resolved:
                return resolved

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    if attached_to_doctype == CONTEXT_EMPLOYEE and attached_to_name:
        return attached_to_name

    frappe.throw(_("File is missing employee ownership context."), frappe.ValidationError)


def _assert_employee_file_access(
    *, user: str, file_employee: str, context_doctype: str | None, context_name: str | None
) -> None:
    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()
    if resolved_context:
        if resolved_context != CONTEXT_EMPLOYEE:
            frappe.throw(_("Unsupported employee file context."), frappe.ValidationError)
        if not resolved_name:
            frappe.throw(_("Context Name is required for Employee access."), frappe.ValidationError)
        if resolved_name != file_employee:
            frappe.throw(_("File does not belong to this Employee context."), frappe.PermissionError)

    if _is_adminish(user):
        return

    employee_row = frappe.db.get_value(
        "Employee",
        file_employee,
        ["name", "organization", "user_id"],
        as_dict=True,
    )
    if not employee_row:
        frappe.throw(_("Employee not found."), frappe.DoesNotExistError)

    if (employee_row.get("user_id") or "").strip() == user:
        return

    base_org = (get_user_base_org(user) or "").strip()
    if not base_org:
        frappe.throw(_("You do not have permission to access this employee file."), frappe.PermissionError)

    target_org = (employee_row.get("organization") or "").strip()
    if not target_org:
        frappe.throw(_("You do not have permission to access this employee file."), frappe.PermissionError)

    allowed_orgs = {item for item in (get_descendant_organizations(base_org) or []) if item}
    if target_org in allowed_orgs:
        return

    frappe.throw(_("You do not have permission to access this employee file."), frappe.PermissionError)


def _assert_guardian_file_access(
    *, user: str, file_guardian: str, context_doctype: str | None, context_name: str | None
):
    linked_guardian = (frappe.db.get_value("Guardian", {"user": user}, "name") or "").strip()
    if not linked_guardian:
        frappe.throw(_("This account is not linked to a Guardian record."), frappe.PermissionError)

    if linked_guardian != file_guardian:
        frappe.throw(_("You do not have permission to access this guardian file."), frappe.PermissionError)

    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()
    if not resolved_context:
        return

    if resolved_context != CONTEXT_GUARDIAN:
        frappe.throw(_("Unsupported guardian file context."), frappe.ValidationError)

    if not resolved_name:
        frappe.throw(_("Context Name is required for Guardian access."), frappe.ValidationError)

    if resolved_name != file_guardian:
        frappe.throw(_("File does not belong to this Guardian context."), frappe.PermissionError)


def _resolve_student_applicant_from_file(file_row: dict) -> str:
    file_name = (file_row.get("name") or "").strip()
    if file_name:
        classification = frappe.db.get_value(
            "File Classification",
            {"file": file_name},
            ["primary_subject_type", "primary_subject_id"],
            as_dict=True,
        )
        if classification and (classification.get("primary_subject_type") or "").strip() == "Student Applicant":
            resolved = (classification.get("primary_subject_id") or "").strip()
            if resolved:
                return resolved

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    if not attached_to_name:
        frappe.throw(_("File attachment context is incomplete."), frappe.ValidationError)

    if attached_to_doctype == "Applicant Document Item":
        applicant_document = frappe.db.get_value("Applicant Document Item", attached_to_name, "applicant_document")
        student_applicant = (
            frappe.db.get_value("Applicant Document", applicant_document, "student_applicant")
            if applicant_document
            else None
        )
    elif attached_to_doctype == "Student Applicant":
        student_applicant = attached_to_name
    else:
        student_applicant = None

    resolved = (student_applicant or "").strip()
    if not resolved:
        frappe.throw(_("File is missing admissions ownership context."), frappe.ValidationError)
    return resolved


def _is_student_applicant_self_user(*, student_applicant: str, user: str) -> bool:
    return user_can_access_student_applicant(user=user, student_applicant=student_applicant)


def _assert_can_access_student_applicant(*, user: str, student_applicant: str) -> None:
    if is_admissions_file_staff_user(user):
        if has_scoped_staff_access_to_student_applicant(user=user, student_applicant=student_applicant):
            return
        frappe.throw(_("You do not have permission to access this applicant file."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & {ADMISSIONS_APPLICANT_ROLE, ADMISSIONS_FAMILY_ROLE} and _is_student_applicant_self_user(
        student_applicant=student_applicant,
        user=user,
    ):
        return

    if has_open_applicant_review_access(user=user, student_applicant=student_applicant):
        return

    frappe.throw(_("You do not have permission to access this applicant file."), frappe.PermissionError)


def _is_interviewer_on_interview(*, user: str, interview_name: str) -> bool:
    return bool(
        frappe.db.exists(
            "Applicant Interviewer",
            {
                "parent": interview_name,
                "parenttype": "Applicant Interview",
                "parentfield": "interviewers",
                "interviewer": user,
            },
        )
    )


def _assert_context_permission(
    *,
    user: str,
    file_student_applicant: str,
    context_doctype: str | None,
    context_name: str | None,
) -> None:
    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()

    if not resolved_context:
        _assert_can_access_student_applicant(user=user, student_applicant=file_student_applicant)
        return

    if resolved_context == CONTEXT_STUDENT_APPLICANT:
        if not resolved_name:
            frappe.throw(_("Context Name is required for Student Applicant access."), frappe.ValidationError)
        if resolved_name != file_student_applicant:
            frappe.throw(_("File does not belong to this Student Applicant."), frappe.PermissionError)
        _assert_can_access_student_applicant(user=user, student_applicant=file_student_applicant)
        return

    if resolved_context == CONTEXT_APPLICANT_INTERVIEW:
        if not resolved_name:
            frappe.throw(_("Context Name is required for Applicant Interview access."), frappe.ValidationError)

        interview_applicant = (
            frappe.db.get_value("Applicant Interview", resolved_name, "student_applicant") or ""
        ).strip()
        if not interview_applicant:
            frappe.throw(_("Applicant Interview not found."), frappe.DoesNotExistError)
        if interview_applicant != file_student_applicant:
            frappe.throw(_("File does not belong to this Applicant Interview context."), frappe.PermissionError)

        if is_admissions_file_staff_user(user) and has_scoped_staff_access_to_student_applicant(
            user=user, student_applicant=file_student_applicant
        ):
            return
        if has_open_applicant_review_access(user=user, student_applicant=file_student_applicant):
            return
        if _is_interviewer_on_interview(user=user, interview_name=resolved_name):
            return

        frappe.throw(_("You do not have permission to access this interview file."), frappe.PermissionError)
        return

    frappe.throw(_("Unsupported file access context."), frappe.ValidationError)


def _read_file_bytes(file_row: dict) -> bytes | None:
    file_url = (file_row.get("file_url") or "").strip()
    if not file_url or file_url.startswith(("http://", "https://")):
        return None

    rel_path = file_url.lstrip("/")
    if rel_path.startswith("private/") or rel_path.startswith("public/"):
        abs_path = frappe.utils.get_site_path(rel_path)
    else:
        base = "private" if frappe.utils.cint(file_row.get("is_private")) else "public"
        abs_path = frappe.utils.get_site_path(base, rel_path)

    if not os.path.exists(abs_path):
        return None

    with open(abs_path, "rb") as handle:
        return handle.read()


def _resolve_student_context_for_file(file_row: dict) -> tuple[str | None, str | None]:
    file_name = (file_row.get("name") or "").strip()
    if not file_name:
        return None, None

    classification = frappe.db.get_value(
        "File Classification",
        {"file": file_name},
        ["primary_subject_type", "primary_subject_id", "school"],
        as_dict=True,
    )
    if classification and (classification.get("primary_subject_type") or "").strip() == "Student":
        return (
            (classification.get("primary_subject_id") or "").strip() or None,
            (classification.get("school") or "").strip() or None,
        )

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    if not attached_to_name:
        return None, None

    if attached_to_doctype == CONTEXT_TASK_SUBMISSION:
        row = frappe.db.get_value(
            "Task Submission",
            attached_to_name,
            ["student", "school"],
            as_dict=True,
        )
        if row:
            return (row.get("student") or None, row.get("school") or None)
    elif attached_to_doctype == CONTEXT_STUDENT:
        school = frappe.db.get_value("Student", attached_to_name, "anchor_school")
        return attached_to_name, school
    elif attached_to_doctype == "Student Reflection Entry":
        row = frappe.db.get_value(
            "Student Reflection Entry",
            attached_to_name,
            ["student", "school"],
            as_dict=True,
        )
        if row:
            return (row.get("student") or None, row.get("school") or None)
    elif attached_to_doctype == CONTEXT_STUDENT_PORTFOLIO_ITEM:
        portfolio = frappe.db.get_value("Student Portfolio Item", attached_to_name, "parent")
        if portfolio:
            row = frappe.db.get_value("Student Portfolio", portfolio, ["student", "school"], as_dict=True)
            if row:
                return (row.get("student") or None, row.get("school") or None)

    return None, None


def _assert_internal_student_access(*, user: str, student: str, school: str | None = None) -> None:
    from ifitwala_ed.api import student_portfolio as student_portfolio_api

    scope = student_portfolio_api._resolve_actor_scope(  # pylint: disable=protected-access
        requested_students=[student],
        school_filter=(school or "").strip() or None,
    )
    if scope.get("students") or scope.get("all_students"):
        return
    frappe.throw(_("You do not have permission to access this file."), frappe.PermissionError)


def _assert_internal_academic_context(
    *,
    file_row: dict,
    context_doctype: str | None,
    context_name: str | None,
    student: str | None,
) -> None:
    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()
    if not resolved_context:
        return
    if not resolved_name:
        frappe.throw(_("Context Name is required."), frappe.ValidationError)

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    file_name = (file_row.get("name") or "").strip()

    if resolved_context == CONTEXT_TASK_SUBMISSION:
        if attached_to_doctype != CONTEXT_TASK_SUBMISSION or attached_to_name != resolved_name:
            frappe.throw(_("File does not belong to this submission."), frappe.PermissionError)
        return

    if resolved_context == CONTEXT_STUDENT:
        if not student or student != resolved_name:
            frappe.throw(_("File does not belong to this student."), frappe.PermissionError)
        return

    if resolved_context == CONTEXT_STUDENT_PORTFOLIO_ITEM:
        row = frappe.db.get_value(
            "Student Portfolio Item",
            resolved_name,
            ["name", "artefact_file"],
            as_dict=True,
        )
        if not row:
            frappe.throw(_("Portfolio item not found."), frappe.DoesNotExistError)
        if (row.get("artefact_file") or "").strip() != file_name:
            frappe.throw(_("File does not belong to this portfolio item."), frappe.PermissionError)
        return

    frappe.throw(_("Unsupported academic file context."), frappe.ValidationError)


def _assert_portfolio_share_file_access(*, file_name: str, share_token: str, viewer_email: str | None = None) -> None:
    from ifitwala_ed.api import student_portfolio as student_portfolio_api

    context = student_portfolio_api.resolve_portfolio_share_context(token=share_token, viewer_email=viewer_email)
    share_link = context.get("share_link") or {}
    if not bool(share_link.get("allow_download")):
        frappe.throw(_("Downloads are disabled for this share link."), frappe.PermissionError)

    allowed_files = {
        (row.get("artefact_file") or "").strip()
        for row in ((context.get("portfolio") or {}).get("items") or [])
        if (row.get("artefact_file") or "").strip()
    }
    if file_name not in allowed_files:
        frappe.throw(_("This file is not available in the shared portfolio scope."), frappe.PermissionError)


@frappe.whitelist()
def download_admissions_file(
    file: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
):
    user = _require_authenticated_user()
    file_name = (file or "").strip()
    if not file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_file_row(file_name)
    file_student_applicant = _resolve_student_applicant_from_file(file_row)
    _assert_context_permission(
        user=user,
        file_student_applicant=file_student_applicant,
        context_doctype=context_doctype,
        context_name=context_name,
    )

    file_url = (file_row.get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    content = _read_file_bytes(file_row)
    if content is None:
        frappe.throw(_("Could not read the file content."), frappe.DoesNotExistError)

    filename = (file_row.get("file_name") or "").strip() or "document"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    frappe.local.response["type"] = "download"
    frappe.local.response["filename"] = filename
    frappe.local.response["filecontent"] = content
    frappe.local.response["display_content_as"] = "inline"
    frappe.local.response["content_type"] = content_type


@frappe.whitelist(allow_guest=True)
def download_academic_file(
    file: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
):
    file_name = (file or "").strip()
    if not file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    token = (share_token or "").strip() or None
    if token:
        _assert_portfolio_share_file_access(
            file_name=file_name,
            share_token=token,
            viewer_email=(viewer_email or "").strip() or None,
        )
        file_row = _resolve_any_file_row(file_name)
    else:
        file_row = _resolve_any_file_row(file_name)
        user = _require_authenticated_user()
        student, school = _resolve_student_context_for_file(file_row)
        if not student:
            frappe.throw(_("File is missing academic ownership context."), frappe.ValidationError)
        _assert_internal_academic_context(
            file_row=file_row,
            context_doctype=context_doctype,
            context_name=context_name,
            student=student,
        )
        _assert_internal_student_access(user=user, student=student, school=school)

    file_url = (file_row.get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    content = _read_file_bytes(file_row)
    if content is None:
        frappe.throw(_("Could not read the file content."), frappe.DoesNotExistError)

    filename = (file_row.get("file_name") or "").strip() or "document"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    frappe.local.response["type"] = "download"
    frappe.local.response["filename"] = filename
    frappe.local.response["filecontent"] = content
    frappe.local.response["display_content_as"] = "inline"
    frappe.local.response["content_type"] = content_type


@frappe.whitelist()
def download_guardian_file(
    file: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
):
    user = _require_authenticated_user()
    file_name = (file or "").strip()
    if not file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_any_file_row(file_name)
    file_guardian = _resolve_guardian_from_file(file_row)
    _assert_guardian_file_access(
        user=user,
        file_guardian=file_guardian,
        context_doctype=context_doctype,
        context_name=context_name,
    )

    file_url = (file_row.get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    content = _read_file_bytes(file_row)
    if content is None:
        frappe.throw(_("Could not read the file content."), frappe.DoesNotExistError)

    filename = (file_row.get("file_name") or "").strip() or "document"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    frappe.local.response["type"] = "download"
    frappe.local.response["filename"] = filename
    frappe.local.response["filecontent"] = content
    frappe.local.response["display_content_as"] = "inline"
    frappe.local.response["content_type"] = content_type


@frappe.whitelist()
def download_employee_file(
    file: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
):
    user = _require_authenticated_user()
    file_name = (file or "").strip()
    if not file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_any_file_row(file_name)
    file_employee = _resolve_employee_from_file(file_row)
    _assert_employee_file_access(
        user=user,
        file_employee=file_employee,
        context_doctype=context_doctype,
        context_name=context_name,
    )

    file_url = (file_row.get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    content = _read_file_bytes(file_row)
    if content is None:
        frappe.throw(_("Could not read the file content."), frappe.DoesNotExistError)

    filename = (file_row.get("file_name") or "").strip() or "document"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    frappe.local.response["type"] = "download"
    frappe.local.response["filename"] = filename
    frappe.local.response["filecontent"] = content
    frappe.local.response["display_content_as"] = "inline"
    frappe.local.response["content_type"] = content_type
