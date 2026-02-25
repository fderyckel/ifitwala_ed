# ifitwala_ed/admission/applicant_review_workflow.py

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.admission.admission_utils import get_applicant_scope_ancestors

TARGET_DOCUMENT = "Applicant Document"
TARGET_HEALTH = "Applicant Health Profile"
TARGET_APPLICATION = "Student Applicant"
ASSIGNMENT_DOCTYPE = "Applicant Review Assignment"
RULE_REVIEWER_DOCTYPE = "Applicant Review Rule Reviewer"
REVIEWER_MODE_ROLE_ONLY = "Role Only"
REVIEWER_MODE_SPECIFIC_USER = "Specific User"

DECISION_OPTIONS_BY_TARGET = {
    TARGET_DOCUMENT: ["Approved", "Needs Follow-Up", "Rejected"],
    TARGET_HEALTH: ["Cleared", "Needs Follow-Up"],
    TARGET_APPLICATION: ["Recommend Admit", "Recommend Waitlist", "Recommend Reject", "Needs Follow-Up"],
}

DOCUMENT_REVIEW_STATUS_BY_DECISION = {
    "Approved": "Approved",
    "Rejected": "Rejected",
    "Needs Follow-Up": "Pending",
}


def get_decision_options_for_target(target_type: str) -> list[str]:
    return list(DECISION_OPTIONS_BY_TARGET.get((target_type or "").strip(), []))


def get_student_applicant_scope(student_applicant: str) -> dict:
    row = frappe.db.get_value(
        "Student Applicant",
        student_applicant,
        [
            "name",
            "organization",
            "school",
            "program_offering",
            "application_status",
            "first_name",
            "middle_name",
            "last_name",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Invalid Student Applicant: {0}.").format(student_applicant))
    return row


def _normalize_reviewer_row(
    reviewer_mode: str | None,
    reviewer_user: str | None,
    reviewer_role: str | None,
) -> tuple[str | None, str | None, str | None]:
    mode = (reviewer_mode or "").strip()
    user = (reviewer_user or "").strip() or None
    role = (reviewer_role or "").strip() or None

    if mode not in {REVIEWER_MODE_ROLE_ONLY, REVIEWER_MODE_SPECIFIC_USER}:
        if user:
            mode = REVIEWER_MODE_SPECIFIC_USER
        elif role:
            mode = REVIEWER_MODE_ROLE_ONLY

    if mode == REVIEWER_MODE_ROLE_ONLY:
        if not role or user:
            return None, None, None
        return mode, None, role

    if mode == REVIEWER_MODE_SPECIFIC_USER:
        if not user:
            return None, None, None
        return mode, user, None

    return None, None, None


def _score_rule_row(
    *,
    row: dict,
    org_rank: dict[str, int],
    school_rank: dict[str, int],
    program_offering: str | None,
) -> tuple[int, int, int] | None:
    row_org = (row.get("organization") or "").strip()
    row_school = (row.get("school") or "").strip()
    row_program_offering = (row.get("program_offering") or "").strip()

    if row_org not in org_rank or row_school not in school_rank:
        return None

    applicant_program = (program_offering or "").strip()
    if row_program_offering:
        if row_program_offering != applicant_program:
            return None
        program_rank = 0
    else:
        program_rank = 1

    return (org_rank[row_org], school_rank[row_school], program_rank)


def _query_matching_rule_rows(
    *,
    target_type: str,
    organization: str,
    school: str,
    program_offering: str | None,
    document_type: str | None,
) -> list[dict]:
    org_ancestors, school_ancestors = get_applicant_scope_ancestors(organization=organization, school=school)
    if not org_ancestors or not school_ancestors:
        return []

    params: dict = {
        "target_type": target_type,
        "organizations": tuple(org_ancestors),
        "schools": tuple(school_ancestors),
    }
    sql = """
        select
            name,
            organization,
            school,
            program_offering,
            ifnull(document_type, '') as document_type
        from `tabApplicant Review Rule`
        where is_active = 1
          and target_type = %(target_type)s
          and organization in %(organizations)s
          and school in %(schools)s
    """
    if target_type == TARGET_DOCUMENT:
        if document_type:
            sql += " and (ifnull(document_type, '') = '' or document_type = %(document_type)s)"
            params["document_type"] = document_type
        else:
            sql += " and ifnull(document_type, '') = ''"

    rows = frappe.db.sql(sql, params, as_dict=True)
    if not rows:
        return []

    rank_by_org = {value: idx for idx, value in enumerate(org_ancestors)}
    rank_by_school = {value: idx for idx, value in enumerate(school_ancestors)}

    scored_rows: list[tuple[tuple[int, int, int], dict]] = []
    for row in rows:
        score = _score_rule_row(
            row=row,
            org_rank=rank_by_org,
            school_rank=rank_by_school,
            program_offering=program_offering,
        )
        if score is None:
            continue
        scored_rows.append((score, row))

    if not scored_rows:
        return []

    best_score = min(score for score, _row in scored_rows)
    return [row for score, row in scored_rows if score == best_score]


def resolve_reviewers_for_target(
    *,
    target_type: str,
    student_applicant: str,
    document_type: str | None = None,
) -> list[dict]:
    scope = get_student_applicant_scope(student_applicant)
    organization = (scope.get("organization") or "").strip()
    school = (scope.get("school") or "").strip()
    program_offering = (scope.get("program_offering") or "").strip() or None
    if not organization or not school:
        return []

    matched_rules = _query_matching_rule_rows(
        target_type=target_type,
        organization=organization,
        school=school,
        program_offering=program_offering,
        document_type=document_type,
    )
    if not matched_rules:
        return []

    reviewer_rows = frappe.get_all(
        RULE_REVIEWER_DOCTYPE,
        filters={"parent": ["in", [row.get("name") for row in matched_rules]]},
        fields=["parent", "reviewer_mode", "reviewer_user", "reviewer_role"],
        order_by="idx asc",
    )

    deduped: list[dict] = []
    seen: set[tuple[str | None, str | None]] = set()
    for row in reviewer_rows:
        reviewer_mode, reviewer_user, reviewer_role = _normalize_reviewer_row(
            row.get("reviewer_mode"),
            row.get("reviewer_user"),
            row.get("reviewer_role"),
        )
        if not reviewer_mode:
            continue
        key = (reviewer_user, reviewer_role)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "reviewer_mode": reviewer_mode,
                "reviewer_user": reviewer_user,
                "reviewer_role": reviewer_role,
            }
        )

    return deduped


