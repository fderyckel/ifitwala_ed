from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime

from ifitwala_ed.api.guardian_home import _resolve_guardian_scope
from ifitwala_ed.api.guardian_policy import _children_with_signer_authority, _expected_guardian_signature_name
from ifitwala_ed.api.student_policy import _expected_student_signature_name, _require_student_name_for_session_user
from ifitwala_ed.governance.doctype.family_consent_request.family_consent_request import (
    AUDIENCE_GUARDIAN,
    AUDIENCE_STUDENT,
    COMPLETION_CHANNEL_PAPER_ONLY,
    DECISION_MODE_APPROVE_DECLINE,
    DECISION_MODE_GRANT_DENY,
    FIELD_MODE_ALLOW_OVERRIDE,
    FIELD_MODE_DISPLAY_ONLY,
    FIELD_TYPE_ADDRESS,
    FIELD_TYPE_CHECKBOX,
    FIELD_TYPE_DATE,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_PUBLISHED,
    SIGNER_RULE_ALL_GUARDIANS,
    SIGNER_RULE_ANY_GUARDIAN,
    SIGNER_RULE_STUDENT_SELF,
    SUBJECT_SCOPE_PER_STUDENT,
)
from ifitwala_ed.students.doctype.student.student import get_contact_linked_to_student
from ifitwala_ed.utilities.html_sanitizer import sanitize_html

CURRENT_STATUS_COMPLETED = "completed"
CURRENT_STATUS_DECLINED = "declined"
CURRENT_STATUS_WITHDRAWN = "withdrawn"
CURRENT_STATUS_EXPIRED = "expired"
CURRENT_STATUS_OVERDUE = "overdue"
CURRENT_STATUS_PENDING = "pending"

SOURCE_CHANNEL_GUARDIAN_PORTAL = "Guardian Portal"
SOURCE_CHANNEL_STUDENT_PORTAL = "Student Portal"

ADDRESS_VALUE_KEYS = (
    "address_line1",
    "address_line2",
    "city",
    "state",
    "country",
    "pincode",
)
DECISION_STATUSES_BY_MODE = {
    DECISION_MODE_APPROVE_DECLINE: {"Approved", "Declined"},
    DECISION_MODE_GRANT_DENY: {"Granted", "Denied"},
}
PORTAL_REQUEST_STATUSES = (REQUEST_STATUS_PUBLISHED, REQUEST_STATUS_CLOSED)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _clean_data(value: Any) -> str:
    return str(value or "").strip()


def _as_bool(value: Any) -> bool:
    return bool(cint(value))


def _normalize_signature_name(value: str | None) -> str:
    return _clean_text(value).casefold()


def _parse_rows(value: Any) -> list[dict[str, Any]]:
    parsed = frappe.parse_json(value) if isinstance(value, str) else value
    if not parsed:
        return []
    if not isinstance(parsed, list):
        frappe.throw(_("Field values must be a list payload."))
    rows: list[dict[str, Any]] = []
    for row in parsed:
        if not isinstance(row, dict):
            frappe.throw(_("Each field value row must be an object."))
        rows.append(row)
    return rows


def _normalize_address_value(value: Any) -> dict[str, str] | None:
    parsed = frappe.parse_json(value) if isinstance(value, str) else value
    if parsed in (None, "", {}):
        return None
    if not isinstance(parsed, dict):
        frappe.throw(_("Address field values must be an object payload."))
    normalized = {key: _clean_data(parsed.get(key)) for key in ADDRESS_VALUE_KEYS}
    return normalized if any(normalized.values()) else None


def _normalize_field_value(field_type: str, value: Any) -> Any:
    if field_type == FIELD_TYPE_ADDRESS:
        return _normalize_address_value(value)
    if field_type == FIELD_TYPE_CHECKBOX:
        return bool(cint(value))
    if field_type == FIELD_TYPE_DATE:
        cleaned = _clean_data(value)
        return str(getdate(cleaned)) if cleaned else None

    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value

    cleaned = str(value).strip()
    return cleaned or None


def _values_equal(left: Any, right: Any) -> bool:
    return json.dumps(left, sort_keys=True, separators=(",", ":"), default=str) == json.dumps(
        right, sort_keys=True, separators=(",", ":"), default=str
    )


def _has_value(field_type: str, value: Any) -> bool:
    if field_type == FIELD_TYPE_ADDRESS:
        return bool(
            value and isinstance(value, dict) and any(_clean_data(value.get(key)) for key in ADDRESS_VALUE_KEYS)
        )
    if field_type == FIELD_TYPE_CHECKBOX:
        return bool(value)
    return value not in (None, "")


def _decision_status_label(current_status: str, latest_decision: dict[str, Any] | None = None) -> str:
    if current_status == CURRENT_STATUS_COMPLETED:
        return _clean_data((latest_decision or {}).get("decision_status")) or _("Completed")
    if current_status == CURRENT_STATUS_DECLINED:
        return _clean_data((latest_decision or {}).get("decision_status")) or _("Declined")
    if current_status == CURRENT_STATUS_WITHDRAWN:
        return _("Withdrawn")
    if current_status == CURRENT_STATUS_EXPIRED:
        return _("Expired")
    if current_status == CURRENT_STATUS_OVERDUE:
        return _("Overdue")
    return _("Action needed")


def _derive_current_target_status(
    *,
    request_row: dict[str, Any],
    latest_decision: dict[str, Any] | None,
    today,
) -> str:
    if latest_decision:
        status = _clean_data(latest_decision.get("decision_status"))
        if status in {"Approved", "Granted"}:
            return CURRENT_STATUS_COMPLETED
        if status in {"Declined", "Denied"}:
            return CURRENT_STATUS_DECLINED
        if status == "Withdrawn":
            return CURRENT_STATUS_WITHDRAWN

    effective_to = getdate(request_row.get("effective_to")) if request_row.get("effective_to") else None
    due_on = getdate(request_row.get("due_on")) if request_row.get("due_on") else None
    if effective_to and effective_to < today:
        return CURRENT_STATUS_EXPIRED
    if due_on and due_on < today:
        return CURRENT_STATUS_OVERDUE
    return CURRENT_STATUS_PENDING


def _get_dynamic_link_parents(*, parenttype: str, link_doctype: str, link_name: str) -> list[str]:
    rows = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": parenttype,
            "link_doctype": link_doctype,
            "link_name": link_name,
        },
        fields=["parent"],
        order_by="creation asc",
        limit=0,
    )
    out: list[str] = []
    seen: set[str] = set()
    for row in rows:
        parent = _clean_data(row.get("parent"))
        if parent and parent not in seen:
            seen.add(parent)
            out.append(parent)
    return out


def _get_linked_address_names(*, link_doctype: str, link_name: str) -> list[str]:
    return _get_dynamic_link_parents(parenttype="Address", link_doctype=link_doctype, link_name=link_name)


