# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/portfolio_share_link/portfolio_share_link.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class PortfolioShareLink(Document):
    def validate(self):
        if self.scope != "Showcase Only":
            frappe.throw(_("Portfolio share links support Showcase Only scope."))
        if self.access_mode != "view":
            frappe.throw(_("Portfolio share links are view-only."))
        if not self.token_hash:
            frappe.throw(_("Token hash is required."))
        if self.expires_on and getdate(self.expires_on) < getdate(nowdate()):
            frappe.throw(_("Expiry date cannot be in the past."))
        if not self.created_by_user:
            self.created_by_user = frappe.session.user

        if self.portfolio and (not self.school or not self.organization):
            ctx = frappe.db.get_value(
                "Student Portfolio",
                self.portfolio,
                ["school", "organization"],
                as_dict=True,
            )
            if ctx:
                self.school = self.school or ctx.get("school")
                self.organization = self.organization or ctx.get("organization")
