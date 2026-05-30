from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.contacts.contact_privacy import (
    get_masked_contact_points_for_owner,
    get_raw_contact_point_value,
    mask_email,
    mask_phone,
    sync_guardian_contact_points,
)

BILLING_CONTACT_PURPOSE = "billing"
BILLING_CONTACT_SYNC_WORKFLOW = "account_holder_billing_contact_sync"
BILLING_CONTACT_RAW_WORKFLOW = "account_holder_billing_follow_up"
BILLING_CONTACT_RAW_ROLES = {"Accounts Manager", "Accounts User", "System Manager", "Administrator"}


def _clean_data(value: Any) -> str:
    return str(value or "").strip()


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_name_list(value: Any) -> list[str]:
    parsed = frappe.parse_json(value) if isinstance(value, str) else value
    if not parsed:
        return []
    if not isinstance(parsed, list):
        frappe.throw(_("Expected a list payload."))

    names: list[str] = []
    seen: set[str] = set()
    for item in parsed:
        name = _clean_data(item)
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _doc_value(doc: Any, fieldname: str) -> Any:
    if isinstance(doc, dict):
        return doc.get(fieldname)
    if hasattr(doc, "get"):
        return doc.get(fieldname)
    return getattr(doc, fieldname, None)


def _require_student_access(student_name: str, *, ptype: str = "write"):
    student_name = _clean_data(student_name)
    if not student_name or not frappe.db.exists("Student", student_name):
        frappe.throw(_("Invalid Student: {student}.").format(student=student_name or _("missing")))

    student = frappe.get_doc("Student", student_name)
    if not frappe.has_permission("Student", doc=student, ptype=ptype):
        frappe.throw(
            _("You do not have permission to {permission_type} this Student.").format(permission_type=ptype),
            frappe.PermissionError,
        )
    return student


def _user_can_read_organization(organization: str) -> bool:
    organization = _clean_data(organization)
    if not organization:
        return False

    user = _clean_data(getattr(frappe.session, "user", ""))
    roles = set(frappe.get_roles(user) or [])
    if user == "Administrator" or "System Manager" in roles:
        return True

    try:
        organization_doc = frappe.get_doc("Organization", organization)
    except Exception:
        return False
    return bool(frappe.has_permission("Organization", doc=organization_doc, ptype="read"))


def _require_account_holder_access(account_holder: str, *, ptype: str = "read"):
    account_holder = _clean_data(account_holder)
    if not account_holder or not frappe.db.exists("Account Holder", account_holder):
        frappe.throw(
            _("Invalid Account Holder: {account_holder}.").format(account_holder=account_holder or _("missing"))
        )

    doc = frappe.get_doc("Account Holder", account_holder)
    if not frappe.has_permission("Account Holder", doc=doc, ptype=ptype):
        frappe.throw(
            _("You do not have permission to {permission_type} this Account Holder.").format(permission_type=ptype),
            frappe.PermissionError,
        )
    if not _user_can_read_organization(doc.organization):
        frappe.throw(
            _("You do not have permission to access this Account Holder organization."), frappe.PermissionError
        )
    return doc


def _require_account_holder_doctype_permission(*, ptype: str) -> None:
    if frappe.has_permission("Account Holder", ptype=ptype):
        return
    frappe.throw(
        _("You do not have permission to {permission_type} Account Holders.").format(permission_type=ptype),
        frappe.PermissionError,
    )


def _ensure_raw_billing_contact_actor() -> None:
    user = _clean_data(getattr(frappe.session, "user", ""))
    roles = set(frappe.get_roles(user) or [])
    if user == "Administrator" or roles & BILLING_CONTACT_RAW_ROLES:
        return
    frappe.throw(_("Only finance users can reveal billing contact values."), frappe.PermissionError)


def _student_organization(student) -> str:
    school = _clean_data(_doc_value(student, "anchor_school"))
    if not school:
        frappe.throw(
            _("Student must have an Anchor School before an Account Holder can be created. Set Anchor School first.")
        )
    return get_school_organization(school)


def _guardian_display_name(row: dict[str, Any]) -> str:
    full_name = _clean_data(row.get("guardian_full_name"))
    if full_name:
        return full_name
    parts = [_clean_data(row.get("guardian_first_name")), _clean_data(row.get("guardian_last_name"))]
    return " ".join(part for part in parts if part).strip() or _clean_data(row.get("name"))


