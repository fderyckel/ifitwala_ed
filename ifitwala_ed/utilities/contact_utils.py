# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe

### THis creates quite a bit of issues in when we call the html card contact.
### Contact should be the primary way to deal with all contact information (tel, email, address)
## the doctype have link to doctype so it should be straight forward. 

def update_profile_from_contact(doc, method=None):
    """Update the main doctype if changes made on Contact DocType.
		Called by hooks.py"""
    
    if frappe.flags.get("skip_contact_to_guardian_sync"):
        return

    #student = next((l.link_name for l in doc.links if l.link_doctype == "Student"), None)
    guardian = next((l.link_name for l in doc.links if l.link_doctype == "Guardian"), None)
    #employee = next((l.link_name for l in doc.links if l.link_doctype == "Employee"), None)
    primary_mobile = next((p.phone for p in doc.phone_nos if p.is_primary_mobile_no), None)

    if guardian:
        guardian_doc = frappe.get_doc("Guardian", guardian)
        guardian_doc.salutation = doc.salutation
        guardian_doc.guardian_gender = doc.gender
        guardian_doc.guardian_mobile_phone = primary_mobile
        guardian_doc.save()

from frappe.contacts.address_and_contact import has_permission as _core_has_permission

# ------------------------------------------------------------------ #
#  Doc‑level gate
# ------------------------------------------------------------------ #
def contact_has_permission(doc, ptype, user):
    """Allow Academic Admin to read any Contact that links to a Student he/she can read."""
    # Non‑read checks → fall back
    if ptype != "read":
        return _core_has_permission(doc, ptype, user)

    # Site owner always ok
    if user == "Administrator":
        return True

    if "Academic Admin" in frappe.get_roles(user):
        for link in doc.links:
            if (
                link.link_doctype == "Student"
                and frappe.has_permission("Student", "read", user=user, doc=link.link_name)
            ):
                return True

    # Everything else → default logic (owner, other roles, etc.)
    return _core_has_permission(doc, ptype, user)


# ------------------------------------------------------------------ #
#  List / report filter
# ------------------------------------------------------------------ #
def contact_permission_query_conditions(user):
    """Academic Admin sees only contacts that reference a Student."""
    if "Academic Admin" not in frappe.get_roles(user):
        return ""   # everyone else — no extra condition

    return """
        EXISTS (
            SELECT 1 FROM `tabDynamic Link` dl
            WHERE dl.parent = `tabContact`.name
              AND dl.parenttype = 'Contact'
              AND dl.link_doctype = 'Student'
        )
    """
