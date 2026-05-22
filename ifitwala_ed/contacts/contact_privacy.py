from __future__ import annotations

import hashlib
import hmac
from typing import Any

import frappe
from frappe import _

from ifitwala_ed.contacts.contact_audit import (
    ACCESS_TYPE_DENIED_ATTEMPT,
    ACCESS_TYPE_RAW_READ,
    ACCESS_TYPE_RAW_WRITE,
    ACCESS_TYPE_RECIPIENT_RESOLUTION,
    CHANNEL_EMAIL,
    CHANNEL_MIXED,
    CHANNEL_PHONE,
    RESULT_ALLOWED,
    RESULT_DENIED,
    log_contact_access,
)

COMMUNICATION_CONTACT_POINT_DOCTYPE = "Communication Contact Point"
PROTECTED_CONTACT_LINK_DOCTYPES = frozenset({"Student", "Guardian", "Employee", "Student Applicant"})
CONTACT_POINT_ALLOWED_OWNER_SUBJECT_DOCTYPES = frozenset(
    {"Guardian", "Student", "Student Applicant", "Inquiry", "Employee"}
)
CONTACT_POINT_SCHOOL_REQUIRED_DOCTYPES = frozenset({"Guardian", "Student", "Student Applicant"})
CONTACT_POINT_ALLOWED_CHANNEL_TYPES = frozenset({"email", "phone", "address"})
CONTACT_POINT_ALLOWED_PURPOSES = frozenset(
    {
        "emergency",
        "billing",
        "admissions_followup",
        "family_consent",
        "school_communication",
        "hr",
        "relationship_crm",
        "export",
    }
)
GUARDIAN_STUDENT_SUMMARY_CONTACT_POINT_PURPOSE = "school_communication"


def _clean_data(value: Any) -> str:
    return str(value or "").strip()