def _assignment_filters_for_actor(
    *,
    target_type: str,
    target_name: str,
    reviewer_user: str | None,
    reviewer_role: str | None,
) -> dict:
    filters = {
        "target_type": target_type,
        "target_name": target_name,
    }
    if reviewer_user:
        filters["assigned_to_user"] = reviewer_user
    else:
        filters["assigned_to_role"] = reviewer_role
    return filters


def _reopen_assignment(assignment_name: str, source_event: str | None):
    doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, assignment_name)
    doc.status = "Open"
    doc.decision = None
    doc.notes = None
    doc.decided_by = None
    doc.decided_on = None
    doc.source_event = source_event
    doc.save(ignore_permissions=True)


def materialize_review_assignments(
    *,
    target_type: str,
    target_name: str,
    student_applicant: str,
    source_event: str,
    document_type: str | None = None,
    reopen_done: bool = True,
) -> list[str]:
    reviewers = resolve_reviewers_for_target(
        target_type=target_type,
        student_applicant=student_applicant,
        document_type=document_type,
    )
    if not reviewers:
        return []

    created_or_reopened: list[str] = []
    lock_key = f"ifitwala_ed:lock:review_assignment:materialize:{target_type}:{target_name}"
    with frappe.cache().lock(lock_key, timeout=10):
        for reviewer in reviewers:
            reviewer_user = reviewer.get("reviewer_user")
            reviewer_role = reviewer.get("reviewer_role")
            actor_filters = _assignment_filters_for_actor(
                target_type=target_type,
                target_name=target_name,
                reviewer_user=reviewer_user,
                reviewer_role=reviewer_role,
            )

            open_name = frappe.db.get_value(
                ASSIGNMENT_DOCTYPE,
                {
                    **actor_filters,
                    "status": "Open",
                },
                "name",
            )
            if open_name:
                created_or_reopened.append(open_name)
                continue

            if reopen_done:
                done_rows = frappe.get_all(
                    ASSIGNMENT_DOCTYPE,
                    filters={
                        **actor_filters,
                        "status": "Done",
                    },
                    fields=["name"],
                    order_by="modified desc",
                    limit_page_length=1,
                )
                done_name = done_rows[0].get("name") if done_rows else None
                if done_name:
                    _reopen_assignment(done_name, source_event)
                    created_or_reopened.append(done_name)
                    continue

            doc = frappe.get_doc(
                {
                    "doctype": ASSIGNMENT_DOCTYPE,
                    "target_type": target_type,
                    "target_name": target_name,
                    "student_applicant": student_applicant,
                    "assigned_to_user": reviewer_user,
                    "assigned_to_role": reviewer_role,
                    "status": "Open",
                    "source_event": source_event,
                }
            )
            doc.insert(ignore_permissions=True)
            created_or_reopened.append(doc.name)

    return created_or_reopened


