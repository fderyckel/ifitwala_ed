# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe

### THis creates quite a bit of issues in when we call the html card contact.
### Contact should be the primary way to deal with all contact information (tel, email, address)
## the doctype have link to doctype so it should be straight forward. 

def update_profile_from_contact(doc, method=None):
    """Update the main doctype if changes made on Contact DocType.
		Called by hooks.py"""

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

    #### I think this is what created all my issues!!!!
    #if student:
    #    student_doc = frappe.get_doc("Student", student)
    #    student_doc.student_mobile_phone = primary_mobile
    #    student_doc.save()    
