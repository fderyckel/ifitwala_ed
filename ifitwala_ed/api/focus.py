# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus.py

import frappe

from ifitwala_ed.api.focus_actions_applicant_review import (
    claim_applicant_review_assignment as _claim_applicant_review_assignment,
)
from ifitwala_ed.api.focus_actions_applicant_review import (
    reassign_applicant_review_assignment as _reassign_applicant_review_assignment,
)
from ifitwala_ed.api.focus_actions_applicant_review import (
    submit_applicant_review_assignment as _submit_applicant_review_assignment,
)
from ifitwala_ed.api.focus_actions_inquiry import mark_inquiry_contacted as _mark_inquiry_contacted
from ifitwala_ed.api.focus_actions_policy import acknowledge_staff_policy as _acknowledge_staff_policy
from ifitwala_ed.api.focus_actions_student_log import review_student_log_outcome as _review_student_log_outcome
from ifitwala_ed.api.focus_actions_student_log import submit_student_log_follow_up as _submit_student_log_follow_up
from ifitwala_ed.api.focus_context import get_focus_context as _get_focus_context
from ifitwala_ed.api.focus_listing import list_focus_items as _list_focus_items


@frappe.whitelist()
def list_focus_items(open_only: int = 1, limit: int = 20, offset: int = 0):
    return _list_focus_items(open_only=open_only, limit=limit, offset=offset)


@frappe.whitelist()
def get_focus_context(
    focus_item_id: str | None = None,
    reference_doctype: str | None = None,
    reference_name: str | None = None,
    action_type: str | None = None,
):
    return _get_focus_context(
        focus_item_id=focus_item_id,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
        action_type=action_type,
    )


@frappe.whitelist()
def submit_student_log_follow_up(
    focus_item_id: str,
    follow_up: str,
    client_request_id: str | None = None,
):
    return _submit_student_log_follow_up(
        focus_item_id=focus_item_id,
        follow_up=follow_up,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def review_student_log_outcome(
    focus_item_id: str,
    decision: str,
    follow_up_person: str | None = None,
    client_request_id: str | None = None,
):
    return _review_student_log_outcome(
        focus_item_id=focus_item_id,
        decision=decision,
        follow_up_person=follow_up_person,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def mark_inquiry_contacted(
    focus_item_id: str,
    complete_todo: int = 1,
    client_request_id: str | None = None,
):
    return _mark_inquiry_contacted(
        focus_item_id=focus_item_id,
        complete_todo=complete_todo,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def acknowledge_staff_policy(
    focus_item_id: str,
    client_request_id: str | None = None,
    typed_signature_name: str | None = None,
    attestation_confirmed: int | str | bool | None = None,
):
    return _acknowledge_staff_policy(
        focus_item_id=focus_item_id,
        client_request_id=client_request_id,
        typed_signature_name=typed_signature_name,
        attestation_confirmed=attestation_confirmed,
    )


@frappe.whitelist()
def claim_applicant_review_assignment(
    assignment: str | None = None,
    focus_item_id: str | None = None,
    client_request_id: str | None = None,
):
    return _claim_applicant_review_assignment(
        assignment=assignment,
        focus_item_id=focus_item_id,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def reassign_applicant_review_assignment(
    assignment: str | None = None,
    reassign_to_user: str | None = None,
    focus_item_id: str | None = None,
    client_request_id: str | None = None,
):
    return _reassign_applicant_review_assignment(
        assignment=assignment,
        reassign_to_user=reassign_to_user,
        focus_item_id=focus_item_id,
        client_request_id=client_request_id,
    )


@frappe.whitelist()
def submit_applicant_review_assignment(
    assignment: str | None = None,
    decision: str | None = None,
    notes: str | None = None,
    focus_item_id: str | None = None,
    client_request_id: str | None = None,
):
    return _submit_applicant_review_assignment(
        assignment=assignment,
        decision=decision,
        notes=notes,
        focus_item_id=focus_item_id,
        client_request_id=client_request_id,
    )