def _row_get(row: Any, fieldname: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(fieldname, default)
    if hasattr(row, "get"):
        return row.get(fieldname, default)
    return getattr(row, fieldname, default)


def _doc_set(doc: Any, fieldname: str, value: Any) -> None:
    if isinstance(doc, dict):
        doc[fieldname] = value
    else:
        setattr(doc, fieldname, value)


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def require_purpose(purpose: str | None) -> str:
    resolved = _clean_data(purpose)
    if not resolved:
        frappe.throw(_("Contact access purpose is required."), frappe.PermissionError)
    return resolved


def _normalize_email_value(value: Any) -> str:
    from ifitwala_ed.admission.admission_utils import normalize_email_value

    return normalize_email_value(value)


def mask_email(value: str | None) -> str:
    email = _normalize_email_value(value)
    if not email or "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    if not local:
        return f"****@{domain}"
    visible = local[:1]
    return f"{visible}****@{domain}"


def mask_phone(value: str | None) -> str:
    phone = _clean_data(value)
    if not phone:
        return ""

    digits = [char for char in phone if char.isdigit()]
    suffix = "".join(digits[-4:])
    if not suffix:
        return "***"
    if phone.startswith("+"):
        prefix_digits = "".join(digits[:2])
        prefix = f"+{prefix_digits}" if prefix_digits else "+"
        return f"{prefix} *** *** {suffix}"
    return f"*** *** {suffix}"


def _site_secret() -> str:
    local = getattr(frappe, "local", None)
    conf = getattr(local, "conf", None) or {}
    if hasattr(conf, "get"):
        secret = conf.get("encryption_key") or conf.get("secret")
    else:
        secret = None
    secret = secret or getattr(local, "site", None)
    resolved_secret = _clean_data(secret)
    if not resolved_secret:
        frappe.throw(_("Contact point hashing requires a site secret."), frappe.PermissionError)
    return resolved_secret


def _normalize_phone_value(value: Any) -> str:
    phone = _clean_data(value)
    if not phone:
        return ""

    digits = "".join(char for char in phone if char.isdigit())
    if not digits:
        return ""
    if phone.startswith("+"):
        return f"+{digits}"
    return digits


def _normalize_contact_point_value(channel_type: str, value: Any) -> str:
    if channel_type == "email":
        return _normalize_email_value(value)
    if channel_type == "phone":
        return _normalize_phone_value(value)
    if channel_type == "address":
        return _clean_data(value)
    return ""


def _masked_contact_point_value(channel_type: str, value: str) -> str:
    if channel_type == "email":
        return mask_email(value)
    if channel_type == "phone":
        return mask_phone(value)
    if channel_type == "address":
        return "***"
    return ""


def _contact_point_hash(*, channel_type: str, normalized_value: str) -> str:
    message = f"{channel_type}|{normalized_value}".encode("utf-8")
    return hmac.new(_site_secret().encode("utf-8"), message, hashlib.sha256).hexdigest()


def _encrypt_contact_point_value(value: str) -> str:
    try:
        from frappe.utils.password import encrypt
    except Exception:
        frappe.throw(_("Contact point encryption is unavailable."), frappe.PermissionError)
    return encrypt(value)


def _decrypt_contact_point_value(value: str) -> str:
    try:
        from frappe.utils.password import decrypt
    except Exception:
        frappe.throw(_("Contact point decryption is unavailable."), frappe.PermissionError)
    return decrypt(value)


def _set_contact_point_service_flag(doc: Any) -> None:
    flags = getattr(doc, "flags", None)
    if flags is None:
        try:
            flags = frappe._dict()
        except Exception:
            flags = {}
        doc.flags = flags
    if isinstance(flags, dict):
        flags["from_contact_point_service"] = True
    else:
        flags.from_contact_point_service = True


def _validate_contact_point_identity(
    *,
    owner_doctype: str,
    owner_name: str,
    subject_doctype: str,
    subject_name: str,
    organization: str,
    school: str | None,
    channel_type: str,
    purpose: str,
) -> None:
    if owner_doctype not in CONTACT_POINT_ALLOWED_OWNER_SUBJECT_DOCTYPES:
        frappe.throw(_("Communication Contact Point owner DocType is not approved."))
    if subject_doctype not in CONTACT_POINT_ALLOWED_OWNER_SUBJECT_DOCTYPES:
        frappe.throw(_("Communication Contact Point subject DocType is not approved."))
    if not owner_name or not subject_name:
        frappe.throw(_("Communication Contact Point requires an owner and subject."))
    if not organization:
        frappe.throw(_("Communication Contact Point requires an Organization."))
    if ({owner_doctype, subject_doctype} & CONTACT_POINT_SCHOOL_REQUIRED_DOCTYPES) and not _clean_data(school):
        frappe.throw(_("Communication Contact Point requires a School for this education record."))
    if channel_type not in CONTACT_POINT_ALLOWED_CHANNEL_TYPES:
        frappe.throw(_("Communication Contact Point channel type is not approved."))
    if purpose not in CONTACT_POINT_ALLOWED_PURPOSES:
        frappe.throw(_("Communication Contact Point purpose is not approved."))


def _get_school_organization_for_contact_point(school: str | None) -> str:
    resolved_school = _clean_data(school)
    if not resolved_school:
        return ""

    try:
        from ifitwala_ed.accounting.account_holder_utils import get_school_organization
    except Exception:
        return ""

    return _clean_data(get_school_organization(resolved_school))


def _find_contact_point_name(
    *,
    owner_doctype: str,
    owner_name: str,
    organization: str,
    school: str | None,
    channel_type: str,
    purpose: str,
    normalized_hash: str,
) -> str | None:
    rows = frappe.get_all(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        filters={
            "owner_doctype": owner_doctype,
            "owner_name": owner_name,
            "organization": organization,
            "school": _clean_data(school) or ["is", "not set"],
            "channel_type": channel_type,
            "purpose": purpose,
            "normalized_hash": normalized_hash,
        },
        fields=["name"],
        limit=1,
        ignore_permissions=True,
    )
    if not rows:
        return None
    return _clean_data(_row_get(rows[0], "name")) or None


def _clear_existing_primary_contact_points(
    *,
    owner_doctype: str,
    owner_name: str,
    organization: str,
    school: str | None,
    channel_type: str,
    purpose: str,
    except_name: str | None = None,
) -> None:
    rows = frappe.get_all(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        filters={
            "owner_doctype": owner_doctype,
            "owner_name": owner_name,
            "organization": organization,
            "school": _clean_data(school) or ["is", "not set"],
            "channel_type": channel_type,
            "purpose": purpose,
            "is_primary": 1,
            "disabled": 0,
        },
        fields=["name"],
        limit=0,
        ignore_permissions=True,
    )
    for row in rows or []:
        contact_point_name = _clean_data(_row_get(row, "name"))
        if not contact_point_name or contact_point_name == _clean_data(except_name):
            continue
        doc = frappe.get_doc(COMMUNICATION_CONTACT_POINT_DOCTYPE, contact_point_name)
        _doc_set(doc, "is_primary", 0)
        _set_contact_point_service_flag(doc)
        doc.save(ignore_permissions=True)


def upsert_contact_point(
    *,
    owner_doctype: str,
    owner_name: str,
    subject_doctype: str,
    subject_name: str,
    organization: str,
    school: str | None,
    channel_type: str,
    purpose: str,
    value: str,
    is_primary: bool = False,
    verified_on: str | None = None,
    workflow: str | None = None,
    user: str | None = None,
) -> str | None:
    resolved_owner_doctype = _clean_data(owner_doctype)
    resolved_owner_name = _clean_data(owner_name)
    resolved_subject_doctype = _clean_data(subject_doctype)
    resolved_subject_name = _clean_data(subject_name)
    resolved_organization = _clean_data(organization)
    resolved_school = _clean_data(school) or None
    resolved_channel_type = _clean_data(channel_type)
    resolved_purpose = require_purpose(purpose)
    raw_value = _clean_data(value)
    if not raw_value:
        return None

    _validate_contact_point_identity(
        owner_doctype=resolved_owner_doctype,
        owner_name=resolved_owner_name,
        subject_doctype=resolved_subject_doctype,
        subject_name=resolved_subject_name,
        organization=resolved_organization,
        school=resolved_school,
        channel_type=resolved_channel_type,
        purpose=resolved_purpose,
    )
    normalized_value = _normalize_contact_point_value(resolved_channel_type, raw_value)
    if not normalized_value:
        return None

    log_contact_access(
        access_type=ACCESS_TYPE_RAW_WRITE,
        purpose=resolved_purpose,
        workflow=workflow or "communication_contact_point_upsert",
        subject_doctype=resolved_subject_doctype,
        subject_name=resolved_subject_name,
        owner_doctype=resolved_owner_doctype,
        owner_name=resolved_owner_name,
        organization=resolved_organization,
        school=resolved_school,
        channel_type=resolved_channel_type,
        result=RESULT_ALLOWED,
        user=user,
        require_success=True,
    )

    normalized_hash = _contact_point_hash(channel_type=resolved_channel_type, normalized_value=normalized_value)
    contact_point_name = _find_contact_point_name(
        owner_doctype=resolved_owner_doctype,
        owner_name=resolved_owner_name,
        organization=resolved_organization,
        school=resolved_school,
        channel_type=resolved_channel_type,
        purpose=resolved_purpose,
        normalized_hash=normalized_hash,
    )
    doc = (
        frappe.get_doc(COMMUNICATION_CONTACT_POINT_DOCTYPE, contact_point_name)
        if contact_point_name
        else frappe.get_doc({"doctype": COMMUNICATION_CONTACT_POINT_DOCTYPE})
    )
    _doc_set(doc, "owner_doctype", resolved_owner_doctype)
    _doc_set(doc, "owner_name", resolved_owner_name)
    _doc_set(doc, "subject_doctype", resolved_subject_doctype)
    _doc_set(doc, "subject_name", resolved_subject_name)
    _doc_set(doc, "organization", resolved_organization)
    _doc_set(doc, "school", resolved_school)
    _doc_set(doc, "channel_type", resolved_channel_type)
    _doc_set(doc, "purpose", resolved_purpose)
    _doc_set(doc, "value_encrypted", _encrypt_contact_point_value(normalized_value))
    _doc_set(doc, "normalized_hash", normalized_hash)
    _doc_set(doc, "masked_display", _masked_contact_point_value(resolved_channel_type, normalized_value))
    _doc_set(doc, "is_primary", 1 if is_primary else 0)
    _doc_set(doc, "verified_on", verified_on)
    _doc_set(doc, "disabled", 0)

    if is_primary:
        _clear_existing_primary_contact_points(
            owner_doctype=resolved_owner_doctype,
            owner_name=resolved_owner_name,
            organization=resolved_organization,
            school=resolved_school,
            channel_type=resolved_channel_type,
            purpose=resolved_purpose,
            except_name=contact_point_name,
        )

    _set_contact_point_service_flag(doc)
    if contact_point_name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)
    return _clean_data(getattr(doc, "name", "")) or None


