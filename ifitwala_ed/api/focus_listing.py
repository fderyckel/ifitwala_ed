# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus_listing.py

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import is_admissions_workspace_user
from ifitwala_ed.admission.applicant_review_workflow import TARGET_DOCUMENT_ITEM
from ifitwala_ed.api.focus_shared import (
    ACTION_APPLICANT_INTERVIEW_FEEDBACK_SUBMIT,
    ACTION_APPLICANT_REVIEW_SUBMIT,
    ACTION_EXPENSE_CLAIM_APPROVE,
    ACTION_EXPENSE_CLAIM_FINANCE,
    ACTION_EXPENSE_CLAIM_UPDATE,
    ACTION_INQUIRY_FIRST_CONTACT,
    ACTION_POLICY_STAFF_SIGN,
    ACTION_STUDENT_LOG_REVIEW,
    ACTION_STUDENT_LOG_SUBMIT,
    APPLICANT_INTERVIEW_DOCTYPE,
    APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
    EXPENSE_CLAIM_DOCTYPE,
    INQUIRY_DOCTYPE,
    POLICY_VERSION_DOCTYPE,
    STUDENT_LOG_DOCTYPE,
    _active_employee_row,
    _applicant_display_name_from_row,
    _assignment_subtitle,
    _assignment_title,
    _badge_from_due_date,
    _can_read_expense_claim,
    _can_read_inquiry,
    _can_read_student_log,
    _get_user_full_names,
    _normalize_roles,
    build_focus_item_id,
)
from ifitwala_ed.api.policy_signature import (
    parse_employee_from_todo_description,
    validate_staff_policy_scope_for_employee,
)
from ifitwala_ed.governance.policy_utils import policy_applies_to_filter_sql