def _guardian_candidates_for_student(student) -> list[dict[str, Any]]:
    child_rows = []
    guardian_names: list[str] = []
    seen: set[str] = set()
    for row in student.get("guardians") or []:
        guardian = _clean_data(row.get("guardian"))
        if not guardian or guardian in seen:
            continue
        seen.add(guardian)
        guardian_names.append(guardian)
        child_rows.append(
            {
                "guardian": guardian,
                "relation": _clean_data(row.get("relation")),
                "can_consent": _as_int(row.get("can_consent")),
                "idx": _as_int(row.get("idx")),
            }
        )

    if not guardian_names:
        return []

    guardian_rows = frappe.get_all(
        "Guardian",
        filters={"name": ["in", guardian_names]},
        fields=[
            "name",
            "guardian_full_name",
            "guardian_first_name",
            "guardian_last_name",
            "guardian_email",
            "guardian_mobile_phone",
            "organization",
            "is_primary_guardian",
            "is_financial_guardian",
        ],
        limit=0,
    )
    guardians_by_name = {_clean_data(row.get("name")): row for row in guardian_rows if _clean_data(row.get("name"))}

    candidates = []
    for child in child_rows:
        guardian_row = guardians_by_name.get(child["guardian"])
        if not guardian_row:
            continue
        candidate = {
            **child,
            "guardian_name": _guardian_display_name(guardian_row),
            "guardian_email": _clean_data(guardian_row.get("guardian_email")),
            "guardian_mobile_phone": _clean_data(guardian_row.get("guardian_mobile_phone")),
            "guardian_organization": _clean_data(guardian_row.get("organization")),
            "is_primary_guardian": _as_int(guardian_row.get("is_primary_guardian")),
            "is_financial_guardian": _as_int(guardian_row.get("is_financial_guardian")),
        }
        candidates.append(candidate)

    candidates.sort(key=_candidate_priority)
    for index, candidate in enumerate(candidates):
        candidate["recommended"] = 1 if index == 0 else 0
    return candidates


def _candidate_priority(candidate: dict[str, Any]) -> tuple[int, int, int, int, str]:
    return (
        0 if _as_int(candidate.get("is_financial_guardian")) else 1,
        0 if _as_int(candidate.get("is_primary_guardian")) else 1,
        0 if _as_int(candidate.get("can_consent")) else 1,
        _as_int(candidate.get("idx")) or 9999,
        _clean_data(candidate.get("guardian_name")),
    )


def _public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    email = _clean_data(candidate.get("guardian_email"))
    phone = _clean_data(candidate.get("guardian_mobile_phone"))
    return {
        "guardian": _clean_data(candidate.get("guardian")),
        "guardian_name": _clean_data(candidate.get("guardian_name")),
        "relation": _clean_data(candidate.get("relation")),
        "can_consent": _as_int(candidate.get("can_consent")),
        "is_primary_guardian": _as_int(candidate.get("is_primary_guardian")),
        "is_financial_guardian": _as_int(candidate.get("is_financial_guardian")),
        "recommended": _as_int(candidate.get("recommended")),
        "email_masked": mask_email(email),
        "phone_masked": mask_phone(phone),
        "has_email": bool(email),
        "has_phone": bool(phone),
    }


