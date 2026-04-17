# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.api.org_comm_utils

import frappe
from frappe import _

from ifitwala_ed.utilities.employee_utils import get_ancestor_organizations, get_descendant_organizations
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools

STAFF_ROLES = {
    "Academic Staff",
    "Instructor",
    "Employee",
    "Academic Admin",
    "Academic Assistant",
    "HR Manager",
    "Accounts Manager",
    "Nurse",
    "System Manager",
}


def _to_text(value) -> str:
    return str(value or "").strip()


def _as_bool(value) -> bool:
    return value in (1, "1", True)


def get_school_organization_map(school_names) -> dict[str, str]:
    normalized_names = sorted({_to_text(school) for school in (school_names or []) if _to_text(school)})
    if not normalized_names:
        return {}

    rows = frappe.get_all(
        "School",
        filters={"name": ["in", tuple(normalized_names)]},
        fields=["name", "organization"],
        limit=0,
    )
    return {
        _to_text(row.get("name")): _to_text(row.get("organization"))
        for row in (rows or [])
        if _to_text(row.get("name"))
    }


def expand_employee_visibility_context(employee: dict | None, roles) -> dict:
    """Expand Academic Admin org/school visibility for archive-like permission checks."""
    employee = dict(employee or {})
    if "Academic Admin" not in (roles or []):
        return employee

    base_school = _to_text(employee.get("school"))
    if base_school:
        school_names = [school for school in (get_descendant_schools(base_school) or []) if _to_text(school)]
        if school_names:
            employee["school_names"] = school_names
        return employee

    base_organization = _to_text(employee.get("organization"))
    if not base_organization:
        return employee

    organization_names = [org for org in (get_descendant_organizations(base_organization) or []) if _to_text(org)]
    if organization_names:
        employee["organization_names"] = organization_names

    school_rows = frappe.get_all(
        "School",
        filters={"organization": ["in", organization_names]}
        if organization_names
        else {"organization": base_organization},
        pluck="name",
    )
    school_names = [school for school in (school_rows or []) if _to_text(school)]
    if school_names:
        employee["school_names"] = school_names

    return employee


def _resolve_student_record_for_user(user_id: str) -> dict:
    student = frappe.db.get_value("Student", {"student_email": user_id}, ["name", "anchor_school"], as_dict=True)
    if student:
        return student or {}

    user_email = frappe.db.get_value("User", user_id, "email")
    if user_email and user_email != user_id:
        student = frappe.db.get_value("Student", {"student_email": user_email}, ["name", "anchor_school"], as_dict=True)
        if student:
            return student or {}

    return {}


def _get_cached_portal_student_context(user_id: str) -> dict:
    cache = getattr(frappe.flags, "_org_comm_student_context_cache", None)
    if cache is None:
        cache = {}
        frappe.flags._org_comm_student_context_cache = cache

    if user_id in cache:
        return cache[user_id]

    student_row = _resolve_student_record_for_user(user_id)
    student_name = (student_row or {}).get("name")
    anchor_school = (student_row or {}).get("anchor_school")

    group_rows = []
    if student_name:
        group_rows = frappe.db.sql(
            """
            SELECT
                sg.name AS student_group,
                sg.school
            FROM `tabStudent Group Student` sgs
            INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
            WHERE sgs.student = %(student)s
              AND COALESCE(sgs.active, 1) = 1
              AND COALESCE(sg.status, 'Active') = 'Active'
            """,
            {"student": student_name},
            as_dict=True,
        )

    school_names = {row.get("school") for row in (group_rows or []) if row.get("school")}
    if anchor_school:
        school_names.add(anchor_school)

    cache[user_id] = {
        "student_name": student_name,
        "student_groups": {row.get("student_group") for row in (group_rows or []) if row.get("student_group")},
        "school_names": school_names,
    }
    return cache[user_id]


