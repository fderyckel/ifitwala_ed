# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime, strip_html, today

from ifitwala_ed.api.guardian_home import _resolve_guardian_scope
from ifitwala_ed.api.org_comm_utils import check_audience_match, get_school_organization_map
from ifitwala_ed.api.org_communication_interactions import get_seen_org_communication_names
from ifitwala_ed.utilities.employee_utils import get_ancestor_organizations
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools

RECENT_WINDOW_DAYS = 90
SOURCE_FILTERS = {"all", "course", "activity", "school", "pastoral", "cohort"}
SOURCE_PRIORITY = ("course", "activity", "pastoral", "cohort", "school")


def _serialize_scalar(value: Any) -> Any:
    if value in (None, ""):
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return value
    return value


def _recent_start_date():
    return add_days(getdate(today()), -RECENT_WINDOW_DAYS)


def _clean_source_filter(source: str | None) -> str:
    value = str(source or "").strip().lower() or "all"
    if value not in SOURCE_FILTERS:
        return "all"
    return value


def _coerce_start(start: int | str | None) -> int:
    try:
        value = int(start or 0)
    except Exception:
        frappe.throw(_("Invalid start."))
    if value < 0:
        frappe.throw(_("start must be 0 or greater."))
    return value


def _coerce_page_length(page_length: int | str | None) -> int:
    try:
        value = int(page_length or 24)
    except Exception:
        frappe.throw(_("Invalid page_length."))
    if value < 1 or value > 100:
        frappe.throw(_("page_length must be between 1 and 100."))
    return value


def _snippet_from_html(value: str | None, limit: int = 260) -> str:
    raw_text = strip_html(value or "") if value else ""
    if raw_text and len(raw_text) > limit:
        return raw_text[:limit] + "..."
    return raw_text


def _group_source_type(group_row: dict[str, Any] | None) -> str:
    based_on = str((group_row or {}).get("group_based_on") or "").strip()
    if based_on == "Course":
        return "course"
    if based_on == "Activity":
        return "activity"
    if based_on == "Pastoral":
        return "pastoral"
    if based_on == "Cohort":
        return "cohort"
    return "school"


def _source_label(source_type: str) -> str:
    if source_type == "course":
        return _("Class Update")
    if source_type == "activity":
        return _("Activity Update")
    if source_type == "pastoral":
        return _("Pastoral Update")
    if source_type == "cohort":
        return _("Cohort Update")
    return _("School Update")


def _summarize_context_labels(source_type: str, labels: list[str]) -> str | None:
    unique_labels = [label for label in dict.fromkeys(label for label in labels if label)]
    if not unique_labels:
        return None
    if len(unique_labels) == 1:
        return unique_labels[0]
    if source_type == "course":
        return _("{count} classes").format(count=len(unique_labels))
    if source_type == "activity":
        return _("{count} activities").format(count=len(unique_labels))
    if source_type == "pastoral":
        return _("{count} pastoral groups").format(count=len(unique_labels))
    if source_type == "cohort":
        return _("{count} cohorts").format(count=len(unique_labels))
    return _("{count} schools").format(count=len(unique_labels))


