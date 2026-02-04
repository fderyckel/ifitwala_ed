# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/stock/doctype/location_type/location_type.py

import frappe
from frappe.model.document import Document
from frappe import _

class LocationType(Document):
	def validate(self):
		# A structural container cannot be schedulable
		if self.is_container and self.is_schedulable:
			frappe.throw(_("Location Type cannot be both a container and schedulable."))