def materialize_document_review_assignments(
    *, applicant_document: str, source_event: str = "document_uploaded"
) -> list[str]:
    row = frappe.db.get_value(
        TARGET_DOCUMENT,
        applicant_document,
        ["name", "student_applicant", "document_type"],
        as_dict=True,
    )
    if not row:
        return []

    return materialize_review_assignments(
        target_type=TARGET_DOCUMENT,
        target_name=row.get("name"),
        student_applicant=row.get("student_applicant"),
        source_event=source_event,
        document_type=row.get("document_type"),
        reopen_done=True,
    )


def materialize_health_review_assignments(
    *, applicant_health_profile: str, source_event: str = "health_submitted"
) -> list[str]:
    row = frappe.db.get_value(
        TARGET_HEALTH,
        applicant_health_profile,
        ["name", "student_applicant"],
        as_dict=True,
    )
    if not row:
        return []

    return materialize_review_assignments(
        target_type=TARGET_HEALTH,
        target_name=row.get("name"),
        student_applicant=row.get("student_applicant"),
        source_event=source_event,
        reopen_done=True,
    )


def materialize_application_review_assignments(
    *, student_applicant: str, source_event: str = "application_submitted"
) -> list[str]:
    if not frappe.db.exists(TARGET_APPLICATION, student_applicant):
        return []

    return materialize_review_assignments(
        target_type=TARGET_APPLICATION,
        target_name=student_applicant,
        student_applicant=student_applicant,
        source_event=source_event,
        reopen_done=True,
    )


def _update_target_review_fields(
    *, target_type: str, target_name: str, decision: str, notes: str | None, decided_by: str
):
    now_ts = now_datetime()
    clean_notes = (notes or "").strip()

    if target_type == TARGET_DOCUMENT:
        review_status = DOCUMENT_REVIEW_STATUS_BY_DECISION.get(decision)
        if not review_status:
            frappe.throw(_("Invalid document decision: {0}.").format(decision), frappe.ValidationError)
        frappe.db.set_value(
            TARGET_DOCUMENT,
            target_name,
            {
                "review_status": review_status,
                "review_notes": clean_notes,
                "reviewed_by": decided_by,
                "reviewed_on": now_ts,
            },
        )
        return

    if target_type == TARGET_HEALTH:
        frappe.db.set_value(
            TARGET_HEALTH,
            target_name,
            {
                "review_status": decision,
                "review_notes": clean_notes,
                "reviewed_by": decided_by,
                "reviewed_on": now_ts,
            },
        )
        return

    if target_type == TARGET_APPLICATION:
        # Overall application review is advisory in v1 and does not mutate application_status.
        return

    frappe.throw(_("Unsupported target type: {0}.").format(target_type), frappe.ValidationError)