def _resolve_guardian_communication_context() -> dict[str, Any]:
    user = frappe.session.user
    roles = set(frappe.get_roles(user))
    guardian_name, children = _resolve_guardian_scope(user)

    child_by_student = {row.get("student"): row for row in children if row.get("student")}
    student_names = sorted(child_by_student.keys())

    group_rows = []
    if student_names:
        group_rows = frappe.db.sql(
            """
            SELECT
                sgs.student,
                sg.name AS student_group,
                sg.student_group_name,
                sg.student_group_abbreviation,
                sg.group_based_on,
                sg.course,
                sg.program_offering,
                sg.school
            FROM `tabStudent Group Student` sgs
            INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
            WHERE sgs.student IN %(students)s
              AND COALESCE(sgs.active, 1) = 1
              AND COALESCE(sg.status, 'Active') = 'Active'
            ORDER BY sg.student_group_name ASC, sg.name ASC
            """,
            {"students": tuple(student_names)},
            as_dict=True,
        )

    membership_by_student: dict[str, set[str]] = {student: set() for student in student_names}
    group_members: dict[str, set[str]] = defaultdict(set)
    group_map: dict[str, dict[str, Any]] = {}
    student_school_names: dict[str, set[str]] = {student: set() for student in student_names}

    for child in children:
        student = child.get("student")
        school = child.get("school")
        if student and school:
            student_school_names.setdefault(student, set()).add(school)

    for row in group_rows or []:
        student = row.get("student")
        group_name = row.get("student_group")
        if not student or not group_name:
            continue
        membership_by_student.setdefault(student, set()).add(group_name)
        group_members[group_name].add(student)
        student_school_names.setdefault(student, set())
        if row.get("school"):
            student_school_names[student].add(row.get("school"))
        if group_name not in group_map:
            group_map[group_name] = row

    eligible_school_targets_by_student: dict[str, set[str]] = {}
    school_names: set[str] = set()
    for student, names in student_school_names.items():
        school_names.update(names)
        eligible_targets = set(names)
        for school_name in list(names):
            try:
                eligible_targets.update(get_ancestor_schools(school_name) or [])
            except Exception:
                continue
        eligible_school_targets_by_student[student] = eligible_targets

    school_org_map = get_school_organization_map(school_names)
    student_organization_names: dict[str, set[str]] = {student: set() for student in student_names}
    eligible_organization_targets_by_student: dict[str, set[str]] = {}
    organization_names: set[str] = set()
    for student, names in student_school_names.items():
        student_orgs = {
            school_org_map.get(str(school_name or "").strip())
            for school_name in names
            if school_org_map.get(str(school_name or "").strip())
        }
        student_organization_names[student] = {org for org in student_orgs if org}
        organization_names.update(student_organization_names[student])

        eligible_org_targets = set(student_organization_names[student])
        for organization_name in list(student_organization_names[student]):
            try:
                eligible_org_targets.update(get_ancestor_organizations(organization_name) or [])
            except Exception:
                continue
        eligible_organization_targets_by_student[student] = eligible_org_targets

    audience_scope = frappe._dict(
        school=next(iter(sorted(school_names)), None),
        organization=next(iter(sorted(organization_names)), None),
        organization_names=sorted(organization_names),
        student_name=None,
        student_groups=sorted(group_map.keys()),
        school_names=sorted(school_names),
    )

    return {
        "user": user,
        "roles": roles,
        "guardian_name": guardian_name,
        "children": children,
        "child_by_student": child_by_student,
        "student_names": student_names,
        "membership_by_student": membership_by_student,
        "group_members": group_members,
        "group_map": group_map,
        "student_school_names": student_school_names,
        "student_organization_names": student_organization_names,
        "eligible_school_targets_by_student": eligible_school_targets_by_student,
        "eligible_organization_targets_by_student": eligible_organization_targets_by_student,
        "audience_scope": audience_scope,
    }


def _validate_selected_student(selected_student: str | None, context: dict[str, Any]) -> str:
    student_name = str(selected_student or "").strip()
    if not student_name:
        return ""
    if student_name not in set(context.get("student_names") or []):
        frappe.throw(_("This student is not available in your guardian scope."), frappe.PermissionError)
    return student_name


def _candidate_scope(
    context: dict[str, Any], selected_student: str | None = None
) -> tuple[set[str], set[str], set[str]]:
    if selected_student:
        return (
            set((context.get("membership_by_student") or {}).get(selected_student) or []),
            set((context.get("eligible_school_targets_by_student") or {}).get(selected_student) or []),
            set((context.get("eligible_organization_targets_by_student") or {}).get(selected_student) or []),
        )

    target_groups = {
        group_name
        for groups in (context.get("membership_by_student") or {}).values()
        for group_name in (groups or set())
        if group_name
    }
    school_targets = {
        school_name
        for names in (context.get("eligible_school_targets_by_student") or {}).values()
        for school_name in (names or set())
        if school_name
    }
    organization_targets = {
        organization_name
        for names in (context.get("eligible_organization_targets_by_student") or {}).values()
        for organization_name in (names or set())
        if organization_name
    }
    return target_groups, school_targets, organization_targets