def list_focus_items(open_only: int = 1, limit: int = 20, offset: int = 0):
    """
    Return FocusItem[] for the current user.

    V1: workflow-owned focus items projected from Student Log, Inquiry, admissions, policy, and Expense Claim.
    - "action" items: ToDo allocated to user for Student Log follow-up work
    - "review" items: log owner, submitted follow-up exists, no active follow-up ToDo, log not completed

    Performance:
    - No N+1 doc loads
    - Batched queries
    - Uses ToDo for assignee visibility (single-open ToDo policy)
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    # ----------------------------
    # 1) Validate/coerce args ONLY
    # ----------------------------
    open_only = frappe.utils.cint(open_only)

    limit = frappe.utils.cint(limit) or 20
    offset = frappe.utils.cint(offset) or 0

    limit = min(max(limit, 1), 50)
    offset = max(offset, 0)

    items: list[dict] = []

    # ------------------------------------------------------------
    # A) Assignee action items (ToDo -> Student Log)
    # ------------------------------------------------------------
    # IMPORTANT:
    # - "Assigned by" must be the person who created/assigned the ToDo.
    #   In Frappe, this is ToDo.assigned_by (with assigned_by_full_name).
    # - We keep a fallback to ToDo.owner for older rows/edge-cases.
    action_rows = frappe.db.sql(
        """
        select
            t.reference_name as log_name,
            t.date as todo_due_date,

            -- canonical assigner identity (can differ from Student Log.owner)
            nullif(trim(ifnull(t.assigned_by, '')), '') as todo_assigned_by,
            nullif(trim(ifnull(t.assigned_by_full_name, '')), '') as todo_assigned_by_full_name,

            -- fallback (older ToDo rows)
            nullif(trim(ifnull(t.owner, '')), '') as todo_owner,

            s.student_name,
            s.next_step,
            s.requires_follow_up,
            s.follow_up_status,
            s.follow_up_person
        from `tabToDo` t
        join `tabStudent Log` s
          on s.name = t.reference_name
        where t.allocated_to = %(user)s
          and t.reference_type = %(ref_type)s
          and (%(open_only)s = 0 or t.status = 'Open')
          and ifnull(s.requires_follow_up, 0) = 1
          and lower(ifnull(s.follow_up_status, '')) != 'completed'
        order by t.date asc, t.modified desc
        limit %(limit)s offset %(offset)s
        """,
        {
            "user": user,
            "ref_type": STUDENT_LOG_DOCTYPE,
            "open_only": open_only,
            "limit": limit,
            "offset": offset,
        },
        as_dict=True,
    )

    # Resolve next-step titles in one batch (optional enrichment)
    next_step_names = sorted({r.get("next_step") for r in action_rows if r.get("next_step")})
    next_step_title_by_name = {}
    if next_step_names:
        ns = frappe.get_all(
            "Student Log Next Step",
            filters={"name": ["in", next_step_names]},
            fields=["name", "next_step"],
            limit=1000,
            ignore_permissions=True,
        )
        next_step_title_by_name = {x["name"]: x.get("next_step") for x in ns}

    # Resolve assigner display names in one batch (only for rows where ToDo didn't already carry full name)
    # We may have:
    # - todo_assigned_by_full_name already (prefer it)
    # - else resolve user.full_name via SQL
    assigner_ids_to_resolve: set[str] = set()
    for r in action_rows:
        if r.get("todo_assigned_by_full_name"):
            continue
        assigner = r.get("todo_assigned_by") or r.get("todo_owner")
        if assigner:
            assigner_ids_to_resolve.add(assigner)

    assigner_name_by_id = _get_user_full_names(sorted(assigner_ids_to_resolve))

    for r in action_rows:
        log_name = r.get("log_name")
        if not log_name:
            continue

        # Hard permission gate (doc-level)
        if not _can_read_student_log(log_name):
            continue

        due = str(r.get("todo_due_date")) if r.get("todo_due_date") else None
        badge = _badge_from_due_date(due)

        next_step_title = None
        if r.get("next_step"):
            next_step_title = next_step_title_by_name.get(r.get("next_step"))

        title = "Follow up"
        subtitle = f"{r.get('student_name') or log_name}"
        if next_step_title:
            subtitle = f"{subtitle} • Next step: {next_step_title}"

        # Assigned-by (ToDo assigner) — keep in payload always.
        # Prefer ToDo.assigned_by; fallback to ToDo.owner if missing.
        assigned_by = (r.get("todo_assigned_by") or r.get("todo_owner") or "").strip() or None

        # Prefer ToDo.assigned_by_full_name if present, else resolve via SQL.
        assigned_by_name = (r.get("todo_assigned_by_full_name") or "").strip() or None
        if not assigned_by_name and assigned_by:
            assigned_by_name = assigner_name_by_id.get(assigned_by) or assigned_by

        action_type = ACTION_STUDENT_LOG_SUBMIT
        items.append(
            {
                "id": build_focus_item_id("student_log", STUDENT_LOG_DOCTYPE, log_name, action_type, user),
                "kind": "action",
                "title": title,
                "subtitle": subtitle,
                "badge": badge,
                "priority": 80,
                "due_date": due,
                "action_type": action_type,
                "reference_doctype": STUDENT_LOG_DOCTYPE,
                "reference_name": log_name,
                "payload": {
                    "student_name": r.get("student_name"),
                    "next_step": r.get("next_step"),
                    "assigned_by": assigned_by,
                    "assigned_by_name": assigned_by_name,
                },
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # B) Assignee action items (ToDo -> Inquiry)
    # ------------------------------------------------------------
    inquiry_rows = frappe.db.sql(
        """
        select
            t.reference_name as inquiry_name,
            t.date as todo_due_date,

            nullif(trim(ifnull(t.assigned_by, '')), '') as todo_assigned_by,
            nullif(trim(ifnull(t.assigned_by_full_name, '')), '') as todo_assigned_by_full_name,
            nullif(trim(ifnull(t.owner, '')), '') as todo_owner,

            i.first_name,
            i.last_name,
            i.school,
            i.organization,
            i.source,
            i.next_action_note,
            i.workflow_state,
            i.assigned_to,
            i.followup_due_on
        from `tabToDo` t
        join `tabInquiry` i
          on i.name = t.reference_name
        where t.allocated_to = %(user)s
          and t.reference_type = %(ref_type)s
          and (%(open_only)s = 0 or t.status = 'Open')
          and ifnull(i.assigned_to, '') = %(user)s
          and ifnull(i.workflow_state, '') = 'Assigned'
        order by ifnull(i.followup_due_on, t.date) asc, t.modified desc
        limit %(limit)s offset %(offset)s
        """,
        {
            "user": user,
            "ref_type": INQUIRY_DOCTYPE,
            "open_only": open_only,
            "limit": limit,
            "offset": offset,
        },
        as_dict=True,
    )

    inquiry_assigner_ids_to_resolve: set[str] = set()
    for r in inquiry_rows:
        if r.get("todo_assigned_by_full_name"):
            continue
        assigner = r.get("todo_assigned_by") or r.get("todo_owner")
        if assigner:
            inquiry_assigner_ids_to_resolve.add(assigner)

    inquiry_assigner_name_by_id = _get_user_full_names(sorted(inquiry_assigner_ids_to_resolve))

    for r in inquiry_rows:
        inquiry_name = r.get("inquiry_name")
        if not inquiry_name:
            continue

        if not _can_read_inquiry(inquiry_name):
            continue

        due_source = r.get("followup_due_on") or r.get("todo_due_date")
        due = str(due_source) if due_source else None
        badge = _badge_from_due_date(due)

        subject_name = " ".join(
            filter(
                None,
                [
                    (r.get("first_name") or "").strip(),
                    (r.get("last_name") or "").strip(),
                ],
            )
        )
        subject_name = subject_name or inquiry_name

        subtitle_parts = [subject_name]
        if r.get("school"):
            subtitle_parts.append(f"School: {r.get('school')}")
        elif r.get("organization"):
            subtitle_parts.append(f"Org: {r.get('organization')}")
        if r.get("source"):
            subtitle_parts.append(f"Source: {r.get('source')}")
        subtitle = " • ".join(subtitle_parts)

        assigned_by = (r.get("todo_assigned_by") or r.get("todo_owner") or "").strip() or None
        assigned_by_name = (r.get("todo_assigned_by_full_name") or "").strip() or None
        if not assigned_by_name and assigned_by:
            assigned_by_name = inquiry_assigner_name_by_id.get(assigned_by) or assigned_by

        action_type = ACTION_INQUIRY_FIRST_CONTACT
        items.append(
            {
                "id": build_focus_item_id("inquiry", INQUIRY_DOCTYPE, inquiry_name, action_type, user),
                "kind": "action",
                "title": "First contact",
                "subtitle": subtitle,
                "badge": badge,
                "priority": 75,
                "due_date": due,
                "action_type": action_type,
                "reference_doctype": INQUIRY_DOCTYPE,
                "reference_name": inquiry_name,
                "payload": {
                    "subject_name": subject_name,
                    "assigned_by": assigned_by,
                    "assigned_by_name": assigned_by_name,
                    "school": r.get("school"),
                    "organization": r.get("organization"),
                    "source": r.get("source"),
                    "next_action_note": r.get("next_action_note"),
                },
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # C) Assignee action items (ToDo -> Expense Claim)
    # ------------------------------------------------------------
    expense_rows = frappe.db.sql(
        """
        select
            t.reference_name as claim_name,
            t.date as todo_due_date,
            nullif(trim(ifnull(t.assigned_by, '')), '') as todo_assigned_by,
            nullif(trim(ifnull(t.assigned_by_full_name, '')), '') as todo_assigned_by_full_name,
            nullif(trim(ifnull(t.owner, '')), '') as todo_owner,
            e.employee_name,
            e.claim_title,
            e.claim_date,
            e.status,
            e.claimed_total,
            e.sanctioned_total,
            e.outstanding_amount,
            e.decision_notes
        from `tabToDo` t
        join `tabExpense Claim` e
          on e.name = t.reference_name
        where t.allocated_to = %(user)s
          and t.reference_type = %(ref_type)s
          and (%(open_only)s = 0 or t.status = 'Open')
          and e.status in ('Submitted', 'Needs Info', 'Approved', 'Payable Posted')
        order by ifnull(t.date, '9999-12-31') asc, t.modified desc
        limit %(limit)s offset %(offset)s
        """,
        {
            "user": user,
            "ref_type": EXPENSE_CLAIM_DOCTYPE,
            "open_only": open_only,
            "limit": limit,
            "offset": offset,
        },
        as_dict=True,
    )

    expense_assigner_ids: set[str] = set()
    for row in expense_rows:
        if row.get("todo_assigned_by_full_name"):
            continue
        assigner = row.get("todo_assigned_by") or row.get("todo_owner")
        if assigner:
            expense_assigner_ids.add(assigner)
    expense_assigner_name_by_id = _get_user_full_names(sorted(expense_assigner_ids))

    for row in expense_rows:
        claim_name = (row.get("claim_name") or "").strip()
        if not claim_name:
            continue

        if not _can_read_expense_claim(claim_name):
            continue

        status = (row.get("status") or "").strip()
        if status == "Submitted":
            action_type = ACTION_EXPENSE_CLAIM_APPROVE
            title = "Review expense claim"
            priority = 82
        elif status == "Needs Info":
            action_type = ACTION_EXPENSE_CLAIM_UPDATE
            title = "Update expense claim"
            priority = 84
        else:
            action_type = ACTION_EXPENSE_CLAIM_FINANCE
            title = "Process reimbursement"
            priority = 80

        due = str(row.get("todo_due_date")) if row.get("todo_due_date") else None
        assigned_by = (row.get("todo_assigned_by") or row.get("todo_owner") or "").strip() or None
        assigned_by_name = (row.get("todo_assigned_by_full_name") or "").strip() or None
        if not assigned_by_name and assigned_by:
            assigned_by_name = expense_assigner_name_by_id.get(assigned_by) or assigned_by

        subtitle_parts = [
            (row.get("employee_name") or "").strip() or claim_name,
            status,
        ]
        if row.get("claim_title"):
            subtitle_parts.append(row.get("claim_title"))

        items.append(
            {
                "id": build_focus_item_id("expense_claim", EXPENSE_CLAIM_DOCTYPE, claim_name, action_type, user),
                "kind": "action",
                "title": title,
                "subtitle": " • ".join(part for part in subtitle_parts if part),
                "badge": _badge_from_due_date(due),
                "priority": priority,
                "due_date": due,
                "action_type": action_type,
                "reference_doctype": EXPENSE_CLAIM_DOCTYPE,
                "reference_name": claim_name,
                "payload": {
                    "employee_name": row.get("employee_name"),
                    "claim_title": row.get("claim_title"),
                    "claim_date": str(row.get("claim_date")) if row.get("claim_date") else None,
                    "status": status,
                    "claimed_total": row.get("claimed_total"),
                    "sanctioned_total": row.get("sanctioned_total"),
                    "outstanding_amount": row.get("outstanding_amount"),
                    "decision_notes": row.get("decision_notes"),
                    "assigned_by": assigned_by,
                    "assigned_by_name": assigned_by_name,
                },
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # D) Author review items
    # ------------------------------------------------------------
    review_rows = frappe.db.sql(
        """
        select
            s.name as log_name,
            s.student_name
        from `tabStudent Log` s
        where s.owner = %(user)s
          and ifnull(s.requires_follow_up, 0) = 1
          and lower(ifnull(s.follow_up_status, '')) != 'completed'
          and exists (
                select 1
                from `tabStudent Log Follow Up` f
                where f.student_log = s.name
                  and f.docstatus = 1
          )
          and not exists (
                select 1
                from `tabToDo` t
                where t.reference_type = %(ref_type)s
                  and t.reference_name = s.name
                  and t.status = 'Open'
          )
        order by s.modified desc
        limit 200
        """,
        {"user": user, "ref_type": STUDENT_LOG_DOCTYPE},
        as_dict=True,
    )

    for r in review_rows:
        log_name = r.get("log_name")
        if not log_name:
            continue

        if not _can_read_student_log(log_name):
            continue

        action_type = ACTION_STUDENT_LOG_REVIEW
        items.append(
            {
                "id": build_focus_item_id("student_log", STUDENT_LOG_DOCTYPE, log_name, action_type, user),
                "kind": "review",
                "title": "Review outcome",
                "subtitle": f"{r.get('student_name') or log_name} • Decide: close or continue follow-up",
                "badge": None,
                "priority": 70,
                "due_date": None,
                "action_type": action_type,
                "reference_doctype": STUDENT_LOG_DOCTYPE,
                "reference_name": log_name,
                "payload": {"student_name": r.get("student_name")},
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # D) Admissions applicant review assignments
    # ------------------------------------------------------------
    user_roles = _normalize_roles(frappe.get_roles(user))
    admissions_workspace_user = is_admissions_workspace_user(user)

    # Build role placeholders for IN clause (frappe.db.sql doesn't expand tuples)
    roles_params = tuple(user_roles) or ("",)
    role_placeholders = ", ".join(["%s"] * len(roles_params))

    assignment_rows = frappe.db.sql(
        f"""
        select
            a.name,
            a.target_type,
            a.target_name,
            a.student_applicant,
            a.assigned_to_user,
            a.assigned_to_role,
            a.modified,
            sa.first_name,
            sa.middle_name,
            sa.last_name,
            sa.school,
            sa.program_offering,
            ad_item.document_type,
            ad_item.document_label,
            adt.document_type_name,
            adt.code as document_type_code,
            adi.item_key,
            adi.item_label
        from `tabApplicant Review Assignment` a
        join `tabStudent Applicant` sa
          on sa.name = a.student_applicant
        left join `tabApplicant Document Item` adi
          on a.target_type = 'Applicant Document Item'
         and adi.name = a.target_name
        left join `tabApplicant Document` ad_item
          on ad_item.name = adi.applicant_document
        left join `tabApplicant Document Type` adt
          on adt.name = ad_item.document_type
        where (%s = 0 or a.status = 'Open')
          and (
                a.assigned_to_user = %s
             or (
                    ifnull(a.assigned_to_role, '') != ''
                and a.assigned_to_role in ({role_placeholders})
             )
          )
        order by a.modified desc
        limit %s offset %s
        """,
        (open_only, user, *roles_params, limit, offset),
        as_dict=True,
    )

    for row in assignment_rows:
        if admissions_workspace_user and (row.get("target_type") or "").strip() == TARGET_DOCUMENT_ITEM:
            continue
        items.append(
            {
                "id": build_focus_item_id(
                    "applicant_review",
                    APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
                    row.get("name"),
                    ACTION_APPLICANT_REVIEW_SUBMIT,
                    user,
                ),
                "kind": "action",
                "title": _assignment_title(row),
                "subtitle": _assignment_subtitle(row),
                "badge": None,
                "priority": 90,
                "due_date": None,
                "action_type": ACTION_APPLICANT_REVIEW_SUBMIT,
                "reference_doctype": APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
                "reference_name": row.get("name"),
                "payload": {
                    "applicant_name": _applicant_display_name_from_row(row),
                    "student_applicant": row.get("student_applicant"),
                    "target_type": row.get("target_type"),
                    "target_name": row.get("target_name"),
                },
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # E) Admissions interview feedback action items
    # ------------------------------------------------------------
    interview_rows = frappe.db.sql(
        """
        select
            ai.name as interview_name,
            ai.student_applicant,
            ai.interview_type,
            ai.mode,
            ai.interview_date,
            ai.interview_start,
            ai.interview_end,
            ai.school_event,
            sa.first_name,
            sa.middle_name,
            sa.last_name,
            sa.school,
            sa.program_offering,
            feedback.name as feedback_name,
            feedback.feedback_status,
            feedback.submitted_on
        from `tabApplicant Interview` ai
        join `tabApplicant Interviewer` interviewer
          on interviewer.parent = ai.name
         and interviewer.parenttype = 'Applicant Interview'
         and interviewer.parentfield = 'interviewers'
         and interviewer.interviewer = %(user)s
        join `tabStudent Applicant` sa
          on sa.name = ai.student_applicant
        left join `tabApplicant Interview Feedback` feedback
          on feedback.applicant_interview = ai.name
         and feedback.interviewer_user = %(user)s
        where ai.docstatus < 2
          and (%(open_only)s = 0 or ifnull(feedback.feedback_status, 'Draft') != 'Submitted')
        order by
            case when ai.interview_start is null then 1 else 0 end asc,
            ai.interview_start asc,
            ai.interview_date asc,
            ai.modified desc
        limit %(limit)s offset %(offset)s
        """,
        {
            "user": user,
            "open_only": open_only,
            "limit": limit,
            "offset": offset,
        },
        as_dict=True,
    )

    for row in interview_rows:
        interview_name = (row.get("interview_name") or "").strip()
        if not interview_name:
            continue

        applicant_name = _applicant_display_name_from_row(row)
        due_source = row.get("interview_start") or row.get("interview_date")
        due = str(frappe.utils.getdate(due_source)) if due_source else None
        scheduled_label = None
        if row.get("interview_start"):
            scheduled_label = frappe.utils.format_datetime(row.get("interview_start"))
        elif row.get("interview_date"):
            scheduled_label = str(row.get("interview_date"))
        badge = _badge_from_due_date(due)
        subtitle_parts = [applicant_name]
        if scheduled_label:
            subtitle_parts.append(scheduled_label)
        if row.get("school"):
            subtitle_parts.append(row.get("school"))

        items.append(
            {
                "id": build_focus_item_id(
                    "applicant_interview",
                    APPLICANT_INTERVIEW_DOCTYPE,
                    interview_name,
                    ACTION_APPLICANT_INTERVIEW_FEEDBACK_SUBMIT,
                    user,
                ),
                "kind": "action",
                "title": "Interview feedback",
                "subtitle": " • ".join(part for part in subtitle_parts if part),
                "badge": badge,
                "priority": 88,
                "due_date": due,
                "action_type": ACTION_APPLICANT_INTERVIEW_FEEDBACK_SUBMIT,
                "reference_doctype": APPLICANT_INTERVIEW_DOCTYPE,
                "reference_name": interview_name,
                "payload": {
                    "applicant_name": applicant_name,
                    "student_applicant": row.get("student_applicant"),
                    "school": row.get("school"),
                    "program_offering": row.get("program_offering"),
                    "interview_type": row.get("interview_type"),
                    "mode": row.get("mode"),
                    "interview_date": str(row.get("interview_date")) if row.get("interview_date") else None,
                    "interview_start": str(row.get("interview_start")) if row.get("interview_start") else None,
                    "interview_end": str(row.get("interview_end")) if row.get("interview_end") else None,
                    "school_event": row.get("school_event"),
                    "feedback_name": row.get("feedback_name"),
                    "feedback_status": row.get("feedback_status") or "Pending",
                    "submitted_on": str(row.get("submitted_on")) if row.get("submitted_on") else None,
                },
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # F) Staff policy signature action items (ToDo -> Policy Version)
    # ------------------------------------------------------------
    active_employee = _active_employee_row(user)
    if active_employee:
        policy_rows = frappe.db.sql(
            f"""
            select
                t.reference_name as policy_version,
                t.date as todo_due_date,
                nullif(trim(ifnull(t.assigned_by, '')), '') as todo_assigned_by,
                nullif(trim(ifnull(t.assigned_by_full_name, '')), '') as todo_assigned_by_full_name,
                nullif(trim(ifnull(t.owner, '')), '') as todo_owner,
                ifnull(t.description, '') as todo_description,
                ip.policy_key,
                ip.policy_title,
                ip.organization as policy_organization,
                ip.school as policy_school,
                pv.version_label
            from `tabToDo` t
            join `tabPolicy Version` pv
              on pv.name = t.reference_name
            join `tabInstitutional Policy` ip
              on ip.name = pv.institutional_policy
            where t.allocated_to = %(user)s
              and t.reference_type = %(ref_type)s
              and (%(open_only)s = 0 or t.status = 'Open')
              and pv.is_active = 1
              and ip.is_active = 1
              and {policy_applies_to_filter_sql(policy_alias="ip", audience_placeholder="%(applies_to)s")}
            order by ifnull(t.date, '9999-12-31') asc, t.modified desc
            limit %(limit)s offset %(offset)s
            """,
            {
                "user": user,
                "ref_type": POLICY_VERSION_DOCTYPE,
                "open_only": open_only,
                "limit": limit,
                "offset": offset,
                "applies_to": "Staff",
            },
            as_dict=True,
        )

        policy_assigner_ids: set[str] = set()
        for row in policy_rows:
            if row.get("todo_assigned_by_full_name"):
                continue
            assigner = row.get("todo_assigned_by") or row.get("todo_owner")
            if assigner:
                policy_assigner_ids.add(assigner)
        policy_assigner_name_by_id = _get_user_full_names(sorted(policy_assigner_ids))

        for row in policy_rows:
            policy_version = (row.get("policy_version") or "").strip()
            if not policy_version:
                continue

            employee_name = parse_employee_from_todo_description(row.get("todo_description")) or active_employee.get(
                "name"
            )
            if not employee_name or employee_name != active_employee.get("name"):
                continue

            policy_context = {
                "policy_organization": row.get("policy_organization"),
                "policy_school": row.get("policy_school"),
            }
            try:
                validate_staff_policy_scope_for_employee(policy_context, active_employee)
            except Exception:
                continue

            already_ack = frappe.db.exists(
                "Policy Acknowledgement",
                {
                    "policy_version": policy_version,
                    "acknowledged_for": "Staff",
                    "context_doctype": "Employee",
                    "context_name": active_employee.get("name"),
                },
            )
            if already_ack:
                continue

            due = str(row.get("todo_due_date")) if row.get("todo_due_date") else None
            badge = _badge_from_due_date(due)
            policy_label = (
                (row.get("policy_title") or "").strip() or (row.get("policy_key") or "").strip() or policy_version
            )
            subtitle_parts = [policy_label]
            version_label = (row.get("version_label") or "").strip()
            if version_label:
                subtitle_parts.append(f"Version {version_label}")
            if row.get("policy_school"):
                subtitle_parts.append(f"School: {row.get('policy_school')}")
            subtitle = " • ".join(subtitle_parts)

            assigned_by = (row.get("todo_assigned_by") or row.get("todo_owner") or "").strip() or None
            assigned_by_name = (row.get("todo_assigned_by_full_name") or "").strip() or None
            if not assigned_by_name and assigned_by:
                assigned_by_name = policy_assigner_name_by_id.get(assigned_by) or assigned_by

            items.append(
                {
                    "id": build_focus_item_id(
                        "policy_ack",
                        POLICY_VERSION_DOCTYPE,
                        policy_version,
                        ACTION_POLICY_STAFF_SIGN,
                        user,
                    ),
                    "kind": "action",
                    "title": "Acknowledge policy",
                    "subtitle": subtitle,
                    "badge": badge,
                    "priority": 85,
                    "due_date": due,
                    "action_type": ACTION_POLICY_STAFF_SIGN,
                    "reference_doctype": POLICY_VERSION_DOCTYPE,
                    "reference_name": policy_version,
                    "payload": {
                        "policy_title": row.get("policy_title"),
                        "policy_key": row.get("policy_key"),
                        "version_label": row.get("version_label"),
                        "policy_organization": row.get("policy_organization"),
                        "policy_school": row.get("policy_school"),
                        "employee": active_employee.get("name"),
                        "employee_group": active_employee.get("employee_group"),
                        "assigned_by": assigned_by,
                        "assigned_by_name": assigned_by_name,
                    },
                    "permissions": {"can_open": True},
                }
            )

    # ------------------------------------------------------------
    # Sort + slice
    # ------------------------------------------------------------
    def _sort_key(x):
        kind_rank = 0 if x.get("kind") == "action" else 1
        pr = x.get("priority") or 0
        due = x.get("due_date") or "9999-12-31"
        return (kind_rank, -pr, due)

    items.sort(key=_sort_key)
    return items[:limit]
