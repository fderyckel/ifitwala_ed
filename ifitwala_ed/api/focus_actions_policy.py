# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus_actions_policy.py

import frappe
from frappe import _

from ifitwala_ed.api.focus_shared import (
    ACTION_POLICY_STAFF_SIGN,
    POLICY_VERSION_DOCTYPE,
    _active_employee_row,
    _as_bool,
    _cache,
    _idempotency_key,
    _lock_key,
    _normalize_signature_name,
    _parse_focus_item_id,
    _require_login,
)
from ifitwala_ed.api.policy_signature import (
    close_open_staff_policy_todos,
    find_open_staff_policy_todos,
    get_policy_version_context,
    parse_employee_from_todo_description,
    validate_staff_policy_scope_for_employee,
)


def acknowledge_staff_policy(
    focus_item_id: str,
    client_request_id: str | None = None,
    typed_signature_name: str | None = None,
    attestation_confirmed: int | str | bool | None = None,
):
    user = _require_login()
    focus_item_id = (focus_item_id or "").strip()
    client_request_id = (client_request_id or "").strip() or None
    typed_signature_name = (typed_signature_name or "").strip()
    attestation_confirmed_flag = _as_bool(attestation_confirmed)

    if not focus_item_id:
        frappe.throw(_("Missing focus_item_id."))

    parsed = _parse_focus_item_id(focus_item_id)
    if parsed.get("user") != user:
        frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)
    if parsed.get("reference_doctype") != POLICY_VERSION_DOCTYPE:
        frappe.throw(_("Invalid focus item reference."), frappe.ValidationError)
    if parsed.get("action_type") != ACTION_POLICY_STAFF_SIGN:
        frappe.throw(_("This focus item is not a staff policy acknowledgement action."), frappe.PermissionError)

    policy_version = (parsed.get("reference_name") or "").strip()
    if not policy_version:
        frappe.throw(_("Invalid focus item reference name."), frappe.ValidationError)

    cache = _cache()
    suffix = "policy_ack_staff_sign"
    if client_request_id:
        key = _idempotency_key(user, focus_item_id, client_request_id, suffix)
        existing = cache.get_value(key)
        if existing:
            try:
                parsed_existing = frappe.parse_json(existing)
            except Exception:
                parsed_existing = None
            if isinstance(parsed_existing, dict):
                return {
                    **parsed_existing,
                    "status": "already_processed",
                    "idempotent": True,
                }

    with cache.lock(_lock_key(user, focus_item_id, suffix), timeout=10):
        if client_request_id:
            key = _idempotency_key(user, focus_item_id, client_request_id, suffix)
            existing = cache.get_value(key)
            if existing:
                try:
                    parsed_existing = frappe.parse_json(existing)
                except Exception:
                    parsed_existing = None
                if isinstance(parsed_existing, dict):
                    return {
                        **parsed_existing,
                        "status": "already_processed",
                        "idempotent": True,
                    }

        policy_row = get_policy_version_context(
            policy_version,
            require_active=True,
            require_staff_applies=True,
        )

        todos = find_open_staff_policy_todos(user=user, policy_version=policy_version)
        active_employee = _active_employee_row(user)
        if not todos and not active_employee:
            frappe.throw(_("No open policy acknowledgement task was found for your account."))

        employee_name = None
        if todos:
            employee_name = parse_employee_from_todo_description(todos[0].get("description"))
        if not employee_name and active_employee:
            employee_name = active_employee.get("name")
        if not employee_name:
            frappe.throw(_("No Employee context could be resolved for this acknowledgement."))

        employee = frappe.db.get_value(
            "Employee",
            employee_name,
            [
                "name",
                "employee_full_name",
                "organization",
                "school",
                "employee_group",
                "user_id",
                "employment_status",
            ],
            as_dict=True,
        )
        if not employee:
            frappe.throw(_("Employee context no longer exists."))
        if (employee.get("user_id") or "").strip() != user:
            frappe.throw(_("You are not assigned to this policy acknowledgement task."), frappe.PermissionError)
        if (employee.get("employment_status") or "").strip() != "Active":
            frappe.throw(_("Only active Employees can acknowledge Staff policies."))

        validate_staff_policy_scope_for_employee(policy_row, employee)

        existing_ack = frappe.db.get_value(
            "Policy Acknowledgement",
            {
                "policy_version": policy_version,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": employee_name,
            },
            ["name", "acknowledged_at"],
            as_dict=True,
        )
        if existing_ack:
            closed_count = close_open_staff_policy_todos(user=user, policy_version=policy_version)
            result = {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "policy_version": policy_version,
                "employee": employee_name,
                "acknowledgement": existing_ack.get("name"),
                "acknowledged_at": existing_ack.get("acknowledged_at"),
                "closed_todos": closed_count,
            }
            if client_request_id:
                cache.set_value(key, frappe.as_json(result), expires_in_sec=60 * 10)
            return result

        expected_full_name = (employee.get("employee_full_name") or "").strip()
        expected_candidates = {
            normalized
            for normalized in {
                _normalize_signature_name(expected_full_name),
                _normalize_signature_name(employee_name),
            }
            if normalized
        }

        if not attestation_confirmed_flag:
            frappe.throw(
                _("You must confirm the electronic signature attestation before signing."),
                frappe.ValidationError,
            )

        normalized_typed_name = _normalize_signature_name(typed_signature_name)
        if not normalized_typed_name:
            frappe.throw(_("Type your full name as your electronic signature."), frappe.ValidationError)

        if expected_candidates and normalized_typed_name not in expected_candidates:
            expected_label = expected_full_name or employee_name
            frappe.throw(
                _("Typed signature must match your employee name exactly: {0}").format(expected_label),
                frappe.ValidationError,
            )

        ack_doc = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": policy_version,
                "acknowledged_by": user,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": employee_name,
            }
        )
        ack_doc.insert(ignore_permissions=True)

        closed_count = close_open_staff_policy_todos(user=user, policy_version=policy_version)
        frappe.publish_realtime(
            event="focus:invalidate",
            message={"source": "policy_signature_ack", "policy_version": policy_version},
            user=user,
        )

        result = {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "policy_version": policy_version,
            "employee": employee_name,
            "acknowledgement": ack_doc.name,
            "acknowledged_at": ack_doc.acknowledged_at,
            "closed_todos": closed_count,
        }
        if client_request_id:
            cache.set_value(key, frappe.as_json(result), expires_in_sec=60 * 10)
        return result