def disable_contact_points_for_owner(
    *,
    owner_doctype: str,
    owner_name: str,
    purpose: str | None = None,
    channel_type: str | None = None,
) -> int:
    filters: dict[str, Any] = {
        "owner_doctype": _clean_data(owner_doctype),
        "owner_name": _clean_data(owner_name),
        "disabled": 0,
    }
    if purpose:
        filters["purpose"] = require_purpose(purpose)
    if channel_type:
        filters["channel_type"] = _clean_data(channel_type)

    rows = frappe.get_all(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        filters=filters,
        fields=["name"],
        limit=0,
        ignore_permissions=True,
    )
    disabled_count = 0
    for row in rows or []:
        contact_point_name = _clean_data(_row_get(row, "name"))
        if not contact_point_name:
            continue
        doc = frappe.get_doc(COMMUNICATION_CONTACT_POINT_DOCTYPE, contact_point_name)
        _doc_set(doc, "disabled", 1)
        _set_contact_point_service_flag(doc)
        doc.save(ignore_permissions=True)
        disabled_count += 1
    return disabled_count


def get_masked_contact_points_for_owner(
    *,
    owner_doctype: str,
    owner_name: str,
    purpose: str | None = None,
    channel_type: str | None = None,
    school: str | None = None,
) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {
        "owner_doctype": _clean_data(owner_doctype),
        "owner_name": _clean_data(owner_name),
        "disabled": 0,
    }
    if purpose:
        filters["purpose"] = require_purpose(purpose)
    if channel_type:
        filters["channel_type"] = _clean_data(channel_type)
    if school:
        filters["school"] = _clean_data(school)

    rows = frappe.get_all(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        filters=filters,
        fields=["name", "subject_doctype", "subject_name", "channel_type", "purpose", "masked_display", "is_primary"],
        order_by="is_primary desc, modified desc",
        limit=0,
        ignore_permissions=True,
    )
    return [
        {
            "name": _clean_data(_row_get(row, "name")),
            "subject_doctype": _clean_data(_row_get(row, "subject_doctype")),
            "subject_name": _clean_data(_row_get(row, "subject_name")),
            "channel_type": _clean_data(_row_get(row, "channel_type")),
            "purpose": _clean_data(_row_get(row, "purpose")),
            "masked_display": _clean_data(_row_get(row, "masked_display")),
            "is_primary": _as_int(_row_get(row, "is_primary")),
        }
        for row in rows or []
    ]