def _get_address_value(address_name: str | None) -> dict[str, str] | None:
    address_name = _clean_data(address_name)
    if not address_name:
        return None
    row = frappe.db.get_value(
        "Address",
        address_name,
        list(ADDRESS_VALUE_KEYS),
        as_dict=True,
    )
    if not row:
        return None
    normalized = {key: _clean_data((row or {}).get(key)) for key in ADDRESS_VALUE_KEYS}
    return normalized if any(normalized.values()) else None


def _resolve_single_address(*, link_doctype: str, link_name: str) -> tuple[str | None, dict[str, str] | None]:
    names = _get_linked_address_names(link_doctype=link_doctype, link_name=link_name)
    if len(names) != 1:
        return None, None
    return names[0], _get_address_value(names[0])


def _get_contact_primary_values(contact_name: str | None) -> dict[str, Any]:
    contact_name = _clean_data(contact_name)
    if not contact_name or not frappe.db.exists("Contact", contact_name):
        return {"name": None, "primary_email": None, "primary_mobile": None}

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
        (_clean_data(row.get("email_id")) for row in email_rows if _clean_data(row.get("email_id"))), ""
    )
    primary_mobile = next((_clean_data(row.get("phone")) for row in phone_rows if _clean_data(row.get("phone"))), "")
    if not primary_email:
        primary_email = _clean_data(contact_row.get("email_id"))
    if not primary_mobile:
        primary_mobile = _clean_data(contact_row.get("mobile_no"))

    return {
        "name": contact_name,
        "primary_email": primary_email or None,
        "primary_mobile": primary_mobile or None,
    }


def _get_guardian_contact_name(guardian_name: str) -> str | None:
    guardian_name = _clean_data(guardian_name)
    if not guardian_name:
        return None

    linked = _get_dynamic_link_parents(parenttype="Contact", link_doctype="Guardian", link_name=guardian_name)
    if linked:
        return linked[0]

    guardian_row = frappe.db.get_value("Guardian", guardian_name, ["user", "guardian_email"], as_dict=True) or {}
    user = _clean_data(guardian_row.get("user"))
    if user:
        contact_name = frappe.db.get_value("Contact", {"user": user}, "name")
        if contact_name:
            return _clean_data(contact_name)

    guardian_email = _clean_data(guardian_row.get("guardian_email"))
    if guardian_email:
        return _clean_data(frappe.db.get_value("Contact Email", {"email_id": guardian_email}, "parent"))
    return None


def _get_or_create_guardian_contact(guardian_name: str) -> str:
    contact_name = _clean_data(_get_guardian_contact_name(guardian_name))
    if contact_name:
        return contact_name

    guardian_doc = frappe.get_doc("Guardian", guardian_name)
    contact_name = guardian_doc._get_or_create_contact()  # noqa: SLF001
    guardian_doc._ensure_contact_link(contact_name)  # noqa: SLF001
    return _clean_data(contact_name)


def _get_or_create_student_contact(student_name: str, student_row: dict[str, Any]) -> str:
    contact_name = _clean_data(get_contact_linked_to_student(student_name))
    if contact_name:
        return contact_name

    display_name = _clean_data(student_row.get("student_preferred_name")) or _clean_data(
        student_row.get("student_full_name")
    )
    contact_payload = {
        "doctype": "Contact",
        "first_name": display_name or student_name,
        "last_name": "",
        "user": frappe.session.user if frappe.session.user != "Guest" else None,
    }
    email = _clean_data(student_row.get("student_email"))
    mobile = _clean_data(student_row.get("student_mobile_number"))
    if email:
        contact_payload["email_ids"] = [{"email_id": email, "is_primary": 1}]
        contact_payload["email_id"] = email
    if mobile:
        contact_payload["phone_nos"] = [{"phone": mobile, "is_primary_mobile_no": 1}]
        contact_payload["mobile_no"] = mobile

    contact_doc = frappe.get_doc(contact_payload)
    contact_doc.insert(ignore_permissions=True)
    frappe.get_doc(
        {
            "doctype": "Dynamic Link",
            "parenttype": "Contact",
            "parentfield": "links",
            "parent": contact_doc.name,
            "link_doctype": "Student",
            "link_name": student_name,
            "link_title": display_name or student_name,
        }
    ).insert(ignore_permissions=True)
    return _clean_data(contact_doc.name)


def _set_contact_primary_email(contact_doc, email: str) -> bool:
    email = _clean_data(email)
    if not email:
        return False

    changed = False
    email_rows = list(contact_doc.get("email_ids") or [])
    has_email = any(_clean_data(row.get("email_id")).casefold() == email.casefold() for row in email_rows)
    if not has_email:
        contact_doc.append("email_ids", {"email_id": email, "is_primary": 1})
        changed = True
        email_rows = list(contact_doc.get("email_ids") or [])

    primary_set = False
    for row in email_rows:
        row_email = _clean_data(row.get("email_id"))
        should_be_primary = row_email.casefold() == email.casefold() and not primary_set
        if should_be_primary:
            primary_set = True
        desired = 1 if should_be_primary else 0
        if cint(row.get("is_primary") or 0) != desired:
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
    has_phone = any(_clean_data(row.get("phone")) == mobile for row in phone_rows)
    if not has_phone:
        contact_doc.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})
        changed = True
        phone_rows = list(contact_doc.get("phone_nos") or [])

    primary_set = False
    for row in phone_rows:
        row_phone = _clean_data(row.get("phone"))
        should_be_primary = row_phone == mobile and not primary_set
        if should_be_primary:
            primary_set = True
        desired = 1 if should_be_primary else 0
        if cint(row.get("is_primary_mobile_no") or 0) != desired:
            row.is_primary_mobile_no = desired
            changed = True

    if _clean_data(contact_doc.get("mobile_no")) != mobile:
        contact_doc.mobile_no = mobile
        changed = True
    return changed


def _ensure_guardian_portal_scope() -> tuple[str, list[dict[str, Any]]]:
    guardian_name, children = _resolve_guardian_scope(frappe.session.user)
    return guardian_name, _children_with_signer_authority(guardian_name=guardian_name, children=children or [])


def _load_request_rows(*, request_names: list[str], audience_mode: str) -> dict[str, dict[str, Any]]:
    if not request_names:
        return {}
    rows = frappe.get_all(
        "Family Consent Request",
        filters={
            "name": ["in", tuple(request_names)],
            "status": ["in", PORTAL_REQUEST_STATUSES],
            "audience_mode": audience_mode,
        },
        fields=[
            "name",
            "request_key",
            "request_title",
            "request_type",
            "request_text",
            "subject_scope",
            "audience_mode",
            "signer_rule",
            "decision_mode",
            "completion_channel_mode",
            "requires_typed_signature",
            "requires_attestation",
            "effective_from",
            "effective_to",
            "due_on",
            "source_file",
            "status",
        ],
        order_by="modified desc",
        limit=0,
    )
    return {_clean_data(row.get("name")): row for row in rows if _clean_data(row.get("name"))}


