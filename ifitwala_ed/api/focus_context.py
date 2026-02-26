# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus_context.py

import frappe
from frappe import _

from ifitwala_ed.admission.applicant_review_workflow import (
    DECISION_OPTIONS_BY_TARGET,
    TARGET_APPLICATION,
    TARGET_DOCUMENT,
    TARGET_HEALTH,
)
from ifitwala_ed.api.focus_shared import (
    ACTION_POLICY_STAFF_SIGN,
    APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
    FOLLOW_UP_DOCTYPE,
    INQUIRY_DOCTYPE,
    POLICY_VERSION_DOCTYPE,
    STUDENT_LOG_DOCTYPE,
    _active_employee_row,
    _applicant_display_name_from_row,
    _enabled_users_for_role,
    _get_user_full_names,
    _parse_focus_item_id,
    _resolve_mode,
    _reviewer_matches_assignment,
)
from ifitwala_ed.api.policy_signature import (
    find_open_staff_policy_todos,
    get_policy_version_context,
    parse_employee_from_todo_description,
    validate_staff_policy_scope_for_employee,
)


def get_focus_context(
    focus_item_id: str | None = None,
    reference_doctype: str | None = None,
    reference_name: str | None = None,
    action_type: str | None = None,
):
    """
    Resolve routing + workflow context for a single Focus item.

    Accepted inputs:
    - focus_item_id (preferred, deterministic, user-bound)
    - OR reference_doctype + reference_name (+ optional action_type)

    SECURITY INVARIANTS:
    - focus_item_id, if provided, must belong to frappe.session.user
    - Doc-level read permission is always enforced
    """
    # ------------------------------------------------------------
    # 1) Resolve reference from focus_item_id (authoritative path)
    # ------------------------------------------------------------
    if focus_item_id:
        parsed = _parse_focus_item_id(focus_item_id)

        reference_doctype = parsed["reference_doctype"]
        reference_name = parsed["reference_name"]
        action_type = parsed["action_type"]

        # Hard guard: focus item must belong to current user
        if parsed.get("user") != frappe.session.user:
            frappe.throw(_("Invalid focus item id (user mismatch)."), frappe.PermissionError)

    # ------------------------------------------------------------
    # 2) Validate reference
    # ------------------------------------------------------------
    if not reference_doctype or not reference_name:
        frappe.throw(_("Missing reference information."), frappe.ValidationError)

    if reference_doctype == STUDENT_LOG_DOCTYPE:
        # ------------------------------------------------------------
        # 3) Load document ONCE (permission + payload)
        # ------------------------------------------------------------
        log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, reference_name)

        # ------------------------------------------------------------
        # 4) Enforce doc-level permission (authoritative)
        # ------------------------------------------------------------
        if not frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", doc=log_doc):
            frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

        # ------------------------------------------------------------
        # 5) Resolve workflow mode (author vs assignee)
        # ------------------------------------------------------------
        mode = _resolve_mode(action_type, STUDENT_LOG_DOCTYPE, log_doc)

        # ------------------------------------------------------------
        # 5b) Resolve original log author (Student Log.owner) name
        # ------------------------------------------------------------
        log_author = (log_doc.owner or "").strip() or None
        log_author_name_by_id = _get_user_full_names([log_author] if log_author else [])

        # ------------------------------------------------------------
        # 6) Fetch recent follow-ups (bounded)
        # ------------------------------------------------------------
        follow_up_rows = frappe.get_all(
            FOLLOW_UP_DOCTYPE,
            filters={"student_log": reference_name},
            fields=["name", "date", "follow_up_author", "follow_up", "docstatus"],
            order_by="modified desc",
            limit_page_length=20,
        )

        follow_ups = [
            {
                "name": row.get("name"),
                "date": str(row.get("date")) if row.get("date") else None,
                "follow_up_author": row.get("follow_up_author"),
                "follow_up_html": row.get("follow_up") or "",
                "docstatus": row.get("docstatus"),
            }
            for row in follow_up_rows
        ]

        return {
            "focus_item_id": focus_item_id,
            "action_type": action_type,
            "reference_doctype": STUDENT_LOG_DOCTYPE,
            "reference_name": reference_name,
            "mode": mode,
            "log": {
                "name": log_doc.name,
                "student": log_doc.student,
                "student_name": log_doc.student_name,
                "school": log_doc.school,
                "log_type": log_doc.log_type,
                "next_step": log_doc.next_step,
                "follow_up_person": log_doc.follow_up_person,
                "follow_up_role": log_doc.follow_up_role,
                "date": str(log_doc.date) if log_doc.date else None,
                "follow_up_status": log_doc.follow_up_status,
                "log_html": log_doc.log or "",
                "log_author": log_author,
                "log_author_name": log_author_name_by_id.get(log_author) if log_author else None,
            },
            "inquiry": None,
            "follow_ups": follow_ups,
        }

    if reference_doctype == INQUIRY_DOCTYPE:
        inquiry_doc = frappe.get_doc(INQUIRY_DOCTYPE, reference_name)

        if not frappe.has_permission(INQUIRY_DOCTYPE, ptype="read", doc=inquiry_doc):
            frappe.throw(_("You are not permitted to view this inquiry."), frappe.PermissionError)

        mode = _resolve_mode(action_type, INQUIRY_DOCTYPE, inquiry_doc)
        subject_name = " ".join(
            filter(
                None,
                [
                    (inquiry_doc.first_name or "").strip(),
                    (inquiry_doc.last_name or "").strip(),
                ],
            )
        )

        return {
            "focus_item_id": focus_item_id,
            "action_type": action_type,
            "reference_doctype": INQUIRY_DOCTYPE,
            "reference_name": reference_name,
            "mode": mode,
            "log": None,
            "inquiry": {
                "name": inquiry_doc.name,
                "subject_name": subject_name or inquiry_doc.name,
                "first_name": inquiry_doc.first_name,
                "last_name": inquiry_doc.last_name,
                "email": inquiry_doc.email,
                "phone_number": inquiry_doc.phone_number,
                "school": inquiry_doc.school,
                "organization": inquiry_doc.organization,
                "type_of_inquiry": inquiry_doc.type_of_inquiry,
                "workflow_state": inquiry_doc.workflow_state,
                "assigned_to": inquiry_doc.assigned_to,
                "followup_due_on": str(inquiry_doc.followup_due_on) if inquiry_doc.followup_due_on else None,
                "sla_status": inquiry_doc.sla_status,
            },
            "follow_ups": [],
        }

    if reference_doctype == APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE:
        assignment_doc = frappe.get_doc(APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE, reference_name)
        assignment_row = assignment_doc.as_dict()
        user_roles = set(frappe.get_roles(frappe.session.user))

        if (assignment_doc.status or "").strip() != "Open":
            frappe.throw(_("This review assignment is no longer open."), frappe.ValidationError)

        if not _reviewer_matches_assignment(
            assignment_row,
            user=frappe.session.user,
            roles=user_roles,
        ):
            frappe.throw(_("You are not assigned to this review item."), frappe.PermissionError)

        student_applicant_row = (
            frappe.db.get_value(
                "Student Applicant",
                assignment_doc.student_applicant,
                [
                    "name",
                    "first_name",
                    "middle_name",
                    "last_name",
                    "organization",
                    "school",
                    "program_offering",
                    "application_status",
                ],
                as_dict=True,
            )
            or {}
        )

        preview = {}
        target_type = (assignment_doc.target_type or "").strip()
        if target_type == TARGET_DOCUMENT:
            document_row = frappe.db.sql(
                """
                select
                    d.name,
                    d.document_type,
                    d.document_label,
                    d.review_status,
                    d.review_notes,
                    ifnull(dt.document_type_name, '') as document_type_name,
                    ifnull(dt.code, '') as document_type_code
                from `tabApplicant Document` d
                left join `tabApplicant Document Type` dt
                  on dt.name = d.document_type
                where d.name = %(name)s
                """,
                {"name": assignment_doc.target_name},
                as_dict=True,
            )
            doc_row = document_row[0] if document_row else {}
            file_rows = frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": TARGET_DOCUMENT,
                    "attached_to_name": assignment_doc.target_name,
                },
                fields=["file_url", "file_name", "creation"],
                order_by="creation desc",
                limit_page_length=1,
            )
            file_row = file_rows[0] if file_rows else {}
            preview = {
                "document_type": doc_row.get("document_type"),
                "document_label": (
                    (doc_row.get("document_label") or "").strip()
                    or (doc_row.get("document_type_code") or "").strip()
                    or (doc_row.get("document_type_name") or "").strip()
                    or (doc_row.get("document_type") or "").strip()
                    or assignment_doc.target_name
                ),
                "review_status": doc_row.get("review_status"),
                "review_notes": doc_row.get("review_notes"),
                "file_url": file_row.get("file_url"),
                "file_name": file_row.get("file_name"),
                "uploaded_at": str(file_row.get("creation")) if file_row.get("creation") else None,
            }
        elif target_type == TARGET_HEALTH:
            health_row = (
                frappe.db.get_value(
                    TARGET_HEALTH,
                    assignment_doc.target_name,
                    [
                        "review_status",
                        "review_notes",
                        "applicant_health_declared_complete",
                        "applicant_health_declared_by",
                        "applicant_health_declared_on",
                    ],
                    as_dict=True,
                )
                or {}
            )
            preview = {
                "review_status": health_row.get("review_status"),
                "review_notes": health_row.get("review_notes"),
                "declared_complete": bool(health_row.get("applicant_health_declared_complete")),
                "declared_by": health_row.get("applicant_health_declared_by"),
                "declared_on": str(health_row.get("applicant_health_declared_on"))
                if health_row.get("applicant_health_declared_on")
                else None,
            }
        elif target_type == TARGET_APPLICATION:
            preview = {
                "application_status": student_applicant_row.get("application_status"),
            }

        previous_rows = frappe.get_all(
            APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
            filters={
                "target_type": assignment_doc.target_type,
                "target_name": assignment_doc.target_name,
                "status": "Done",
            },
            fields=["name", "assigned_to_user", "assigned_to_role", "decision", "notes", "decided_by", "decided_on"],
            order_by="decided_on desc, modified desc",
            limit_page_length=10,
        )
        user_name_map = _get_user_full_names(
            [row.get("assigned_to_user") for row in previous_rows if (row.get("assigned_to_user") or "").strip()]
            + [row.get("decided_by") for row in previous_rows if (row.get("decided_by") or "").strip()]
            + ([assignment_doc.assigned_to_user] if (assignment_doc.assigned_to_user or "").strip() else [])
        )
        previous_reviews = []
        for row in previous_rows:
            reviewer_user = (row.get("assigned_to_user") or "").strip()
            reviewer_role = (row.get("assigned_to_role") or "").strip()
            decided_by = (row.get("decided_by") or "").strip()
            previous_reviews.append(
                {
                    "assignment": row.get("name"),
                    "reviewer": reviewer_role or user_name_map.get(reviewer_user) or reviewer_user or None,
                    "decision": row.get("decision"),
                    "notes": row.get("notes"),
                    "decided_by": user_name_map.get(decided_by) or decided_by or None,
                    "decided_on": str(row.get("decided_on")) if row.get("decided_on") else None,
                }
            )

        assigned_to_role = (assignment_doc.assigned_to_role or "").strip()
        can_claim = bool(assigned_to_role and assigned_to_role in user_roles)
        can_reassign = can_claim
        role_candidates = _enabled_users_for_role(assigned_to_role) if can_reassign else []

        return {
            "focus_item_id": focus_item_id,
            "action_type": action_type,
            "reference_doctype": APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
            "reference_name": assignment_doc.name,
            "mode": "assignee",
            "log": None,
            "inquiry": None,
            "follow_ups": [],
            "review_assignment": {
                "name": assignment_doc.name,
                "target_type": assignment_doc.target_type,
                "target_name": assignment_doc.target_name,
                "student_applicant": assignment_doc.student_applicant,
                "applicant_name": _applicant_display_name_from_row(student_applicant_row),
                "organization": student_applicant_row.get("organization"),
                "school": student_applicant_row.get("school"),
                "program_offering": student_applicant_row.get("program_offering"),
                "assigned_to_user": assignment_doc.assigned_to_user,
                "assigned_to_user_name": user_name_map.get(assignment_doc.assigned_to_user)
                or assignment_doc.assigned_to_user,
                "assigned_to_role": assignment_doc.assigned_to_role,
                "can_claim": can_claim,
                "can_reassign": can_reassign,
                "role_candidates": role_candidates,
                "source_event": assignment_doc.source_event,
                "decision_options": DECISION_OPTIONS_BY_TARGET.get(target_type, []),
                "preview": preview,
                "previous_reviews": previous_reviews,
            },
        }

    if reference_doctype == POLICY_VERSION_DOCTYPE:
        if action_type and action_type != ACTION_POLICY_STAFF_SIGN:
            frappe.throw(_("This focus item is not a staff policy acknowledgement action."), frappe.PermissionError)

        policy_row = get_policy_version_context(
            reference_name,
            require_active=False,
            require_staff_applies=True,
        )

        todos = find_open_staff_policy_todos(user=frappe.session.user, policy_version=reference_name)
        if not todos:
            frappe.throw(_("This policy acknowledgement task is no longer open."))

        todo = todos[0]
        employee_name = parse_employee_from_todo_description(todo.get("description"))
        employee = (
            frappe.db.get_value(
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
            if employee_name
            else _active_employee_row(frappe.session.user)
        )
        if not employee:
            frappe.throw(_("No active Employee context could be resolved for this policy task."))

        if (employee.get("user_id") or "").strip() != frappe.session.user:
            frappe.throw(_("You are not assigned to this policy acknowledgement task."), frappe.PermissionError)
        if (employee.get("employment_status") or "").strip() != "Active":
            frappe.throw(_("Only active Employees can acknowledge Staff policies."))

        validate_staff_policy_scope_for_employee(policy_row, employee)

        existing_ack = frappe.db.get_value(
            "Policy Acknowledgement",
            {
                "policy_version": reference_name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": employee.get("name"),
            },
            ["name", "acknowledged_at", "acknowledged_by"],
            as_dict=True,
        )

        policy_label = (
            (policy_row.get("policy_title") or "").strip()
            or (policy_row.get("policy_key") or "").strip()
            or (policy_row.get("institutional_policy") or "").strip()
            or reference_name
        )
        raw_change_stats = policy_row.get("change_stats")
        parsed_change_stats = None
        if isinstance(raw_change_stats, dict):
            parsed_change_stats = raw_change_stats
        elif raw_change_stats:
            try:
                maybe_stats = frappe.parse_json(raw_change_stats)
            except Exception:
                maybe_stats = None
            if isinstance(maybe_stats, dict):
                parsed_change_stats = maybe_stats

        return {
            "focus_item_id": focus_item_id,
            "action_type": action_type or ACTION_POLICY_STAFF_SIGN,
            "reference_doctype": POLICY_VERSION_DOCTYPE,
            "reference_name": reference_name,
            "mode": "assignee",
            "log": None,
            "inquiry": None,
            "follow_ups": [],
            "review_assignment": None,
            "policy_signature": {
                "policy_version": reference_name,
                "institutional_policy": policy_row.get("institutional_policy"),
                "policy_key": policy_row.get("policy_key"),
                "policy_title": policy_row.get("policy_title"),
                "policy_label": policy_label,
                "version_label": policy_row.get("version_label"),
                "amended_from": policy_row.get("amended_from"),
                "change_summary": policy_row.get("change_summary"),
                "diff_html": policy_row.get("diff_html") or "",
                "change_stats": parsed_change_stats,
                "effective_from": str(policy_row.get("effective_from")) if policy_row.get("effective_from") else None,
                "effective_to": str(policy_row.get("effective_to")) if policy_row.get("effective_to") else None,
                "policy_text_html": policy_row.get("policy_text") or "",
                "policy_organization": policy_row.get("policy_organization"),
                "policy_school": policy_row.get("policy_school"),
                "employee": employee.get("name"),
                "employee_name": employee.get("employee_full_name"),
                "employee_group": employee.get("employee_group"),
                "todo_due_date": str(todo.get("date")) if todo.get("date") else None,
                "is_acknowledged": bool(existing_ack),
                "acknowledged_at": existing_ack.get("acknowledged_at") if existing_ack else None,
            },
        }

    frappe.throw(
        _("Only Student Log, Inquiry, Applicant Review Assignment, and Policy Version focus items are supported."),
        frappe.ValidationError,
    )
