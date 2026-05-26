# ifitwala_ed/admission/api/portal/invites.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.access import (
    ADMISSIONS_ACCESS_MODE_FAMILY,
    ADMISSIONS_FAMILY_ROLE,
    get_admissions_access_mode,
    is_family_workspace_enabled,
)
from ifitwala_ed.admission.access import (
    ADMISSIONS_APPLICANT_ROLE as ADMISSIONS_ROLE,
)
from ifitwala_ed.admission.admission_utils import (
    ensure_admissions_permission,
    ensure_contact_dynamic_link,
    ensure_contact_for_email,
    get_contact_primary_email,
    normalize_email_value,
    sync_student_applicant_contact_binding,
    upsert_contact_email,
)
from ifitwala_ed.admission.api.portal.contacts import (
    _applicant_contact_prefill_payload,
    _resolve_applicant_contact,
)
from ifitwala_ed.admission.api.portal.guardians import (
    APPLICANT_CONTACT_GUARDIAN_ROW,
    _create_or_update_guardian_contact,
    _guardian_row_display_name,
    _hydrate_guardian_row_from_applicant_contact,
    _normalize_guardian_row,
    _validate_guardian_profile_row,
)
from ifitwala_ed.contacts.contact_privacy import (
    assert_user_can_access_student_applicant_contact,
    get_raw_contact_email_options_for_applicant_invite,
)
from ifitwala_ed.governance.policy_utils import (
    ADMISSIONS_POLICY_MODE_FAMILY,
    get_applicant_policy_status,
)


def _as_text(value) -> str:
    if value is None:
        return ""
    return str(value)


def _ensure_admissions_applicant_role(user_doc) -> None:
    changed = False
    role_names = []
    seen = set()
    had_desk_user = False

    for row in user_doc.roles or []:
        role = (row.role or "").strip()
        if not role:
            continue
        if role == "Desk User":
            had_desk_user = True
            continue
        if role in seen:
            continue
        seen.add(role)
        role_names.append(role)

    if ADMISSIONS_ROLE not in seen:
        role_names.append(ADMISSIONS_ROLE)
        changed = True

    if had_desk_user:
        changed = True

    if changed:
        user_doc.set("roles", [{"role": role} for role in role_names])

    if (user_doc.user_type or "").strip() != "Website User":
        user_doc.user_type = "Website User"
        changed = True

    if not int(user_doc.enabled or 0):
        user_doc.enabled = 1
        changed = True
    if changed:
        user_doc.save(ignore_permissions=True)


def _ensure_admissions_family_role(user_doc) -> None:
    changed = False
    role_names = []
    seen = set()

    for row in user_doc.roles or []:
        role = (row.role or "").strip()
        if not role or role in seen:
            continue
        seen.add(role)
        role_names.append(role)

    if ADMISSIONS_FAMILY_ROLE not in seen:
        role_names.append(ADMISSIONS_FAMILY_ROLE)
        changed = True

    if changed:
        user_doc.set("roles", [{"role": role} for role in role_names])

    if not (user_doc.user_type or "").strip():
        user_doc.user_type = "Website User"
        changed = True

    if not int(user_doc.enabled or 0):
        user_doc.enabled = 1
        changed = True

    if changed:
        user_doc.save(ignore_permissions=True)


def _call_user_method_if_available(user_doc, method_name: str) -> bool:
    target = getattr(user_doc, method_name, None)
    if not callable(target):
        return False
    try:
        target()
        return True
    except TypeError:
        return False


def _send_applicant_invite_email(user_doc, recipient: str) -> bool:
    try:
        if _call_user_method_if_available(user_doc, "send_welcome_email"):
            return True
        if _call_user_method_if_available(user_doc, "send_password_notification"):
            return True
        frappe.sendmail(
            recipients=[recipient],
            subject=_("Admissions Portal Access"),
            message=_("Your admissions portal access is ready. Use Forgot Password if needed."),
        )
        return True
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Admissions applicant invite email failed")
        return False


def _contact_linked_to_user(user_name: str | None) -> str | None:
    user_name = (user_name or "").strip()
    if not user_name:
        return None

    contact_name = (frappe.db.get_value("Contact", {"user": user_name}, "name") or "").strip()
    if contact_name:
        return contact_name

    contact_name = (
        frappe.db.get_value(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parentfield": "links",
                "link_doctype": "User",
                "link_name": user_name,
            },
            "parent",
        )
        or ""
    ).strip()
    return contact_name or None