def _validate_account_holder_scope(account_holder: str, organization: str) -> dict[str, Any]:
    row = frappe.db.get_value(
        "Account Holder",
        account_holder,
        ["name", "organization", "status"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Account Holder {account_holder} was not found.").format(account_holder=account_holder))
    if row.get("organization") != organization:
        frappe.throw(_("Account Holder must belong to the same Organization as the Student."))
    if _clean_data(row.get("status")) == "Inactive":
        frappe.throw(_("Account Holder is inactive."))
    return dict(row)


def _selected_candidates(candidates: list[dict[str, Any]], selected_guardians: list[str]) -> list[dict[str, Any]]:
    if not candidates:
        frappe.throw(
            _("Student has no linked Guardians to use for Account Holder billing contacts. Add a Guardian first.")
        )

    candidate_by_guardian = {_clean_data(candidate.get("guardian")): candidate for candidate in candidates}
    selected = selected_guardians or [_clean_data(candidates[0].get("guardian"))]
    missing = [guardian for guardian in selected if guardian not in candidate_by_guardian]
    if missing:
        frappe.throw(_("Selected Guardian rows are stale. Refresh the Student form and try again."))

    picked = [candidate_by_guardian[guardian] for guardian in selected]
    picked.sort(key=_candidate_priority)
    return picked


def _compose_account_holder_name(student, selected: list[dict[str, Any]]) -> str:
    if len(selected) == 1:
        return _clean_data(selected[0].get("guardian_name")) or _clean_data(selected[0].get("guardian"))
    if len(selected) == 2:
        return _("{first_guardian} and {second_guardian}").format(
            first_guardian=_clean_data(selected[0].get("guardian_name")),
            second_guardian=_clean_data(selected[1].get("guardian_name")),
        )
    return _("{student_name} Family").format(student_name=_clean_data(student.student_full_name) or student.name)


def _create_account_holder(student, organization: str, selected: list[dict[str, Any]]):
    primary = selected[0]
    doc = frappe.get_doc(
        {
            "doctype": "Account Holder",
            "organization": organization,
            "account_holder_name": _compose_account_holder_name(student, selected),
            "account_holder_type": "Joint" if len(selected) > 1 else "Individual",
            "status": "Active",
            "primary_email": _clean_data(primary.get("guardian_email")),
            "primary_phone": _clean_data(primary.get("guardian_mobile_phone")),
            "notes": _("Created from Student {student}.").format(student=student.name),
        }
    )
    doc.insert(ignore_permissions=True)
    return doc


def _link_student_to_account_holder(student, account_holder: str) -> None:
    account_holder = _clean_data(account_holder)
    if _clean_data(student.account_holder) == account_holder:
        return
    if _clean_data(student.account_holder) and _clean_data(student.account_holder) != account_holder:
        frappe.throw(_("Student already has a different Account Holder."))

    student.account_holder = account_holder
    student.save(ignore_permissions=True)


def _ensure_account_holder_billing_contacts(account_holder_doc, student, selected: list[dict[str, Any]]) -> int:
    rows = list(account_holder_doc.get("billing_contacts") or [])
    existing_by_guardian = {_clean_data(row.get("guardian")): row for row in rows if _clean_data(row.get("guardian"))}
    has_primary = any(_as_int(row.get("is_primary")) for row in rows)
    added = 0
    changed = False

    for index, candidate in enumerate(selected):
        guardian = _clean_data(candidate.get("guardian"))
        row = existing_by_guardian.get(guardian)
        if row:
            if not _clean_data(row.get("source_student")):
                row.source_student = student.name
                changed = True
            if _clean_data(row.get("relation")) != _clean_data(candidate.get("relation")):
                row.relation = _clean_data(candidate.get("relation"))
                changed = True
            if _clean_data(row.get("guardian_name")) != _clean_data(candidate.get("guardian_name")):
                changed = True
            row.guardian_name = _clean_data(candidate.get("guardian_name"))
        else:
            row = account_holder_doc.append(
                "billing_contacts",
                {
                    "guardian": guardian,
                    "guardian_name": _clean_data(candidate.get("guardian_name")),
                    "relation": _clean_data(candidate.get("relation")),
                    "source_student": student.name,
                    "receives_billing_follow_up": 1,
                },
            )
            added += 1
            changed = True

        if not has_primary and index == 0:
            row.is_primary = 1
            has_primary = True
            changed = True

    if changed:
        account_holder_doc.save(ignore_permissions=True)
    return added


def normalize_account_holder_billing_contacts(account_holder_doc) -> None:
    rows = list(account_holder_doc.get("billing_contacts") or [])
    if not rows:
        return

    guardian_names = [_clean_data(row.get("guardian")) for row in rows if _clean_data(row.get("guardian"))]
    if not guardian_names:
        return

    duplicate_guardians = sorted(guardian for guardian in set(guardian_names) if guardian_names.count(guardian) > 1)
    if duplicate_guardians:
        frappe.throw(_("Each Guardian can only appear once in Account Holder billing contacts."))

    guardian_rows = frappe.get_all(
        "Guardian",
        filters={"name": ["in", guardian_names]},
        fields=[
            "name",
            "guardian_full_name",
            "guardian_first_name",
            "guardian_last_name",
            "guardian_email",
            "guardian_mobile_phone",
            "organization",
        ],
        limit=0,
    )
    guardians_by_name = {_clean_data(row.get("name")): row for row in guardian_rows if _clean_data(row.get("name"))}

    primary_rows = [row for row in rows if _as_int(row.get("is_primary"))]
    if len(primary_rows) > 1:
        frappe.throw(_("Only one Account Holder billing contact can be primary."))
    if not primary_rows:
        rows[0].is_primary = 1
        primary_rows = [rows[0]]

    for row in rows:
        guardian = _clean_data(row.get("guardian"))
        guardian_row = guardians_by_name.get(guardian)
        if not guardian_row:
            frappe.throw(_("Guardian {guardian} was not found.").format(guardian=guardian))
        guardian_organization = _clean_data(guardian_row.get("organization"))
        if guardian_organization and guardian_organization != account_holder_doc.organization:
            frappe.throw(_("Billing contact Guardian must belong to the Account Holder organization."))
        row.guardian_name = _guardian_display_name(guardian_row)
        if row.get("receives_billing_follow_up") in (None, ""):
            row.receives_billing_follow_up = 1

        source_student = _clean_data(row.get("source_student"))
        if source_student:
            _validate_billing_contact_source_student(
                account_holder_doc=account_holder_doc,
                source_student=source_student,
                guardian=guardian,
            )

    primary = primary_rows[0]
    primary_guardian = guardians_by_name.get(_clean_data(primary.get("guardian")))
    if primary_guardian:
        account_holder_doc.primary_email = _clean_data(primary_guardian.get("guardian_email"))
        account_holder_doc.primary_phone = _clean_data(primary_guardian.get("guardian_mobile_phone"))


def _validate_billing_contact_source_student(*, account_holder_doc, source_student: str, guardian: str) -> None:
    student = frappe.db.get_value(
        "Student",
        source_student,
        ["name", "anchor_school", "account_holder"],
        as_dict=True,
    )
    if not student:
        frappe.throw(_("Billing contact source Student {student} was not found.").format(student=source_student))

    student_account_holder = _clean_data(student.get("account_holder"))
    if student_account_holder and student_account_holder != account_holder_doc.name:
        frappe.throw(_("Billing contact source Student belongs to a different Account Holder."))

    school = _clean_data(student.get("anchor_school"))
    if school and get_school_organization(school) != account_holder_doc.organization:
        frappe.throw(_("Billing contact source Student must belong to the Account Holder organization."))

    linked = frappe.db.exists(
        "Student Guardian",
        {
            "parent": source_student,
            "parenttype": "Student",
            "parentfield": "guardians",
            "guardian": guardian,
        },
    )
    if not linked:
        frappe.throw(_("Billing contact Guardian must be linked to the source Student."))


def sync_account_holder_billing_contact_points(account_holder_doc) -> list[str]:
    synced: list[str] = []
    fallback_school = ""
    for row in account_holder_doc.get("billing_contacts") or []:
        if not _as_int(row.get("receives_billing_follow_up")):
            continue
        if not _clean_data(row.get("source_student")) and not fallback_school:
            fallback_school = _first_account_holder_student_school(account_holder_doc.name)
        synced.extend(
            _sync_billing_contact_points_for_row(
                row,
                account_holder_doc.organization,
                school=fallback_school,
            )
        )
    return synced


def _sync_billing_contact_points_for_row(row, organization: str, *, school: str | None = None) -> list[str]:
    guardian = _clean_data(row.get("guardian"))
    source_student = _clean_data(row.get("source_student"))
    if not guardian:
        return []

    resolved_school = _clean_data(school)
    if not resolved_school and source_student:
        student = frappe.db.get_value("Student", source_student, ["anchor_school"], as_dict=True)
        resolved_school = _clean_data((student or {}).get("anchor_school"))
    if not resolved_school:
        return []

    guardian_row = frappe.db.get_value(
        "Guardian",
        guardian,
        ["name", "organization", "guardian_email", "guardian_mobile_phone"],
        as_dict=True,
    )
    if not guardian_row:
        return []
    guardian_organization = _clean_data(guardian_row.get("organization"))
    if guardian_organization and guardian_organization != organization:
        frappe.throw(_("Billing contact Guardian must belong to the Account Holder organization."))

    return sync_guardian_contact_points(
        guardian_row,
        school=resolved_school,
        purpose=BILLING_CONTACT_PURPOSE,
        workflow=BILLING_CONTACT_SYNC_WORKFLOW,
    )


def sync_account_holder_billing_contacts_for_guardian(guardian: str) -> list[str]:
    guardian = _clean_data(guardian)
    if not guardian:
        return []

    rows = frappe.get_all(
        "Account Holder Billing Contact",
        filters={"guardian": guardian, "parenttype": "Account Holder"},
        fields=["parent"],
        limit=0,
    )
    account_holders = sorted({_clean_data(row.get("parent")) for row in rows if _clean_data(row.get("parent"))})
    touched: list[str] = []
    for account_holder in account_holders:
        doc = frappe.get_doc("Account Holder", account_holder)
        doc.save(ignore_permissions=True)
        touched.append(account_holder)
    return touched


@frappe.whitelist()
def get_student_account_holder_guardian_proposal(student_name: str) -> dict[str, Any]:
    student = _require_student_access(student_name, ptype="write")
    organization = _student_organization(student)
    candidates = [_public_candidate(candidate) for candidate in _guardian_candidates_for_student(student)]
    return {
        "student": student.name,
        "student_name": _clean_data(student.student_full_name) or student.name,
        "organization": organization,
        "account_holder": _clean_data(student.account_holder),
        "guardian_candidates": candidates,
        "can_create": bool(candidates),
        "blocker": None
        if candidates
        else _("Student has no linked Guardians. Add a Guardian before creating the Account Holder."),
    }


@frappe.whitelist()
def create_account_holder_from_student_guardians(student_name: str, guardians=None) -> dict[str, Any]:
    student_name = _clean_data(student_name)
    if not student_name:
        frappe.throw(_("Student is required."))

    locked = frappe.db.sql(
        "select name from `tabStudent` where name = %s for update",
        (student_name,),
        as_dict=True,
    )
    if not locked:
        frappe.throw(_("Invalid Student: {student}.").format(student=student_name))

    student = _require_student_access(student_name, ptype="write")
    organization = _student_organization(student)
    selected = _selected_candidates(_guardian_candidates_for_student(student), _parse_name_list(guardians))

    existing = _clean_data(student.account_holder)
    if existing:
        _validate_account_holder_scope(existing, organization)
        account_holder_doc = _require_account_holder_access(existing, ptype="write")
        created = False
    else:
        _require_account_holder_doctype_permission(ptype="create")
        account_holder_doc = _create_account_holder(student, organization, selected)
        _link_student_to_account_holder(student, account_holder_doc.name)
        created = True

    added = _ensure_account_holder_billing_contacts(account_holder_doc, student, selected)

    return {
        "ok": True,
        "created": created,
        "billing_contacts_added": added,
        "student": student.name,
        "account_holder": _account_holder_summary(account_holder_doc.name),
    }


def _account_holder_summary(account_holder: str) -> dict[str, Any]:
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
        frappe.throw(_("Account Holder {account_holder} was not found.").format(account_holder=account_holder))
    return {
        "name": _clean_data(row.get("name")),
        "organization": _clean_data(row.get("organization")),
        "account_holder_name": _clean_data(row.get("account_holder_name")),
        "account_holder_type": _clean_data(row.get("account_holder_type")),
        "status": _clean_data(row.get("status")),
        "primary_email_masked": mask_email(_clean_data(row.get("primary_email"))),
        "primary_phone_masked": mask_phone(_clean_data(row.get("primary_phone"))),
    }


@frappe.whitelist()
def get_account_holder_billing_contact_summary(account_holder: str) -> dict[str, Any]:
    doc = _require_account_holder_access(account_holder, ptype="read")
    can_view_raw = _can_view_raw_billing_contacts()
    rows = list(doc.get("billing_contacts") or [])
    if not rows:
        return {
            "account_holder": doc.name,
            "primary_email_masked": mask_email(_clean_data(doc.primary_email)),
            "primary_phone_masked": mask_phone(_clean_data(doc.primary_phone)),
            "contacts": [],
            "can_reveal": can_view_raw,
            "shows_raw_contact_values": can_view_raw,
        }

    guardian_names = [_clean_data(row.get("guardian")) for row in rows if _clean_data(row.get("guardian"))]
    guardians = _guardian_rows_by_name(guardian_names)
    student_names = [_clean_data(row.get("source_student")) for row in rows if _clean_data(row.get("source_student"))]
    students = _student_rows_by_name(student_names)

    contacts = []
    fallback_school = ""
    for row in rows:
        guardian_name = _clean_data(row.get("guardian"))
        source_student = _clean_data(row.get("source_student"))
        guardian = guardians.get(guardian_name, {})
        student = students.get(source_student, {})
        school = _clean_data(student.get("anchor_school"))
        if not school and not fallback_school:
            fallback_school = _first_account_holder_student_school(doc.name)
        school = school or fallback_school
        masked_points = _masked_billing_points_for_guardian(guardian_name, school=school)
        email_masked = masked_points.get("email") or mask_email(_clean_data(guardian.get("guardian_email")))
        phone_masked = masked_points.get("phone") or mask_phone(_clean_data(guardian.get("guardian_mobile_phone")))
        email_value = (
            _get_raw_billing_contact_value_for_display(doc, row, school=school, channel_type="email")
            if can_view_raw
            else ""
        )
        phone_value = (
            _get_raw_billing_contact_value_for_display(doc, row, school=school, channel_type="phone")
            if can_view_raw
            else ""
        )
        contacts.append(
            {
                "name": row.name,
                "guardian": guardian_name,
                "guardian_name": _clean_data(row.get("guardian_name")) or _guardian_display_name(guardian),
                "relation": _clean_data(row.get("relation")),
                "source_student": source_student,
                "source_student_name": _clean_data(student.get("student_full_name")) or source_student,
                "is_primary": _as_int(row.get("is_primary")),
                "receives_billing_follow_up": _as_int(row.get("receives_billing_follow_up")),
                "email_masked": email_masked,
                "phone_masked": phone_masked,
                "email_display": email_value or email_masked,
                "phone_display": phone_value or phone_masked,
                "email_is_raw": bool(email_value),
                "phone_is_raw": bool(phone_value),
                "has_email": bool(email_value or email_masked),
                "has_phone": bool(phone_value or phone_masked),
            }
        )

    return {
        "account_holder": doc.name,
        "primary_email_masked": mask_email(_clean_data(doc.primary_email)),
        "primary_phone_masked": mask_phone(_clean_data(doc.primary_phone)),
        "contacts": contacts,
        "can_reveal": can_view_raw,
        "shows_raw_contact_values": can_view_raw,
    }


def _can_reveal_billing_contacts() -> bool:
    return _can_view_raw_billing_contacts()


def _can_view_raw_billing_contacts() -> bool:
    user = _clean_data(getattr(frappe.session, "user", ""))
    roles = set(frappe.get_roles(user) or [])
    return user == "Administrator" or bool(roles & BILLING_CONTACT_RAW_ROLES)


def _get_raw_billing_contact_value_for_display(doc, row, *, school: str, channel_type: str) -> str:
    if not _as_int(row.get("receives_billing_follow_up")) or not school:
        return ""

    points = _billing_contact_points(row, school=school, channel_type=channel_type)
    if not points:
        _sync_billing_contact_points_for_row(row, doc.organization, school=school)
        points = _billing_contact_points(row, school=school, channel_type=channel_type)
    if not points:
        return ""

    return get_raw_contact_point_value(
        contact_point=_clean_data(points[0].get("name")),
        purpose=BILLING_CONTACT_PURPOSE,
        workflow=BILLING_CONTACT_RAW_WORKFLOW,
    )


def _guardian_rows_by_name(guardian_names: list[str]) -> dict[str, dict[str, Any]]:
    if not guardian_names:
        return {}
    rows = frappe.get_all(
        "Guardian",
        filters={"name": ["in", list(dict.fromkeys(guardian_names))]},
        fields=[
            "name",
            "guardian_full_name",
            "guardian_first_name",
            "guardian_last_name",
            "guardian_email",
            "guardian_mobile_phone",
        ],
        limit=0,
    )
    return {_clean_data(row.get("name")): row for row in rows if _clean_data(row.get("name"))}


def _student_rows_by_name(student_names: list[str]) -> dict[str, dict[str, Any]]:
    if not student_names:
        return {}
    rows = frappe.get_all(
        "Student",
        filters={"name": ["in", list(dict.fromkeys(student_names))]},
        fields=["name", "student_full_name", "anchor_school"],
        limit=0,
    )
    return {_clean_data(row.get("name")): row for row in rows if _clean_data(row.get("name"))}


def _masked_billing_points_for_guardian(guardian: str, *, school: str | None = None) -> dict[str, str]:
    if not guardian:
        return {}
    points = get_masked_contact_points_for_owner(
        owner_doctype="Guardian",
        owner_name=guardian,
        purpose=BILLING_CONTACT_PURPOSE,
        school=school,
    )
    by_channel: dict[str, str] = {}
    for point in points:
        channel = _clean_data(point.get("channel_type"))
        if channel and channel not in by_channel:
            by_channel[channel] = _clean_data(point.get("masked_display"))
    return by_channel


@frappe.whitelist()
def reveal_account_holder_billing_contact_value(
    account_holder: str,
    billing_contact: str,
    channel_type: str,
) -> dict[str, Any]:
    doc = _require_account_holder_access(account_holder, ptype="read")
    _ensure_raw_billing_contact_actor()

    channel = _clean_data(channel_type)
    if channel not in {"email", "phone"}:
        frappe.throw(_("Billing contact channel must be email or phone."))

    contact_row = None
    for row in doc.get("billing_contacts") or []:
        if _clean_data(row.name) == _clean_data(billing_contact):
            contact_row = row
            break
    if not contact_row:
        frappe.throw(_("Billing contact row was not found."))
    if not cint(contact_row.get("receives_billing_follow_up")):
        frappe.throw(_("This billing contact is not enabled for billing follow-up."))

    school = _billing_contact_school(contact_row) or _first_account_holder_student_school(doc.name)
    if not school:
        frappe.throw(
            _(
                "Billing contact cannot be revealed because no School context is available. "
                "Link the billing contact from a Student first."
            )
        )

    points = _billing_contact_points(contact_row, school=school, channel_type=channel)
    if not points:
        _sync_billing_contact_points_for_row(contact_row, doc.organization, school=school)
        points = _billing_contact_points(contact_row, school=school, channel_type=channel)
    if not points:
        frappe.throw(_("Selected billing contact does not have a {channel_type}.").format(channel_type=channel))

    point_name = _clean_data(points[0].get("name"))
    value = get_raw_contact_point_value(
        contact_point=point_name,
        purpose=BILLING_CONTACT_PURPOSE,
        workflow=BILLING_CONTACT_RAW_WORKFLOW,
    )
    return {
        "guardian": _clean_data(contact_row.get("guardian")),
        "guardian_name": _clean_data(contact_row.get("guardian_name")),
        "channel_type": channel,
        "value": value,
    }


def _billing_contact_points(row, *, school: str, channel_type: str) -> list[dict[str, Any]]:
    guardian = _clean_data(row.get("guardian"))
    if not guardian:
        return []
    points = get_masked_contact_points_for_owner(
        owner_doctype="Guardian",
        owner_name=guardian,
        purpose=BILLING_CONTACT_PURPOSE,
        channel_type=channel_type,
        school=school,
    )
    points.sort(key=lambda point: (0 if _as_int(point.get("is_primary")) else 1, _clean_data(point.get("name"))))
    return points


def _billing_contact_school(row) -> str:
    source_student = _clean_data(row.get("source_student"))
    if not source_student:
        return ""
    return _clean_data(frappe.db.get_value("Student", source_student, "anchor_school"))


def _first_account_holder_student_school(account_holder: str) -> str:
    rows = frappe.get_all(
        "Student",
        filters={"account_holder": account_holder},
        fields=["anchor_school"],
        order_by="modified desc",
        limit=1,
    )
    if not rows:
        return ""
    return _clean_data(rows[0].get("anchor_school"))
