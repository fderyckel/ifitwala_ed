# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import get_descendants_of

def get_accessible_schools(user):
    """Return all schools a user can access based on their default school."""
    default_school = frappe.defaults.get_user_default("school")
    if not default_school:
        return []

    # Get all child schools if the default is a parent
    descendant_schools = get_descendants_of("School", default_school)
    
    # Include the parent itself
    return [default_school] + descendant_schools
