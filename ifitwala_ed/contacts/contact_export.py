from __future__ import annotations

import json
import re
from datetime import timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from ifitwala_ed.contacts.contact_audit import (
    ACCESS_TYPE_EXPORT,
    CHANNEL_MIXED,
    RESULT_ALLOWED,
    RESULT_DENIED,
    log_contact_access,
)

CONTACT_EXPORT_REQUEST_DOCTYPE = "Contact Export Request"

STATUS_DRAFT = "Draft"
STATUS_SUBMITTED = "Submitted"
STATUS_APPROVED = "Approved"
STATUS_REJECTED = "Rejected"
STATUS_EXPIRED = "Expired"
STATUS_USED = "Used"
STATUS_CANCELLED = "Cancelled"

ALLOWED_SCOPE_TYPES = frozenset(
    {
        "Student Group Guardians",
        "Admissions Applicants",
        "Inquiry Leads",
        "Employees",
    }
)
REJECTED_SCOPE_TYPES = frozenset(
    {
        "All Contacts",
        "All Guardians",
        "All Students",
        "All Applicants",
        "All Employees",
    }
)
PRIVACY_APPROVER_ROLES = frozenset({"Data Protection Officer"})
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _clean_data(value: Any) -> str:
    return str(value or "").strip()


def _doc_get(doc, fieldname: str, default: Any = None) -> Any:
    if isinstance(doc, dict):
        return doc.get(fieldname, default)
    if hasattr(doc, "get"):
        return doc.get(fieldname, default)
    return getattr(doc, fieldname, default)


def _doc_set(doc, fieldname: str, value: Any) -> None:
    if isinstance(doc, dict):
        doc[fieldname] = value
    else:
        setattr(doc, fieldname, value)


def _set_service_flag(doc) -> None:
    flags = getattr(doc, "flags", None)
    if flags is None:
        try:
            flags = frappe._dict()
        except Exception:
            flags = {}
        doc.flags = flags
    if isinstance(flags, dict):
        flags["from_contact_export_service"] = True
    else:
        flags.from_contact_export_service = True