def _get_cached_guardian_context(user_id: str) -> dict:
    cache = getattr(frappe.flags, "_org_comm_guardian_context_cache", None)
    if cache is None:
        cache = {}
        frappe.flags._org_comm_guardian_context_cache = cache

    if user_id in cache:
        return cache[user_id]

    guardian_name = frappe.db.get_value("Guardian", {"user": user_id}, "name")
    if not guardian_name:
        cache[user_id] = {
            "guardian_name": None,
            "student_names": set(),
            "student_groups": set(),
            "school_names": set(),
            "organization_names": set(),
        }
        return cache[user_id]

    student_guardian_rows = frappe.get_all(
        "Student Guardian",
        filters={"guardian": guardian_name, "parenttype": "Student"},
        fields=["parent"],
    )
    guardian_student_rows = frappe.get_all(
        "Guardian Student",
        filters={"parent": guardian_name, "parenttype": "Guardian"},
        fields=["student"],
    )
    linked_students = sorted(
        {row.get("parent") for row in (student_guardian_rows or []) if row.get("parent")}
        | {row.get("student") for row in (guardian_student_rows or []) if row.get("student")}
    )

    student_rows = []
    if linked_students:
        student_rows = frappe.get_all(
            "Student",
            filters={"name": ["in", linked_students], "enabled": 1},
            fields=["name", "anchor_school"],
        )

    enabled_students = sorted({row.get("name") for row in (student_rows or []) if row.get("name")})
    group_rows = []
    if enabled_students:
        group_rows = frappe.db.sql(
            """
            SELECT
                sgs.student,
                sg.name AS student_group,
                sg.school
            FROM `tabStudent Group Student` sgs
            INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
            WHERE sgs.student IN %(students)s
              AND COALESCE(sgs.active, 1) = 1
              AND COALESCE(sg.status, 'Active') = 'Active'
            """,
            {"students": tuple(enabled_students)},
            as_dict=True,
        )

    school_names = {row.get("anchor_school") for row in (student_rows or []) if row.get("anchor_school")}
    school_names.update({row.get("school") for row in (group_rows or []) if row.get("school")})
    school_org_map = get_school_organization_map(school_names)
    organization_names = {
        school_org_map.get(_to_text(school_name))
        for school_name in school_names
        if school_org_map.get(_to_text(school_name))
    }

    cache[user_id] = {
        "guardian_name": guardian_name,
        "student_names": set(enabled_students),
        "student_groups": {row.get("student_group") for row in (group_rows or []) if row.get("student_group")},
        "school_names": school_names,
        "organization_names": organization_names,
    }
    return cache[user_id]


