# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from ifitwala_ed.utilities.school_tree import get_ancestor_schools

def check_audience_match(comm_name, user, roles, employee, filter_team=None, filter_student_group=None):
    """
    Checks if the current user (employee) matches the audience criteria
    for a given Org Communication.
    
    Optional filters:
    - filter_team: If set, only returns True if the matched audience is specifically for this team.
    - filter_student_group: If set, only returns True if the matched audience is specifically for this group.
    """
    if "System Manager" in roles:
        # If filtering, even Sys Man adheres to the filter constraint (i.e. does this comm have this specific audience?)
        # BUT, usually Sys Man sees everything.
        # If I am acting as Sys Man and I filter by "Group A", I expect to see msgs to "Group A".
        # So we should probably NOT return True immediately if filters are present.
        if not filter_team and not filter_student_group:
            return True

    audiences = frappe.get_all("Org Communication Audience",
        filters={"parent": comm_name},
        fields=["target_group", "school", "team", "program", "student_group"]
    )

    if not audiences: return False

    # 1. Determine User's "Scope of View" relative to the audience row
    # We want inheritance based on the audience row's school (not the parent doc's school).
    # If I am at School B (child), I should see comms targeted to School A (ancestor).
    user_school = None
    valid_target_schools = []

    if employee and employee.school:
        user_school = employee.school
        # Include the user's school and all its ancestors (inherit upwards)
        valid_target_schools = get_ancestor_schools(user_school)

    for aud in audiences:
        # --- FILTER CHECKS ---
        if filter_team and aud.team != filter_team:
            continue
        if filter_student_group and aud.student_group != filter_student_group:
            continue

        # --- HIERARCHY CHECK ---
        # If the audience targets a specific school, it must be in my ancestor scope.
        if aud.school:
            if not user_school: continue
            if aud.school not in valid_target_schools: continue

        # --- TARGET GROUP CHECK ---
        match_found = False

        if aud.target_group == "Whole Community": match_found = True
        elif aud.target_group == "Whole Staff": match_found = True

        elif aud.target_group == "Academic Staff" and ("Academic Staff" in roles or "Instructor" in roles):
            match_found = True
        elif aud.target_group == "Support Staff" and "Academic Staff" not in roles:
            match_found = True

        elif aud.team and employee and employee.department == aud.team:
            match_found = True
            
        elif aud.student_group:
            # Check if user is linked to this student group (e.g. as Instructor)
            # This is expensive if we do a DB call per row.
            # Ideally, we pass in the user's allowed groups.
            # For now, let's assume if the filter passed (permission checked in API), AND the audience matches the filter, we are good.
            # But if NO filter is set, and we encounter a student_group audience, should we match?
            # Only if the user is an instructor for it.
            # Let's do a quick optimized check or pass in allowed_groups.
            # For this iteration, let's assume validation happened before calling this if filtering.
            # If not filtering, we skip student_group rows unless we strictly check permissions.
            # Let's rely on the caller to handle specific SG permission if filtering.
            # If NOT filtering, "Whole Staff" shouldn't see "Student Group A" messages unless they are involved.
            # So we need a check.
            if is_instructor_for_group(user, aud.student_group):
                match_found = True

        if match_found: return True

    return False

def is_instructor_for_group(user, student_group):
    # Determine if user is an instructor for this group.
    # Check `tabStudent Group Instructor`
    return frappe.db.exists("Student Group Instructor", {"parent": student_group, "instructor": frappe.db.get_value("Employee", {"user_id": user}, "instructor")})