def _as_json(value: Any) -> str | None:
    if value in (None, "", []):
        return None
    try:
        return frappe.as_json(value)
    except Exception:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _parse_fields_requested(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            parsed = [part.strip() for part in value.split(",")]
    else:
        parsed = value

    if not isinstance(parsed, list):
        frappe.throw(_("Fields requested must be a list."))

    fields: list[str] = []
    for item in parsed:
        fieldname = _clean_data(item)
        if not fieldname:
            continue
        if EMAIL_PATTERN.search(fieldname) or len([char for char in fieldname if char.isdigit()]) >= 7:
            frappe.throw(_("Fields requested must not contain raw contact values."))
        fields.append(fieldname[:140])
    return list(dict.fromkeys(fields))


def _validate_scope_type(scope_type: str) -> str:
    resolved = _clean_data(scope_type)
    if not resolved:
        frappe.throw(_("Scope type is required for contact export requests."))
    if resolved in REJECTED_SCOPE_TYPES or resolved not in ALLOWED_SCOPE_TYPES:
        frappe.throw(_("Global contact export scopes are not allowed."))
    return resolved


def _validate_request_scope(*, scope_type: str, scope_name: str | None, organization: str | None, school: str | None):
    if scope_type == "Student Group Guardians" and not _clean_data(scope_name):
        frappe.throw(_("Student Group Guardians export requires a Student Group scope name."))

    if scope_type in {"Admissions Applicants", "Inquiry Leads", "Employees"}:
        if not (_clean_data(organization) or _clean_data(school)):
            frappe.throw(_("Contact export requires an Organization or School scope."))


def _validate_request_inputs(payload: dict[str, Any]) -> dict[str, Any]:
    purpose = _clean_data(payload.get("purpose"))
    legal_basis = _clean_data(payload.get("legal_basis"))
    scope_type = _validate_scope_type(_clean_data(payload.get("scope_type")))
    organization = _clean_data(payload.get("organization"))
    school = _clean_data(payload.get("school"))
    scope_name = _clean_data(payload.get("scope_name"))

    if not purpose:
        frappe.throw(_("Purpose is required for contact export requests."))
    if not legal_basis:
        frappe.throw(_("Legal basis is required for contact export requests."))

    _validate_request_scope(
        scope_type=scope_type,
        scope_name=scope_name,
        organization=organization,
        school=school,
    )

    return {
        "requester": _clean_data(payload.get("requester")) or _clean_data(frappe.session.user),
        "organization": organization or None,
        "school": school or None,
        "scope_type": scope_type,
        "scope_name": scope_name or None,
        "purpose": purpose,
        "legal_basis": legal_basis,
        "fields_requested": _as_json(_parse_fields_requested(payload.get("fields_requested"))),
        "status": STATUS_DRAFT,
    }


def create_contact_export_request(payload: dict) -> str:
    if not isinstance(payload, dict):
        frappe.throw(_("Contact export request payload must be an object."))

    values = _validate_request_inputs(payload)
    doc = frappe.get_doc({"doctype": CONTACT_EXPORT_REQUEST_DOCTYPE, **values})
    _set_service_flag(doc)
    doc.insert(ignore_permissions=True)
    return _clean_data(getattr(doc, "name", ""))


def _nested_scope_names(doctype: str, name: str | None) -> list[str]:
    resolved_name = _clean_data(name)
    if not resolved_name:
        return []

    row = frappe.db.get_value(doctype, resolved_name, ["lft", "rgt"], as_dict=True)
    lft = _doc_get(row, "lft") if row else None
    rgt = _doc_get(row, "rgt") if row else None
    if lft is None or rgt is None:
        return [resolved_name]

    names = frappe.get_all(
        doctype,
        filters={"lft": [">=", lft], "rgt": ["<=", rgt]},
        pluck="name",
        order_by="lft asc",
    )
    cleaned_names = [_clean_data(row_name) for row_name in names or [] if _clean_data(row_name)]
    return list(dict.fromkeys(cleaned_names)) or [resolved_name]


def _scope_filter_value(scope_names: list[str], fallback: str):
    if not scope_names:
        return fallback
    if len(scope_names) == 1:
        return scope_names[0]
    return ["in", scope_names]


def _scope_filters(doc) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    organization = _clean_data(_doc_get(doc, "organization"))
    school = _clean_data(_doc_get(doc, "school"))
    if organization:
        filters["organization"] = _scope_filter_value(_nested_scope_names("Organization", organization), organization)
    if school:
        filters["school"] = _scope_filter_value(_nested_scope_names("School", school), school)
    return filters


def _count_doctype(doctype: str, filters: dict[str, Any]) -> int:
    counter = getattr(frappe.db, "count", None)
    if callable(counter):
        return int(counter(doctype, filters=filters) or 0)
    return len(frappe.get_all(doctype, filters=filters, fields=["name"], limit=0) or [])


def _estimate_student_group_guardians(student_group: str) -> int:
    rows = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT sg.guardian)
        FROM `tabStudent Group Student` sgs
        INNER JOIN `tabStudent Guardian` sg
            ON sg.parent = sgs.student
            AND sg.parenttype = 'Student'
            AND sg.parentfield = 'guardians'
        WHERE sgs.parent = %(student_group)s
            AND sgs.parenttype = 'Student Group'
            AND sgs.parentfield = 'students'
        """,
        {"student_group": student_group},
    )
    if not rows:
        return 0
    first = rows[0]
    if isinstance(first, dict):
        return int(next(iter(first.values())) or 0)
    if isinstance(first, (list, tuple)):
        return int(first[0] or 0)
    return int(first or 0)


def _estimate_rows_for_doc(doc) -> int:
    scope_type = _validate_scope_type(_doc_get(doc, "scope_type"))
    _validate_request_scope(
        scope_type=scope_type,
        scope_name=_doc_get(doc, "scope_name"),
        organization=_doc_get(doc, "organization"),
        school=_doc_get(doc, "school"),
    )

    if scope_type == "Student Group Guardians":
        return _estimate_student_group_guardians(_clean_data(_doc_get(doc, "scope_name")))
    if scope_type == "Admissions Applicants":
        return _count_doctype("Student Applicant", _scope_filters(doc))
    if scope_type == "Inquiry Leads":
        return _count_doctype("Inquiry", _scope_filters(doc))
    if scope_type == "Employees":
        return _count_doctype("Employee", _scope_filters(doc))

    frappe.throw(_("Unsupported contact export scope."))
    return 0


def estimate_contact_export_rows(request_name: str) -> int:
    doc = frappe.get_doc(CONTACT_EXPORT_REQUEST_DOCTYPE, _clean_data(request_name))
    count = _estimate_rows_for_doc(doc)
    _doc_set(doc, "estimated_row_count", count)
    if _doc_get(doc, "status") == STATUS_DRAFT:
        _doc_set(doc, "status", STATUS_SUBMITTED)
    _set_service_flag(doc)
    doc.save(ignore_permissions=True)
    return count


def _has_privacy_approval_role(user: str | None = None) -> bool:
    resolved_user = _clean_data(user) or _clean_data(frappe.session.user)
    roles = set(frappe.get_roles(resolved_user))
    return bool(roles & PRIVACY_APPROVER_ROLES)


def _require_privacy_approver(*, request_name: str, purpose: str, result_on_deny: str = RESULT_DENIED) -> str:
    user = _clean_data(frappe.session.user)
    if _has_privacy_approval_role(user):
        return user

    log_contact_access(
        access_type=ACCESS_TYPE_EXPORT,
        purpose=purpose or "contact_export_request",
        workflow="contact_export_request",
        subject_doctype=CONTACT_EXPORT_REQUEST_DOCTYPE,
        subject_name=request_name,
        channel_type=CHANNEL_MIXED,
        result=result_on_deny,
        details={"reason": "missing_privacy_approver_role"},
        user=user,
    )
    frappe.throw(
        _("Only Data Protection Officer can approve or reject contact export requests."), frappe.PermissionError
    )
    return user


def _default_expiry():
    now_value = now_datetime()
    try:
        return now_value + timedelta(days=1)
    except TypeError:
        return now_value


def _save_workflow_doc(doc) -> None:
    _set_service_flag(doc)
    doc.save(ignore_permissions=True)


def approve_contact_export_request(request_name: str, reason: str | None = None) -> None:
    request_id = _clean_data(request_name)
    doc = frappe.get_doc(CONTACT_EXPORT_REQUEST_DOCTYPE, request_id)
    approver = _require_privacy_approver(
        request_name=request_id,
        purpose=_doc_get(doc, "purpose"),
    )

    if _doc_get(doc, "status") != STATUS_SUBMITTED:
        frappe.throw(_("Only submitted contact export requests can be approved."))
    if _doc_get(doc, "estimated_row_count") in (None, ""):
        frappe.throw(_("Estimated row count is required before approval."))
    if _validate_scope_type(_doc_get(doc, "scope_type")) not in ALLOWED_SCOPE_TYPES:
        frappe.throw(_("Global contact export scopes are not allowed."))

    _doc_set(doc, "status", STATUS_APPROVED)
    _doc_set(doc, "approved_by", approver)
    _doc_set(doc, "approved_on", now_datetime())
    if not _doc_get(doc, "expires_on"):
        _doc_set(doc, "expires_on", _default_expiry())

    log_contact_access(
        access_type=ACCESS_TYPE_EXPORT,
        purpose=_doc_get(doc, "purpose"),
        workflow="contact_export_request",
        subject_doctype=CONTACT_EXPORT_REQUEST_DOCTYPE,
        subject_name=request_id,
        organization=_doc_get(doc, "organization"),
        school=_doc_get(doc, "school"),
        channel_type=CHANNEL_MIXED,
        result=RESULT_ALLOWED,
        details={"scope_type": _doc_get(doc, "scope_type"), "row_count": _doc_get(doc, "estimated_row_count")},
        require_success=True,
    )
    _save_workflow_doc(doc)


def reject_contact_export_request(request_name: str, reason: str) -> None:
    request_id = _clean_data(request_name)
    doc = frappe.get_doc(CONTACT_EXPORT_REQUEST_DOCTYPE, request_id)
    approver = _require_privacy_approver(
        request_name=request_id,
        purpose=_doc_get(doc, "purpose"),
    )
    rejection_reason = _clean_data(reason)
    if not rejection_reason:
        frappe.throw(_("Rejection reason is required."))
    if _doc_get(doc, "status") not in {STATUS_DRAFT, STATUS_SUBMITTED}:
        frappe.throw(_("Only draft or submitted contact export requests can be rejected."))

    _doc_set(doc, "status", STATUS_REJECTED)
    _doc_set(doc, "approved_by", approver)
    _doc_set(doc, "approved_on", now_datetime())
    _doc_set(doc, "rejection_reason", rejection_reason)

    log_contact_access(
        access_type=ACCESS_TYPE_EXPORT,
        purpose=_doc_get(doc, "purpose"),
        workflow="contact_export_request",
        subject_doctype=CONTACT_EXPORT_REQUEST_DOCTYPE,
        subject_name=request_id,
        organization=_doc_get(doc, "organization"),
        school=_doc_get(doc, "school"),
        channel_type=CHANNEL_MIXED,
        result=RESULT_DENIED,
        details={"scope_type": _doc_get(doc, "scope_type"), "reason": "request_rejected"},
        require_success=True,
    )
    _save_workflow_doc(doc)


def _request_is_expired(doc) -> bool:
    expires_on = _doc_get(doc, "expires_on")
    if not expires_on:
        return True
    return get_datetime(expires_on) < get_datetime(now_datetime())


def _can_use_approved_request(doc, user: str) -> bool:
    requester = _clean_data(_doc_get(doc, "requester"))
    return bool(requester and requester == user) or _has_privacy_approval_role(user)


def _deny_export_assertion(doc, *, request_name: str, purpose: str, reason: str) -> None:
    doc_purpose = _clean_data(_doc_get(doc, "purpose")) if doc else ""
    doc_scope_type = _doc_get(doc, "scope_type") if doc else None
    log_contact_access(
        access_type=ACCESS_TYPE_EXPORT,
        purpose=purpose or doc_purpose or "contact_export_assertion",
        workflow="contact_export_request",
        subject_doctype=CONTACT_EXPORT_REQUEST_DOCTYPE,
        subject_name=request_name,
        organization=_doc_get(doc, "organization") if doc else None,
        school=_doc_get(doc, "school") if doc else None,
        channel_type=CHANNEL_MIXED,
        result=RESULT_DENIED,
        details={"reason": reason, "scope_type": doc_scope_type},
    )
    frappe.throw(
        _("Approved Contact Export Request is required before exporting contact data."), frappe.PermissionError
    )


def assert_approved_contact_export(request_name: str, *, purpose: str, scope_type: str) -> None:
    request_id = _clean_data(request_name)
    resolved_purpose = _clean_data(purpose)
    resolved_scope_type = _validate_scope_type(scope_type)
    if not request_id:
        _deny_export_assertion(None, request_name="", purpose=resolved_purpose, reason="missing_request")
        return
    if not resolved_purpose:
        _deny_export_assertion(
            None, request_name=request_id, purpose="contact_export_assertion", reason="missing_purpose"
        )
        return

    doc = frappe.get_doc(CONTACT_EXPORT_REQUEST_DOCTYPE, request_id)
    if _doc_get(doc, "status") != STATUS_APPROVED:
        _deny_export_assertion(doc, request_name=request_id, purpose=resolved_purpose, reason="not_approved")
        return
    if _clean_data(_doc_get(doc, "purpose")) != resolved_purpose:
        _deny_export_assertion(doc, request_name=request_id, purpose=resolved_purpose, reason="purpose_mismatch")
        return
    if _clean_data(_doc_get(doc, "scope_type")) != resolved_scope_type:
        _deny_export_assertion(doc, request_name=request_id, purpose=resolved_purpose, reason="scope_mismatch")
        return
    if _request_is_expired(doc):
        _doc_set(doc, "status", STATUS_EXPIRED)
        _save_workflow_doc(doc)
        _deny_export_assertion(doc, request_name=request_id, purpose=resolved_purpose, reason="expired")
        return
    if not _can_use_approved_request(doc, _clean_data(frappe.session.user)):
        _deny_export_assertion(doc, request_name=request_id, purpose=resolved_purpose, reason="requester_mismatch")
        return

    log_contact_access(
        access_type=ACCESS_TYPE_EXPORT,
        purpose=resolved_purpose,
        workflow="contact_export_request",
        subject_doctype=CONTACT_EXPORT_REQUEST_DOCTYPE,
        subject_name=request_id,
        organization=_doc_get(doc, "organization"),
        school=_doc_get(doc, "school"),
        channel_type=CHANNEL_MIXED,
        result=RESULT_ALLOWED,
        details={"scope_type": resolved_scope_type, "row_count": _doc_get(doc, "estimated_row_count")},
        require_success=True,
    )