def get_raw_contact_point_value(
    *,
    contact_point: str,
    purpose: str,
    workflow: str | None = None,
    user: str | None = None,
) -> str:
    resolved_purpose = require_purpose(purpose)
    contact_point_name = _clean_data(contact_point)
    if not contact_point_name:
        frappe.throw(_("Communication Contact Point is required."))

    doc = frappe.get_doc(COMMUNICATION_CONTACT_POINT_DOCTYPE, contact_point_name)
    if _clean_data(doc.get("purpose")) != resolved_purpose or _as_int(doc.get("disabled")):
        frappe.throw(_("Communication Contact Point is not available for this purpose."), frappe.PermissionError)

    log_contact_access(
        access_type=ACCESS_TYPE_RAW_READ,
        purpose=resolved_purpose,
        workflow=workflow or "communication_contact_point_raw_read",
        subject_doctype=doc.get("subject_doctype"),
        subject_name=doc.get("subject_name"),
        owner_doctype=doc.get("owner_doctype"),
        owner_name=doc.get("owner_name"),
        organization=doc.get("organization"),
        school=doc.get("school"),
        channel_type=doc.get("channel_type"),
        result=RESULT_ALLOWED,
        user=user,
        require_success=True,
    )
    return _decrypt_contact_point_value(_clean_data(doc.get("value_encrypted")))


def resolve_contact_point_recipients(
    *,
    organization: str,
    school: str | None,
    purpose: str,
    channel_type: str,
) -> list[dict[str, Any]]:
    resolved_purpose = require_purpose(purpose)
    resolved_channel_type = _clean_data(channel_type)
    if resolved_channel_type not in CONTACT_POINT_ALLOWED_CHANNEL_TYPES:
        frappe.throw(_("Communication Contact Point channel type is not approved."))

    filters: dict[str, Any] = {
        "organization": _clean_data(organization),
        "purpose": resolved_purpose,
        "channel_type": resolved_channel_type,
        "disabled": 0,
    }
    if not filters["organization"]:
        frappe.throw(_("Communication Contact Point requires an Organization."))
    if school:
        filters["school"] = _clean_data(school)

    log_contact_access(
        access_type=ACCESS_TYPE_RECIPIENT_RESOLUTION,
        purpose=resolved_purpose,
        workflow="communication_contact_point_recipient_resolution",
        organization=filters["organization"],
        school=filters.get("school"),
        channel_type=resolved_channel_type,
        result=RESULT_ALLOWED,
        require_success=True,
    )

    rows = frappe.get_all(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        filters=filters,
        fields=["name", "subject_doctype", "subject_name", "masked_display", "is_primary"],
        order_by="subject_doctype asc, subject_name asc, is_primary desc",
        limit=0,
        ignore_permissions=True,
    )
    return [
        {
            "name": _clean_data(_row_get(row, "name")),
            "subject_doctype": _clean_data(_row_get(row, "subject_doctype")),
            "subject_name": _clean_data(_row_get(row, "subject_name")),
            "masked_display": _clean_data(_row_get(row, "masked_display")),
            "is_primary": _as_int(_row_get(row, "is_primary")),
        }
        for row in rows or []
    ]


def sync_guardian_contact_points(
    guardian_doc: Any,
    *,
    school: str,
    purpose: str = "school_communication",
    workflow: str | None = None,
    user: str | None = None,
) -> list[str]:
    guardian_name = _clean_data(_row_get(guardian_doc, "name"))
    explicit_organization = _clean_data(_row_get(guardian_doc, "organization"))
    resolved_school = _clean_data(school)
    school_organization = _get_school_organization_for_contact_point(resolved_school)
    if explicit_organization and school_organization and explicit_organization != school_organization:
        frappe.throw(_("Guardian organization does not match the School organization for contact point sync."))
    organization = school_organization or explicit_organization

    if not guardian_name:
        frappe.throw(_("Guardian is required for contact point sync."))
    if not resolved_school:
        frappe.throw(_("School is required for Guardian contact point sync."))
    if not organization:
        frappe.throw(_("Organization is required for Guardian contact point sync."))

    synced: list[str] = []
    guardian_email = _normalize_email_value(_row_get(guardian_doc, "guardian_email"))
    if guardian_email:
        contact_point_name = upsert_contact_point(
            owner_doctype="Guardian",
            owner_name=guardian_name,
            subject_doctype="Guardian",
            subject_name=guardian_name,
            organization=organization,
            school=resolved_school,
            channel_type="email",
            purpose=purpose,
            value=guardian_email,
            is_primary=True,
            workflow=workflow or "guardian_contact_point_sync",
            user=user,
        )
        if contact_point_name:
            synced.append(contact_point_name)

    guardian_phone = _clean_data(_row_get(guardian_doc, "guardian_mobile_phone"))
    if guardian_phone:
        contact_point_name = upsert_contact_point(
            owner_doctype="Guardian",
            owner_name=guardian_name,
            subject_doctype="Guardian",
            subject_name=guardian_name,
            organization=organization,
            school=resolved_school,
            channel_type="phone",
            purpose=purpose,
            value=guardian_phone,
            is_primary=True,
            workflow=workflow or "guardian_contact_point_sync",
            user=user,
        )
        if contact_point_name:
            synced.append(contact_point_name)

    return synced


def _mask_email_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    masked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        raw_value = _normalize_email_value(_row_get(row, "email_id"))
        if not raw_value or raw_value in seen:
            continue
        seen.add(raw_value)
        masked.append(
            {
                "value": mask_email(raw_value),
                "is_primary": _as_int(_row_get(row, "is_primary")),
            }
        )
    return masked


def _mask_phone_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    masked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        raw_value = _clean_data(_row_get(row, "phone"))
        if not raw_value or raw_value in seen:
            continue
        seen.add(raw_value)
        masked.append(
            {
                "value": mask_phone(raw_value),
                "is_primary": _as_int(_row_get(row, "is_primary_mobile_no")),
            }
        )
    return masked


