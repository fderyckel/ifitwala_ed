# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import importlib
import re
from typing import Any

import frappe
from frappe import _

EXPENSE_CLAIM_RECEIPT_BINDING_ROLE = "expense_claim_receipt"
EXPENSE_CLAIM_RECEIPT_DATA_CLASS = "financial"
EXPENSE_CLAIM_RECEIPT_PURPOSE = "administrative"
EXPENSE_CLAIM_RECEIPT_RETENTION_POLICY = "fixed_7y"
EXPENSE_CLAIM_RECEIPT_SLOT_PREFIX = "expense_claim_receipt__"
EXPENSE_CLAIM_RECEIPT_CATEGORY = "Expense Claim Receipt"


def _refresh_runtime_bindings():
    global frappe

    current_frappe = importlib.import_module("frappe")
    bound_is_stub = getattr(frappe, "__file__", None) is None
    current_is_real = getattr(current_frappe, "__file__", None) is not None

    if not bound_is_stub or not current_is_real or current_frappe is frappe:
        return frappe

    frappe = current_frappe
    return frappe


def _clean_link_value(value: str | None) -> str | None:
    _refresh_runtime_bindings()

    resolved = str(value or "").strip()
    return resolved or None


def _normalize_row_key(value: str | None) -> str:
    _refresh_runtime_bindings()

    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip()).strip("-_")
    if normalized:
        return normalized
    return frappe.generate_hash(length=10)


def parse_expense_claim_receipt_row_key(slot: str | None) -> str | None:
    _refresh_runtime_bindings()

    resolved_slot = str(slot or "").strip()
    if not resolved_slot.startswith(EXPENSE_CLAIM_RECEIPT_SLOT_PREFIX):
        return None
    row_key = resolved_slot.split(EXPENSE_CLAIM_RECEIPT_SLOT_PREFIX, 1)[1].strip()
    return row_key or None


def _get_doc(name: str, *, permission_type: str | None = None):
    _refresh_runtime_bindings()

    if not _clean_link_value(name):
        frappe.throw(_("Save the Expense Claim before attaching receipts."))

    if not frappe.db.exists("Expense Claim", name):
        frappe.throw(_("Expense Claim does not exist: {claim}").format(claim=name))

    doc = frappe.get_doc("Expense Claim", name)
    if permission_type and not frappe.has_permission("Expense Claim", doc=doc, ptype=permission_type):
        frappe.throw(_("You do not have permission to access this Expense Claim."), frappe.PermissionError)
    return doc


def assert_expense_claim_receipt_upload_access(
    expense_claim: str,
    *,
    permission_type: str = "write",
):
    _refresh_runtime_bindings()

    doc = _get_doc(expense_claim, permission_type=permission_type)
    if doc.status != "Draft" and not (
        set(frappe.get_roles()) & {"Accounts Manager", "Accounts User", "System Manager"}
    ):
        frappe.throw(_("Receipts can only be changed on draft claims unless finance is processing the claim."))
    return doc


def _assert_receipt_row_exists(doc, row_key: str) -> None:
    _refresh_runtime_bindings()

    if not row_key:
        frappe.throw(_("Receipt row key is required."))
    for row in doc.get("receipts") or []:
        if str(getattr(row, "name", "") or "").strip() == row_key:
            return
    frappe.throw(_("Expense Claim receipt row was not found: {row_key}.").format(row_key=row_key))


def build_expense_claim_receipt_upload_contract(
    doc,
    *,
    row_name: str | None = None,
    require_existing_row: bool = False,
) -> dict[str, Any]:
    if getattr(doc, "is_new", lambda: False)():
        frappe.throw(_("Save the Expense Claim before attaching receipts."))

    if not doc.organization or not doc.employee:
        frappe.throw(_("Expense Claim requires organization and employee context before receipt upload."))

    row_key = _normalize_row_key(row_name)
    if row_name and require_existing_row:
        _assert_receipt_row_exists(doc, row_key)

    return {
        "owner_doctype": "Expense Claim",
        "owner_name": doc.name,
        "attached_doctype": "Expense Claim",
        "attached_name": doc.name,
        "organization": doc.organization,
        "school": doc.school,
        "primary_subject_type": "Employee",
        "primary_subject_id": doc.employee,
        "data_class": EXPENSE_CLAIM_RECEIPT_DATA_CLASS,
        "purpose": EXPENSE_CLAIM_RECEIPT_PURPOSE,
        "retention_policy": EXPENSE_CLAIM_RECEIPT_RETENTION_POLICY,
        "slot": f"{EXPENSE_CLAIM_RECEIPT_SLOT_PREFIX}{row_key}",
        "row_name": row_key,
    }