def _contact_linked_to_applicant(contact_name: str | None) -> str | None:
    contact_name = (contact_name or "").strip()
    if not contact_name:
        return None

    applicant_name = (
        frappe.db.get_value(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parentfield": "links",
                "parent": contact_name,
                "link_doctype": "Student Applicant",
            },
            "link_name",
        )
        or ""
    ).strip()
    return applicant_name or None


def _canonical_applicant_contact_for_invite(
    applicant_doc,
    *,
    user_doc=None,
    contact_name: str | None = None,
    invite_email: str | None = None,
    allow_create: bool = False,
) -> str | None:
    current_contact = (applicant_doc.get("applicant_contact") or "").strip()
    if current_contact:
        return current_contact

    invite_email = normalize_email_value(invite_email)
    candidate_names: list[str] = []
    for candidate in (
        _contact_linked_to_user(getattr(user_doc, "name", None) if user_doc else None),
        (frappe.db.get_value("Contact Email", {"email_id": invite_email}, "parent") or "").strip()
        if invite_email
        else "",
        (contact_name or "").strip(),
    ):
        candidate = (candidate or "").strip()
        if not candidate or candidate in candidate_names:
            continue
        linked_applicant = _contact_linked_to_applicant(candidate)
        if linked_applicant and linked_applicant != applicant_doc.name:
            frappe.throw(_("Invite email is linked to a different Contact."))
        candidate_names.append(candidate)

    if candidate_names:
        return candidate_names[0]

    if allow_create and invite_email:
        return ensure_contact_for_email(
            first_name=applicant_doc.get("first_name"),
            last_name=applicant_doc.get("last_name"),
            email=invite_email,
        )

    return None


def _invite_contact_email_options(contact_name: str | None, student_applicant: str | None) -> list[str]:
    return get_raw_contact_email_options_for_applicant_invite(
        contact=contact_name,
        student_applicant=student_applicant,
        purpose="applicant_invite_contact_options",
    )


def _invite_contact_primary_email(contact_name: str | None, student_applicant: str | None) -> str | None:
    options = _invite_contact_email_options(contact_name, student_applicant)
    if options:
        return options[0]
    return get_contact_primary_email(contact_name)


def _applicant_invite_options_payload(applicant) -> dict:
    contact_name = _canonical_applicant_contact_for_invite(
        applicant,
        user_doc=frappe.get_doc("User", applicant.applicant_user)
        if applicant.applicant_user and frappe.db.exists("User", applicant.applicant_user)
        else None,
        contact_name=_resolve_applicant_contact(applicant, allow_create=False),
        invite_email=normalize_email_value(applicant.get("portal_account_email"))
        or normalize_email_value(applicant.get("applicant_email"))
        or normalize_email_value(applicant.get("applicant_user")),
        allow_create=False,
    )

    emails: list[str] = []
    seen: set[str] = set()
    for value in (
        normalize_email_value(applicant.get("portal_account_email")),
        normalize_email_value(applicant.get("applicant_email")),
        normalize_email_value(applicant.get("applicant_user")),
    ):
        if value and value not in seen:
            seen.add(value)
            emails.append(value)

    for value in _invite_contact_email_options(contact_name, applicant.name):
        if value and value not in seen:
            seen.add(value)
            emails.append(value)

    selected = (
        normalize_email_value(applicant.get("portal_account_email"))
        or normalize_email_value(applicant.get("applicant_user"))
        or normalize_email_value(applicant.get("applicant_email"))
        or (emails[0] if emails else None)
    )

    return {
        "contact": contact_name,
        "emails": emails,
        "selected_email": selected,
        "has_linked_user": bool(_as_text(applicant.get("applicant_user")).strip()),
    }


