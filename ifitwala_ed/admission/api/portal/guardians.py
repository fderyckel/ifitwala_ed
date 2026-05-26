# ifitwala_ed/admission/api/portal/guardians.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, validate_email_address, validate_phone_number

from ifitwala_ed.admission.admission_utils import (
    ensure_contact_dynamic_link,
    normalize_email_value,
    upsert_contact_email,
)
from ifitwala_ed.admission.api.common.request_payload import _as_bool, _as_check
from ifitwala_ed.admission.api.portal.access import _as_text
from ifitwala_ed.admission.api.portal.contacts import (
    _applicant_contact_prefill_payload,
    _resolve_applicant_contact,
)
from ifitwala_ed.admission.api.portal.profile_images import _build_admissions_profile_image_urls

APPLICANT_GUARDIAN_RELATIONSHIP_OPTIONS = (
    "Mother",
    "Father",
    "Stepmother",
    "Stepfather",
    "Grandmother",
    "Grandfather",
    "Aunt",
    "Uncle",
    "Sister",
    "Brother",
    "Other",
)
APPLICANT_GUARDIAN_GENDER_OPTIONS = ("Female", "Male", "Other", "Prefer Not To Say")
APPLICANT_GUARDIAN_EMPLOYMENT_SECTOR_OPTIONS = (
    "Corporate – Finance / Banking",
    "Corporate – Tech / IT",
    "Corporate – Manufacturing",
    "Corporate – Retail / FMCG",
    "Corporate – Hospitality / Tourism",
    "Corporate – Logistics / Transport",
    "Corporate – Construction / Engineering",
    "Corporate – Real Estate / Property",
    "Healthcare / Medical",
    "Education",
    "Government",
    "Embassy / Diplomatic Corps",
    "NGO / Non-Profit",
    "Armed Forces",
    "Creative Industries (Media / Design / Arts)",
    "Self-Employed",
    "Freelance / Consultant",
    "Homemaker",
    "Retired",
    "Other",
)
APPLICANT_GUARDIAN_CHECK_FIELDS = (
    "use_applicant_contact",
    "is_primary",
    "can_consent",
    "is_primary_guardian",
    "is_financial_guardian",
)
APPLICANT_GUARDIAN_TEXT_FIELDS = (
    "guardian",
    "contact",
    "relationship",
    "salutation",
    "guardian_full_name",
    "guardian_first_name",
    "guardian_last_name",
    "guardian_gender",
    "guardian_mobile_phone",
    "guardian_email",
    "guardian_work_email",
    "guardian_work_phone",
    "guardian_image",
    "user",
    "employment_sector",
    "work_place",
    "guardian_designation",
)
APPLICANT_GUARDIAN_FIELDS = ("name",) + APPLICANT_GUARDIAN_TEXT_FIELDS + APPLICANT_GUARDIAN_CHECK_FIELDS
APPLICANT_GUARDIAN_REQUIRED_FIELDS = (
    "guardian_first_name",
    "guardian_last_name",
    "guardian_email",
    "guardian_mobile_phone",
    "guardian_image",
)
APPLICANT_GUARDIAN_INVITE_REQUIRED_FIELDS = (
    "guardian_first_name",
    "guardian_last_name",
    "guardian_email",
    "guardian_mobile_phone",
)
APPLICANT_CONTACT_GUARDIAN_ROW = "__applicant_contact_guardian__"


def _guardian_salutation_options() -> list[dict]:
    try:
        rows = frappe.get_all(
            "Salutation",
            fields=["name", "salutation"],
            order_by="name asc",
        )
    except Exception:
        return []
    output = []
    for row in rows:
        value = _as_text(row.get("name")).strip()
        if not value:
            continue
        label = _as_text(row.get("salutation")).strip() or value
        output.append({"value": value, "label": label})
    return output


def _guardians_feature_enabled() -> bool:
    try:
        setting = frappe.db.get_single_value("Admission Settings", "show_guardians_in_admissions_profile")
    except Exception:
        return False
    return bool(cint(setting or 0))


