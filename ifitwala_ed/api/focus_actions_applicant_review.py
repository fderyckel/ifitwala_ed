# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus_actions_applicant_review.py

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.admission.applicant_review_workflow import complete_assignment_decision
from ifitwala_ed.api.focus_shared import (
    APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
    _cache,
    _idempotency_key,
    _lock_key,
    _require_login,
    _resolve_review_assignment_name,
    _reviewer_matches_assignment,
)


def claim_applicant_review_assignment(
    assignment: str | None = None,
    focus_item_id: str | None = None,
    client_request_id: str | None = None,
):
    user = _require_login()
    user_roles = set(frappe.get_roles(user))

    assignment_name = _resolve_review_assignment_name(user=user, assignment=assignment, focus_item_id=focus_item_id)
    lock_target = (focus_item_id or "").strip() or assignment_name
    client_request_id = (client_request_id or "").strip() or None

    cache = _cache()
    if client_request_id:
        key = _idempotency_key(user, lock_target, client_request_id, "applicant_review_assignment_claim")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "assignment": assignment_name,
                "assigned_to_user": existing,
            }

    with cache.lock(_lock_key(user, lock_target, "applicant_review_assignment_claim"), timeout=10):
        if client_request_id:
            key = _idempotency_key(user, lock_target, client_request_id, "applicant_review_assignment_claim")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "assignment": assignment_name,
                    "assigned_to_user": existing,
                }

        assignment_doc = frappe.get_doc(APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE, assignment_name)
        if (assignment_doc.status or "").strip() != "Open":
            frappe.throw(_("This review assignment is not open."), frappe.ValidationError)

        assigned_to_user = (assignment_doc.assigned_to_user or "").strip()
        assigned_to_role = (assignment_doc.assigned_to_role or "").strip()

        if assigned_to_user:
            if assigned_to_user == user:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "assignment": assignment_doc.name,
                    "assigned_to_user": user,
                }
            frappe.throw(_("This review assignment is already assigned to a specific user."), frappe.PermissionError)

        if not assigned_to_role:
            frappe.throw(_("This review assignment is missing an assigned role."), frappe.ValidationError)
        if assigned_to_role not in user_roles:
            frappe.throw(_("You are not assigned to this review item."), frappe.PermissionError)

        assignment_doc.assigned_to_user = user
        assignment_doc.assigned_to_role = None
        assignment_doc.save(ignore_permissions=True)

        if client_request_id:
            cache.set_value(key, user, expires_in_sec=60 * 10)

        frappe.publish_realtime(
            event="focus:invalidate",
            message={
                "assignment": assignment_doc.name,
                "target_type": assignment_doc.target_type,
                "target_name": assignment_doc.target_name,
                "claimed_by": user,
                "claimed_on": str(now_datetime()),
            },
            user=user,
        )

        return {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "assignment": assignment_doc.name,
            "assigned_to_user": user,
        }


