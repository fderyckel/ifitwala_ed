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

    # student = next((link.link_name for link in doc.links if link.link_doctype == "Student"), None)
    guardian = next((link.link_name for link in doc.links if link.link_doctype == "Guardian"), None)
    # employee = next((link.link_name for link in doc.links if link.link_doctype == "Employee"), None)
    primary_mobile = next((p.phone for p in doc.phone_nos if p.is_primary_mobile_no), None)

    if guardian:
        guardian_doc = frappe.get_doc("Guardian", guardian)
        changed = False

        salutation = (doc.salutation or "").strip()
        if salutation and salutation != (guardian_doc.salutation or "").strip():
            guardian_doc.salutation = salutation
            changed = True

        gender = (doc.gender or "").strip()
        if gender and gender != (guardian_doc.guardian_gender or "").strip():
            guardian_doc.guardian_gender = gender
            changed = True

        mobile = (primary_mobile or "").strip()
        if mobile and mobile != (guardian_doc.guardian_mobile_phone or "").strip():
            guardian_doc.guardian_mobile_phone = mobile
            changed = True

        if changed:
            guardian_doc.save(ignore_permissions=True)


from frappe.contacts.address_and_contact import has_permission as _core_has_permission  # noqa: E402


# ------------------------------------------------------------------ #
#  Doc‑level gate
# ------------------------------------------------------------------ #
def contact_has_permission(doc, ptype, user):
    """Defer Contact permission checks to the Frappe core implementation."""
    return _core_has_permission(doc, ptype, user)


# ------------------------------------------------------------------ #
#  List / report filter
# ------------------------------------------------------------------ #
def contact_permission_query_conditions(user):
    """Do not add app-level list scoping on top of Contact DocPerm rules."""
    return ""