def _serialize_applicant_guardians(
    applicant,
    *,
    authority_map: dict[str, tuple[dict, dict | None]] | None = None,
    thumbnail_ready_map: dict[str, bool] | None = None,
) -> list[dict]:
    authority_map = authority_map or {}
    thumbnail_ready_map = thumbnail_ready_map or {}
    rows: list[dict] = []
    for row in applicant.get("guardians") or []:
        payload: dict = {}
        guardian_row_name = _as_text(row.get("name")).strip()
        for fieldname in APPLICANT_GUARDIAN_FIELDS:
            if fieldname in APPLICANT_GUARDIAN_CHECK_FIELDS:
                payload[fieldname] = _as_check(row.get(fieldname))
            elif fieldname == "guardian_image":
                drive_file, file_row = authority_map.get(guardian_row_name, ({}, None))
                image_urls = _build_admissions_profile_image_urls(
                    applicant_name=applicant.name,
                    guardian_row_name=guardian_row_name,
                    original_image=_as_text(row.get(fieldname)).strip(),
                    drive_file=drive_file,
                    file_row=file_row,
                    thumbnail_ready=thumbnail_ready_map.get(str((drive_file or {}).get("name") or "").strip()),
                )
                payload[fieldname] = image_urls["image_url"]
                payload["guardian_image_open_url"] = image_urls["open_url"]
            else:
                payload[fieldname] = _as_text(row.get(fieldname)).strip()
        payload.setdefault("guardian_image_open_url", "")
        rows.append(payload)
    return rows


def _parse_guardians_payload(guardians) -> list[dict] | None:
    if guardians is None:
        return None

    payload = guardians
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, list):
        frappe.throw(_("Guardians payload must be a list."))

    normalized: list[dict] = []
    for row in payload:
        if not isinstance(row, dict):
            frappe.throw(_("Each guardian entry must be an object."))
        normalized.append(row)
    return normalized


def _guardian_row_is_empty(row: dict) -> bool:
    identity_fields = (
        "guardian",
        "guardian_first_name",
        "guardian_last_name",
        "guardian_email",
        "guardian_mobile_phone",
        "salutation",
        "guardian_work_email",
        "guardian_work_phone",
        "employment_sector",
        "work_place",
        "guardian_designation",
        "guardian_image",
    )
    return not any(_as_text(row.get(fieldname)).strip() for fieldname in identity_fields)


def _guardian_signer_flag_from_primary_guardian(row: dict) -> int:
    return 1 if _as_check(row.get("is_primary_guardian")) else 0


def _applicant_guardian_required_field_label(fieldname: str) -> str:
    if fieldname == "guardian_first_name":
        return _("Guardian First Name")
    if fieldname == "guardian_last_name":
        return _("Guardian Last Name")
    if fieldname == "guardian_email":
        return _("Guardian Personal Email")
    if fieldname == "guardian_mobile_phone":
        return _("Guardian Mobile Phone")
    if fieldname == "guardian_image":
        return _("Guardian Photo")
    return fieldname


def _validate_guardian_profile_row(row: dict, *, require_photo: bool = True) -> dict:
    required_fields = APPLICANT_GUARDIAN_REQUIRED_FIELDS if require_photo else APPLICANT_GUARDIAN_INVITE_REQUIRED_FIELDS
    missing_labels = [
        _applicant_guardian_required_field_label(fieldname)
        for fieldname in required_fields
        if not _as_text(row.get(fieldname)).strip()
    ]
    if missing_labels:
        frappe.throw(
            _("Each guardian must include: {missing_fields}.").format(missing_fields=", ".join(missing_labels))
        )

    guardian_email = normalize_email_value(row.get("guardian_email"))
    try:
        validate_email_address(guardian_email, True)
    except Exception:
        frappe.throw(_("Guardian personal email must be a valid email address."))
    row["guardian_email"] = guardian_email

    guardian_work_email = normalize_email_value(row.get("guardian_work_email"))
    if guardian_work_email:
        try:
            validate_email_address(guardian_work_email, True)
        except Exception:
            frappe.throw(_("Guardian work email must be a valid email address."))
    row["guardian_work_email"] = guardian_work_email

    guardian_mobile_phone = _as_text(row.get("guardian_mobile_phone")).strip()
    try:
        validate_phone_number(guardian_mobile_phone, throw=True)
    except Exception:
        frappe.throw(_("Guardian mobile phone must be a valid phone number."))
    row["guardian_mobile_phone"] = guardian_mobile_phone

    guardian_work_phone = _as_text(row.get("guardian_work_phone")).strip()
    if guardian_work_phone:
        try:
            validate_phone_number(guardian_work_phone, throw=True)
        except Exception:
            frappe.throw(_("Guardian work phone must be a valid phone number."))
    row["guardian_work_phone"] = guardian_work_phone
    row["can_consent"] = _guardian_signer_flag_from_primary_guardian(row)

    return row