def _family_invite_options_payload(applicant) -> dict:
    guardian_payload = []
    contact_payload = _applicant_contact_prefill_payload(applicant)
    contact_email = normalize_email_value(contact_payload.get("email"))
    applicant_user_email = normalize_email_value(applicant.get("applicant_user"))
    portal_account_email = normalize_email_value(applicant.get("portal_account_email"))

    for row in applicant.get("guardians") or []:
        email = normalize_email_value(row.get("guardian_email"))
        is_primary_guardian = bool(cint(row.get("is_primary_guardian") or 0))
        can_consent = bool(cint(row.get("can_consent")))
        can_hydrate_from_applicant_contact = False
        if not email and is_primary_guardian and can_consent and contact_payload.get("available"):
            row_contact = _as_text(row.get("contact")).strip()
            row_user = normalize_email_value(row.get("user"))
            contact_matches_row = not row_contact or row_contact == _as_text(contact_payload.get("contact")).strip()
            user_matches_contact = not row_user or row_user in {
                contact_email,
                applicant_user_email,
                portal_account_email,
            }
            can_hydrate_from_applicant_contact = bool(contact_matches_row and user_matches_contact)
            if can_hydrate_from_applicant_contact:
                email = contact_email

        eligible = bool(email and cint(row.get("can_consent")) and is_primary_guardian)
        reason = ""
        if not is_primary_guardian:
            reason = _("Mark this family collaborator as the primary guardian before inviting admissions access.")
        elif not cint(row.get("can_consent")):
            reason = _("Only the primary guardian may be invited as the authorized family signer.")
        elif not email:
            reason = _("Add a family collaborator email before inviting admissions access.")
        guardian_payload.append(
            {
                "name": row.name,
                "label": _guardian_row_display_name(row),
                "relationship": _as_text(row.get("relationship")).strip(),
                "email": email,
                "user": _as_text(row.get("user")).strip() or None,
                "guardian": _as_text(row.get("guardian")).strip() or None,
                "can_consent": bool(cint(row.get("can_consent"))),
                "eligible": eligible,
                "reason": reason or None,
                "bootstrap_from_applicant_contact": can_hydrate_from_applicant_contact,
            }
        )

    if not guardian_payload:
        if contact_payload.get("available"):
            guardian_payload.append(
                {
                    "name": APPLICANT_CONTACT_GUARDIAN_ROW,
                    "label": " ".join(
                        part
                        for part in [
                            _as_text(contact_payload.get("first_name")).strip(),
                            _as_text(contact_payload.get("last_name")).strip(),
                        ]
                        if part
                    ),
                    "relationship": "Other",
                    "email": normalize_email_value(contact_payload.get("email")),
                    "user": None,
                    "guardian": None,
                    "can_consent": True,
                    "eligible": True,
                    "reason": None,
                    "bootstrap_from_applicant_contact": True,
                }
            )

    return {"guardians": guardian_payload}


def _required_family_acknowledgement_policy_labels(applicant) -> list[str]:
    policy_status = get_applicant_policy_status(
        student_applicant=applicant.name,
        organization=applicant.get("organization"),
        school=applicant.get("school"),
    )
    labels: list[str] = []
    for row_policy in policy_status.get("rows") or []:
        if row_policy.get("admissions_acknowledgement_mode") != ADMISSIONS_POLICY_MODE_FAMILY:
            continue
        if not row_policy.get("is_required"):
            continue
        label = _as_text(row_policy.get("label") or row_policy.get("policy_title") or row_policy.get("policy_key"))
        labels.append(label.strip() or _as_text(row_policy.get("policy_version")).strip())
    return [label for label in labels if label]


def _applicant_self_invite_blocked_reason(applicant) -> str:
    if is_family_workspace_enabled():
        return _("Applicant-self invites are disabled while Family Workspace mode is enabled.")

    family_policy_labels = _required_family_acknowledgement_policy_labels(applicant)
    if family_policy_labels:
        return _(
            "Applicant-self invite cannot satisfy Family Acknowledgement policies: {policies}. "
            "Change those admissions policies to Child Acknowledgement, or enable Family Workspace and invite an "
            "Admissions Family collaborator."
        ).format(policies=", ".join(family_policy_labels))

    return ""


def _require_family_workspace_mode() -> None:
    if not is_family_workspace_enabled():
        frappe.throw(
            _("Family Workspace mode is not enabled in Admission Settings."),
            frappe.ValidationError,
        )


def _require_scoped_staff_applicant_access(student_applicant: str | None) -> str:
    user = ensure_admissions_permission()
    applicant_name = _as_text(student_applicant).strip()
    if not applicant_name:
        frappe.throw(_("student_applicant is required."))
    assert_user_can_access_student_applicant_contact(
        student_applicant=applicant_name,
        purpose="admissions_staff_contact_workflow",
        user=user,
    )
    return user