def check_audience_match(
    comm_name,
    user,
    roles,
    employee,
    filter_team=None,
    filter_student_group=None,
    filter_school=None,
    allow_owner: bool = False,
):
    """
    Checks if the current user matches the audience criteria for a given Org Communication.

    Strict filter behavior:
    - If filter_student_group is set:
            Only include communications that have an audience row with that exact student_group.
            The match MUST happen on that Student Group row.
            Eligibility:
                    - Academic Admin: allowed only when the group belongs to the admin's allowed school scope
                    - Instructors: must teach that group
                    - Students: must belong to that group and be an enabled recipient
    - Else if filter_team is set:
            Only include communications that have an audience row with that exact team.
            The match MUST happen on that Team row.
            Eligibility:
                    - Academic Admin: allowed
                    - Others: must be member of that Team via Team Member child table

    Strict filter behavior for organization-wide rows:
    - Organization target mode matches the communication organization against the user's
      organization ancestry.
    - Archive callers may widen this with explicit descendant organization scope in
      employee.organization_names.

    Strict school filter behaviour:
    - If filter_school = X, only School Scope rows are eligible.
    - Match only audiences where audience.school is in {X} ∪ Anc(X).
    - Never include descendants of X.
    - School scope does not include organization rows.
    """

    def _get_enabled_recipient_flags(aud) -> set[str]:
        flags = set()
        if _as_bool(aud.to_staff):
            flags.add("to_staff")
        if _as_bool(aud.to_students):
            flags.add("to_students")
        if _as_bool(aud.to_guardians):
            flags.add("to_guardians")
        return flags

    def _get_user_recipient_flags() -> set[str]:
        flags = set()
        if set(roles or []) & STAFF_ROLES:
            flags.add("to_staff")
        if "Student" in roles:
            flags.add("to_students")
        if "Guardian" in roles:
            flags.add("to_guardians")
        return flags

    def _get_instructor_groups(user_id, employee_doc) -> set[str]:
        employee_name = employee_doc.get("name") if employee_doc else None
        if not employee_name:
            employee_name = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
        if not employee_name:
            return set()

        instructor_name = frappe.db.get_value("Instructor", {"employee": employee_name}, "name")
        if not instructor_name:
            return set()

        return set(
            frappe.get_all(
                "Student Group Instructor",
                filters={"instructor": instructor_name},
                pluck="parent",
            )
        )

    def _student_group_in_allowed_school_scope(student_group_name: str | None, allowed_school_names: set[str]) -> bool:
        if not student_group_name or not allowed_school_names:
            return False
        student_group_school = frappe.get_cached_value("Student Group", student_group_name, "school")
        return bool(student_group_school and student_group_school in allowed_school_names)

    def _school_scope_match(aud_school, include_descendants, user_school_names, descendants_cache):
        if not aud_school or not user_school_names:
            return False
        if _as_bool(include_descendants):
            if aud_school not in descendants_cache:
                try:
                    descendants_cache[aud_school] = set(get_descendant_schools(aud_school) or [])
                except Exception:
                    descendants_cache[aud_school] = set()
            return any(
                user_school == aud_school or user_school in descendants_cache[aud_school]
                for user_school in user_school_names
            )
        return aud_school in user_school_names

    def _organization_scope_match(comm_org, user_org_names, ancestor_cache):
        if not comm_org:
            return False

        normalized_user_org_names = {_to_text(org) for org in (user_org_names or []) if _to_text(org)}
        if not normalized_user_org_names:
            return False
        if comm_org in normalized_user_org_names:
            return True

        for user_org_name in normalized_user_org_names:
            if user_org_name not in ancestor_cache:
                try:
                    ancestor_cache[user_org_name] = set(get_ancestor_organizations(user_org_name) or [])
                except Exception:
                    ancestor_cache[user_org_name] = set()
            if comm_org in ancestor_cache[user_org_name]:
                return True

        return False

    # Normalize "All"/empty
    if filter_team in ("All", "", None):
        filter_team = None
    if filter_student_group in ("All", "", None):
        filter_student_group = None
    if filter_school in ("All", "", None):
        filter_school = None

    # Defensive: scope filters are mutually exclusive (student_group > team > school).
    active_scope = None
    if filter_student_group:
        active_scope = "Student Group"
        filter_team = None
        filter_school = None
    elif filter_team:
        active_scope = "Team"
        filter_school = None
    elif filter_school:
        active_scope = "School"

    if allow_owner and user and user != "Guest" and not active_scope:
        owner = frappe.get_cached_value("Org Communication", comm_name, "owner") if comm_name else None
        if owner == user:
            return True

    is_academic_admin = "Academic Admin" in roles
    is_system_manager = "System Manager" in roles

    # System Manager baseline:
    # - If no extra filters: see everything without checking audiences.
    # - If filters are present, still respect them.
    if "System Manager" in roles and not filter_team and not filter_student_group and not filter_school:
        return True

    audiences = frappe.get_all(
        "Org Communication Audience",
        filters={"parent": comm_name},
        fields=[
            "target_mode",
            "school",
            "include_descendants",
            "team",
            "student_group",
            "to_staff",
            "to_students",
            "to_guardians",
        ],
    )

    if not audiences:
        return False

    comm_org = frappe.get_cached_value("Org Communication", comm_name, "organization") if comm_name else None
    employee = employee or {}
    user_school_names = set()
    user_school = employee.get("school") if employee else None
    if user_school:
        user_school_names.add(user_school)
    explicit_school_names = employee.get("school_names") or []
    user_school_names.update({school for school in explicit_school_names if school})

    student_groups = set(employee.get("student_groups") or [])
    if "Student" in roles and (not student_groups or not user_school_names):
        student_context = _get_cached_portal_student_context(user)
        if not student_groups:
            student_groups = set(student_context.get("student_groups") or [])
        if not user_school_names:
            user_school_names = set(student_context.get("school_names") or [])

    user_organization_names = {_to_text(employee.get("organization"))} if employee else set()
    user_organization_names.update(
        {_to_text(org) for org in (employee.get("organization_names") or []) if _to_text(org)}
    )

    if "Guardian" in roles and (not student_groups or not user_school_names or not user_organization_names):
        guardian_context = _get_cached_guardian_context(user)
        student_groups.update(set(guardian_context.get("student_groups") or []))
        user_school_names.update(set(guardian_context.get("school_names") or []))
        user_organization_names.update(
            {_to_text(org) for org in (guardian_context.get("organization_names") or []) if _to_text(org)}
        )

    user_recipient_flags = _get_user_recipient_flags()

    filter_school_scope: set[str] | None = None
    if filter_school:
        try:
            up_f = get_ancestor_schools(filter_school) or []
        except Exception:
            up_f = []
        filter_school_scope = set(up_f + [filter_school])

    employee_name = employee.get("name") if employee else None

    team_names = {a.team for a in audiences if a.team}
    if filter_team:
        team_names.add(filter_team)

    user_teams: set[str] = set()

    if team_names and (user or employee_name):
        conds = []
        params = {"teams": tuple(team_names)}

        if user and user != "Guest":
            conds.append("tm.member = %(user)s")
            params["user"] = user

        if employee_name:
            conds.append("tm.employee = %(employee)s")
            params["employee"] = employee_name

        if conds:
            rows = frappe.db.sql(
                f"""
                SELECT DISTINCT tm.parent
                FROM `tabTeam Member` tm
                WHERE tm.parent IN %(teams)s
                  AND ({" OR ".join(conds)})
                """,
                params,
                as_dict=True,
            )
            user_teams = {r.get("parent") for r in rows if r.get("parent")}

    needs_instructor_groups = not student_groups and (
        filter_student_group is not None or any((a.target_mode or "").strip() == "Student Group" for a in audiences)
    )
    instructor_groups: set[str] = set()
    if needs_instructor_groups and not is_academic_admin:
        instructor_groups = _get_instructor_groups(user, employee)

    descendants_cache: dict[str, set[str]] = {}
    organization_ancestor_cache: dict[str, set[str]] = {}

    for aud in audiences:
        target_mode = (aud.target_mode or "").strip()
        if not target_mode:
            continue

        if active_scope == "School" and target_mode != "School Scope":
            continue
        if active_scope == "Team" and target_mode != "Team":
            continue
        if active_scope == "Student Group" and target_mode != "Student Group":
            continue

        if filter_student_group:
            if target_mode != "Student Group" or aud.student_group != filter_student_group:
                continue
            if is_system_manager:
                return True
            if is_academic_admin:
                return _student_group_in_allowed_school_scope(aud.student_group, user_school_names)
            enabled_recipients = _get_enabled_recipient_flags(aud)
            recipient_overlap = not user_recipient_flags or bool(enabled_recipients & user_recipient_flags)
            if aud.student_group and aud.student_group in student_groups and recipient_overlap:
                return True
            if aud.student_group and aud.student_group in instructor_groups:
                return True
            continue

        if filter_team:
            if target_mode != "Team" or aud.team != filter_team:
                continue
            if is_academic_admin or is_system_manager:
                return True
            if aud.team and aud.team in user_teams:
                return True
            continue

        if target_mode == "School Scope":
            if is_academic_admin:
                if filter_school_scope is not None and aud.school:
                    if aud.school not in filter_school_scope:
                        continue
                if _school_scope_match(
                    aud.school,
                    aud.include_descendants,
                    user_school_names,
                    descendants_cache,
                ):
                    return True
                continue
            enabled_recipients = _get_enabled_recipient_flags(aud)
            if not enabled_recipients:
                continue
            if user_recipient_flags and not (enabled_recipients & user_recipient_flags):
                continue
            if filter_school_scope is not None and aud.school:
                if aud.school not in filter_school_scope:
                    continue
            if _school_scope_match(
                aud.school,
                aud.include_descendants,
                user_school_names,
                descendants_cache,
            ):
                return True
            continue

        if target_mode == "Organization":
            if is_academic_admin:
                if _organization_scope_match(comm_org, user_organization_names, organization_ancestor_cache):
                    return True
                continue
            enabled_recipients = _get_enabled_recipient_flags(aud)
            if not enabled_recipients:
                continue
            if user_recipient_flags and not (enabled_recipients & user_recipient_flags):
                continue
            if _organization_scope_match(comm_org, user_organization_names, organization_ancestor_cache):
                return True
            continue

        if target_mode == "Team":
            if is_academic_admin:
                if aud.team:
                    return True
                continue
            enabled_recipients = _get_enabled_recipient_flags(aud)
            if not enabled_recipients:
                continue
            if user_recipient_flags and not (enabled_recipients & user_recipient_flags):
                continue
            if aud.team and (is_academic_admin or aud.team in user_teams):
                return True
            continue

        if target_mode == "Student Group":
            if is_academic_admin:
                if _student_group_in_allowed_school_scope(aud.student_group, user_school_names):
                    return True
                continue
            enabled_recipients = _get_enabled_recipient_flags(aud)
            if not enabled_recipients:
                continue
            if user_recipient_flags and not (enabled_recipients & user_recipient_flags):
                continue
            if aud.student_group and (aud.student_group in instructor_groups or aud.student_group in student_groups):
                return True
            continue

    return False