def validate_expense_claim_receipt_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != "Expense Claim":
        return None

    row_key = parse_expense_claim_receipt_row_key(getattr(upload_session_doc, "intended_slot", None))
    if not row_key:
        frappe.throw(_("Expense Claim receipt upload sessions require a receipt slot."))

    doc = assert_expense_claim_receipt_upload_access(upload_session_doc.owner_name, permission_type="write")
    authoritative = build_expense_claim_receipt_upload_contract(
        doc,
        row_name=row_key,
        require_existing_row=False,
    )

    field_map = {
        "owner_doctype": "owner_doctype",
        "owner_name": "owner_name",
        "attached_doctype": "attached_doctype",
        "attached_name": "attached_name",
        "organization": "organization",
        "school": "school",
        "intended_primary_subject_type": "primary_subject_type",
        "intended_primary_subject_id": "primary_subject_id",
        "intended_data_class": "data_class",
        "intended_purpose": "purpose",
        "intended_retention_policy": "retention_policy",
        "intended_slot": "slot",
    }

    for session_field, authoritative_field in field_map.items():
        if getattr(upload_session_doc, session_field, None) != authoritative[authoritative_field]:
            frappe.throw(
                _(
                    "Upload session no longer matches the authoritative Expense Claim receipt context for field '{fieldname}'."
                ).format(fieldname=session_field)
            )

    return authoritative


def get_expense_claim_receipt_context_override(owner_name: str | None, slot: str | None) -> dict[str, Any] | None:
    if not owner_name or not frappe.db.exists("Expense Claim", owner_name):
        return None

    doc = _get_doc(owner_name)
    organization = _clean_link_value(doc.organization)
    if not organization:
        return None

    if _clean_link_value(doc.school):
        subfolder = f"{organization}/Schools/{doc.school}/Finance/Expense Claims/{doc.name}/Receipts"
    else:
        subfolder = f"{organization}/Finance/Expense Claims/{doc.name}/Receipts"

    return {
        "root_folder": "Home/Organizations",
        "subfolder": subfolder,
        "file_category": EXPENSE_CLAIM_RECEIPT_CATEGORY,
        "logical_key": str(slot or "").strip() or f"expense_claim_receipt_{doc.name}",
    }


def run_expense_claim_receipt_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Expense Claim":
        return {}

    row_key = parse_expense_claim_receipt_row_key(getattr(upload_session_doc, "intended_slot", None))
    if not row_key:
        return {}

    doc = frappe.get_doc("Expense Claim", upload_session_doc.owner_name)
    target_row = None
    for row in doc.get("receipts") or []:
        if str(getattr(row, "name", "") or "").strip() == row_key:
            target_row = row
            break

    if not target_row:
        target_row = doc.append("receipts", {})
        target_row.name = row_key

    file_url = getattr(created_file, "file_url", None) or frappe.db.get_value("File", created_file.name, "file_url")
    file_name = getattr(created_file, "file_name", None) or frappe.db.get_value("File", created_file.name, "file_name")
    file_size = getattr(created_file, "file_size", None) or frappe.db.get_value("File", created_file.name, "file_size")

    if not getattr(target_row, "section_break_sbex", None):
        target_row.section_break_sbex = file_name
    target_row.file = file_url
    target_row.file_name = file_name
    target_row.file_size = file_size
    target_row.external_url = None
    target_row.public = 0
    doc.flags.ignore_expense_claim_lock = True
    doc.save(ignore_permissions=True)

    return {
        "row_name": row_key,
        "file_url": file_url,
    }