def _contact_is_linked_to_applicant(*, contact_name: str, applicant_name: str) -> bool:
    if not contact_name or not applicant_name:
        return False
    return bool(
        frappe.db.exists(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parentfield": "links",
                "parent": contact_name,
                "link_doctype": "Student Applicant",
                "link_name": applicant_name,
            },
        )
    )


def _set_contact_primary_mobile(contact_doc, mobile: str) -> bool:
    mobile = _as_text(mobile).strip()
    if not mobile:
        return False

    changed = False
    phone_rows = list(contact_doc.get("phone_nos") or [])
    has_phone = any(_as_text(row.get("phone")).strip() == mobile for row in phone_rows)
    if not has_phone:
        contact_doc.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})
        changed = True
        phone_rows = list(contact_doc.get("phone_nos") or [])

    primary_set = False
    for row in phone_rows:
        row_phone = _as_text(row.get("phone")).strip()
        should_be_primary = row_phone == mobile and not primary_set
        if should_be_primary:
            primary_set = True
        desired = 1 if should_be_primary else 0
        if cint(row.get("is_primary_mobile_no") or 0) != desired:
            row.is_primary_mobile_no = desired
            changed = True

    if _as_text(contact_doc.get("mobile_no")).strip() != mobile:
        contact_doc.mobile_no = mobile
        changed = True

    return changed


def _set_contact_primary_email(contact_name: str, email: str) -> None:
    contact_name = _as_text(contact_name).strip()
    email = normalize_email_value(email)
    if not contact_name or not email:
        return

    upsert_contact_email(contact_name, email, set_primary_if_missing=True)
    contact_doc = frappe.get_doc("Contact", contact_name)
    changed = False
    primary_set = False
    for row in contact_doc.get("email_ids") or []:
        row_email = normalize_email_value(row.get("email_id"))
        should_be_primary = row_email == email and not primary_set
        if should_be_primary:
            primary_set = True
        desired = 1 if should_be_primary else 0
        if cint(row.get("is_primary") or 0) != desired:
            row.is_primary = desired
            changed = True

    if changed:
        contact_doc.save(ignore_permissions=True)


def _guardian_contact_name_from_guardian_email(email: str) -> str:
    normalized = normalize_email_value(email)
    if not normalized:
        return ""
    return _as_text(
        frappe.db.get_value(
            "Contact Email",
            {"email_id": normalized},
            "parent",
        )
    ).strip()