def _has_scoped_staff_access_to_student_applicant(*, user: str, student_applicant: str) -> bool:
    from ifitwala_ed.admission.admission_utils import has_scoped_staff_access_to_student_applicant

    return has_scoped_staff_access_to_student_applicant(
        user=user,
        student_applicant=student_applicant,
        allow_system_bypass=False,
    )


def _user_can_access_student_applicant(*, user: str, student_applicant: str) -> bool:
    from ifitwala_ed.admission.access import user_can_access_student_applicant

    return user_can_access_student_applicant(user=user, student_applicant=student_applicant)


def assert_user_can_access_student_applicant_contact(
    *,
    student_applicant: str | None,
    purpose: str | None,
    user: str | None = None,
    workflow: str | None = None,
    owner_doctype: str | None = None,
    owner_name: str | None = None,
    channel_type: str | None = None,
) -> str:
    resolved_purpose = require_purpose(purpose)
    applicant_name = _clean_data(student_applicant)
    if not applicant_name:
        frappe.throw(_("student_applicant is required."))

    resolved_user = _clean_data(user) or _clean_data(getattr(frappe.session, "user", ""))
    if not resolved_user or resolved_user == "Guest":
        log_contact_access(
            access_type=ACCESS_TYPE_DENIED_ATTEMPT,
            purpose=resolved_purpose,
            workflow=workflow,
            subject_doctype="Student Applicant",
            subject_name=applicant_name,
            owner_doctype=owner_doctype,
            owner_name=owner_name,
            channel_type=channel_type,
            result=RESULT_DENIED,
            user=resolved_user or None,
        )
        frappe.throw(_("You do not have permission to access this Applicant."), frappe.PermissionError)

    if _user_can_access_student_applicant(user=resolved_user, student_applicant=applicant_name):
        return resolved_user
    if _has_scoped_staff_access_to_student_applicant(user=resolved_user, student_applicant=applicant_name):
        return resolved_user

    log_contact_access(
        access_type=ACCESS_TYPE_DENIED_ATTEMPT,
        purpose=resolved_purpose,
        workflow=workflow,
        subject_doctype="Student Applicant",
        subject_name=applicant_name,
        owner_doctype=owner_doctype,
        owner_name=owner_name,
        channel_type=channel_type,
        result=RESULT_DENIED,
        user=resolved_user,
    )
    frappe.throw(_("You do not have permission to access this Applicant."), frappe.PermissionError)
    return resolved_user


def _contact_primary_mobile_from_doc(contact_doc) -> str:
    for row in contact_doc.get("phone_nos") or []:
        if _as_int(_row_get(row, "is_primary_mobile_no")):
            phone = _clean_data(_row_get(row, "phone"))
            if phone:
                return phone

    mobile = _clean_data(contact_doc.get("mobile_no"))
    if mobile:
        return mobile

    for row in contact_doc.get("phone_nos") or []:
        phone = _clean_data(_row_get(row, "phone"))
        if phone:
            return phone

    return ""


def get_raw_applicant_contact_prefill(
    *,
    student_applicant: str | None,
    contact: str | None,
    purpose: str | None,
    user: str | None = None,
) -> dict[str, Any]:
    assert_user_can_access_student_applicant_contact(
        student_applicant=student_applicant,
        purpose=purpose,
        user=user,
        workflow="applicant_contact_prefill",
        owner_doctype="Contact",
        owner_name=contact,
        channel_type=CHANNEL_MIXED,
    )
    contact_name = _clean_data(contact)
    payload = {
        "available": False,
        "contact": contact_name,
        "first_name": "",
        "last_name": "",
        "email": "",
        "mobile_phone": "",
    }
    if not contact_name or not frappe.db.exists("Contact", contact_name):
        payload["contact"] = ""
        return payload

    log_contact_access(
        access_type=ACCESS_TYPE_RAW_READ,
        purpose=purpose,
        workflow="applicant_contact_prefill",
        subject_doctype="Student Applicant",
        subject_name=student_applicant,
        owner_doctype="Contact",
        owner_name=contact_name,
        channel_type=CHANNEL_MIXED,
        result=RESULT_ALLOWED,
        user=user,
        require_success=True,
    )

    from ifitwala_ed.admission.admission_utils import get_contact_primary_email

    contact_doc = frappe.get_doc("Contact", contact_name)
    payload.update(
        {
            "first_name": _clean_data(contact_doc.get("first_name")),
            "last_name": _clean_data(contact_doc.get("last_name")),
            "email": _normalize_email_value(get_contact_primary_email(contact_name)) or "",
            "mobile_phone": _contact_primary_mobile_from_doc(contact_doc),
        }
    )
    payload["available"] = bool(
        payload["first_name"] and payload["last_name"] and payload["email"] and payload["mobile_phone"]
    )
    return payload


