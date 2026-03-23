# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import cint

ROLE_RENAMES = (
    ("Assistant Admin", "Academic Assistant"),
    ("Counsellor", "Counselor"),
)


def _ensure_role(role_name: str, *, desk_access: int = 1) -> None:
    existing = frappe.db.exists("Role", role_name)
    if existing:
        doc = frappe.get_doc("Role", role_name)
        if int(doc.desk_access or 0) != int(desk_access):
            doc.desk_access = desk_access
            doc.save(ignore_permissions=True)
        return

    frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": desk_access}).insert(
        ignore_permissions=True
    )


def _update_link_fields(*, old_role: str, new_role: str) -> None:
    rows = frappe.get_all(
        "DocField",
        filters={"fieldtype": "Link", "options": "Role", "parenttype": "DocType"},
        fields=["parent", "fieldname"],
        limit=500,
    )

    for row in rows:
        doctype = row.get("parent")
        fieldname = row.get("fieldname")
        if not doctype or not fieldname:
            continue
        is_single = cint(frappe.db.get_value("DocType", doctype, "issingle") or 0)
        if is_single:
            current_value = frappe.db.get_single_value(doctype, fieldname)
            if (current_value or "").strip() == old_role:
                frappe.db.set_single_value(doctype, fieldname, new_role, update_modified=False)
            continue
        if not frappe.db.table_exists(doctype):
            continue
        frappe.db.sql(
            f"UPDATE `tab{doctype}` SET `{fieldname}` = %s WHERE `{fieldname}` = %s",
            (new_role, old_role),
        )


def _dedupe_has_role_rows(role_name: str) -> None:
    rows = frappe.get_all(
        "Has Role",
        filters={"role": role_name},
        fields=["name", "parent", "parenttype"],
        order_by="creation asc, name asc",
        limit=100000,
    )

    seen: set[tuple[str, str]] = set()
    duplicates: list[str] = []

    for row in rows:
        key = ((row.get("parent") or "").strip(), (row.get("parenttype") or "").strip())
        if key in seen:
            duplicates.append(row.get("name"))
            continue
        seen.add(key)

    if duplicates:
        frappe.db.delete("Has Role", {"name": ["in", duplicates]})


def _dedupe_permission_rows(doctype: str) -> None:
    if not frappe.db.table_exists(doctype):
        return

    dedupe_fields = [
        fieldname
        for fieldname in ("parent", "parenttype", "parentfield", "role", "permlevel")
        if frappe.db.has_column(doctype, fieldname)
    ]
    if not dedupe_fields:
        return

    rows = frappe.get_all(
        doctype,
        fields=["name", *dedupe_fields],
        order_by="creation asc, name asc",
        limit=100000,
    )

    seen: set[tuple[object, ...]] = set()
    duplicates: list[str] = []

    for row in rows:
        key = tuple(
            int(row.get(fieldname) or 0) if fieldname == "permlevel" else (row.get(fieldname) or "").strip()
            for fieldname in dedupe_fields
        )
        if key in seen:
            duplicates.append(row.get("name"))
            continue
        seen.add(key)

    if duplicates:
        frappe.db.delete(doctype, {"name": ["in", duplicates]})


def _drop_legacy_role(role_name: str) -> None:
    if not frappe.db.exists("Role", role_name):
        return
    frappe.delete_doc("Role", role_name, force=1, ignore_permissions=True)


def _migrate_role(old_role: str, new_role: str) -> None:
    _ensure_role(new_role)

    if not frappe.db.exists("Role", old_role):
        _dedupe_has_role_rows(new_role)
        return

    old_doc = frappe.get_doc("Role", old_role)
    new_doc = frappe.get_doc("Role", new_role)

    changed = False
    if int(old_doc.desk_access or 0) and not int(new_doc.desk_access or 0):
        new_doc.desk_access = 1
        changed = True
    if not (new_doc.home_page or "").strip() and (old_doc.home_page or "").strip():
        new_doc.home_page = old_doc.home_page
        changed = True
    if changed:
        new_doc.save(ignore_permissions=True)

    _update_link_fields(old_role=old_role, new_role=new_role)
    _dedupe_has_role_rows(new_role)
    _drop_legacy_role(old_role)


def execute():
    if not frappe.db.table_exists("Role"):
        return

    for old_role, new_role in ROLE_RENAMES:
        _migrate_role(old_role, new_role)

    _dedupe_permission_rows("DocPerm")
    _dedupe_permission_rows("Custom DocPerm")

    from ifitwala_ed.setup.setup import ensure_canonical_role_records, grant_core_crm_permissions

    ensure_canonical_role_records()
    grant_core_crm_permissions()
    frappe.clear_cache(doctype="Role")