def _request_is_executable(request_row: dict[str, Any], *, audience_mode: str) -> bool:
    if _clean_data(request_row.get("subject_scope")) != SUBJECT_SCOPE_PER_STUDENT:
        return False
    if _clean_data(request_row.get("audience_mode")) != audience_mode:
        return False
    decision_mode = _clean_data(request_row.get("decision_mode"))
    if decision_mode not in DECISION_STATUSES_BY_MODE:
        return False
    signer_rule = _clean_data(request_row.get("signer_rule"))
    if audience_mode == AUDIENCE_GUARDIAN:
        return signer_rule in {SIGNER_RULE_ANY_GUARDIAN, SIGNER_RULE_ALL_GUARDIANS}
    if audience_mode == AUDIENCE_STUDENT:
        return signer_rule == SIGNER_RULE_STUDENT_SELF
    return False


def _get_relevant_decisions(
    *,
    request_names: list[str],
    student_names: list[str],
    decision_by_doctype: str,
    decision_by: str,
    descending: bool = False,
) -> list[dict[str, Any]]:
    if not request_names or not student_names:
        return []
    return frappe.get_all(
        "Family Consent Decision",
        filters={
            "family_consent_request": ["in", tuple(request_names)],
            "student": ["in", tuple(student_names)],
            "decision_by_doctype": decision_by_doctype,
            "decision_by": decision_by,
        },
        fields=[
            "name",
            "family_consent_request",
            "student",
            "decision_status",
            "decision_at",
            "decision_by_doctype",
            "decision_by",
            "source_channel",
            "response_snapshot",
            "profile_writeback_mode",
        ],
        order_by="decision_at desc, creation desc" if descending else "decision_at asc, creation asc",
        limit=0,
    )


def _load_target_rows(student_names: list[str]) -> list[dict[str, Any]]:
    if not student_names:
        return []
    return frappe.get_all(
        "Family Consent Target",
        filters={
            "student": ["in", tuple(student_names)],
            "parenttype": "Family Consent Request",
            "parentfield": "targets",
        },
        fields=["parent", "student", "organization", "school", "idx"],
        order_by="creation desc, idx asc",
        limit=0,
    )


def _build_board_rows(
    *,
    audience_mode: str,
    decision_by_doctype: str,
    decision_by: str,
    student_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    student_by_name = {_clean_data(row.get("student")): row for row in student_refs if _clean_data(row.get("student"))}
    target_rows = _load_target_rows(list(student_by_name))
    request_names = sorted({_clean_data(row.get("parent")) for row in target_rows if _clean_data(row.get("parent"))})
    request_map = _load_request_rows(request_names=request_names, audience_mode=audience_mode)
    target_rows = [row for row in target_rows if request_map.get(_clean_data(row.get("parent")))]

    relevant_request_names = sorted(
        {_clean_data(row.get("parent")) for row in target_rows if _clean_data(row.get("parent"))}
    )
    decision_rows = _get_relevant_decisions(
        request_names=relevant_request_names,
        student_names=list(student_by_name),
        decision_by_doctype=decision_by_doctype,
        decision_by=decision_by,
        descending=False,
    )
    latest_decisions: dict[tuple[str, str], dict[str, Any]] = {}
    for row in decision_rows:
        key = (_clean_data(row.get("family_consent_request")), _clean_data(row.get("student")))
        if all(key):
            latest_decisions[key] = row

    today = getdate()
    board_rows: list[dict[str, Any]] = []
    for target_row in target_rows:
        request_name = _clean_data(target_row.get("parent"))
        student_name = _clean_data(target_row.get("student"))
        request_row = request_map.get(request_name)
        student_ref = student_by_name.get(student_name, {})
        if not request_row or not _request_is_executable(request_row, audience_mode=audience_mode):
            continue

        latest_decision = latest_decisions.get((request_name, student_name))
        current_status = _derive_current_target_status(
            request_row=request_row,
            latest_decision=latest_decision,
            today=today,
        )
        board_rows.append(
            {
                "family_consent_request": request_name,
                "request_key": _clean_data(request_row.get("request_key")),
                "request_title": _clean_data(request_row.get("request_title")),
                "request_type": _clean_data(request_row.get("request_type")),
                "decision_mode": _clean_data(request_row.get("decision_mode")),
                "student": student_name,
                "student_name": _clean_data(student_ref.get("full_name"))
                or _clean_data(student_ref.get("student_name"))
                or student_name,
                "organization": _clean_data(target_row.get("organization"))
                or _clean_data(request_row.get("organization")),
                "school": _clean_data(target_row.get("school")) or _clean_data(request_row.get("school")),
                "due_on": str(request_row.get("due_on") or ""),
                "effective_from": str(request_row.get("effective_from") or ""),
                "effective_to": str(request_row.get("effective_to") or ""),
                "completion_channel_mode": _clean_data(request_row.get("completion_channel_mode")),
                "current_status": current_status,
                "current_status_label": _decision_status_label(current_status, latest_decision),
                "last_decision_at": str((latest_decision or {}).get("decision_at") or ""),
                "last_decision_by": _clean_data((latest_decision or {}).get("decision_by")),
            }
        )
    return board_rows


def _sort_board_rows(rows: list[dict[str, Any]], *, group: str) -> list[dict[str, Any]]:
    if group == "action_needed":
        return sorted(
            rows,
            key=lambda row: (
                0 if row.get("current_status") == CURRENT_STATUS_OVERDUE else 1,
                row.get("due_on") or "9999-12-31",
                row.get("request_title") or "",
                row.get("student_name") or "",
            ),
        )
    return sorted(
        rows,
        key=lambda row: (
            row.get("last_decision_at") or row.get("effective_to") or row.get("due_on") or "",
            row.get("request_title") or "",
            row.get("student_name") or "",
        ),
        reverse=True,
    )


def _build_board_payload(
    *,
    audience_mode: str,
    decision_by_doctype: str,
    decision_by: str,
    student_refs: list[dict[str, Any]],
    meta_key: str,
    meta_name: str,
) -> dict[str, Any]:
    rows = _build_board_rows(
        audience_mode=audience_mode,
        decision_by_doctype=decision_by_doctype,
        decision_by=decision_by,
        student_refs=student_refs,
    )
    groups = {
        "action_needed": _sort_board_rows(
            [row for row in rows if row.get("current_status") in {CURRENT_STATUS_PENDING, CURRENT_STATUS_OVERDUE}],
            group="action_needed",
        ),
        "completed": _sort_board_rows(
            [row for row in rows if row.get("current_status") == CURRENT_STATUS_COMPLETED],
            group="completed",
        ),
        "declined_or_withdrawn": _sort_board_rows(
            [row for row in rows if row.get("current_status") in {CURRENT_STATUS_DECLINED, CURRENT_STATUS_WITHDRAWN}],
            group="declined_or_withdrawn",
        ),
        "expired": _sort_board_rows(
            [row for row in rows if row.get("current_status") == CURRENT_STATUS_EXPIRED],
            group="expired",
        ),
    }
    counts = {
        "pending": sum(1 for row in rows if row.get("current_status") == CURRENT_STATUS_PENDING),
        "completed": sum(1 for row in rows if row.get("current_status") == CURRENT_STATUS_COMPLETED),
        "declined": sum(1 for row in rows if row.get("current_status") == CURRENT_STATUS_DECLINED),
        "withdrawn": sum(1 for row in rows if row.get("current_status") == CURRENT_STATUS_WITHDRAWN),
        "expired": sum(1 for row in rows if row.get("current_status") == CURRENT_STATUS_EXPIRED),
        "overdue": sum(1 for row in rows if row.get("current_status") == CURRENT_STATUS_OVERDUE),
    }
    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            meta_key: {"name": meta_name},
        },
        "counts": counts,
        "groups": groups,
    }