def get_raw_contact_email_options_for_applicant_invite(
    *,
    contact: str | None,
    student_applicant: str | None,
    purpose: str | None,
    user: str | None = None,
) -> list[str]:
    assert_user_can_access_student_applicant_contact(
        student_applicant=student_applicant,
        purpose=purpose,
        user=user,
        workflow="applicant_invite_contact_options",
        owner_doctype="Contact",
        owner_name=contact,
        channel_type=CHANNEL_EMAIL,
    )
    contact_name = _clean_data(contact)
    if not contact_name:
        return []

    log_contact_access(
        access_type=ACCESS_TYPE_RECIPIENT_RESOLUTION,
        purpose=purpose,
        workflow="applicant_invite_contact_options",
        subject_doctype="Student Applicant",
        subject_name=student_applicant,
        owner_doctype="Contact",
        owner_name=contact_name,
        channel_type=CHANNEL_EMAIL,
        result=RESULT_ALLOWED,
        user=user,
        require_success=True,
    )

    rows = frappe.get_all(
        "Contact Email",
        filters={"parent": contact_name},
        fields=["email_id", "is_primary", "idx"],
        order_by="is_primary desc, idx asc, creation asc",
        ignore_permissions=True,
    )
    emails: list[str] = []
    seen: set[str] = set()
    for row in rows:
        normalized = _normalize_email_value(_row_get(row, "email_id"))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        emails.append(normalized)
    return emails


def get_raw_contact_primary_values_for_portal_context(
    *,
    contact: str | None,
    purpose: str | None,
    subject_doctype: str | None = None,
    subject_name: str | None = None,
    workflow: str | None = None,
    channel_type: str | None = None,
    log_access: bool = True,
) -> dict[str, Any]:
    resolved_purpose = require_purpose(purpose)
    contact_name = _clean_data(contact)
    if not contact_name or not frappe.db.exists("Contact", contact_name):
        return {"name": None, "primary_email": None, "primary_mobile": None}

    if log_access:
        log_contact_access(
            access_type=ACCESS_TYPE_RAW_READ,
            purpose=resolved_purpose,
            workflow=workflow or resolved_purpose,
            subject_doctype=subject_doctype,
            subject_name=subject_name,
            owner_doctype="Contact",
            owner_name=contact_name,
            channel_type=channel_type or CHANNEL_MIXED,
            result=RESULT_ALLOWED,
            require_success=True,
        )

    contact_row = frappe.db.get_value("Contact", contact_name, ["email_id", "mobile_no"], as_dict=True) or {}
    email_rows = frappe.get_all(
        "Contact Email",
        filters={"parent": contact_name},
        fields=["email_id", "is_primary", "idx"],
        order_by="is_primary desc, idx asc, creation asc",
        limit=0,
    )
    phone_rows = frappe.get_all(
        "Contact Phone",
        filters={"parent": contact_name},
        fields=["phone", "is_primary_mobile_no", "idx"],
        order_by="is_primary_mobile_no desc, idx asc, creation asc",
        limit=0,
    )

    primary_email = next(
        (_normalize_email_value(_row_get(row, "email_id")) for row in email_rows if _row_get(row, "email_id")),
        "",
    )
    primary_mobile = next((_clean_data(_row_get(row, "phone")) for row in phone_rows if _row_get(row, "phone")), "")
    if not primary_email:
        primary_email = _normalize_email_value(_row_get(contact_row, "email_id"))
    if not primary_mobile:
        primary_mobile = _clean_data(_row_get(contact_row, "mobile_no"))

    return {
        "name": contact_name,
        "primary_email": primary_email or None,
        "primary_mobile": primary_mobile or None,
    }


def _set_contact_primary_email(contact_doc, email: str) -> bool:
    email = _clean_data(email)
    if not email:
        return False

    changed = False
    email_rows = list(contact_doc.get("email_ids") or [])
    has_email = any(_clean_data(_row_get(row, "email_id")).casefold() == email.casefold() for row in email_rows)
    if not has_email:
        contact_doc.append("email_ids", {"email_id": email, "is_primary": 1})
        changed = True
        email_rows = list(contact_doc.get("email_ids") or [])

    primary_set = False
    for row in email_rows:
        row_email = _clean_data(_row_get(row, "email_id"))
        should_be_primary = row_email.casefold() == email.casefold() and not primary_set
        if should_be_primary:
            primary_set = True
        desired = 1 if should_be_primary else 0
        if _as_int(_row_get(row, "is_primary")) != desired:
            row.is_primary = desired
            changed = True

    if _clean_data(contact_doc.get("email_id")).casefold() != email.casefold():
        contact_doc.email_id = email
        changed = True
    return changed


def _set_contact_primary_mobile(contact_doc, mobile: str) -> bool:
    mobile = _clean_data(mobile)
    if not mobile:
        return False

    changed = False
    phone_rows = list(contact_doc.get("phone_nos") or [])
    has_phone = any(_clean_data(_row_get(row, "phone")) == mobile for row in phone_rows)
    if not has_phone:
        contact_doc.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})
        changed = True
        phone_rows = list(contact_doc.get("phone_nos") or [])

    primary_set = False
    for row in phone_rows:
        row_phone = _clean_data(_row_get(row, "phone"))
        should_be_primary = row_phone == mobile and not primary_set
        if should_be_primary:
            primary_set = True
        desired = 1 if should_be_primary else 0
        if _as_int(_row_get(row, "is_primary_mobile_no")) != desired:
            row.is_primary_mobile_no = desired
            changed = True

    if _clean_data(contact_doc.get("mobile_no")) != mobile:
        contact_doc.mobile_no = mobile
        changed = True
    return changed


def _assert_contact_linked_to_context(
    *,
    contact_name: str,
    context_doctype: str,
    context_name: str,
) -> None:
    if frappe.db.exists(
        "Dynamic Link",
        {
            "parenttype": "Contact",
            "parentfield": "links",
            "parent": contact_name,
            "link_doctype": context_doctype,
            "link_name": context_name,
        },
    ):
        return

    frappe.throw(_("Contact is not linked to the authorized family context."), frappe.PermissionError)