def _get_applicant_guardian_row(applicant, guardian_row_name: str):
    target_name = (guardian_row_name or "").strip()
    if not target_name:
        frappe.throw(_("guardian_row is required."))
    for row in applicant.get("guardians") or []:
        if (row.name or "").strip() == target_name:
            return row
    frappe.throw(
        _("Guardian row {guardian_row} was not found on this Applicant.").format(guardian_row=target_name),
        frappe.DoesNotExistError,
    )


def _bootstrap_applicant_contact_guardian_row(*, applicant, email: str | None = None):
    if applicant.get("guardians"):
        frappe.throw(_("Select an existing family collaborator row for this applicant."))

    contact_name = _resolve_applicant_contact(applicant, allow_create=False, bind_to_applicant=True)
    contact_payload = _applicant_contact_prefill_payload(applicant)
    if not contact_name or not contact_payload.get("available"):
        frappe.throw(
            _(
                "Complete the Inquiry Contact first: first name, last name, personal email, and mobile phone are required."
            )
        )

    invite_email = normalize_email_value(email or contact_payload.get("email"))
    if not invite_email:
        frappe.throw(_("email is required."))
    contact_emails = set(_invite_contact_email_options(contact_name, applicant.name))
    if invite_email not in contact_emails:
        frappe.throw(_("Invite email must belong to the Inquiry Contact."))

    row_payload = _validate_guardian_profile_row(
        _normalize_guardian_row(
            {
                "contact": contact_name,
                "use_applicant_contact": 1,
                "relationship": "Other",
                "is_primary": 1,
                "is_primary_guardian": 1,
                "guardian_first_name": contact_payload.get("first_name"),
                "guardian_last_name": contact_payload.get("last_name"),
                "guardian_email": invite_email,
                "guardian_mobile_phone": contact_payload.get("mobile_phone"),
            }
        ),
        require_photo=False,
    )
    row_payload["contact"] = contact_name
    row_payload["guardian_full_name"] = _guardian_row_display_name(row_payload)

    target_row = applicant.append(
        "guardians",
        {
            "contact": contact_name,
            "use_applicant_contact": 1,
            "relationship": "Other",
            "is_primary": 1,
            "can_consent": 1,
            "guardian_full_name": row_payload.get("guardian_full_name") or None,
            "guardian_first_name": row_payload.get("guardian_first_name") or None,
            "guardian_last_name": row_payload.get("guardian_last_name") or None,
            "guardian_mobile_phone": row_payload.get("guardian_mobile_phone") or None,
            "guardian_email": row_payload.get("guardian_email") or None,
            "is_primary_guardian": 1,
        },
    )
    applicant.save(ignore_permissions=True)
    sync_student_applicant_contact_binding(student_applicant=applicant.name, contact_name=contact_name)
    return target_row


def _ensure_family_guardian_user(*, guardian, email: str, applicant_name: str, row_payload: dict):
    resolved_email = normalize_email_value(email)
    if not resolved_email:
        frappe.throw(_("Guardian email is required."))

    existing_user_guardian = frappe.db.get_value("Guardian", {"user": resolved_email}, "name")
    if existing_user_guardian and existing_user_guardian != guardian.name:
        frappe.throw(_("This email is already linked to a different Guardian account."))

    existing_applicant = frappe.db.get_value("Student Applicant", {"applicant_user": resolved_email}, "name")
    if existing_applicant and existing_applicant != applicant_name:
        frappe.throw(
            _(
                "This email is already reserved as an Applicant login ({applicant}). Use a different family collaborator email."
            ).format(applicant=existing_applicant)
        )

    resent = False
    if guardian.user:
        linked_user = normalize_email_value(guardian.user)
        if linked_user != resolved_email:
            frappe.throw(_("Guardian is already linked to a different user account."))
        user_doc = frappe.get_doc("User", linked_user)
        resent = True
    elif frappe.db.exists("User", resolved_email):
        user_doc = frappe.get_doc("User", resolved_email)
    else:
        user_doc = frappe.get_doc(
            {
                "doctype": "User",
                "enabled": 1,
                "first_name": row_payload.get("guardian_first_name") or resolved_email,
                "last_name": row_payload.get("guardian_last_name") or "",
                "email": resolved_email,
                "username": resolved_email,
                "mobile_no": row_payload.get("guardian_mobile_phone") or "",
                "user_type": "Website User",
            }
        )
        user_doc.append("roles", {"role": ADMISSIONS_FAMILY_ROLE})
        user_doc.insert(ignore_permissions=True)

    _ensure_admissions_family_role(user_doc)

    if not (guardian.user or "").strip():
        guardian.db_set("user", user_doc.name, update_modified=False)
    if (guardian.user or "").strip() != user_doc.name:
        frappe.throw(_("Guardian is already linked to a different user account."))

    return user_doc, resent


