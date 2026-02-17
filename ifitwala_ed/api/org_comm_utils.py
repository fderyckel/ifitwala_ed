# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.api.org_comm_utils

import frappe
from frappe import _

from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools


def check_audience_match(
    comm_name, user, roles, employee, filter_team=None, filter_student_group=None, filter_school=None
):
    """
    Checks if the current user matches the audience criteria for a given Org Communication.

    Strict filter behavior:
    - If filter_student_group is set:
            Only include communications that have an audience row with that exact student_group.
            The match MUST happen on that Student Group row.
            Eligibility:
                    - Academic Admin: allowed
                    - Others: must be instructor for that group
    - Else if filter_team is set:
            Only include communications that have an audience row with that exact team.
            The match MUST happen on that Team row.
            Eligibility:
                    - Academic Admin: allowed
                    - Others: must be member of that Team via Team Member child table

    Strict school filter behaviour:
    - If filter_school = X, only School Scope rows are eligible.
    - Match only audiences where audience.school is in {X} ∪ Anc(X).
    - Never include descendants of X.
    - Org Communication Audience does not define an explicit global/organization mode,
      so School scope does not include global rows.
    """

    def _as_bool(value) -> bool:
        return value in (1, "1", True)

    def _get_enabled_recipient_flags(aud) -> set[str]:
        flags = set()
        if _as_bool(aud.to_staff):
            flags.add("to_staff")
        if _as_bool(aud.to_students):
            flags.add("to_students")
        if _as_bool(aud.to_guardians):
            flags.add("to_guardians")
        if _as_bool(aud.to_community):
            flags.add("to_community")
        return flags

    def _get_user_recipient_flags() -> set[str]:
        flags = set()
        staff_roles = {
            "Academic Staff",
            "Instructor",
            "Employee",
            "Academic Admin",
            "Assistant Admin",
            "System Manager",
        }
        if set(roles or []) & staff_roles:
            flags.add("to_staff")
        if "Student" in roles:
            flags.add("to_students")
        if "Guardian" in roles:
            flags.add("to_guardians")
        if not flags and user and user != "Guest":
            flags.add("to_community")
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

    def _school_scope_match(aud_school, include_descendants, user_school_name, descendants_cache):
        if not aud_school or not user_school_name:
            return False
        if _as_bool(include_descendants):
            if aud_school not in descendants_cache:
                try:
                    descendants_cache[aud_school] = set(get_descendant_schools(aud_school) or [])
                except Exception:
                    descendants_cache[aud_school] = set()
            return user_school_name == aud_school or user_school_name in descendants_cache[aud_school]
        return user_school_name == aud_school

    # Normalize "All"/empty
    if filter_team in ("All", "", None):
        filter_team = None
    if filter_student_group in ("All", "", None):
        filter_student_group = None
    if filter_school in ("All", "", None):
        filter_school = None

    # Defensive: scope filters are mutually exclusive (student_group > team > school).
    # NOTE: Org Communication Audience only defines School Scope / Team / Student Group.
    # There is no explicit global/organization audience mode to include here.
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

    is_academic_admin = "Academic Admin" in roles

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
            "to_community",
        ],
    )

    if not audiences:
        return False

    user_school = employee.get("school") if employee else None
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

    needs_instructor_groups = filter_student_group is not None or any(
        (a.target_mode or "").strip() == "Student Group" for a in audiences
    )
    instructor_groups: set[str] = set()
    if needs_instructor_groups and not is_academic_admin:
        instructor_groups = _get_instructor_groups(user, employee)

    descendants_cache: dict[str, set[str]] = {}

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

        enabled_recipients = _get_enabled_recipient_flags(aud)
        if not enabled_recipients:
            continue
        if user_recipient_flags and not (enabled_recipients & user_recipient_flags):
            continue

        if filter_student_group:
            if target_mode != "Student Group" or aud.student_group != filter_student_group:
                continue
            if is_academic_admin:
                return True
            if aud.student_group and aud.student_group in instructor_groups:
                return True
            continue

        if filter_team:
            if target_mode != "Team" or aud.team != filter_team:
                continue
            if is_academic_admin:
                return True
            if aud.team and aud.team in user_teams:
                return True
            continue

        if target_mode == "School Scope":
            if filter_school_scope is not None and aud.school:
                if aud.school not in filter_school_scope:
                    continue
            if _school_scope_match(
                aud.school,
                aud.include_descendants,
                user_school,
                descendants_cache,
            ):
                return True
            continue

        if target_mode == "Team":
            if aud.team and (is_academic_admin or aud.team in user_teams):
                return True
            continue

        if target_mode == "Student Group":
            if aud.student_group and (is_academic_admin or aud.student_group in instructor_groups):
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
        if _as_bool(aud.to_community):
            recipients.append("Community")
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
            "to_community",
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
        scope_label = "Whole community"
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
            "scope_label": "Whole community",
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


@frappe.whitelist()
def post_activity_communication_interaction(
    org_communication: str,
    intent_type: str | None = None,
    reaction_code: str | None = None,
    note: str | None = None,
    surface: str | None = "Portal Feed",
):
    from ifitwala_ed.setup.doctype.communication_interaction.communication_interaction import (
        upsert_communication_interaction,
    )

    return upsert_communication_interaction(
        org_communication=org_communication,
        intent_type=intent_type,
        reaction_code=reaction_code,
        note=note,
        surface=surface,
    )
