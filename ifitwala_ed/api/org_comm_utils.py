# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from ifitwala_ed.utilities.school_tree import get_ancestor_schools

def check_audience_match(comm_name, user, roles, employee):
    """
    Checks if the current user (employee) matches the audience criteria
    for a given Org Communication.
    """
    if "System Manager" in roles: return True

    audiences = frappe.get_all("Org Communication Audience",
        filters={"parent": comm_name},
        fields=["target_group", "school", "team", "program"]
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

        if match_found: return True

    return False