def _hydrate_guardian_row_from_guardian_doc(*, row_payload: dict, guardian_doc) -> dict:
    row = dict(row_payload)
    row["guardian"] = guardian_doc.name
    row["salutation"] = row.get("salutation") or _as_text(guardian_doc.get("salutation")).strip()
    row["guardian_first_name"] = (
        row.get("guardian_first_name") or _as_text(guardian_doc.get("guardian_first_name")).strip()
    )
    row["guardian_last_name"] = (
        row.get("guardian_last_name") or _as_text(guardian_doc.get("guardian_last_name")).strip()
    )
    row["guardian_gender"] = row.get("guardian_gender") or _as_text(guardian_doc.get("guardian_gender")).strip()
    row["guardian_mobile_phone"] = (
        row.get("guardian_mobile_phone") or _as_text(guardian_doc.get("guardian_mobile_phone")).strip()
    )
    row["guardian_email"] = row.get("guardian_email") or _as_text(guardian_doc.get("guardian_email")).strip()
    row["guardian_work_email"] = (
        row.get("guardian_work_email") or _as_text(guardian_doc.get("guardian_work_email")).strip()
    )
    row["guardian_work_phone"] = (
        row.get("guardian_work_phone") or _as_text(guardian_doc.get("guardian_work_phone")).strip()
    )
    row["employment_sector"] = row.get("employment_sector") or _as_text(guardian_doc.get("employment_sector")).strip()
    row["work_place"] = row.get("work_place") or _as_text(guardian_doc.get("work_place")).strip()
    row["guardian_designation"] = (
        row.get("guardian_designation") or _as_text(guardian_doc.get("guardian_designation")).strip()
    )
    row["guardian_image"] = row.get("guardian_image") or _as_text(guardian_doc.get("guardian_image")).strip()
    row["user"] = row.get("user") or _as_text(guardian_doc.get("user")).strip()

    if row.get("is_primary_guardian") in (None, ""):
        row["is_primary_guardian"] = _as_check(guardian_doc.get("is_primary_guardian"))
    if row.get("is_financial_guardian") in (None, ""):
        row["is_financial_guardian"] = _as_check(guardian_doc.get("is_financial_guardian"))

    row["guardian_full_name"] = _as_text(guardian_doc.get("guardian_full_name")).strip() or " ".join(
        part for part in [row.get("guardian_first_name"), row.get("guardian_last_name")] if _as_text(part).strip()
    )

    contact_name = _as_text(row.get("contact")).strip()
    if not contact_name:
        contact_name = _guardian_contact_name_from_guardian_email(_as_text(row.get("guardian_email")).strip())
    if contact_name:
        row["contact"] = contact_name

    return row


def _hydrate_guardian_row_from_applicant_contact(*, applicant, row_payload: dict) -> dict:
    row = dict(row_payload)
    _resolve_applicant_contact(applicant, allow_create=False, bind_to_applicant=True)
    contact_payload = _applicant_contact_prefill_payload(applicant)
    if not contact_payload.get("contact"):
        frappe.throw(_("Applicant Contact is required before using it for guardian contact tracking."))

    row["contact"] = contact_payload["contact"]
    row["guardian_first_name"] = row.get("guardian_first_name") or contact_payload.get("first_name") or ""
    row["guardian_last_name"] = row.get("guardian_last_name") or contact_payload.get("last_name") or ""
    row["guardian_email"] = row.get("guardian_email") or contact_payload.get("email") or ""
    row["guardian_mobile_phone"] = row.get("guardian_mobile_phone") or contact_payload.get("mobile_phone") or ""
    if not _as_text(row.get("guardian_full_name")).strip():
        row["guardian_full_name"] = " ".join(
            part
            for part in [
                _as_text(row.get("guardian_first_name")).strip(),
                _as_text(row.get("guardian_last_name")).strip(),
            ]
            if part
        )
    return row


def _update_contact_identity_from_guardian_row(*, contact_name: str, row_payload: dict) -> None:
    contact_name = _as_text(contact_name).strip()
    if not contact_name:
        frappe.throw(_("Contact is required."))

    contact_doc = frappe.get_doc("Contact", contact_name)
    changed = False

    first_name = _as_text(row_payload.get("guardian_first_name")).strip()
    last_name = _as_text(row_payload.get("guardian_last_name")).strip()
    mobile = _as_text(row_payload.get("guardian_mobile_phone")).strip()
    email = normalize_email_value(row_payload.get("guardian_email"))

    if first_name and _as_text(contact_doc.get("first_name")).strip() != first_name:
        contact_doc.first_name = first_name
        changed = True
    if last_name and _as_text(contact_doc.get("last_name")).strip() != last_name:
        contact_doc.last_name = last_name
        changed = True
    if mobile and _set_contact_primary_mobile(contact_doc, mobile):
        changed = True

    if changed:
        contact_doc.save(ignore_permissions=True)
    if email:
        _set_contact_primary_email(contact_name, email)


