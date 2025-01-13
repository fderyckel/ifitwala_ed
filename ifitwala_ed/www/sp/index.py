import frappe

def get_context(context):
    """
    Builds the context for the student portal index page.
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.redirect_to_login()

    context.user = frappe.get_doc("User", frappe.session.user)

    # Check if the user has the "Student" role
    if "Student" not in context.user.get_roles():
        frappe.throw(
            _("You do not have permission to access this page."),
            frappe.PermissionError
        )

    context.no_cache = 1 # Prevent caching to ensure fresh data on each load

    # Placeholder for future data fetching from server if needed