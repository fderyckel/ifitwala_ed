from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    READ_LIKE_PERMISSION_TYPES,
    get_admissions_file_staff_scope,
)

CRM_MANAGER_ROLES = {"Admission Manager", "System Manager"}
CRM_MUTATION_ROLES = ADMISSIONS_ROLES | {"System Manager"}


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _roles(user: str) -> set[str]:
    return {(role or "").strip() for role in frappe.get_roles(user) if (role or "").strip()}


def is_admissions_crm_manager(user: str | None = None) -> bool:
    resolved_user = _clean(user or frappe.session.user)
    if not resolved_user or resolved_user == "Guest":
        return False
    if resolved_user == "Administrator":
        return True
    return bool(_roles(resolved_user) & CRM_MANAGER_ROLES)


def is_admissions_crm_user(user: str | None = None) -> bool:
    resolved_user = _clean(user or frappe.session.user)
    if not resolved_user or resolved_user == "Guest":
        return False
    if resolved_user == "Administrator":
        return True
    return bool(_roles(resolved_user) & CRM_MUTATION_ROLES)


def ensure_admissions_crm_permission(*, manager_only: bool = False, user: str | None = None) -> str:
    resolved_user = _clean(user or frappe.session.user)
    if not resolved_user or resolved_user == "Guest":
        frappe.throw(_("You need to sign in to perform this action."), frappe.PermissionError)

    allowed = is_admissions_crm_manager(resolved_user) if manager_only else is_admissions_crm_user(resolved_user)
    if allowed:
        return resolved_user

    frappe.throw(_("You do not have permission to perform this admissions CRM action."), frappe.PermissionError)
    return resolved_user


def _scope_values_to_sql(values: set[str]) -> str:
    cleaned = sorted({_clean(value) for value in values if _clean(value)})
    return ", ".join(frappe.db.escape(value) for value in cleaned)


def _has_admissions_role(user: str) -> bool:
    if user == "Administrator":
        return True
    return bool(_roles(user) & CRM_MUTATION_ROLES)


def _scope_condition_for_alias(*, user: str, alias: str) -> str | None:
    if not _has_admissions_role(user):
        return "1=0"

    scope = get_admissions_file_staff_scope(user)
    if not scope.get("allowed"):
        return "1=0"
    if scope.get("bypass"):
        return None

    org_scope = set(scope.get("org_scope") or set())
    school_scope = set(scope.get("school_scope") or set())

    conditions: list[str] = []
    org_values = _scope_values_to_sql(org_scope)
    if org_values:
        conditions.append(f"`tab{alias}`.`organization` IN ({org_values})")

    school_values = _scope_values_to_sql(school_scope)
    if school_values:
        conditions.append(f"(IFNULL(`tab{alias}`.`school`, '') = '' OR `tab{alias}`.`school` IN ({school_values}))")

    return " AND ".join(conditions) if conditions else "1=0"


def doc_is_in_admissions_crm_scope(*, user: str, organization: str | None, school: str | None) -> bool:
    if not _has_admissions_role(user):
        return False

    scope = get_admissions_file_staff_scope(user)
    if not scope.get("allowed"):
        return False
    if scope.get("bypass"):
        return True

    doc_org = _clean(organization)
    doc_school = _clean(school)
    org_scope = set(scope.get("org_scope") or set())
    school_scope = set(scope.get("school_scope") or set())

    if org_scope and doc_org not in org_scope:
        return False
    if doc_school and school_scope and doc_school not in school_scope:
        return False
    if not doc_org and not doc_school:
        return False
    return True


def channel_account_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = _clean(user or frappe.session.user)
    if not resolved_user or resolved_user == "Guest":
        return "1=0"
    return _scope_condition_for_alias(user=resolved_user, alias="Admission Channel Account")


def channel_account_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = _clean(user or frappe.session.user)
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False
    if op not in READ_LIKE_PERMISSION_TYPES | {"create", "write", "delete"}:
        return False
    if op not in READ_LIKE_PERMISSION_TYPES and not is_admissions_crm_manager(resolved_user):
        return False
    if op == "create":
        return is_admissions_crm_manager(resolved_user)
    if not doc:
        return True
    if isinstance(doc, str):
        doc = frappe.db.get_value("Admission Channel Account", doc, ["organization", "school"], as_dict=True)
        if not doc:
            return False
    return doc_is_in_admissions_crm_scope(
        user=resolved_user,
        organization=getattr(doc, "organization", None) or doc.get("organization"),
        school=getattr(doc, "school", None) or doc.get("school"),
    )