def _build_guardian_binding_context(student_name: str, guardian_name: str) -> dict[str, Any]:
    student_row = (
        frappe.db.get_value(
            "Student",
            student_name,
            [
                "name",
                "student_full_name",
                "student_preferred_name",
                "student_email",
                "student_mobile_number",
                "anchor_school",
            ],
            as_dict=True,
        )
        or {}
    )
    guardian_row = (
        frappe.db.get_value(
            "Guardian",
            guardian_name,
            ["name", "guardian_full_name", "guardian_email", "guardian_mobile_phone"],
            as_dict=True,
        )
        or {}
    )

    student_contact_name = _clean_data(get_contact_linked_to_student(student_name))
    guardian_contact_name = _clean_data(_get_guardian_contact_name(guardian_name))
    student_address_name, student_address_value = _resolve_single_address(
        link_doctype="Student", link_name=student_name
    )
    guardian_address_name, guardian_address_value = _resolve_single_address(
        link_doctype="Guardian", link_name=guardian_name
    )
    return {
        "student_name": student_name,
        "guardian_name": guardian_name,
        "student_row": student_row,
        "guardian_row": guardian_row,
        "student_contact_name": student_contact_name or None,
        "guardian_contact_name": guardian_contact_name or None,
        "student_contact_values": _get_contact_primary_values(student_contact_name),
        "guardian_contact_values": _get_contact_primary_values(guardian_contact_name),
        "student_primary_address_name": student_address_name,
        "student_primary_address_value": student_address_value,
        "guardian_primary_address_name": guardian_address_name,
        "guardian_primary_address_value": guardian_address_value,
    }


def _build_student_binding_context(student_name: str) -> dict[str, Any]:
    student_row = (
        frappe.db.get_value(
            "Student",
            student_name,
            [
                "name",
                "student_full_name",
                "student_preferred_name",
                "student_email",
                "student_mobile_number",
                "anchor_school",
            ],
            as_dict=True,
        )
        or {}
    )
    student_contact_name = _clean_data(get_contact_linked_to_student(student_name))
    student_address_name, student_address_value = _resolve_single_address(
        link_doctype="Student", link_name=student_name
    )
    return {
        "student_name": student_name,
        "guardian_name": None,
        "student_row": student_row,
        "guardian_row": {},
        "student_contact_name": student_contact_name or None,
        "guardian_contact_name": None,
        "student_contact_values": _get_contact_primary_values(student_contact_name),
        "guardian_contact_values": {"name": None, "primary_email": None, "primary_mobile": None},
        "student_primary_address_name": student_address_name,
        "student_primary_address_value": student_address_value,
        "guardian_primary_address_name": None,
        "guardian_primary_address_value": None,
    }


def _resolve_binding(field_row, *, context: dict[str, Any]) -> dict[str, Any]:
    binding_key = _clean_data(field_row.get("value_source"))
    field_type = _clean_data(field_row.get("field_type"))
    binding_label = binding_key or _("Form field")
    presented_value: Any = None
    supports_writeback = False

    if binding_key == "Student.student_full_name":
        binding_label = _("Student full name")
        presented_value = _clean_data(context["student_row"].get("student_full_name")) or context.get("student_name")
    elif binding_key == "Student.student_email":
        binding_label = _("Student email")
        presented_value = context["student_contact_values"].get("primary_email") or _clean_data(
            context["student_row"].get("student_email")
        )
        supports_writeback = False
    elif binding_key == "Student.student_mobile_number":
        binding_label = _("Student mobile number")
        presented_value = context["student_contact_values"].get("primary_mobile") or _clean_data(
            context["student_row"].get("student_mobile_number")
        )
        supports_writeback = True
    elif binding_key == "Student.anchor_school":
        binding_label = _("Student school")
        presented_value = _clean_data(context["student_row"].get("anchor_school"))
    elif binding_key == "Student.primary_address":
        binding_label = _("Student primary address")
        presented_value = context.get("student_primary_address_value")
        supports_writeback = bool(context.get("student_primary_address_name"))
    elif binding_key == "Guardian.guardian_full_name":
        binding_label = _("Guardian full name")
        presented_value = _clean_data(context["guardian_row"].get("guardian_full_name"))
    elif binding_key == "Guardian.guardian_email":
        binding_label = _("Guardian email")
        presented_value = context["guardian_contact_values"].get("primary_email") or _clean_data(
            context["guardian_row"].get("guardian_email")
        )
        supports_writeback = bool(context.get("guardian_name"))
    elif binding_key == "Guardian.guardian_mobile_phone":
        binding_label = _("Guardian mobile phone")
        presented_value = context["guardian_contact_values"].get("primary_mobile") or _clean_data(
            context["guardian_row"].get("guardian_mobile_phone")
        )
        supports_writeback = bool(context.get("guardian_name"))
    elif binding_key == "Guardian.primary_address":
        binding_label = _("Guardian primary address")
        presented_value = context.get("guardian_primary_address_value")
        supports_writeback = bool(context.get("guardian_primary_address_name"))

    return {
        "binding_key": binding_key,
        "binding_label": binding_label,
        "presented_value": _normalize_field_value(field_type, presented_value),
        "supports_writeback": supports_writeback,
    }