def _remove_admissions_applicant_role(user_doc) -> None:
    roles = []
    changed = False
    for row in user_doc.roles or []:
        role = (row.role or "").strip()
        if role == ADMISSIONS_ROLE:
            changed = True
            continue
        if role:
            roles.append({"role": role})
    if changed:
        user_doc.set("roles", roles)
        user_doc.save(ignore_permissions=True)


def _clear_applicant_self_login_for_family_conversion(*, applicant, invite_email: str, user_doc) -> bool:
    if normalize_email_value(applicant.get("applicant_user")) != normalize_email_value(invite_email):
        return False

    applicant.applicant_user = None
    applicant.portal_account_email = None
    _remove_admissions_applicant_role(user_doc)
    return True


def get_family_invite_options_impl(*, student_applicant: str | None = None) -> dict:
    _require_scoped_staff_applicant_access(student_applicant)
    _require_family_workspace_mode()

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    return _family_invite_options_payload(applicant)


def invite_family_collaborator_impl(
    *,
    student_applicant: str | None = None,
    guardian_row: str | None = None,
    email: str | None = None,
) -> dict:
    _require_scoped_staff_applicant_access(student_applicant)
    _require_family_workspace_mode()

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    requested_guardian_row = (guardian_row or "").strip()
    if requested_guardian_row == APPLICANT_CONTACT_GUARDIAN_ROW:
        target_row = _bootstrap_applicant_contact_guardian_row(applicant=applicant, email=email)
    else:
        target_row = _get_applicant_guardian_row(applicant, requested_guardian_row)
    if not cint(target_row.get("is_primary_guardian") or 0):
        frappe.throw(_("Only primary family collaborator rows may be invited to the family workspace as signers."))
    if not cint(target_row.get("can_consent")):
        frappe.throw(
            _("Only family collaborator rows marked as authorized signers may be invited to the family workspace.")
        )

    invite_email = normalize_email_value(email or target_row.get("guardian_email"))
    if not invite_email:
        frappe.throw(_("email is required."))

    row_payload = dict(target_row.as_dict())
    row_payload["guardian_email"] = invite_email
    if not _as_text(target_row.get("guardian_email")).strip():
        row_payload = _hydrate_guardian_row_from_applicant_contact(applicant=applicant, row_payload=row_payload)
        row_payload["guardian_email"] = invite_email
    row_payload = _validate_guardian_profile_row(_normalize_guardian_row(row_payload), require_photo=False)
    contact_name = _create_or_update_guardian_contact(
        applicant=applicant,
        row_payload=row_payload,
        existing_contact_name=_as_text(target_row.get("contact")).strip() or None,
    )
    row_payload["contact"] = contact_name

    if (target_row.get("guardian") or "").strip():
        guardian_doc = frappe.get_doc("Guardian", target_row.get("guardian"))
    else:
        guardian_spec = applicant._create_or_reuse_guardian_from_profile_row(row_payload)
        guardian_doc = guardian_spec["guardian"]

    user_doc, resent = _ensure_family_guardian_user(
        guardian=guardian_doc,
        email=invite_email,
        applicant_name=applicant.name,
        row_payload=row_payload,
    )
    converted_applicant_login = _clear_applicant_self_login_for_family_conversion(
        applicant=applicant,
        invite_email=invite_email,
        user_doc=user_doc,
    )

    if contact_name:
        ensure_contact_dynamic_link(contact_name=contact_name, link_doctype="Guardian", link_name=guardian_doc.name)
        contact_user = _as_text(frappe.db.get_value("Contact", contact_name, "user")).strip()
        if not contact_user:
            frappe.db.set_value("Contact", contact_name, "user", user_doc.name, update_modified=False)

    target_row.guardian = guardian_doc.name
    target_row.contact = contact_name
    target_row.user = user_doc.name
    target_row.guardian_email = invite_email
    target_row.guardian_full_name = _guardian_row_display_name(row_payload)
    target_row.guardian_first_name = row_payload.get("guardian_first_name")
    target_row.guardian_last_name = row_payload.get("guardian_last_name")
    target_row.guardian_mobile_phone = row_payload.get("guardian_mobile_phone")
    applicant.save(ignore_permissions=True)
    if _as_text(applicant.get("applicant_contact")).strip():
        sync_student_applicant_contact_binding(
            student_applicant=applicant.name,
            contact_name=_as_text(applicant.get("applicant_contact")).strip(),
        )

    email_sent = _send_applicant_invite_email(user_doc, invite_email)
    applicant.add_comment(
        "Comment",
        text=_("Family admissions portal access invited for {guardian_label} ({invite_email}) by {actor}.").format(
            guardian_label=frappe.bold(_guardian_row_display_name(target_row)),
            invite_email=frappe.bold(invite_email),
            actor=frappe.bold(frappe.session.user),
        ),
    )

    return {
        "ok": True,
        "user": user_doc.name,
        "resent": resent,
        "email_sent": email_sent,
        "converted_applicant_login": converted_applicant_login,
    }