def _create_or_update_guardian_contact(
    *,
    applicant,
    row_payload: dict,
    existing_contact_name: str | None = None,
) -> str:
    use_applicant_contact = _as_bool(row_payload.get("use_applicant_contact"))
    applicant_contact = _as_text(
        _resolve_applicant_contact(applicant, allow_create=False, bind_to_applicant=use_applicant_contact)
    ).strip()
    if use_applicant_contact:
        if not applicant_contact:
            frappe.throw(_("Applicant Contact is required before using it for guardian contact tracking."))
        ensure_contact_dynamic_link(
            contact_name=applicant_contact,
            link_doctype="Student Applicant",
            link_name=applicant.name,
        )
        _update_contact_identity_from_guardian_row(contact_name=applicant_contact, row_payload=row_payload)
        return applicant_contact

    first_name = _as_text(row_payload.get("guardian_first_name")).strip()
    last_name = _as_text(row_payload.get("guardian_last_name")).strip()
    email = normalize_email_value(row_payload.get("guardian_email"))
    mobile = _as_text(row_payload.get("guardian_mobile_phone")).strip()

    if not first_name:
        frappe.throw(_("Guardian first name is required."))
    if not last_name:
        frappe.throw(_("Guardian last name is required."))
    if not email:
        frappe.throw(_("Guardian personal email is required."))
    if not mobile:
        frappe.throw(_("Guardian mobile phone is required."))

    contact_name = _as_text(existing_contact_name).strip()
    if contact_name:
        if not frappe.db.exists("Contact", contact_name):
            contact_name = ""
        elif not _contact_is_linked_to_applicant(contact_name=contact_name, applicant_name=applicant.name):
            frappe.throw(_("Guardian Contact must already be linked to this applicant."))

    contact_from_email = _guardian_contact_name_from_guardian_email(email)
    if contact_from_email and contact_from_email != contact_name:
        if not _contact_is_linked_to_applicant(contact_name=contact_from_email, applicant_name=applicant.name):
            frappe.throw(
                _("Guardian email is linked to another contact. Ask admissions staff to link that contact first.")
            )
        contact_name = contact_from_email

    if contact_name:
        contact_doc = frappe.get_doc("Contact", contact_name)
    else:
        contact_doc = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": first_name,
                "last_name": last_name,
                "email_ids": [{"email_id": email, "is_primary": 1}],
                "phone_nos": [{"phone": mobile, "is_primary_mobile_no": 1}],
                "mobile_no": mobile,
            }
        )
        contact_doc.insert(ignore_permissions=True)
        contact_name = contact_doc.name

    changed = False
    if _as_text(contact_doc.get("first_name")).strip() != first_name:
        contact_doc.first_name = first_name
        changed = True
    if _as_text(contact_doc.get("last_name")).strip() != last_name:
        contact_doc.last_name = last_name
        changed = True

    upsert_contact_email(contact_name, email, set_primary_if_missing=True)
    if _set_contact_primary_mobile(contact_doc, mobile):
        changed = True

    if changed:
        contact_doc.save(ignore_permissions=True)

    ensure_contact_dynamic_link(
        contact_name=contact_name,
        link_doctype="Student Applicant",
        link_name=applicant.name,
    )
    return contact_name


def _normalize_guardian_row(row_payload: dict) -> dict:
    normalized: dict = {}
    for fieldname in APPLICANT_GUARDIAN_TEXT_FIELDS:
        normalized[fieldname] = _as_text(row_payload.get(fieldname)).strip()
    for fieldname in APPLICANT_GUARDIAN_CHECK_FIELDS:
        normalized[fieldname] = _as_check(row_payload.get(fieldname))

    normalized["name"] = _as_text(row_payload.get("name")).strip()
    normalized["relationship"] = normalized.get("relationship") or "Other"
    normalized["can_consent"] = _guardian_signer_flag_from_primary_guardian(normalized)
    return normalized