def _apply_profile_writeback(*, binding_key: str, value: Any, context: dict[str, Any]) -> Any:
    if binding_key == "Student.student_mobile_number":
        mobile = _clean_data(value)
        contact_name = _get_or_create_student_contact(context["student_name"], context["student_row"])
        contact_doc = frappe.get_doc("Contact", contact_name)
        if _set_contact_primary_mobile(contact_doc, mobile):
            contact_doc.save(ignore_permissions=True)
        frappe.db.set_value("Student", context["student_name"], "student_mobile_number", mobile, update_modified=False)
        context["student_contact_name"] = contact_name
        context["student_contact_values"] = _get_contact_primary_values(contact_name)
        context["student_row"]["student_mobile_number"] = mobile
        return context["student_contact_values"].get("primary_mobile") or mobile

    if binding_key == "Guardian.guardian_email":
        email = _clean_data(value)
        contact_name = _get_or_create_guardian_contact(context["guardian_name"])
        contact_doc = frappe.get_doc("Contact", contact_name)
        if _set_contact_primary_email(contact_doc, email):
            contact_doc.save(ignore_permissions=True)
        frappe.db.set_value("Guardian", context["guardian_name"], "guardian_email", email, update_modified=False)
        context["guardian_contact_name"] = contact_name
        context["guardian_contact_values"] = _get_contact_primary_values(contact_name)
        context["guardian_row"]["guardian_email"] = email
        return context["guardian_contact_values"].get("primary_email") or email

    if binding_key == "Guardian.guardian_mobile_phone":
        mobile = _clean_data(value)
        contact_name = _get_or_create_guardian_contact(context["guardian_name"])
        contact_doc = frappe.get_doc("Contact", contact_name)
        if _set_contact_primary_mobile(contact_doc, mobile):
            contact_doc.save(ignore_permissions=True)
        frappe.db.set_value(
            "Guardian", context["guardian_name"], "guardian_mobile_phone", mobile, update_modified=False
        )
        context["guardian_contact_name"] = contact_name
        context["guardian_contact_values"] = _get_contact_primary_values(contact_name)
        context["guardian_row"]["guardian_mobile_phone"] = mobile
        return context["guardian_contact_values"].get("primary_mobile") or mobile

    if binding_key in {"Student.primary_address", "Guardian.primary_address"}:
        address_name = _clean_data(
            context.get("student_primary_address_name")
            if binding_key == "Student.primary_address"
            else context.get("guardian_primary_address_name")
        )
        if not address_name:
            frappe.throw(
                _(
                    "Profile write-back is not available for this address because no single canonical linked Address could be resolved."
                ),
                frappe.ValidationError,
            )
        normalized = _normalize_address_value(value)
        if not normalized:
            frappe.throw(_("Address value is required."), frappe.ValidationError)
        address_doc = frappe.get_doc("Address", address_name)
        changed = False
        for key in ADDRESS_VALUE_KEYS:
            desired = _clean_data(normalized.get(key))
            if _clean_data(address_doc.get(key)) != desired:
                address_doc.set(key, desired)
                changed = True
        if changed:
            address_doc.save(ignore_permissions=True)
        current_value = _get_address_value(address_name)
        if binding_key == "Student.primary_address":
            context["student_primary_address_value"] = current_value
        else:
            context["guardian_primary_address_value"] = current_value
        return current_value

    return value


def _load_request_doc_for_portal(
    *,
    request_key: str,
    student: str,
    audience_mode: str,
) -> tuple[Any, dict[str, Any]]:
    request_key = _clean_data(request_key)
    student = _clean_data(student)
    if not request_key:
        frappe.throw(_("Request key is required."))
    if not student:
        frappe.throw(_("Student is required."))

    request_name = frappe.db.get_value("Family Consent Request", {"request_key": request_key}, "name")
    if not request_name:
        frappe.throw(_("This form request could not be found."), frappe.PermissionError)

    request_doc = frappe.get_doc("Family Consent Request", request_name)
    request_row = {
        "name": request_doc.name,
        "request_key": request_doc.request_key,
        "request_title": request_doc.request_title,
        "request_type": request_doc.request_type,
        "request_text": request_doc.request_text,
        "subject_scope": request_doc.subject_scope,
        "audience_mode": request_doc.audience_mode,
        "signer_rule": request_doc.signer_rule,
        "decision_mode": request_doc.decision_mode,
        "completion_channel_mode": request_doc.completion_channel_mode,
        "requires_typed_signature": request_doc.requires_typed_signature,
        "requires_attestation": request_doc.requires_attestation,
        "effective_from": request_doc.effective_from,
        "effective_to": request_doc.effective_to,
        "due_on": request_doc.due_on,
        "source_file": request_doc.source_file,
        "status": request_doc.status,
    }
    if not _request_is_executable(request_row, audience_mode=audience_mode):
        frappe.throw(_("This form request is not executable in the current portal workflow."), frappe.ValidationError)

    target_rows = frappe.get_all(
        "Family Consent Target",
        filters={
            "parent": request_doc.name,
            "parenttype": "Family Consent Request",
            "parentfield": "targets",
            "student": student,
        },
        fields=["student", "organization", "school"],
        limit=1,
    )
    if not target_rows:
        frappe.throw(_("You do not have permission to access this form request."), frappe.PermissionError)

    return request_doc, target_rows[0]


