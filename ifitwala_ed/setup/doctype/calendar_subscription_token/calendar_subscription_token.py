# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/calendar_subscription_token/calendar_subscription_token.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

STAFF_FEED_TYPE = "staff_calendar"
STAFF_SUBJECT_TYPE = "Staff"
VALID_STATUSES = {"Active", "Revoked"}


class CalendarSubscriptionToken(Document):
    def validate(self):
        self.user = (self.user or "").strip()
        self.employee = (self.employee or "").strip() or None
        self.feed_type = (self.feed_type or STAFF_FEED_TYPE).strip()
        self.subject_type = (self.subject_type or STAFF_SUBJECT_TYPE).strip()
        self.status = (self.status or "Active").strip()
        self.token_hash = (self.token_hash or "").strip()
        self.token_hint = (self.token_hint or "").strip() or None

        if not self.user:
            frappe.throw(_("User is required."))
        if not self.token_hash:
            frappe.throw(_("Token hash is required."))
        if self.feed_type != STAFF_FEED_TYPE:
            frappe.throw(_("Unsupported calendar subscription feed type."))
        if self.subject_type != STAFF_SUBJECT_TYPE:
            frappe.throw(_("Unsupported calendar subscription subject type."))
        if self.status not in VALID_STATUSES:
            frappe.throw(_("Unsupported calendar subscription status."))
        if self.employee:
            employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
            if employee_user and employee_user != self.user:
                frappe.throw(_("Calendar subscription Employee must belong to the subscription User."))


def on_doctype_update():
    frappe.db.add_index("Calendar Subscription Token", fields=["user", "feed_type", "subject_type", "status"])
    frappe.db.add_index("Calendar Subscription Token", fields=["employee", "feed_type", "status"])