def build_audience_summary(comm_name: str) -> dict:
    """Return a structured audience summary for UI chips."""

    def _as_bool(value) -> bool:
        return value in (1, "1", True)

    def _get_cached(doctype, name, field, cache):
        if not name:
            return None
        if name not in cache:
            cache[name] = frappe.get_cached_value(doctype, name, field)
        return cache[name]

    def _get_recipients(aud) -> list[str]:
        recipients = []
        if _as_bool(aud.to_staff):
            recipients.append("Staff")
        if _as_bool(aud.to_students):
            recipients.append("Students")
        if _as_bool(aud.to_guardians):
            recipients.append("Guardians")
        return recipients

    if not comm_name:
        comm_name = ""

    audiences = frappe.get_all(
        "Org Communication Audience",
        filters={"parent": comm_name},
        fields=[
            "target_mode",
            "school",
            "include_descendants",
            "team",
            "student_group",
            "to_staff",
            "to_students",
            "to_guardians",
        ],
    )

    comm_org = None
    if comm_name:
        comm_org = frappe.get_cached_value("Org Communication", comm_name, "organization")

    school_abbr_cache = {}
    school_name_cache = {}
    org_abbr_cache = {}
    org_name_cache = {}
    sg_abbr_cache = {}
    sg_name_cache = {}
    team_code_cache = {}
    team_name_cache = {}

    rows = []
    for aud in audiences:
        recipients = _get_recipients(aud)
        if not recipients:
            continue

        target_mode = (aud.target_mode or "").strip()
        scope_type = "Global"
        scope_value = None
        scope_label = "Whole audience"
        include_descendants = 0

        if target_mode == "Student Group" or (not target_mode and aud.student_group):
            scope_type = "Student Group"
            sg_name = _get_cached("Student Group", aud.student_group, "student_group_name", sg_name_cache)
            sg_abbr = _get_cached("Student Group", aud.student_group, "student_group_abbreviation", sg_abbr_cache)
            scope_value = sg_abbr or sg_name or aud.student_group
            scope_label = sg_name or aud.student_group

        elif target_mode == "Team" or (not target_mode and aud.team):
            scope_type = "Team"
            team_name = _get_cached("Team", aud.team, "team_name", team_name_cache)
            team_code = _get_cached("Team", aud.team, "team_code", team_code_cache)
            scope_value = team_code or team_name or aud.team
            scope_label = team_name or aud.team

        elif target_mode == "School Scope" or (not target_mode and aud.school):
            scope_type = "School"
            include_descendants = 1 if _as_bool(aud.include_descendants) else 0
            school_name = _get_cached("School", aud.school, "school_name", school_name_cache)
            school_abbr = _get_cached("School", aud.school, "abbr", school_abbr_cache)
            scope_value = school_abbr or school_name or aud.school
            scope_label = school_name or aud.school

        elif target_mode == "Organization":
            scope_type = "Organization"
            org_name = _get_cached("Organization", comm_org, "organization_name", org_name_cache)
            org_abbr = _get_cached("Organization", comm_org, "abbr", org_abbr_cache)
            scope_value = org_abbr or org_name or comm_org
            scope_label = org_name or comm_org

        rows.append(
            {
                "scope_type": scope_type,
                "scope_value": scope_value,
                "scope_label": scope_label,
                "recipients": recipients,
                "include_descendants": include_descendants,
            }
        )

    scope_priority = {
        "Student Group": 0,
        "Team": 1,
        "School": 2,
        "Organization": 2,
        "Global": 3,
    }

    def _row_sort_key(row: dict) -> tuple:
        priority = scope_priority.get(row.get("scope_type"), 99)
        label = row.get("scope_label") or row.get("scope_value") or ""
        return (priority, str(label).lower())

    if rows:
        primary = sorted(rows, key=_row_sort_key)[0]
    else:
        primary = {
            "scope_type": "Global",
            "scope_value": None,
            "scope_label": "Whole audience",
            "recipients": [],
            "include_descendants": 0,
        }

    chips = []
    recipient_labels = list(primary.get("recipients") or [])
    for label in recipient_labels[:2]:
        chips.append({"type": "recipient", "label": label})
    if len(recipient_labels) > 2:
        chips.append({"type": "recipient", "label": f"+{len(recipient_labels) - 2}"})

    scope_chip_label = primary.get("scope_value") or "All"
    chips.append({"type": "scope", "label": scope_chip_label})

    audience_rows = len(rows)
    recipient_count = len(recipient_labels)

    return {
        "primary": primary,
        "chips": chips,
        "meta": {
            "audience_rows": audience_rows,
            "recipient_count": recipient_count,
            "has_multiple_audiences": 1 if audience_rows > 1 else 0,
        },
    }