def external_identity_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = _clean(user or frappe.session.user)
    if not resolved_user or resolved_user == "Guest":
        return "1=0"

    account_scope = _scope_condition_for_alias(user=resolved_user, alias="Admission Channel Account")
    if account_scope is None:
        return None
    if account_scope == "1=0":
        return "1=0"
    return (
        "EXISTS ("
        "SELECT 1 FROM `tabAdmission Channel Account` "
        "WHERE `tabAdmission Channel Account`.`name` = `tabAdmission External Identity`.`channel_account` "
        f"AND {account_scope}"
        ")"
    )


def external_identity_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = _clean(user or frappe.session.user)
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False
    if op not in READ_LIKE_PERMISSION_TYPES | {"create", "write", "delete"}:
        return False
    if op == "delete" and not is_admissions_crm_manager(resolved_user):
        return False
    if op == "create":
        return is_admissions_crm_user(resolved_user)
    if not doc:
        return True
    if isinstance(doc, str):
        doc = frappe.db.get_value("Admission External Identity", doc, ["channel_account"], as_dict=True)
        if not doc:
            return False

    account_name = getattr(doc, "channel_account", None) or doc.get("channel_account")
    if not account_name:
        return False
    account = frappe.db.get_value(
        "Admission Channel Account",
        account_name,
        ["organization", "school"],
        as_dict=True,
    )
    if not account:
        return False
    return doc_is_in_admissions_crm_scope(
        user=resolved_user,
        organization=account.get("organization"),
        school=account.get("school"),
    )


def conversation_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = _clean(user or frappe.session.user)
    if not resolved_user or resolved_user == "Guest":
        return "1=0"

    scope_condition = _scope_condition_for_alias(user=resolved_user, alias="Admission Conversation")
    if scope_condition is None:
        return None
    if scope_condition == "1=0":
        return "1=0"

    if is_admissions_crm_manager(resolved_user):
        return scope_condition

    escaped_user = frappe.db.escape(resolved_user)
    return (
        f"({scope_condition}) "
        "AND COALESCE(NULLIF(`tabAdmission Conversation`.`assigned_to`, ''), "
        f"`tabAdmission Conversation`.`owner`) = {escaped_user}"
    )


def conversation_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = _clean(user or frappe.session.user)
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False
    if op not in READ_LIKE_PERMISSION_TYPES | {"create", "write", "delete"}:
        return False
    if op == "delete" and not is_admissions_crm_manager(resolved_user):
        return False
    if op == "create":
        return is_admissions_crm_user(resolved_user)
    if not doc:
        return True
    if isinstance(doc, str):
        doc = frappe.db.get_value(
            "Admission Conversation",
            doc,
            ["organization", "school", "assigned_to", "owner"],
            as_dict=True,
        )
        if not doc:
            return False

    organization = getattr(doc, "organization", None) or doc.get("organization")
    school = getattr(doc, "school", None) or doc.get("school")
    if not doc_is_in_admissions_crm_scope(user=resolved_user, organization=organization, school=school):
        return False
    if is_admissions_crm_manager(resolved_user):
        return True

    assigned_to = _clean(getattr(doc, "assigned_to", None) or doc.get("assigned_to"))
    owner = _clean(getattr(doc, "owner", None) or doc.get("owner"))
    return (assigned_to or owner) == resolved_user


def linked_conversation_permission_query_conditions(*, doctype: str, user: str | None = None) -> str | None:
    resolved_user = _clean(user or frappe.session.user)
    if not resolved_user or resolved_user == "Guest":
        return "1=0"

    conversation_scope = conversation_permission_query_conditions(resolved_user)
    if conversation_scope is None:
        return None
    if conversation_scope == "1=0":
        return "1=0"

    return (
        "EXISTS ("
        "SELECT 1 FROM `tabAdmission Conversation` "
        f"WHERE `tabAdmission Conversation`.`name` = `tab{doctype}`.`conversation` "
        f"AND {conversation_scope}"
        ")"
    )


def linked_conversation_has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = _clean(user or frappe.session.user)
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False
    if op not in READ_LIKE_PERMISSION_TYPES | {"create", "write", "delete"}:
        return False
    if op == "delete" and not is_admissions_crm_manager(resolved_user):
        return False
    if op == "create" and not doc:
        return is_admissions_crm_user(resolved_user)
    if not doc:
        return True
    if isinstance(doc, str):
        return False

    conversation = _clean(getattr(doc, "conversation", None) or doc.get("conversation"))
    if not conversation:
        return False
    conversation_doc = frappe.db.get_value(
        "Admission Conversation",
        conversation,
        ["organization", "school", "assigned_to", "owner"],
        as_dict=True,
    )
    if not conversation_doc:
        return False
    return conversation_has_permission(conversation_doc, ptype=op, user=resolved_user)
