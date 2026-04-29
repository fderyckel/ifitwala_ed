# ifitwala_ed/www/calendar/subscriptions/staff/index.py

import frappe

from ifitwala_ed.api.calendar_subscription import serve_staff_calendar_subscription


def get_context(context):
    path = frappe.request.path if hasattr(frappe, "request") else ""
    token = (path.rstrip("/").split("/")[-1] or "").strip()

    context.no_cache = 1
    context.noindex = 1

    serve_staff_calendar_subscription(token)
    return context
