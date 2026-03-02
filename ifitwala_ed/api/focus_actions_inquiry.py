# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus_actions_inquiry.py

import frappe
from frappe import _

from ifitwala_ed.api.focus_shared import (
    ACTION_INQUIRY_FIRST_CONTACT,
    INQUIRY_DOCTYPE,
    _cache,
    _idempotency_key,
    _lock_key,
    _parse_focus_item_id,
    _require_login,
)


def mark_inquiry_contacted(
    focus_item_id: str,
    complete_todo: int = 1,
    client_request_id: str | None = None,
):
    user = _require_login()

    focus_item_id = (focus_item_id or "").strip()
    client_request_id = (client_request_id or "").strip() or None
    complete_todo = frappe.utils.cint(complete_todo)

    if not focus_item_id:
        frappe.throw(_("Missing focus_item_id."))

    parsed = _parse_focus_item_id(focus_item_id)

    if parsed.get("user") != user:
        frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

    if parsed.get("reference_doctype") != INQUIRY_DOCTYPE:
        frappe.throw(_("Invalid focus item reference."), frappe.ValidationError)

    action_type = parsed.get("action_type")
    if action_type != ACTION_INQUIRY_FIRST_CONTACT:
        frappe.throw(_("This focus item is not an inquiry follow-up action."), frappe.PermissionError)

    inquiry_name = parsed.get("reference_name")
    if not inquiry_name:
        frappe.throw(_("Invalid focus item reference name."), frappe.ValidationError)

    cache = _cache()

    # Idempotency must short-circuit before state/assignee checks because
    # a successful first call mutates both workflow_state and assigned_to.
    if client_request_id:
        key = _idempotency_key(user, focus_item_id, client_request_id, "inquiry_mark_contacted")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "inquiry_name": inquiry_name,
                "result": existing,
            }

    inquiry_doc = frappe.get_doc(INQUIRY_DOCTYPE, inquiry_name)

    if not frappe.has_permission(INQUIRY_DOCTYPE, ptype="read", doc=inquiry_doc):
        frappe.throw(_("You are not permitted to view this inquiry."), frappe.PermissionError)

    current_state = (inquiry_doc.workflow_state or "").strip()
    if current_state == "Contacted":
        result = "contacted"
        if client_request_id:
            key = _idempotency_key(user, focus_item_id, client_request_id, "inquiry_mark_contacted")
            cache.set_value(key, result, expires_in_sec=60 * 10)
        return {
            "ok": True,
            "idempotent": True,
            "status": "already_processed",
            "inquiry_name": inquiry_name,
            "result": result,
        }

    if (inquiry_doc.assigned_to or "").strip() != user:
        frappe.throw(_("Only the assigned user can complete this inquiry follow-up."), frappe.PermissionError)

    if current_state != "Assigned":
        frappe.throw(_("This Inquiry is not in Assigned state."))

    lock_name = _lock_key(user, focus_item_id, "inquiry_mark_contacted")
    with cache.lock(lock_name, timeout=10):
        if client_request_id:
            key = _idempotency_key(user, focus_item_id, client_request_id, "inquiry_mark_contacted")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "inquiry_name": inquiry_name,
                    "result": existing,
                }

        inquiry_doc.mark_contacted(complete_todo=1 if complete_todo else 0)
        result = "contacted"

        if client_request_id:
            cache.set_value(key, result, expires_in_sec=60 * 10)

        return {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "inquiry_name": inquiry_name,
            "result": result,
        }
