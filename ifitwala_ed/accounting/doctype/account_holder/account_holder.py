import frappe
from frappe.model.document import Document

class AccountHolder(Document):
	def validate(self):
		if not self.organization:
			frappe.throw("Organization is required")