def update_family_contact_from_portal_context(
    *,
    context_doctype: str,
    context_name: str,
    payload: dict[str, Any],
    purpose: str | None,
) -> dict[str, Any]:
    resolved_purpose = require_purpose(purpose)
    contact_name = _clean_data(payload.get("contact"))
    channel_type = _clean_data(payload.get("channel_type"))
    value = _clean_data(payload.get("value"))
    resolved_context_doctype = _clean_data(context_doctype)
    resolved_context_name = _clean_data(context_name)

    if resolved_context_doctype not in {"Student", "Guardian"}:
        frappe.throw(_("Unsupported family contact context."), frappe.PermissionError)
    if not contact_name or not resolved_context_name:
        frappe.throw(_("Contact context is required."), frappe.PermissionError)

    _assert_contact_linked_to_context(
        contact_name=contact_name,
        context_doctype=resolved_context_doctype,
        context_name=resolved_context_name,
    )

    log_contact_access(
        access_type=ACCESS_TYPE_RAW_WRITE,
        purpose=resolved_purpose,
        workflow=resolved_purpose,
        subject_doctype=resolved_context_doctype,
        subject_name=resolved_context_name,
        owner_doctype="Contact",
        owner_name=contact_name,
        channel_type=CHANNEL_EMAIL if channel_type == "email" else CHANNEL_PHONE,
        result=RESULT_ALLOWED,
        require_success=True,
    )

    contact_doc = frappe.get_doc("Contact", contact_name)
    changed = False
    if channel_type == "email":
        changed = _set_contact_primary_email(contact_doc, value)
    elif channel_type == "mobile":
        changed = _set_contact_primary_mobile(contact_doc, value)
    else:
        frappe.throw(_("Unsupported family contact channel."), frappe.PermissionError)

    if changed:
        contact_doc.save(ignore_permissions=True)

    return get_raw_contact_primary_values_for_portal_context(
        contact=contact_name,
        purpose=resolved_purpose,
        subject_doctype=resolved_context_doctype,
        subject_name=resolved_context_name,
        workflow=resolved_purpose,
        channel_type=CHANNEL_EMAIL if channel_type == "email" else CHANNEL_PHONE,
        log_access=False,
    )


def _require_student_read_access(student: str | None, *, user: str | None = None):
    student_name = _clean_data(student)
    if not student_name or not frappe.db.exists("Student", student_name):
        frappe.throw(_("Student is required."), frappe.PermissionError)

    student_doc = frappe.get_doc("Student", student_name)
    if not frappe.has_permission("Student", doc=student_doc, ptype="read", user=user):
        frappe.throw(_("You do not have permission to access this Student."), frappe.PermissionError)
    return student_doc


def _contact_linked_to_student(student_name: str) -> str | None:
    contact_name = frappe.db.get_value(
        "Dynamic Link",
        {
            "parenttype": "Contact",
            "parentfield": "links",
            "link_doctype": "Student",
            "link_name": student_name,
        },
        "parent",
    )
    return _clean_data(contact_name) or None


def _get_masked_guardian_contact_point_values_for_student(
    *,
    guardian_names: list[str],
    school: str | None,
) -> dict[str, dict[str, str]]:
    resolved_school = _clean_data(school)
    if not resolved_school:
        return {}

    scoped_guardians = sorted({_clean_data(guardian) for guardian in guardian_names if _clean_data(guardian)})
    if not scoped_guardians:
        return {}

    rows = frappe.get_all(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        filters={
            "owner_doctype": "Guardian",
            "owner_name": ["in", scoped_guardians],
            "purpose": GUARDIAN_STUDENT_SUMMARY_CONTACT_POINT_PURPOSE,
            "school": resolved_school,
            "disabled": 0,
        },
        fields=["owner_name", "channel_type", "masked_display", "is_primary"],
        order_by="owner_name asc, channel_type asc, is_primary desc, modified desc",
        limit=0,
        ignore_permissions=True,
    )

    contact_points_by_guardian: dict[str, dict[str, str]] = {}
    for row in rows or []:
        guardian_name = _clean_data(_row_get(row, "owner_name"))
        channel_type = _clean_data(_row_get(row, "channel_type"))
        masked_display = _clean_data(_row_get(row, "masked_display"))
        if not guardian_name or not masked_display or channel_type not in {"email", "phone"}:
            continue
        guardian_payload = contact_points_by_guardian.setdefault(guardian_name, {})
        guardian_payload.setdefault(channel_type, masked_display)

    return contact_points_by_guardian