def _serialize_detail_fields(request_doc, *, context: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for field_row in request_doc.get("fields") or []:
        resolved = _resolve_binding(field_row, context=context)
        effective_allow_writeback = bool(
            cint(field_row.allow_profile_writeback)
            and _clean_data(field_row.field_mode) == FIELD_MODE_ALLOW_OVERRIDE
            and resolved.get("supports_writeback")
        )
        fields.append(
            {
                "field_key": _clean_data(field_row.field_key),
                "field_label": _clean_text(field_row.field_label) or _clean_data(field_row.field_key),
                "field_type": _clean_data(field_row.field_type),
                "field_mode": _clean_data(field_row.field_mode),
                "required": int(bool(cint(field_row.required))),
                "presented_value": resolved.get("presented_value"),
                "allow_profile_writeback": effective_allow_writeback,
                "binding_label": resolved.get("binding_label"),
            }
        )
    return fields


def _get_detail_history(
    *,
    request_name: str,
    student: str,
    decision_by_doctype: str,
    decision_by: str,
) -> list[dict[str, Any]]:
    rows = frappe.get_all(
        "Family Consent Decision",
        filters={
            "family_consent_request": request_name,
            "student": student,
            "decision_by_doctype": decision_by_doctype,
            "decision_by": decision_by,
        },
        fields=["decision_status", "decision_at", "decision_by_doctype", "decision_by", "source_channel"],
        order_by="decision_at desc, creation desc",
        limit=0,
    )
    return [
        {
            "decision_status": _clean_data(row.get("decision_status")),
            "decision_at": str(row.get("decision_at") or ""),
            "decision_by_doctype": _clean_data(row.get("decision_by_doctype")),
            "decision_by": _clean_data(row.get("decision_by")),
            "source_channel": _clean_data(row.get("source_channel")),
        }
        for row in rows
    ]


def _submit_portal_consent_decision(
    *,
    request_key: str,
    student: str,
    decision_status: str,
    typed_signature_name: str | None,
    attestation_confirmed: Any,
    field_values: Any,
    profile_writeback_mode: str | None,
    audience_mode: str,
    decision_by_doctype: str,
    decision_by: str,
    expected_signature_name: str,
    source_channel: str,
    context_builder,
) -> dict[str, Any]:
    request_doc, target_row = _load_request_doc_for_portal(
        request_key=request_key, student=student, audience_mode=audience_mode
    )
    if _clean_data(request_doc.status) != REQUEST_STATUS_PUBLISHED:
        existing_rows = _get_relevant_decisions(
            request_names=[request_doc.name],
            student_names=[student],
            decision_by_doctype=decision_by_doctype,
            decision_by=decision_by,
            descending=True,
        )
        if existing_rows:
            latest_existing = existing_rows[0]
            if _clean_data(latest_existing.get("decision_status")) == _clean_data(decision_status):
                return {
                    "ok": True,
                    "status": "already_current",
                    "decision_name": latest_existing.get("name"),
                    "request_key": request_doc.request_key,
                    "student": student,
                    "current_status": _derive_current_target_status(
                        request_row={
                            "effective_to": request_doc.effective_to,
                            "due_on": request_doc.due_on,
                        },
                        latest_decision=latest_existing,
                        today=getdate(),
                    ),
                    "profile_writeback_mode": _clean_data(latest_existing.get("profile_writeback_mode")) or None,
                }
        frappe.throw(_("This form request is no longer open for portal submission."), frappe.ValidationError)

    if _clean_data(request_doc.completion_channel_mode) == COMPLETION_CHANNEL_PAPER_ONLY:
        frappe.throw(_("This request accepts paper completion only."), frappe.ValidationError)

    allowed_statuses = DECISION_STATUSES_BY_MODE.get(_clean_data(request_doc.decision_mode), set())
    if _clean_data(decision_status) not in allowed_statuses:
        frappe.throw(_("Decision status does not match the request decision mode."), frappe.ValidationError)

    typed_signature_name = _clean_text(typed_signature_name)
    if cint(request_doc.requires_typed_signature):
        if not typed_signature_name:
            frappe.throw(_("Type your full name as your electronic signature."), frappe.ValidationError)
        normalized_typed = _normalize_signature_name(typed_signature_name)
        expected_candidates = {
            normalized
            for normalized in {
                _normalize_signature_name(expected_signature_name),
                _normalize_signature_name(decision_by),
            }
            if normalized
        }
        if expected_candidates and normalized_typed not in expected_candidates:
            frappe.throw(
                _("Typed signature must match exactly: {expected_name}").format(expected_name=expected_signature_name),
                frappe.ValidationError,
            )

    if cint(request_doc.requires_attestation) and not _as_bool(attestation_confirmed):
        frappe.throw(
            _("You must confirm the electronic signature attestation before signing."),
            frappe.ValidationError,
        )

    submitted_rows = _parse_rows(field_values)
    submitted_by_key: dict[str, Any] = {}
    for row in submitted_rows:
        field_key = _clean_data(row.get("field_key"))
        if not field_key:
            frappe.throw(_("Each field value must include field_key."))
        if field_key in submitted_by_key:
            frappe.throw(_("Field value rows must not repeat the same field_key."), frappe.ValidationError)
        submitted_by_key[field_key] = row.get("value")

    request_field_keys = {_clean_data(row.field_key) for row in request_doc.get("fields") or []}
    unknown_keys = sorted(field_key for field_key in submitted_by_key if field_key not in request_field_keys)
    if unknown_keys:
        frappe.throw(
            _("This submit payload includes unknown field keys: {field_keys}").format(
                field_keys=", ".join(unknown_keys)
            ),
            frappe.ValidationError,
        )

    context = context_builder(student)
    processed_field_values: list[dict[str, Any]] = []
    changed_profile_fields: list[str] = []
    before_values: dict[str, Any] = {}
    after_values: dict[str, Any] = {}

    for field_row in request_doc.get("fields") or []:
        field_key = _clean_data(field_row.field_key)
        field_type = _clean_data(field_row.field_type)
        field_mode = _clean_data(field_row.field_mode)
        resolved = _resolve_binding(field_row, context=context)
        presented_value = resolved.get("presented_value")
        effective_allow_writeback = bool(
            cint(field_row.allow_profile_writeback)
            and field_mode == FIELD_MODE_ALLOW_OVERRIDE
            and resolved.get("supports_writeback")
        )

        if field_mode == FIELD_MODE_ALLOW_OVERRIDE:
            submitted_value = _normalize_field_value(field_type, submitted_by_key.get(field_key))
            if not _has_value(field_type, submitted_value):
                submitted_value = presented_value
        else:
            submitted_value = presented_value

        if (
            cint(field_row.required)
            and field_mode != FIELD_MODE_DISPLAY_ONLY
            and not _has_value(field_type, submitted_value)
        ):
            frappe.throw(
                _("Field {field_label} is required.").format(
                    field_label=_clean_text(field_row.field_label) or field_key
                ),
                frappe.ValidationError,
            )

        changed = not _values_equal(presented_value, submitted_value)
        processed_field_values.append(
            {
                "field_key": field_key,
                "field_label": _clean_text(field_row.field_label) or field_key,
                "field_type": field_type,
                "field_mode": field_mode,
                "value_source": _clean_data(field_row.value_source),
                "presented_value": presented_value,
                "submitted_value": submitted_value,
                "changed": changed,
                "allow_profile_writeback": effective_allow_writeback,
            }
        )
        if changed and effective_allow_writeback:
            changed_profile_fields.append(field_key)
            before_values[field_key] = presented_value

    normalized_writeback_mode = _clean_data(profile_writeback_mode)
    if changed_profile_fields:
        if normalized_writeback_mode not in {"Form Only", "Update Profile"}:
            frappe.throw(
                _(
                    "Choose whether the changed profile fields apply only to this form or update your profile everywhere."
                ),
                frappe.ValidationError,
            )
    else:
        normalized_writeback_mode = ""

    if normalized_writeback_mode == "Update Profile":
        for processed in processed_field_values:
            if not processed.get("changed") or not processed.get("allow_profile_writeback"):
                continue
            after_values[processed["field_key"]] = _apply_profile_writeback(
                binding_key=processed.get("value_source") or "",
                value=processed.get("submitted_value"),
                context=context,
            )
    else:
        for field_key in changed_profile_fields:
            after_values[field_key] = before_values.get(field_key)

    response_snapshot = {
        "request": {
            "request_key": request_doc.request_key,
            "request_title": request_doc.request_title,
            "request_type": request_doc.request_type,
            "decision_mode": request_doc.decision_mode,
            "effective_from": str(request_doc.effective_from or ""),
            "effective_to": str(request_doc.effective_to or ""),
            "due_on": str(request_doc.due_on or ""),
        },
        "signer": {
            "decision_by_doctype": decision_by_doctype,
            "decision_by": decision_by,
            "typed_signature_name": typed_signature_name or "",
            "attestation_confirmed": int(_as_bool(attestation_confirmed)),
        },
        "field_values": processed_field_values,
        "writeback": {
            "profile_writeback_mode": normalized_writeback_mode,
            "changed_profile_fields": changed_profile_fields,
            "before_values": before_values,
            "after_values": after_values,
        },
    }

    latest_rows = _get_relevant_decisions(
        request_names=[request_doc.name],
        student_names=[student],
        decision_by_doctype=decision_by_doctype,
        decision_by=decision_by,
        descending=True,
    )
    latest_decision = latest_rows[0] if latest_rows else None
    if latest_decision and _clean_data(latest_decision.get("decision_status")) == _clean_data(decision_status):
        existing_snapshot = frappe.parse_json(latest_decision.get("response_snapshot") or "{}") or {}
        if (
            _values_equal(existing_snapshot, response_snapshot)
            and _clean_data(latest_decision.get("profile_writeback_mode")) == normalized_writeback_mode
        ):
            return {
                "ok": True,
                "status": "already_current",
                "decision_name": latest_decision.get("name"),
                "request_key": request_doc.request_key,
                "student": student,
                "current_status": _derive_current_target_status(
                    request_row={
                        "effective_to": request_doc.effective_to,
                        "due_on": request_doc.due_on,
                    },
                    latest_decision=latest_decision,
                    today=getdate(),
                ),
                "profile_writeback_mode": normalized_writeback_mode or None,
            }

    decision_doc = frappe.get_doc(
        {
            "doctype": "Family Consent Decision",
            "family_consent_request": request_doc.name,
            "student": _clean_data(target_row.get("student")),
            "decision_by_doctype": decision_by_doctype,
            "decision_by": decision_by,
            "decision_status": _clean_data(decision_status),
            "typed_signature_name": typed_signature_name or "",
            "attestation_confirmed": int(_as_bool(attestation_confirmed)),
            "source_channel": source_channel,
            "response_snapshot": json.dumps(response_snapshot, sort_keys=True, separators=(",", ":"), default=str),
            "profile_writeback_mode": normalized_writeback_mode or "",
            "supersedes_decision": _clean_data((latest_decision or {}).get("name")),
        }
    )
    decision_doc.insert(ignore_permissions=True)
    current_status = _derive_current_target_status(
        request_row={"effective_to": request_doc.effective_to, "due_on": request_doc.due_on},
        latest_decision={"decision_status": decision_doc.decision_status},
        today=getdate(),
    )
    return {
        "ok": True,
        "status": "submitted",
        "decision_name": decision_doc.name,
        "request_key": request_doc.request_key,
        "student": student,
        "current_status": current_status,
        "profile_writeback_mode": normalized_writeback_mode or None,
    }


def get_guardian_consent_home_summary(*, guardian_name: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    guardian_name = _clean_data(guardian_name)
    if not guardian_name:
        return {"pending_count": 0, "overdue_count": 0, "items": []}
    authorized_children = _children_with_signer_authority(guardian_name=guardian_name, children=children or [])
    board = _build_board_payload(
        audience_mode=AUDIENCE_GUARDIAN,
        decision_by_doctype="Guardian",
        decision_by=guardian_name,
        student_refs=authorized_children,
        meta_key="guardian",
        meta_name=guardian_name,
    )
    action_rows = board["groups"]["action_needed"]
    return {
        "pending_count": len(action_rows),
        "overdue_count": board["counts"]["overdue"],
        "items": [
            {
                "request_key": row.get("request_key") or "",
                "request_title": row.get("request_title") or "",
                "student": row.get("student") or "",
                "student_name": row.get("student_name") or "",
                "due_on": row.get("due_on") or "",
                "status_label": row.get("current_status_label") or "",
                "href": {
                    "name": "guardian-consent-detail",
                    "params": {
                        "request_key": row.get("request_key") or "",
                        "student_id": row.get("student") or "",
                    },
                },
            }
            for row in action_rows[:3]
        ],
    }


def get_student_consent_home_summary(student_name: str) -> dict[str, Any]:
    student_name = _clean_data(student_name)
    if not student_name:
        return {"pending_count": 0, "overdue_count": 0, "items": []}
    student_row = (
        frappe.db.get_value(
            "Student",
            student_name,
            ["name", "student_full_name", "anchor_school"],
            as_dict=True,
        )
        or {}
    )
    board = _build_board_payload(
        audience_mode=AUDIENCE_STUDENT,
        decision_by_doctype="Student",
        decision_by=student_name,
        student_refs=[
            {
                "student": student_name,
                "full_name": _clean_data(student_row.get("student_full_name")) or student_name,
                "school": _clean_data(student_row.get("anchor_school")),
            }
        ],
        meta_key="student",
        meta_name=student_name,
    )
    action_rows = board["groups"]["action_needed"]
    return {
        "pending_count": len(action_rows),
        "overdue_count": board["counts"]["overdue"],
        "items": [
            {
                "request_key": row.get("request_key") or "",
                "request_title": row.get("request_title") or "",
                "student": student_name,
                "student_name": row.get("student_name") or student_name,
                "due_on": row.get("due_on") or "",
                "status_label": row.get("current_status_label") or "",
                "href": {
                    "name": "student-consent-detail",
                    "params": {
                        "request_key": row.get("request_key") or "",
                        "student_id": student_name,
                    },
                },
            }
            for row in action_rows[:3]
        ],
    }


@frappe.whitelist()
def get_guardian_consent_board() -> dict[str, Any]:
    guardian_name, children = _ensure_guardian_portal_scope()
    payload = _build_board_payload(
        audience_mode=AUDIENCE_GUARDIAN,
        decision_by_doctype="Guardian",
        decision_by=guardian_name,
        student_refs=children,
        meta_key="guardian",
        meta_name=guardian_name,
    )
    payload["family"] = {"children": children}
    return payload


@frappe.whitelist()
def get_guardian_consent_detail(request_key: str, student: str) -> dict[str, Any]:
    guardian_name, children = _ensure_guardian_portal_scope()
    allowed_students = {_clean_data(child.get("student")) for child in children if _clean_data(child.get("student"))}
    student = _clean_data(student)
    if student not in allowed_students:
        frappe.throw(_("You do not have permission to access this form request."), frappe.PermissionError)

    request_doc, target_row = _load_request_doc_for_portal(
        request_key=request_key,
        student=student,
        audience_mode=AUDIENCE_GUARDIAN,
    )
    context = _build_guardian_binding_context(student, guardian_name)
    relevant_history = _get_relevant_decisions(
        request_names=[request_doc.name],
        student_names=[student],
        decision_by_doctype="Guardian",
        decision_by=guardian_name,
        descending=True,
    )
    latest_decision = relevant_history[0] if relevant_history else None
    current_status = _derive_current_target_status(
        request_row={"effective_to": request_doc.effective_to, "due_on": request_doc.due_on},
        latest_decision=latest_decision,
        today=getdate(),
    )
    student_name = next(
        (_clean_data(child.get("full_name")) for child in children if _clean_data(child.get("student")) == student),
        student,
    )
    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
        },
        "request": {
            "family_consent_request": request_doc.name,
            "request_key": request_doc.request_key,
            "request_title": request_doc.request_title,
            "request_type": request_doc.request_type,
            "status": request_doc.status,
            "decision_mode": request_doc.decision_mode,
            "completion_channel_mode": request_doc.completion_channel_mode,
            "request_text": sanitize_html(request_doc.request_text or "", allow_headings_from="h2"),
            "source_file": _clean_data(request_doc.source_file),
            "effective_from": str(request_doc.effective_from or ""),
            "effective_to": str(request_doc.effective_to or ""),
            "due_on": str(request_doc.due_on or ""),
            "requires_typed_signature": int(bool(cint(request_doc.requires_typed_signature))),
            "requires_attestation": int(bool(cint(request_doc.requires_attestation))),
        },
        "target": {
            "student": student,
            "student_name": student_name,
            "organization": _clean_data(target_row.get("organization")),
            "school": _clean_data(target_row.get("school")),
            "current_status": current_status,
            "current_status_label": _decision_status_label(current_status, latest_decision),
        },
        "signer": {
            "doctype": "Guardian",
            "name": guardian_name,
            "expected_signature_name": _expected_guardian_signature_name(guardian_name),
        },
        "fields": _serialize_detail_fields(request_doc, context=context),
        "history": _get_detail_history(
            request_name=request_doc.name,
            student=student,
            decision_by_doctype="Guardian",
            decision_by=guardian_name,
        ),
    }