def get_invite_email_options_impl(*, student_applicant: str | None = None) -> dict:
    _require_scoped_staff_applicant_access(student_applicant)
    if is_family_workspace_enabled():
        frappe.throw(
            _("Single applicant invites are disabled while Family Workspace mode is enabled."),
            frappe.ValidationError,
        )

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    blocked_reason = _applicant_self_invite_blocked_reason(applicant)
    if blocked_reason:
        frappe.throw(blocked_reason, frappe.ValidationError)

    return _applicant_invite_options_payload(applicant)


def get_admissions_portal_invite_options_impl(*, student_applicant: str | None = None) -> dict:
    _require_scoped_staff_applicant_access(student_applicant)

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    access_mode = get_admissions_access_mode()
    family_workspace_enabled = bool(access_mode == ADMISSIONS_ACCESS_MODE_FAMILY)
    applicant_invite = _applicant_invite_options_payload(applicant)
    family_invite = _family_invite_options_payload(applicant)

    applicant_blocked_reason = _applicant_self_invite_blocked_reason(applicant)
    family_blocked_reason = ""
    if not family_workspace_enabled:
        family_blocked_reason = _(
            "Family collaborator invites require Admission Settings to use Family Workspace mode."
        )
    elif not any(bool(row.get("eligible")) for row in family_invite.get("guardians") or []):
        if not applicant.get("guardians"):
            family_blocked_reason = _(
                "Complete the Inquiry Contact first: first name, last name, personal email, and mobile phone are required."
            )
        else:
            family_blocked_reason = _(
                "Complete a primary family collaborator row with signer authority and a personal email, or link a "
                "complete Inquiry/Applicant Contact that can prefill that row."
            )

    applicant_invite["enabled"] = not bool(applicant_blocked_reason)
    applicant_invite["disabled_reason"] = applicant_blocked_reason or None
    family_invite["enabled"] = not bool(family_blocked_reason)
    family_invite["disabled_reason"] = family_blocked_reason or None

    return {
        "access_mode": access_mode,
        "family_workspace_enabled": family_workspace_enabled,
        "recommended_invite_mode": "Family Collaborator" if family_workspace_enabled else "Applicant Self",
        "applicant_invite": applicant_invite,
        "family_invite": family_invite,
    }


