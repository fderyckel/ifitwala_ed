from __future__ import annotations

import frappe


def execute():
    required_tables = ("Guardian", "Contact", "Dynamic Link")
    if any(not frappe.db.table_exists(doctype) for doctype in required_tables):
        return

    guardian_rows = frappe.get_all(
        "Guardian",
        fields=["name", "user", "guardian_email"],
        limit=100000,
    )

    for guardian_row in guardian_rows:
        _backfill_guardian_contact_link(guardian_row)


def _backfill_guardian_contact_link(guardian_row: dict) -> None:
    guardian_name = str(guardian_row.get("name") or "").strip()
    if not guardian_name:
        return

    contact_name = _resolve_contact_name(
        user=guardian_row.get("user"),
        guardian_email=guardian_row.get("guardian_email"),
    )
    if not contact_name:
        return

    guardian_doc = frappe.get_doc("Guardian", guardian_name)
    guardian_doc._ensure_contact_link(contact_name)


def _resolve_contact_name(*, user: str | None, guardian_email: str | None) -> str | None:
    user_contact = _resolve_contact_name_by_user(user)
    if user_contact is False:
        return None
    if user_contact:
        return user_contact
    return _resolve_contact_name_by_primary_email(guardian_email)


def _resolve_contact_name_by_user(user: str | None) -> str | bool | None:
    user = str(user or "").strip()
    if not user:
        return None

    rows = frappe.get_all(
        "Contact",
        filters={"user": user},
        fields=["name"],
        limit=2,
    )
    contact_names = sorted({str(row.get("name") or "").strip() for row in rows if str(row.get("name") or "").strip()})
    if len(contact_names) > 1:
        return False
    return contact_names[0] if contact_names else None


def _resolve_contact_name_by_primary_email(guardian_email: str | None) -> str | None:
    guardian_email = str(guardian_email or "").strip()
    if not guardian_email or not frappe.db.table_exists("Contact Email"):
        return None

    rows = frappe.get_all(
        "Contact Email",
        filters={"email_id": guardian_email, "is_primary": 1},
        fields=["parent"],
        limit=2,
    )
    contact_names = sorted(
        {str(row.get("parent") or "").strip() for row in rows if str(row.get("parent") or "").strip()}
    )
    if len(contact_names) != 1:
        return None
    return contact_names[0]
