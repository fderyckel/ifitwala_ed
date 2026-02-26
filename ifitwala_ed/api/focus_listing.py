# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus_listing.py

import frappe
from frappe import _

from ifitwala_ed.api.focus_shared import (
    ACTION_APPLICANT_REVIEW_SUBMIT,
    ACTION_INQUIRY_FIRST_CONTACT,
    ACTION_POLICY_STAFF_SIGN,
    ACTION_STUDENT_LOG_REVIEW,
    ACTION_STUDENT_LOG_SUBMIT,
    APPLICANT_REVIEW_ASSIGNMENT_DOCTYPE,
    INQUIRY_DOCTYPE,
    POLICY_VERSION_DOCTYPE,
    STUDENT_LOG_DOCTYPE,
    _active_employee_row,
    _applicant_display_name_from_row,
    _assignment_subtitle,
    _assignment_title,
    _badge_from_due_date,
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


def list_focus_items(open_only: int = 1, limit: int = 20, offset: int = 0):
    """
    Return FocusItem[] for the current user.

    V1: Student Log + Inquiry.
    - "action" items: ToDo allocated to user for Student Log follow-up work
    - "review" items: log owner, submitted follow-up exists, log not completed

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
          and not exists (
                select 1
                from `tabStudent Log Follow Up` f
                where f.student_log = s.name
                  and f.docstatus = 1
          )
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
            limit_page_length=1000,
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
                },
                "permissions": {"can_open": True},
            }
        )

    # ------------------------------------------------------------
    # C) Author review items
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
        order by s.modified desc
        limit 200
        """,
        {"user": user},
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
    assignment_rows = frappe.db.sql(
        """
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
            ad.document_type,
            ad.document_label,
            adt.document_type_name,
            adt.code as document_type_code
        from `tabApplicant Review Assignment` a
        join `tabStudent Applicant` sa
          on sa.name = a.student_applicant
        left join `tabApplicant Document` ad
          on a.target_type = 'Applicant Document'
         and ad.name = a.target_name
        left join `tabApplicant Document Type` adt
          on adt.name = ad.document_type
        where (%(open_only)s = 0 or a.status = 'Open')
          and (
                a.assigned_to_user = %(user)s
             or (
                    ifnull(a.assigned_to_role, '') != ''
                and a.assigned_to_role in %(roles)s
             )
          )
        order by a.modified desc
        limit %(limit)s offset %(offset)s
        """,
        {
            "open_only": open_only,
            "user": user,
            "roles": tuple(user_roles) or ("",),
            "limit": limit,
            "offset": offset,
        },
        as_dict=True,
    )

    for row in assignment_rows:
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
    # E) Staff policy signature action items (ToDo -> Policy Version)
    # ------------------------------------------------------------
    active_employee = _active_employee_row(user)
    if active_employee:
        policy_rows = frappe.db.sql(
            """
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
              and ip.applies_to like %(applies_to)s
            order by ifnull(t.date, '9999-12-31') asc, t.modified desc
            limit %(limit)s offset %(offset)s
            """,
            {
                "user": user,
                "ref_type": POLICY_VERSION_DOCTYPE,
                "open_only": open_only,
                "limit": limit,
                "offset": offset,
                "applies_to": "%Staff%",
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