def get_masked_student_contact_summary(
    student: str | None,
    *,
    purpose: str | None,
    user: str | None = None,
) -> dict[str, Any] | None:
    require_purpose(purpose)
    student_doc = _require_student_read_access(student, user=user)
    contact_name = _contact_linked_to_student(student_doc.name)
    if not contact_name or not frappe.db.exists("Contact", contact_name):
        return None

    contact_row = (
        frappe.db.get_value(
            "Contact",
            contact_name,
            ["first_name", "last_name", "email_id", "mobile_no"],
            as_dict=True,
        )
        or {}
    )
    display_name = (
        " ".join(
            part
            for part in [
                _clean_data(_row_get(contact_row, "first_name")),
                _clean_data(_row_get(contact_row, "last_name")),
            ]
            if part
        ).strip()
        or contact_name
    )

    email_rows = frappe.get_all(
        "Contact Email",
        filters={"parent": contact_name},
        fields=["email_id", "is_primary", "idx"],
        order_by="is_primary desc, idx asc, creation asc",
        limit=0,
    )
    phone_rows = frappe.get_all(
        "Contact Phone",
        filters={"parent": contact_name},
        fields=["phone", "is_primary_mobile_no", "idx"],
        order_by="is_primary_mobile_no desc, idx asc, creation asc",
        limit=0,
    )

    emails = _mask_email_rows(email_rows)
    fallback_email = _normalize_email_value(_row_get(contact_row, "email_id"))
    if fallback_email and mask_email(fallback_email) not in {row["value"] for row in emails}:
        emails.insert(0, {"value": mask_email(fallback_email), "is_primary": 1})

    phones = _mask_phone_rows(phone_rows)
    fallback_phone = _clean_data(_row_get(contact_row, "mobile_no"))
    if fallback_phone and mask_phone(fallback_phone) not in {row["value"] for row in phones}:
        phones.insert(0, {"value": mask_phone(fallback_phone), "is_primary": 1})

    return {
        "name": contact_name,
        "display_name": display_name,
        "emails": emails,
        "phones": phones,
    }


def get_masked_guardian_contacts_for_student(
    student: str | None,
    *,
    purpose: str | None,
    user: str | None = None,
) -> list[dict[str, Any]]:
    require_purpose(purpose)
    student_doc = _require_student_read_access(student, user=user)
    rows = frappe.get_all(
        "Student Guardian",
        filters={"parent": student_doc.name, "parenttype": "Student", "parentfield": "guardians"},
        fields=["guardian", "guardian_name", "relation", "can_consent", "email", "phone"],
    )
    contact_points_by_guardian = _get_masked_guardian_contact_point_values_for_student(
        guardian_names=[_clean_data(_row_get(row, "guardian")) for row in rows or []],
        school=_row_get(student_doc, "anchor_school"),
    )
    return [
        {
            "guardian": _clean_data(_row_get(row, "guardian")),
            "guardian_name": _clean_data(_row_get(row, "guardian_name")),
            "relation": _clean_data(_row_get(row, "relation")),
            "can_consent": _as_int(_row_get(row, "can_consent")),
            "email": contact_points_by_guardian.get(_clean_data(_row_get(row, "guardian")), {}).get("email")
            or mask_email(_row_get(row, "email")),
            "phone": contact_points_by_guardian.get(_clean_data(_row_get(row, "guardian")), {}).get("phone")
            or mask_phone(_row_get(row, "phone")),
        }
        for row in rows
    ]


def assert_contact_not_protected_for_inquiry_reuse(
    contact: str | None,
    *,
    purpose: str | None,
    subject_doctype: str | None = None,
    subject_name: str | None = None,
) -> None:
    resolved_purpose = require_purpose(purpose)
    contact_name = _clean_data(contact)
    if not contact_name:
        return

    rows = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": "Contact",
            "parentfield": "links",
            "parent": contact_name,
            "link_doctype": ["in", sorted(PROTECTED_CONTACT_LINK_DOCTYPES)],
        },
        fields=["link_doctype", "link_name"],
        limit=1,
    )
    if rows:
        log_contact_access(
            access_type=ACCESS_TYPE_DENIED_ATTEMPT,
            purpose=resolved_purpose,
            workflow="inquiry_contact_reuse",
            subject_doctype=subject_doctype,
            subject_name=subject_name,
            owner_doctype="Contact",
            owner_name=contact_name,
            channel_type=CHANNEL_MIXED,
            result=RESULT_DENIED,
            details={"matched_link_doctype": _row_get(rows[0], "link_doctype")},
        )
        frappe.throw(
            _("Matched Contact is already linked to protected education records. Ask admissions staff to review."),
            frappe.PermissionError,
        )


def get_existing_contact_for_inquiry_reuse(
    *,
    email: str | None,
    phone: str | None,
    purpose: str | None,
    subject_doctype: str | None = None,
    subject_name: str | None = None,
) -> str | None:
    resolved_purpose = require_purpose(purpose)
    existing_contact = None
    normalized_email = _normalize_email_value(email)
    if normalized_email:
        existing_contact = frappe.db.get_value(
            "Contact Email",
            {"email_id": normalized_email, "is_primary": 1},
            "parent",
        )

    if not existing_contact and phone:
        existing_contact = frappe.db.get_value(
            "Contact Phone",
            {"phone": phone, "is_primary_mobile_no": 1},
            "parent",
        )

    if existing_contact:
        assert_contact_not_protected_for_inquiry_reuse(
            existing_contact,
            purpose=resolved_purpose,
            subject_doctype=subject_doctype,
            subject_name=subject_name,
        )
        log_contact_access(
            access_type=ACCESS_TYPE_RECIPIENT_RESOLUTION,
            purpose=resolved_purpose,
            workflow="inquiry_contact_reuse",
            subject_doctype=subject_doctype,
            subject_name=subject_name,
            owner_doctype="Contact",
            owner_name=existing_contact,
            channel_type=CHANNEL_MIXED,
            result=RESULT_ALLOWED,
            require_success=True,
        )
    return _clean_data(existing_contact) or None
