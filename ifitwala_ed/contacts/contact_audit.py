from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe import _

CONTACT_ACCESS_LOG_DOCTYPE = "Contact Access Log"

ACCESS_TYPE_MASKED_READ = "masked_read"
ACCESS_TYPE_RAW_READ = "raw_read"
ACCESS_TYPE_RAW_WRITE = "raw_write"
ACCESS_TYPE_RECIPIENT_RESOLUTION = "recipient_resolution"
ACCESS_TYPE_EXPORT = "export"
ACCESS_TYPE_DENIED_ATTEMPT = "denied_attempt"

RESULT_ALLOWED = "allowed"
RESULT_DENIED = "denied"

CHANNEL_EMAIL = "email"
CHANNEL_PHONE = "phone"
CHANNEL_ADDRESS = "address"
CHANNEL_MIXED = "mixed"
CHANNEL_UNKNOWN = "unknown"

ALLOWED_ACCESS_TYPES = {
    ACCESS_TYPE_MASKED_READ,
    ACCESS_TYPE_RAW_READ,
    ACCESS_TYPE_RAW_WRITE,
    ACCESS_TYPE_RECIPIENT_RESOLUTION,
    ACCESS_TYPE_EXPORT,
    ACCESS_TYPE_DENIED_ATTEMPT,
}
ALLOWED_RESULTS = {RESULT_ALLOWED, RESULT_DENIED}
ALLOWED_CHANNEL_TYPES = {CHANNEL_EMAIL, CHANNEL_PHONE, CHANNEL_ADDRESS, CHANNEL_MIXED, CHANNEL_UNKNOWN}

SENSITIVE_DETAIL_KEY_PARTS = (
    "address",
    "email",
    "file",
    "mobile",
    "payload",
    "phone",
    "value",
)
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _clean_data(value: Any) -> str:
    return str(value or "").strip()


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value

    cleaned = _clean_data(value)
    if not cleaned:
        return ""
    if EMAIL_PATTERN.search(cleaned):
        return "[redacted]"
    digits = [char for char in cleaned if char.isdigit()]
    if len(digits) >= 7:
        return "[redacted]"
    return cleaned[:500]


def sanitize_details(details: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(details, dict):
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in details.items():
        clean_key = _clean_data(key)
        if not clean_key:
            continue

        folded_key = clean_key.casefold()
        if any(part in folded_key for part in SENSITIVE_DETAIL_KEY_PARTS):
            continue

        if isinstance(value, dict):
            nested = sanitize_details(value)
            if nested:
                sanitized[clean_key] = nested
            continue

        if isinstance(value, list):
            safe_items = [_safe_value(item) for item in value[:20] if not isinstance(item, dict)]
            if safe_items:
                sanitized[clean_key] = safe_items
            continue

        sanitized[clean_key] = _safe_value(value)

    return sanitized


def _json_details(details: dict[str, Any] | None) -> str | None:
    sanitized = sanitize_details(details)
    if not sanitized:
        return None
    try:
        return frappe.as_json(sanitized)
    except Exception:
        return json.dumps(sanitized, sort_keys=True, separators=(",", ":"), default=str)


def _request_context() -> dict[str, str | None]:
    local = getattr(frappe, "local", None)
    request = getattr(local, "request", None)
    headers = getattr(request, "headers", None) if request else None

    user_agent = None
    if headers and hasattr(headers, "get"):
        user_agent = headers.get("User-Agent")

    return {
        "request_path": _clean_data(getattr(request, "path", "")) or None,
        "ip_address": _clean_data(getattr(local, "request_ip", "")) or None,
        "user_agent": _clean_data(user_agent) or None,
    }


def _log_failure(error: Exception) -> None:
    try:
        frappe.log_error(
            getattr(frappe, "get_traceback", lambda: str(error))(),
            "Contact access audit logging failed",
        )
    except Exception:
        return


def log_contact_access(
    *,
    access_type: str,
    purpose: str,
    workflow: str | None = None,
    subject_doctype: str | None = None,
    subject_name: str | None = None,
    owner_doctype: str | None = None,
    owner_name: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    channel_type: str | None = None,
    result: str = RESULT_ALLOWED,
    details: dict[str, Any] | None = None,
    user: str | None = None,
    require_success: bool = False,
) -> str | None:
    resolved_access_type = _clean_data(access_type)
    resolved_result = _clean_data(result)
    resolved_purpose = _clean_data(purpose)
    resolved_channel = _clean_data(channel_type) or CHANNEL_UNKNOWN

    if resolved_access_type not in ALLOWED_ACCESS_TYPES:
        frappe.throw(_("Invalid contact access audit type."))
    if resolved_result not in ALLOWED_RESULTS:
        frappe.throw(_("Invalid contact access audit result."))
    if resolved_channel not in ALLOWED_CHANNEL_TYPES:
        resolved_channel = CHANNEL_UNKNOWN
    if not resolved_purpose:
        frappe.throw(_("Contact access purpose is required."), frappe.PermissionError)

    request_context = _request_context()
    payload = {
        "doctype": CONTACT_ACCESS_LOG_DOCTYPE,
        "user": _clean_data(user) or _clean_data(getattr(frappe.session, "user", "")) or None,
        "access_type": resolved_access_type,
        "purpose": resolved_purpose,
        "workflow": _clean_data(workflow) or None,
        "subject_doctype": _clean_data(subject_doctype) or None,
        "subject_name": _clean_data(subject_name) or None,
        "owner_doctype": _clean_data(owner_doctype) or None,
        "owner_name": _clean_data(owner_name) or None,
        "organization": _clean_data(organization) or None,
        "school": _clean_data(school) or None,
        "channel_type": resolved_channel,
        "result": resolved_result,
        "request_path": request_context["request_path"],
        "ip_address": request_context["ip_address"],
        "user_agent": request_context["user_agent"],
        "details": _json_details(details),
    }

    try:
        doc = frappe.get_doc(payload)
        flags = getattr(doc, "flags", None)
        if flags is None:
            try:
                flags = frappe._dict()
            except Exception:
                flags = {}
            doc.flags = flags
        if isinstance(flags, dict):
            flags["from_contact_privacy_service"] = True
        else:
            flags.from_contact_privacy_service = True
        doc.insert(ignore_permissions=True)
        return _clean_data(getattr(doc, "name", "")) or None
    except Exception as error:
        _log_failure(error)
        if require_success:
            frappe.throw(_("Contact access audit logging failed."), frappe.PermissionError)
        return None
