import frappe
from frappe import _

def get_context(context):
    """
    Builds the context for the student portal index page.
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"  # Set redirect location
        raise frappe.Redirect  # Raise the Redirect exception

    context.user = frappe.get_doc("User", frappe.session.user)

    # Check if the user has the "Student" role (version-independent)
    roles = frappe.get_roles(frappe.session.user)
    if "Student" not in roles:
        frappe.throw(
            _("You do not have permission to access this page."),
            frappe.PermissionError
        )

    context.no_cache = 1

    return context