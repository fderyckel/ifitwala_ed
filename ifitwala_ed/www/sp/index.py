import frappe
from frappe import _

def get_context(context):
    """
    Builds the context for the student portal index page.
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    user = frappe.get_doc("User", frappe.session.user)
    context.user = user

    # Check if the user has the "Student" role (version-independent)
    roles = frappe.get_roles(frappe.session.user)
    if "Student" not in roles:
        frappe.throw(
            _("You do not have permission to access this page."),
            frappe.PermissionError
        )

    context.no_cache = 1

    # Add user's first name to the context
    context.first_name = user.first_name

    return context