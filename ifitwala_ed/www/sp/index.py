import frappe

def get_context(context):
    """
    Prepares the context for the Student Portal (sp.html).
    """
    context.title = "Student Portal"
    return context
