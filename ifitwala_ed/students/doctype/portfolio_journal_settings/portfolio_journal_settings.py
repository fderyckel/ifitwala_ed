# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/portfolio_journal_settings/portfolio_journal_settings.py

import frappe
from frappe import _
from frappe.model.document import Document


class PortfolioJournalSettings(Document):
	def validate(self):
		if self.school and not self.organization:
			self.organization = frappe.db.get_value("School", self.school, "organization")
		if not self.organization:
			frappe.throw(_("Organization is required."))

		if self.share_link_max_days is not None and int(self.share_link_max_days) < 1:
			frappe.throw(_("Share Link Max Days must be at least 1."))
		if self.export_purge_days is not None and int(self.export_purge_days) < 1:
			frappe.throw(_("Export Purge Days must be at least 1."))

		self._seed_default_roles()

	def _seed_default_roles(self):
		if self.moderation_roles:
			return
		for role in ("Academic Admin", "Academic Staff"):
			self.append(
				"moderation_roles",
				{
					"role": role,
					"can_moderate_showcase": 1,
					"can_moderate_reflection": 0,
				},
			)