def _fetch_candidate_rows(
    target_groups: set[str],
    school_targets: set[str],
    organization_targets: set[str],
) -> list[dict[str, Any]]:
    if not target_groups and not school_targets and not organization_targets:
        return []

    conditions = ["oc.status IN ('Published', 'Archived')", "oc.publish_from >= %(recent_start)s"]
    audience_clauses: list[str] = []
    values: dict[str, Any] = {"recent_start": _recent_start_date()}

    if target_groups:
        audience_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM `tabOrg Communication Audience` a
                WHERE a.parent = oc.name
                  AND a.parenttype = 'Org Communication'
                  AND a.parentfield = 'audiences'
                  AND a.target_mode = 'Student Group'
                  AND a.student_group IN %(student_groups)s
                  AND COALESCE(a.to_guardians, 0) = 1
            )
            """
        )
        values["student_groups"] = tuple(sorted(target_groups))

    if school_targets:
        audience_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM `tabOrg Communication Audience` a
                WHERE a.parent = oc.name
                  AND a.parenttype = 'Org Communication'
                  AND a.parentfield = 'audiences'
                  AND a.target_mode = 'School Scope'
                  AND a.school IN %(school_targets)s
                  AND COALESCE(a.to_guardians, 0) = 1
            )
            """
        )
        values["school_targets"] = tuple(sorted(school_targets))

    if organization_targets:
        audience_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM `tabOrg Communication Audience` a
                WHERE a.parent = oc.name
                  AND a.parenttype = 'Org Communication'
                  AND a.parentfield = 'audiences'
                  AND a.target_mode = 'Organization'
                  AND oc.organization IN %(organization_targets)s
                  AND COALESCE(a.to_guardians, 0) = 1
            )
            """
        )
        values["organization_targets"] = tuple(sorted(organization_targets))

    conditions.append("IFNULL(oc.portal_surface, 'Everywhere') IN ('Everywhere', 'Portal Feed', 'Guardian Portal')")
    conditions.append("(" + " OR ".join(clause.strip() for clause in audience_clauses) + ")")

    sql = f"""
        SELECT
            oc.name,
            oc.title,
            oc.message,
            oc.communication_type,
            oc.status,
            oc.priority,
            oc.portal_surface,
            oc.school,
            oc.organization,
            oc.publish_from,
            oc.publish_to,
            oc.brief_start_date,
            oc.brief_end_date,
            oc.interaction_mode,
            oc.allow_private_notes,
            oc.allow_public_thread,
            oc.activity_program_offering,
            oc.activity_booking,
            oc.activity_student_group,
            oc.creation
        FROM `tabOrg Communication` oc
        WHERE {" AND ".join(condition.strip() for condition in conditions)}
        ORDER BY oc.publish_from DESC, oc.creation DESC
        LIMIT 400
    """
    return frappe.db.sql(sql, values, as_dict=True) or []


def _school_scope_matches(
    aud_school: str | None,
    include_descendants: bool,
    student_school_names: set[str],
    descendants_cache: dict[str, set[str]],
) -> bool:
    if not aud_school or not student_school_names:
        return False
    if aud_school in student_school_names:
        return True
    if not include_descendants:
        return False
    if aud_school not in descendants_cache:
        descendants_cache[aud_school] = set(get_descendant_schools(aud_school) or [])
    return bool(student_school_names & descendants_cache[aud_school])


def _matched_students_for_audience(
    audience_row: dict[str, Any],
    context: dict[str, Any],
    selected_student: str | None,
    descendants_cache: dict[str, set[str]],
    comm_organization: str | None,
) -> tuple[set[str], set[str]]:
    if int(audience_row.get("to_guardians") or 0) != 1:
        return set(), set()

    target_mode = str(audience_row.get("target_mode") or "").strip()
    relevant_students = [selected_student] if selected_student else list(context.get("student_names") or [])

    if target_mode == "Student Group":
        group_name = audience_row.get("student_group")
        if not group_name:
            return set(), set()
        matched_students = set((context.get("group_members") or {}).get(group_name) or [])
        if selected_student:
            matched_students &= {selected_student}
        if not matched_students:
            return set(), set()
        return matched_students, {group_name}

    if target_mode == "Organization":
        organization_name = str(comm_organization or "").strip()
        if not organization_name:
            return set(), set()

        matched_students = {
            student
            for student in relevant_students
            if organization_name
            in set((context.get("eligible_organization_targets_by_student") or {}).get(student) or [])
        }
        return matched_students, set()

    if target_mode != "School Scope":
        return set(), set()

    matched_students: set[str] = set()
    for student in relevant_students:
        student_school_names = set((context.get("student_school_names") or {}).get(student) or [])
        if _school_scope_matches(
            aud_school=audience_row.get("school"),
            include_descendants=int(audience_row.get("include_descendants") or 0) == 1,
            student_school_names=student_school_names,
            descendants_cache=descendants_cache,
        ):
            matched_students.add(student)
    return matched_students, set()


def _resolve_source_meta(
    matched_groups: set[str],
    context: dict[str, Any],
    row: dict[str, Any],
) -> dict[str, str | None]:
    labels_by_source: dict[str, list[str]] = defaultdict(list)

    for group_name in matched_groups:
        group_row = (context.get("group_map") or {}).get(group_name) or {}
        source_type = _group_source_type(group_row)
        label = group_row.get("student_group_name") or group_row.get("student_group_abbreviation") or group_name
        if label and label not in labels_by_source[source_type]:
            labels_by_source[source_type].append(label)

    for source_type in SOURCE_PRIORITY:
        labels = labels_by_source.get(source_type) or []
        if labels:
            return {
                "source_type": source_type,
                "source_label": _source_label(source_type),
                "context_label": _summarize_context_labels(source_type, labels),
            }

    if row.get("activity_program_offering") or row.get("activity_student_group"):
        return {
            "source_type": "activity",
            "source_label": _source_label("activity"),
            "context_label": row.get("activity_program_offering") or row.get("activity_student_group"),
        }

    return {
        "source_type": "school",
        "source_label": _source_label("school"),
        "context_label": row.get("school") or row.get("organization") or None,
    }


def _serialize_guardian_org_communication_item(
    row: dict[str, Any],
    *,
    context: dict[str, Any],
    matched_students: set[str],
    matched_groups: set[str],
    unread_names: set[str],
) -> dict[str, Any]:
    source_meta = _resolve_source_meta(matched_groups, context, row)
    ordered_children = [
        (context.get("child_by_student") or {}).get(student)
        for student in (child.get("student") for child in (context.get("children") or []))
        if student in matched_students
    ]
    matched_children = [child for child in ordered_children if child]

    return {
        "kind": "org_communication",
        "item_id": f"org::{row.get('name')}",
        "sort_at": _serialize_scalar(row.get("publish_from") or row.get("creation")),
        "source_type": source_meta["source_type"],
        "source_label": source_meta["source_label"],
        "context_label": source_meta["context_label"],
        "matched_children": matched_children,
        "is_unread": row.get("name") in unread_names,
        "org_communication": {
            "name": row.get("name"),
            "title": row.get("title"),
            "communication_type": row.get("communication_type"),
            "status": row.get("status"),
            "priority": row.get("priority"),
            "portal_surface": row.get("portal_surface"),
            "school": row.get("school"),
            "organization": row.get("organization"),
            "publish_from": _serialize_scalar(row.get("publish_from")),
            "publish_to": _serialize_scalar(row.get("publish_to")),
            "brief_start_date": _serialize_scalar(row.get("brief_start_date")),
            "brief_end_date": _serialize_scalar(row.get("brief_end_date")),
            "interaction_mode": row.get("interaction_mode"),
            "allow_private_notes": row.get("allow_private_notes"),
            "allow_public_thread": row.get("allow_public_thread"),
            "activity_program_offering": row.get("activity_program_offering"),
            "activity_booking": row.get("activity_booking"),
            "activity_student_group": row.get("activity_student_group"),
            "snippet": _snippet_from_html(row.get("message")),
            "has_active_thread": row.get("interaction_mode") == "Student Q&A",
        },
    }


def _ordered_matched_children(context: dict[str, Any], matched_students: set[str]) -> list[dict[str, Any]]:
    ordered_children = [
        (context.get("child_by_student") or {}).get(student)
        for student in (child.get("student") for child in (context.get("children") or []))
        if student in matched_students
    ]
    return [child for child in ordered_children if child]


def _selected_or_all_students(context: dict[str, Any], selected_student: str | None) -> list[str]:
    if selected_student:
        return [selected_student]
    return list(context.get("student_names") or [])


def _students_for_school_scope(
    context: dict[str, Any],
    *,
    selected_student: str | None,
    selected_school: str | None = None,
) -> list[str]:
    relevant_students = _selected_or_all_students(context, selected_student)
    school_name = str(selected_school or "").strip()
    if not school_name:
        return [student for student in relevant_students if student]

    return [
        student
        for student in relevant_students
        if school_name in set((context.get("student_school_names") or {}).get(student) or [])
    ]


def _event_students_matching_school(
    context: dict[str, Any],
    *,
    selected_student: str | None,
    selected_school: str | None = None,
    event_school: str | None,
) -> set[str]:
    relevant_students = _students_for_school_scope(
        context,
        selected_student=selected_student,
        selected_school=selected_school,
    )
    school_name = str(event_school or "").strip()
    if not school_name:
        return {student for student in relevant_students if student}

    matched_students: set[str] = set()
    for student in relevant_students:
        eligible_school_targets = set((context.get("eligible_school_targets_by_student") or {}).get(student) or [])
        if not eligible_school_targets:
            eligible_school_targets = set((context.get("student_school_names") or {}).get(student) or [])
        if school_name in eligible_school_targets:
            matched_students.add(student)

    return matched_students


def _matched_students_for_school_event_audience(
    event_row: dict[str, Any],
    audience_row: dict[str, Any],
    *,
    context: dict[str, Any],
    selected_student: str | None,
    selected_school: str | None = None,
    explicit_participant_events: set[str],
) -> set[str]:
    audience_type = str(audience_row.get("audience_type") or "").strip()
    event_name = str(event_row.get("name") or "").strip()
    eligible_students = _event_students_matching_school(
        context,
        selected_student=selected_student,
        selected_school=selected_school,
        event_school=event_row.get("school"),
    )
    if not eligible_students:
        return set()

    include_guardians = int(audience_row.get("include_guardians") or 0) == 1

    if audience_type in {"All Students, Guardians, and Employees", "All Guardians"}:
        return eligible_students

    if audience_type == "All Students":
        return eligible_students if include_guardians else set()

    if audience_type == "Students in Student Group":
        if not include_guardians:
            return set()
        group_name = audience_row.get("student_group")
        if not group_name:
            return set()
        return {
            student
            for student in eligible_students
            if group_name in set((context.get("membership_by_student") or {}).get(student) or [])
        }

    if audience_type == "Custom Users":
        if event_name not in explicit_participant_events:
            return set()
        return eligible_students

    return set()


def _fetch_guardian_school_events(
    context: dict[str, Any],
    *,
    selected_student: str | None = None,
    start_date=None,
    end_date=None,
    selected_school: str | None = None,
) -> list[dict[str, Any]]:
    target_schools = {
        school_name
        for student in _students_for_school_scope(
            context,
            selected_student=selected_student,
            selected_school=selected_school,
        )
        for school_name in set(
            (context.get("eligible_school_targets_by_student") or {}).get(student)
            or (context.get("student_school_names") or {}).get(student)
            or []
        )
        if school_name
    }
    if not target_schools and not context.get("user"):
        return []

    window_start = getdate(start_date) if start_date else _recent_start_date()
    window_end = getdate(end_date) if end_date else None

    conditions = [
        "se.docstatus < 2",
        "COALESCE(se.ends_on, se.starts_on) >= %(window_start)s",
        "("
        "EXISTS ("
        "    SELECT 1 FROM `tabSchool Event Participant` sep"
        "    WHERE sep.parent = se.name"
        "      AND sep.parenttype = 'School Event'"
        "      AND sep.participant = %(user)s"
        ")"
        " OR COALESCE(se.school, '') = ''" + (" OR se.school IN %(target_schools)s" if target_schools else "") + ")",
    ]
    values: dict[str, Any] = {
        "window_start": window_start,
        "user": context.get("user"),
    }
    if window_end:
        conditions.append("se.starts_on < %(window_end_exclusive)s")
        values["window_end_exclusive"] = add_days(window_end, 1)
    if target_schools:
        values["target_schools"] = tuple(sorted(target_schools))

    sql = f"""
        SELECT
            se.name,
            se.subject,
            se.school,
            se.location,
            se.event_category,
            se.description,
            se.starts_on,
            se.ends_on,
            se.all_day,
            se.creation
        FROM `tabSchool Event` se
        WHERE {" AND ".join(condition.strip() for condition in conditions)}
        ORDER BY se.starts_on DESC, se.creation DESC
        LIMIT 200
    """
    rows = frappe.db.sql(sql, values, as_dict=True) or []
    if not rows:
        return []

    event_names = [row.get("name") for row in rows if row.get("name")]
    audience_rows = frappe.get_all(
        "School Event Audience",
        filters={"parent": ["in", event_names]},
        fields=[
            "parent",
            "audience_type",
            "student_group",
            "include_guardians",
            "include_students",
        ],
    )
    audiences_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in audience_rows or []:
        parent = row.get("parent")
        if parent:
            audiences_by_event[parent].append(row)

    participant_rows = frappe.get_all(
        "School Event Participant",
        filters={
            "parent": ["in", event_names],
            "parenttype": "School Event",
            "participant": context.get("user"),
        },
        fields=["parent"],
    )
    explicit_participant_events = {row.get("parent") for row in participant_rows or [] if row.get("parent")}

    items: list[dict[str, Any]] = []
    for row in rows:
        event_name = row.get("name")
        if not event_name:
            continue

        matched_students: set[str] = set()
        for audience_row in audiences_by_event.get(event_name, []):
            matched_students.update(
                _matched_students_for_school_event_audience(
                    row,
                    audience_row,
                    context=context,
                    selected_student=selected_student,
                    selected_school=selected_school,
                    explicit_participant_events=explicit_participant_events,
                )
            )

        if not matched_students:
            continue

        items.append(
            {
                "kind": "school_event",
                "item_id": f"event::{event_name}",
                "sort_at": _serialize_scalar(row.get("starts_on") or row.get("creation")),
                "source_type": "school",
                "source_label": _("School Event"),
                "context_label": row.get("school") or None,
                "matched_children": _ordered_matched_children(context, matched_students),
                "school_event": {
                    "name": event_name,
                    "subject": row.get("subject") or _("School Event"),
                    "school": row.get("school"),
                    "location": row.get("location"),
                    "event_type": row.get("event_type"),
                    "event_category": row.get("event_category"),
                    "description": row.get("description") or "",
                    "snippet": _snippet_from_html(row.get("description"), limit=220),
                    "starts_on": _serialize_scalar(row.get("starts_on")),
                    "ends_on": _serialize_scalar(row.get("ends_on")),
                    "all_day": 1 if row.get("all_day") else 0,
                },
            }
        )

    return _sort_items(items)


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (str(item.get("sort_at") or ""), str(item.get("item_id") or "")),
        reverse=True,
    )


def _fetch_guardian_org_communications(
    context: dict[str, Any],
    *,
    selected_student: str | None = None,
) -> list[dict[str, Any]]:
    target_groups, school_targets, organization_targets = _candidate_scope(context, selected_student=selected_student)
    candidates = _fetch_candidate_rows(
        target_groups=target_groups,
        school_targets=school_targets,
        organization_targets=organization_targets,
    )
    if not candidates:
        return []

    candidate_names = [row.get("name") for row in candidates if row.get("name")]
    audience_rows = frappe.get_all(
        "Org Communication Audience",
        filters={"parent": ["in", candidate_names]},
        fields=["parent", "target_mode", "school", "student_group", "include_descendants", "to_guardians"],
    )
    audiences_by_comm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in audience_rows or []:
        parent = row.get("parent")
        if parent:
            audiences_by_comm[parent].append(row)

    visible_names = [row.get("name") for row in candidates if row.get("name")]
    seen_names = set(
        get_seen_org_communication_names(
            user=context.get("user"),
            communication_names=visible_names,
        )
    )

    descendants_cache: dict[str, set[str]] = {}
    items: list[dict[str, Any]] = []
    for row in candidates:
        comm_name = row.get("name")
        if not comm_name:
            continue
        if not check_audience_match(
            comm_name,
            context.get("user"),
            context.get("roles"),
            context.get("audience_scope"),
        ):
            continue

        matched_students: set[str] = set()
        matched_groups: set[str] = set()
        for audience_row in audiences_by_comm.get(comm_name, []):
            audience_students, audience_groups = _matched_students_for_audience(
                audience_row,
                context=context,
                selected_student=selected_student,
                descendants_cache=descendants_cache,
                comm_organization=row.get("organization"),
            )
            matched_students.update(audience_students)
            matched_groups.update(audience_groups)

        if not matched_students:
            continue

        items.append(
            _serialize_guardian_org_communication_item(
                row,
                context=context,
                matched_students=matched_students,
                matched_groups=matched_groups,
                unread_names=set(visible_names) - seen_names,
            )
        )

    return _sort_items(items)


@frappe.whitelist()
def get_guardian_communication_center(
    source: str | None = None,
    student: str | None = None,
    start: int = 0,
    page_length: int = 24,
) -> dict[str, Any]:
    context = _resolve_guardian_communication_context()
    selected_student = _validate_selected_student(student, context)
    source_filter = _clean_source_filter(source)
    offset = _coerce_start(start)
    page_len = _coerce_page_length(page_length)

    org_items = _fetch_guardian_org_communications(
        context,
        selected_student=selected_student or None,
    )

    if source_filter == "all":
        items = list(org_items)
        items.extend(
            _fetch_guardian_school_events(
                context,
                selected_student=selected_student or None,
            )
        )
        items = _sort_items(items)
    elif source_filter == "school":
        items = [row for row in org_items if row.get("source_type") == "school"]
        items.extend(
            _fetch_guardian_school_events(
                context,
                selected_student=selected_student or None,
            )
        )
        items = _sort_items(items)
    else:
        items = [row for row in org_items if row.get("source_type") == source_filter]

    summary_counts = Counter(item.get("source_type") or "other" for item in items)
    unread_count = sum(1 for row in items if row.get("is_unread"))
    paged_items = items[offset : offset + page_len]

    return {
        "meta": {
            "generated_at": _serialize_scalar(now_datetime()),
            "source": source_filter,
            "student": selected_student or None,
        },
        "family": {
            "children": context.get("children") or [],
        },
        "summary": {
            "total_items": len(items),
            "source_counts": dict(summary_counts),
            "unread_items": unread_count,
        },
        "items": paged_items,
        "total_count": len(items),
        "has_more": (offset + page_len) < len(items),
        "start": offset,
        "page_length": page_len,
    }


def get_guardian_portal_communication_unread_count() -> int:
    context = _resolve_guardian_communication_context()
    items = _fetch_guardian_org_communications(context)
    return sum(1 for item in items if item.get("is_unread"))