@frappe.whitelist()
def submit_guardian_consent_decision(
    request_key: str,
    student: str,
    decision_status: str,
    typed_signature_name: str | None = None,
    attestation_confirmed: Any = None,
    field_values: Any = None,
    profile_writeback_mode: str | None = None,
) -> dict[str, Any]:
    guardian_name, children = _ensure_guardian_portal_scope()
    allowed_students = {_clean_data(child.get("student")) for child in children if _clean_data(child.get("student"))}
    student = _clean_data(student)
    if student not in allowed_students:
        frappe.throw(_("You do not have permission to submit this form request."), frappe.PermissionError)

    return _submit_portal_consent_decision(
        request_key=request_key,
        student=student,
        decision_status=decision_status,
        typed_signature_name=typed_signature_name,
        attestation_confirmed=attestation_confirmed,
        field_values=field_values,
        profile_writeback_mode=profile_writeback_mode,
        audience_mode=AUDIENCE_GUARDIAN,
        decision_by_doctype="Guardian",
        decision_by=guardian_name,
        expected_signature_name=_expected_guardian_signature_name(guardian_name),
        source_channel=SOURCE_CHANNEL_GUARDIAN_PORTAL,
        context_builder=lambda student_name: _build_guardian_binding_context(student_name, guardian_name),
    )