def invite_applicant_impl(*, student_applicant: str | None = None, email: str | None = None) -> dict:
    _require_scoped_staff_applicant_access(student_applicant)
    if is_family_workspace_enabled():
        frappe.throw(
            _("Use the Family collaborator invite while Family Workspace mode is enabled."),
            frappe.ValidationError,
        )

    if not email:
        frappe.throw(_("email is required."))

    email = normalize_email_value(email)
    if not email:
        frappe.throw(_("email is required."))

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    blocked_reason = _applicant_self_invite_blocked_reason(applicant)
    if blocked_reason:
        frappe.throw(blocked_reason, frappe.ValidationError)

    if applicant.applicant_user:
        linked_user = normalize_email_value(applicant.applicant_user)
        if linked_user != email:
            frappe.throw(_("Applicant already linked to a different user."))

    contact_name = _resolve_applicant_contact(applicant, invite_email=email, allow_create=False)

    if applicant.applicant_user:
        user_doc = frappe.get_doc("User", linked_user)
        _ensure_admissions_applicant_role(user_doc)
        contact_name = _canonical_applicant_contact_for_invite(
            applicant,
            user_doc=user_doc,
            contact_name=contact_name,
            invite_email=email,
            allow_create=True,
        )
        if not contact_name:
            frappe.throw(_("Unable to resolve Applicant Contact for this invite."))
        upsert_contact_email(contact_name, email, set_primary_if_missing=True)
        primary_contact_email = _invite_contact_primary_email(contact_name, applicant.name) or email

        applicant.flags.from_applicant_invite = True
        applicant.flags.from_contact_sync = True
        applicant.applicant_contact = contact_name
        applicant.applicant_email = primary_contact_email
        applicant.portal_account_email = email

        if applicant.application_status == "Draft":
            applicant._set_status("Invited", "Applicant invited", permission_checker=None)
        else:
            applicant.save(ignore_permissions=True)
        sync_student_applicant_contact_binding(
            student_applicant=applicant.name,
            contact_name=contact_name,
        )

        email_sent = _send_applicant_invite_email(user_doc, email)
        applicant.add_comment(
            "Comment",
            text=_("Applicant portal invite email re-sent for {applicant} by {actor}.").format(
                applicant=frappe.bold(applicant.name),
                actor=frappe.bold(frappe.session.user),
            ),
        )
        return {"ok": True, "user": user_doc.name, "resent": True, "email_sent": email_sent}

    user_doc = None
    if frappe.db.exists("User", email):
        user_doc = frappe.get_doc("User", email)
        existing_roles = {row.role for row in (user_doc.roles or [])}
        non_portal_roles = existing_roles - {ADMISSIONS_ROLE, "All", "Guest", "Desk User"}
        if non_portal_roles:
            frappe.throw(_("User already has non-admissions roles and cannot be invited."))
    else:
        user_doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": applicant.first_name or email,
                "last_name": applicant.last_name or "",
                "enabled": 1,
                "username": email,
                "user_type": "Website User",
            }
        )
        user_doc.append("roles", {"role": ADMISSIONS_ROLE})
        user_doc.insert(ignore_permissions=True)

    _ensure_admissions_applicant_role(user_doc)
    contact_name = _canonical_applicant_contact_for_invite(
        applicant,
        user_doc=user_doc,
        contact_name=contact_name,
        invite_email=email,
        allow_create=True,
    )
    if not contact_name:
        frappe.throw(_("Unable to resolve Applicant Contact for this invite."))
    upsert_contact_email(contact_name, email, set_primary_if_missing=True)
    primary_contact_email = _invite_contact_primary_email(contact_name, applicant.name) or email

    existing_link = frappe.db.get_value(
        "Student Applicant",
        {"applicant_user": user_doc.name},
        "name",
    )
    if existing_link and existing_link != applicant.name:
        frappe.throw(_("User is already linked to another Applicant."))

    if frappe.db.exists("Student", {"student_user_id": user_doc.name}):
        frappe.throw(_("User is already linked to a Student."))
    if frappe.db.exists("Guardian", {"user": user_doc.name}):
        frappe.throw(_("User is already linked to a Guardian."))
    if frappe.db.exists("Employee", {"user_id": user_doc.name}):
        frappe.throw(_("User is already linked to an Employee."))

    applicant.flags.from_applicant_invite = True
    applicant.flags.from_contact_sync = True
    applicant.applicant_user = user_doc.name
    applicant.applicant_contact = contact_name
    applicant.applicant_email = primary_contact_email
    applicant.portal_account_email = email

    if applicant.application_status == "Draft":
        applicant._set_status("Invited", "Applicant invited", permission_checker=None)
    else:
        applicant.save(ignore_permissions=True)
    sync_student_applicant_contact_binding(
        student_applicant=applicant.name,
        contact_name=contact_name,
    )

    applicant.add_comment(
        "Comment",
        text=_("Applicant portal user invited for {applicant} by {actor}.").format(
            applicant=frappe.bold(applicant.name),
            actor=frappe.bold(frappe.session.user),
        ),
    )

    email_sent = _send_applicant_invite_email(user_doc, email)

    return {"ok": True, "user": user_doc.name, "resent": False, "email_sent": email_sent}
