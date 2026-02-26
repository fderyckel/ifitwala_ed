# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus_actions_student_log.py

import frappe
from frappe import _

from ifitwala_ed.api.focus_shared import (
    ACTION_STUDENT_LOG_REVIEW,
    ACTION_STUDENT_LOG_SUBMIT,
    FOLLOW_UP_DOCTYPE,
    STUDENT_LOG_DOCTYPE,
    _cache,
    _idempotency_key,
    _lock_key,
    _parse_focus_item_id,
    _require_login,
)


def submit_student_log_follow_up(
    focus_item_id: str,
    follow_up: str,
    client_request_id: str | None = None,
):
    """
    Submit a Student Log Follow Up as a Focus workflow action.

    Client (Vue) sends:
    - focus_item_id
    - follow_up
    - client_request_id (optional but recommended)

    Server guarantees:
    - focus_item_id belongs to session user
    - action_type is the submit action
    - doc-level permission enforced on the Student Log
    - log not Completed
    - idempotent against rapid double submits
    - creates + submits Student Log Follow Up (so your controller side effects run)
    """
    user = _require_login()

    focus_item_id = (focus_item_id or "").strip()
    follow_up = (follow_up or "").strip()
    client_request_id = (client_request_id or "").strip() or None

    if not focus_item_id:
        frappe.throw(_("Missing focus_item_id."))
    if not follow_up or len(follow_up) < 5:
        frappe.throw(_("Follow-up text is too short."))

    parsed = _parse_focus_item_id(focus_item_id)

    # Hard guard: focus item must belong to current user
    if parsed.get("user") != user:
        frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

    # Hard guard: must be Student Log submit action
    if parsed.get("reference_doctype") != STUDENT_LOG_DOCTYPE:
        frappe.throw(_("Invalid focus item reference."), frappe.ValidationError)

    action_type = parsed.get("action_type")
    if action_type != ACTION_STUDENT_LOG_SUBMIT:
        frappe.throw(_("This focus item is not a follow-up submission action."), frappe.PermissionError)

    log_name = parsed.get("reference_name")
    if not log_name:
        frappe.throw(_("Invalid focus item reference name."), frappe.ValidationError)

    # Load log ONCE (permission + state)
    log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, log_name)

    # Doc-level permission (authoritative)
    if not frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", doc=log_doc):
        frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

    # State guard
    if (log_doc.follow_up_status or "").lower() == "completed":
        frappe.throw(_("This Student Log is already <b>Completed</b>."))

    cache = _cache()

    # Idempotency (schema-free)
    if client_request_id:
        key = _idempotency_key(user, focus_item_id, client_request_id, "submit_follow_up")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "log_name": log_name,
                "follow_up_name": existing,
            }

    lock_name = _lock_key(user, focus_item_id, "submit_follow_up")
    with cache.lock(lock_name, timeout=10):
        # re-check inside lock
        if client_request_id:
            key = _idempotency_key(user, focus_item_id, client_request_id, "submit_follow_up")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "log_name": log_name,
                    "follow_up_name": existing,
                }

        # Create + submit follow-up: triggers your StudentLogFollowUp controller side effects
        fu = frappe.get_doc(
            {
                "doctype": FOLLOW_UP_DOCTYPE,
                "student_log": log_name,
                "follow_up": follow_up,
            }
        )
        fu.insert(ignore_permissions=False)
        fu.submit()

        if client_request_id:
            cache.set_value(key, fu.name, expires_in_sec=60 * 10)

        return {
            "ok": True,
            "idempotent": False,
            "status": "created",
            "log_name": log_name,
            "follow_up_name": fu.name,
        }


def review_student_log_outcome(
    focus_item_id: str,
    decision: str,
    follow_up_person: str | None = None,
    client_request_id: str | None = None,
):
    """
    Author review action for "student_log.follow_up.review.decide".

    decisions:
    - "complete"  -> completes the parent log
    - "reassign"  -> reassigns follow_up_person (and ToDo) via Student Log controller

    Why focus_item_id:
    - user-bound, deterministic
    - prevents spoofing log_name/action_type
    """
    user = _require_login()

    focus_item_id = (focus_item_id or "").strip()
    decision = (decision or "").strip().lower()
    follow_up_person = (follow_up_person or "").strip() or None
    client_request_id = (client_request_id or "").strip() or None

    if not focus_item_id:
        frappe.throw(_("Missing focus_item_id."))

    if decision not in ("complete", "reassign"):
        frappe.throw(_("Invalid decision."), frappe.ValidationError)

    parsed = _parse_focus_item_id(focus_item_id)

    # Hard guard: focus item must belong to current user
    if parsed.get("user") != user:
        frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

    # Hard guard: must be Student Log review action
    if parsed.get("reference_doctype") != STUDENT_LOG_DOCTYPE:
        frappe.throw(_("Invalid focus item reference."), frappe.ValidationError)

    action_type = parsed.get("action_type")
    if action_type != ACTION_STUDENT_LOG_REVIEW:
        frappe.throw(_("This focus item is not a review action."), frappe.PermissionError)

    log_name = parsed.get("reference_name")
    if not log_name:
        frappe.throw(_("Invalid focus item reference name."), frappe.ValidationError)

    # Load log ONCE (permission + state)
    log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, log_name)

    # Doc-level permission (authoritative)
    if not frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", doc=log_doc):
        frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

    # Strong semantic guard: review outcome is for log owner
    if (log_doc.owner or "") != user:
        frappe.throw(_("Only the log author can review the outcome."), frappe.PermissionError)

    # State guard
    if (log_doc.follow_up_status or "").lower() == "completed":
        frappe.throw(_("This Student Log is already <b>Completed</b>."))

    if decision == "reassign" and not follow_up_person:
        frappe.throw(_("Missing follow_up_person."), frappe.ValidationError)

    cache = _cache()

    # Idempotency
    if client_request_id:
        key = _idempotency_key(user, focus_item_id, client_request_id, f"review_{decision}")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "log_name": log_name,
                "result": existing,
            }

    lock_name = _lock_key(user, focus_item_id, f"review_{decision}")
    with cache.lock(lock_name, timeout=10):
        # re-check inside lock
        if client_request_id:
            key = _idempotency_key(user, focus_item_id, client_request_id, f"review_{decision}")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "log_name": log_name,
                    "result": existing,
                }

        # Delegate to Student Log controller APIs (authoritative ToDo handling)
        from ifitwala_ed.students.doctype.student_log.student_log import assign_follow_up, complete_log

        if decision == "complete":
            complete_log(log_name=log_name)
            result = "completed"
        else:
            assign_follow_up(log_name=log_name, user=follow_up_person)
            result = f"reassigned:{follow_up_person}"

        if client_request_id:
            cache.set_value(key, result, expires_in_sec=60 * 10)

        return {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "log_name": log_name,
            "result": result,
        }