@frappe.whitelist()
def get_student_consent_board() -> dict[str, Any]:
    student_name = _require_student_name_for_session_user()
    student_row = (
        frappe.db.get_value(
            "Student",
            student_name,
            ["name", "student_full_name", "anchor_school"],
            as_dict=True,
        )
        or {}
    )
    payload = _build_board_payload(
        audience_mode=AUDIENCE_STUDENT,
        decision_by_doctype="Student",
        decision_by=student_name,
        student_refs=[
            {
                "student": student_name,
                "full_name": _clean_data(student_row.get("student_full_name")) or student_name,
                "school": _clean_data(student_row.get("anchor_school")),
            }
        ],
        meta_key="student",
        meta_name=student_name,
    )
    payload["identity"] = {"student": student_name}
    return payload


@frappe.whitelist()
def get_student_consent_detail(request_key: str, student: str) -> dict[str, Any]:
    student_name = _require_student_name_for_session_user()
    student = _clean_data(student)
    if student and student != student_name:
        frappe.throw(_("You do not have permission to access this form request."), frappe.PermissionError)

    request_doc, target_row = _load_request_doc_for_portal(
        request_key=request_key,
        student=student_name,
        audience_mode=AUDIENCE_STUDENT,
    )
    context = _build_student_binding_context(student_name)
    relevant_history = _get_relevant_decisions(
        request_names=[request_doc.name],
        student_names=[student_name],
        decision_by_doctype="Student",
        decision_by=student_name,
        descending=True,
    )
    latest_decision = relevant_history[0] if relevant_history else None
    current_status = _derive_current_target_status(
        request_row={"effective_to": request_doc.effective_to, "due_on": request_doc.due_on},
        latest_decision=latest_decision,
        today=getdate(),
    )
    student_label = _clean_data(context["student_row"].get("student_full_name")) or student_name
    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
        },
        "request": {
            "family_consent_request": request_doc.name,
            "request_key": request_doc.request_key,
            "request_title": request_doc.request_title,
            "request_type": request_doc.request_type,
            "status": request_doc.status,
            "decision_mode": request_doc.decision_mode,
            "completion_channel_mode": request_doc.completion_channel_mode,
            "request_text": sanitize_html(request_doc.request_text or "", allow_headings_from="h2"),
            "source_file": _clean_data(request_doc.source_file),
            "effective_from": str(request_doc.effective_from or ""),
            "effective_to": str(request_doc.effective_to or ""),
            "due_on": str(request_doc.due_on or ""),
            "requires_typed_signature": int(bool(cint(request_doc.requires_typed_signature))),
            "requires_attestation": int(bool(cint(request_doc.requires_attestation))),
        },
        "target": {
            "student": student_name,
            "student_name": student_label,
            "organization": _clean_data(target_row.get("organization")),
            "school": _clean_data(target_row.get("school")),
            "current_status": current_status,
            "current_status_label": _decision_status_label(current_status, latest_decision),
        },
        "signer": {
            "doctype": "Student",
            "name": student_name,
            "expected_signature_name": _expected_student_signature_name(student_name),
        },
        "fields": _serialize_detail_fields(request_doc, context=context),
        "history": _get_detail_history(
            request_name=request_doc.name,
            student=student_name,
            decision_by_doctype="Student",
            decision_by=student_name,
        ),
    }


@frappe.whitelist()
def submit_student_consent_decision(
    request_key: str,
    student: str,
    decision_status: str,
    typed_signature_name: str | None = None,
    attestation_confirmed: Any = None,
    field_values: Any = None,
    profile_writeback_mode: str | None = None,
) -> dict[str, Any]:
    student_name = _require_student_name_for_session_user()
    student = _clean_data(student)
    if student and student != student_name:
        frappe.throw(_("You do not have permission to submit this form request."), frappe.PermissionError)

    return _submit_portal_consent_decision(
        request_key=request_key,
        student=student_name,
        decision_status=decision_status,
        typed_signature_name=typed_signature_name,
        attestation_confirmed=attestation_confirmed,
        field_values=field_values,
        profile_writeback_mode=profile_writeback_mode,
        audience_mode=AUDIENCE_STUDENT,
        decision_by_doctype="Student",
        decision_by=student_name,
        expected_signature_name=_expected_student_signature_name(student_name),
        source_channel=SOURCE_CHANNEL_STUDENT_PORTAL,
        context_builder=_build_student_binding_context,
    )