def reassign_applicant_review_assignment(
    assignment: str | None = None,
    reassign_to_user: str | None = None,
    focus_item_id: str | None = None,
    client_request_id: str | None = None,
):
    user = _require_login()
    user_roles = set(frappe.get_roles(user))

    assignment_name = _resolve_review_assignment_name(user=user, assignment=assignment, focus_item_id=focus_item_id)
    target_user = (reassign_to_user or "").strip() or None
    if not target_user:
        frappe.throw(_("Reassign To User is required."), frappe.ValidationError)

    lock_target = (focus_item_id or "").strip() or assignment_name
    client_request_id = (client_request_id or "").strip() or None

    cache = _cache()
    if client_request_id:
        key = _idempotency_key(user, lock_target, client_request_id, "applicant_review_assignment_reassign")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "assignment": assignment_name,
                "assigned_to_user": existing,
            }

    with cache.lock(_lock_key(user, lock_target, "applicant_review_assignment_reassign"), timeout=10):
        if client_request_id:
            key = _idempotency_key(user, lock_target, client_request_id, "applicant_review_assignment_reassign")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "assignment": assignment_name,
                    "assigned_to_user": existing,
                }

        assignment_doc = frappe.get_doc(APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE, assignment_name)
        if (assignment_doc.status or "").strip() != "Open":
            frappe.throw(_("This review assignment is not open."), frappe.ValidationError)

        assigned_to_role = (assignment_doc.assigned_to_role or "").strip()
        if not assigned_to_role:
            frappe.throw(
                _("Only role-queue assignments can be reassigned from this action."),
                frappe.ValidationError,
            )
        if assigned_to_role not in user_roles:
            frappe.throw(_("You are not assigned to this review item."), frappe.PermissionError)

        if not frappe.db.exists("User", {"name": target_user, "enabled": 1}):
            frappe.throw(_("Reassign To User must be an enabled user."), frappe.ValidationError)
        if not frappe.db.exists("Has Role", {"parent": target_user, "role": assigned_to_role}):
            frappe.throw(_("Reassign To User must have role {0}.").format(assigned_to_role), frappe.ValidationError)

        assignment_doc.assigned_to_user = target_user
        assignment_doc.assigned_to_role = None
        assignment_doc.save(ignore_permissions=True)

        if client_request_id:
            cache.set_value(key, target_user, expires_in_sec=60 * 10)

        frappe.publish_realtime(
            event="focus:invalidate",
            message={
                "assignment": assignment_doc.name,
                "target_type": assignment_doc.target_type,
                "target_name": assignment_doc.target_name,
                "reassigned_by": user,
                "reassigned_to": target_user,
                "reassigned_on": str(now_datetime()),
            },
            user=user,
        )

        return {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "assignment": assignment_doc.name,
            "assigned_to_user": target_user,
        }


def submit_applicant_review_assignment(
    assignment: str | None = None,
    decision: str | None = None,
    notes: str | None = None,
    focus_item_id: str | None = None,
    client_request_id: str | None = None,
):
    user = _require_login()
    user_roles = set(frappe.get_roles(user))

    decision = (decision or "").strip()
    notes = (notes or "").strip() or None
    assignment_name = _resolve_review_assignment_name(user=user, assignment=assignment, focus_item_id=focus_item_id)
    focus_item_id = (focus_item_id or "").strip() or None
    client_request_id = (client_request_id or "").strip() or None
    if not decision:
        frappe.throw(_("Decision is required."))

    cache = _cache()
    lock_target = focus_item_id or assignment_name

    if client_request_id:
        key = _idempotency_key(user, lock_target, client_request_id, "applicant_review_assignment_submit")
        existing = cache.get_value(key)
        if existing:
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "assignment": assignment_name,
                "decision": existing,
            }

    lock_name = _lock_key(user, lock_target, "applicant_review_assignment_submit")
    with cache.lock(lock_name, timeout=10):
        if client_request_id:
            key = _idempotency_key(user, lock_target, client_request_id, "applicant_review_assignment_submit")
            existing = cache.get_value(key)
            if existing:
                return {
                    "ok": True,
                    "idempotent": True,
                    "status": "already_processed",
                    "assignment": assignment_name,
                    "decision": existing,
                }

        assignment_doc = frappe.get_doc(APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE, assignment_name)
        if not _reviewer_matches_assignment(assignment_doc.as_dict(), user=user, roles=user_roles):
            frappe.throw(_("You are not assigned to this review item."), frappe.PermissionError)

        if (assignment_doc.status or "").strip() == "Done":
            return {
                "ok": True,
                "idempotent": True,
                "status": "already_processed",
                "assignment": assignment_doc.name,
                "decision": assignment_doc.decision,
            }

        if (assignment_doc.status or "").strip() != "Open":
            frappe.throw(_("This review assignment is not open."), frappe.ValidationError)

        complete_assignment_decision(
            assignment_doc=assignment_doc,
            decision=decision,
            notes=notes,
            decided_by=user,
        )

        if client_request_id:
            cache.set_value(key, decision, expires_in_sec=60 * 10)

        frappe.publish_realtime(
            event="focus:invalidate",
            message={
                "assignment": assignment_doc.name,
                "target_type": assignment_doc.target_type,
                "target_name": assignment_doc.target_name,
                "decided_by": user,
                "decided_on": str(now_datetime()),
            },
            user=user,
        )

        return {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "assignment": assignment_doc.name,
            "target_type": assignment_doc.target_type,
            "target_name": assignment_doc.target_name,
            "decision": decision,
        }