def complete_assignment_decision(*, assignment_doc, decision: str, notes: str | None, decided_by: str):
    options = DECISION_OPTIONS_BY_TARGET.get((assignment_doc.target_type or "").strip(), [])
    if decision not in options:
        frappe.throw(_("Decision {0} is not valid for target type {1}.").format(decision, assignment_doc.target_type))

    assignment_doc.status = "Done"
    assignment_doc.decision = decision
    assignment_doc.notes = (notes or "").strip() or None
    assignment_doc.decided_by = decided_by
    assignment_doc.decided_on = now_datetime()
    assignment_doc.save(ignore_permissions=True)

    _update_target_review_fields(
        target_type=assignment_doc.target_type,
        target_name=assignment_doc.target_name,
        decision=decision,
        notes=notes,
        decided_by=decided_by,
    )


def get_review_assignments_summary(*, student_applicant: str) -> dict:
    rows = frappe.get_all(
        ASSIGNMENT_DOCTYPE,
        filters={
            "student_applicant": student_applicant,
            "status": "Done",
        },
        fields=[
            "name",
            "target_type",
            "target_name",
            "assigned_to_user",
            "assigned_to_role",
            "decision",
            "notes",
            "decided_by",
            "decided_on",
            "status",
        ],
        order_by="decided_on desc, modified desc",
    )

    if not rows:
        return {
            TARGET_DOCUMENT: [],
            TARGET_HEALTH: [],
            TARGET_APPLICATION: [],
        }

    user_ids = sorted(
        {
            value
            for row in rows
            for value in [
                (row.get("assigned_to_user") or "").strip(),
                (row.get("decided_by") or "").strip(),
            ]
            if value
        }
    )

    full_name_map: dict[str, str] = {}
    if user_ids:
        for user_row in frappe.get_all("User", filters={"name": ["in", user_ids]}, fields=["name", "full_name"]):
            full_name_map[user_row.get("name")] = (user_row.get("full_name") or "").strip() or user_row.get("name")

    document_targets = [row.get("target_name") for row in rows if row.get("target_type") == TARGET_DOCUMENT]
    document_label_by_target: dict[str, str] = {}
    if document_targets:
        document_rows = frappe.db.sql(
            """
            select
                d.name,
                d.document_type,
                d.document_label,
                ifnull(dt.document_type_name, '') as document_type_name,
                ifnull(dt.code, '') as document_type_code
            from `tabApplicant Document` d
            left join `tabApplicant Document Type` dt
              on dt.name = d.document_type
            where d.name in %(targets)s
            """,
            {"targets": tuple(document_targets)},
            as_dict=True,
        )
        for row in document_rows:
            label = (
                (row.get("document_label") or "").strip()
                or (row.get("document_type_code") or "").strip()
                or (row.get("document_type_name") or "").strip()
                or (row.get("document_type") or "").strip()
                or (row.get("name") or "").strip()
            )
            document_label_by_target[row.get("name")] = label

    grouped: dict[str, list[dict]] = defaultdict(list)

    for row in rows:
        target_type = row.get("target_type")
        assigned_to_user = (row.get("assigned_to_user") or "").strip()
        assigned_to_role = (row.get("assigned_to_role") or "").strip()
        decided_by = (row.get("decided_by") or "").strip()

        reviewer_label = assigned_to_role or full_name_map.get(assigned_to_user) or assigned_to_user
        decided_by_label = full_name_map.get(decided_by) or decided_by or reviewer_label

        target_label = row.get("target_name")
        if target_type == TARGET_DOCUMENT:
            target_label = document_label_by_target.get(row.get("target_name")) or row.get("target_name")
        elif target_type == TARGET_HEALTH:
            target_label = _("Health Profile")
        elif target_type == TARGET_APPLICATION:
            target_label = _("Overall Application")

        grouped[target_type].append(
            {
                "assignment": row.get("name"),
                "target_name": row.get("target_name"),
                "target_label": target_label,
                "reviewer": reviewer_label,
                "decision": row.get("decision"),
                "notes": row.get("notes"),
                "decided_by": decided_by_label,
                "decided_on": row.get("decided_on"),
            }
        )

    return {
        TARGET_DOCUMENT: grouped.get(TARGET_DOCUMENT, []),
        TARGET_HEALTH: grouped.get(TARGET_HEALTH, []),
        TARGET_APPLICATION: grouped.get(TARGET_APPLICATION, []),
    }