def is_instructor_for_group(user, student_group):
    """Determine if user is an instructor for this group."""
    employee_name = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee_name:
        return False

    # If you have a dedicated Instructor doctype linked from Employee, resolve it here.
    instructor_name = frappe.db.get_value("Instructor", {"employee": employee_name}, "name")
    if not instructor_name:
        return False

    return frappe.db.exists(
        "Student Group Instructor",
        {"parent": student_group, "instructor": instructor_name},
    )


@frappe.whitelist()
def create_activity_communication(
    *,
    title: str,
    message: str,
    school: str,
    activity_program_offering: str | None = None,
    activity_booking: str | None = None,
    activity_student_group: str | None = None,
    communication_type: str = "Information",
    portal_surface: str = "Portal Feed",
    to_guardians: int = 1,
    to_students: int = 1,
    to_staff: int = 0,
    publish_from: str | None = None,
    publish_to: str | None = None,
):
    if not title:
        frappe.throw(_("Title is required."))
    if not school:
        frappe.throw(_("School is required."))
    if not message:
        frappe.throw(_("Message is required."))

    system_write = bool(getattr(frappe.flags, "allow_activity_comm_system_write", False))
    allowed_roles = {"System Manager", "Academic Admin", "Activity Coordinator", "Academic Staff"}
    if not system_write and not (set(frappe.get_roles(frappe.session.user)) & allowed_roles):
        frappe.throw(_("You are not permitted to create activity communications."), frappe.PermissionError)

    doc = frappe.new_doc("Org Communication")
    doc.title = title
    doc.message = message
    doc.school = school
    doc.communication_type = communication_type or "Information"
    doc.status = "Published"
    doc.portal_surface = portal_surface or "Portal Feed"
    doc.publish_from = publish_from
    doc.publish_to = publish_to
    doc.activity_program_offering = activity_program_offering
    doc.activity_booking = activity_booking
    doc.activity_student_group = activity_student_group

    if activity_student_group:
        doc.append(
            "audiences",
            {
                "target_mode": "Student Group",
                "student_group": activity_student_group,
                "to_guardians": 1 if int(to_guardians or 0) else 0,
                "to_students": 1 if int(to_students or 0) else 0,
                "to_staff": 1 if int(to_staff or 0) else 0,
            },
        )
    else:
        doc.append(
            "audiences",
            {
                "target_mode": "School Scope",
                "school": school,
                "include_descendants": 0,
                "to_guardians": 1 if int(to_guardians or 0) else 0,
                "to_students": 1 if int(to_students or 0) else 0,
                "to_staff": 1 if int(to_staff or 0) else 0,
            },
        )

    doc.insert(ignore_permissions=system_write)
    return {"name": doc.name}


@frappe.whitelist()
def get_activity_communication_feed(
    activity_program_offering: str | None = None,
    activity_student_group: str | None = None,
    start: int = 0,
    page_length: int = 30,
):
    from ifitwala_ed.api.org_communication_archive import get_org_communication_feed

    filters = {
        "activity_program_offering": activity_program_offering,
        "activity_student_group": activity_student_group,
        "status": "PublishedOrArchived",
    }
    return get_org_communication_feed(
        filters=filters,
        start=start,
        page_length=page_length,
    )