def _apply_guardians_to_applicant(*, applicant, guardians_payload: list[dict]):
    existing_by_name = {row.name: row for row in (applicant.get("guardians") or []) if row.name}
    normalized_rows: list[dict] = []

    for row_payload in guardians_payload:
        row = _normalize_guardian_row(row_payload)
        existing_row = existing_by_name.get(_as_text(row.get("name")).strip())

        guardian_name = _as_text(row.get("guardian")).strip()
        if guardian_name:
            if not frappe.db.exists("Guardian", guardian_name):
                frappe.throw(_("Invalid Guardian: {guardian}.").format(guardian=guardian_name))
            guardian_doc = frappe.get_doc("Guardian", guardian_name)
            row = _hydrate_guardian_row_from_guardian_doc(row_payload=row, guardian_doc=guardian_doc)
        if _as_check(row.get("use_applicant_contact")):
            row = _hydrate_guardian_row_from_applicant_contact(applicant=applicant, row_payload=row)

        if existing_row and not _as_text(row.get("guardian_image")).strip():
            row["guardian_image"] = _as_text(existing_row.get("guardian_image")).strip()

        if _guardian_row_is_empty(row):
            continue
        row = _validate_guardian_profile_row(row)

        existing_contact_name = _as_text(row.get("contact")).strip()
        if not existing_contact_name and existing_row:
            existing_contact_name = _as_text(existing_row.get("contact")).strip()
        row["contact"] = _create_or_update_guardian_contact(
            applicant=applicant,
            row_payload=row,
            existing_contact_name=existing_contact_name,
        )
        row["guardian_image"] = _as_text(row.get("guardian_image")).strip()

        if not _as_text(row.get("guardian_full_name")).strip():
            row["guardian_full_name"] = " ".join(
                part
                for part in [
                    _as_text(row.get("guardian_first_name")).strip(),
                    _as_text(row.get("guardian_last_name")).strip(),
                ]
                if part
            )

        normalized_rows.append(row)

    applicant.set("guardians", [])
    for row in normalized_rows:
        applicant.append(
            "guardians",
            {
                "guardian": row.get("guardian") or None,
                "contact": row.get("contact") or None,
                "use_applicant_contact": _as_check(row.get("use_applicant_contact")),
                "relationship": row.get("relationship") or "Other",
                "is_primary": _as_check(row.get("is_primary")),
                "can_consent": _as_check(row.get("can_consent")),
                "salutation": row.get("salutation") or None,
                "guardian_full_name": row.get("guardian_full_name") or None,
                "guardian_first_name": row.get("guardian_first_name") or None,
                "guardian_last_name": row.get("guardian_last_name") or None,
                "guardian_gender": row.get("guardian_gender") or None,
                "guardian_mobile_phone": row.get("guardian_mobile_phone") or None,
                "guardian_email": normalize_email_value(row.get("guardian_email")) or None,
                "guardian_work_email": normalize_email_value(row.get("guardian_work_email")) or None,
                "guardian_work_phone": row.get("guardian_work_phone") or None,
                "guardian_image": row.get("guardian_image") or None,
                "user": row.get("user") or None,
                "is_primary_guardian": _as_check(row.get("is_primary_guardian")),
                "is_financial_guardian": _as_check(row.get("is_financial_guardian")),
                "employment_sector": row.get("employment_sector") or None,
                "work_place": row.get("work_place") or None,
                "guardian_designation": row.get("guardian_designation") or None,
            },
        )


def _guardian_row_display_name(row) -> str:
    full_name = _as_text(row.get("guardian_full_name")).strip()
    if full_name:
        return full_name
    parts = [
        _as_text(row.get("guardian_first_name")).strip(),
        _as_text(row.get("guardian_last_name")).strip(),
    ]
    name = " ".join(part for part in parts if part).strip()
    return name or _as_text(row.get("relationship")).strip() or _as_text(row.get("name")).strip()
