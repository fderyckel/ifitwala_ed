# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ContactAccessLog(Document):
    def _created_by_contact_service(self) -> bool:
        flags = getattr(self, "flags", None)
        if hasattr(flags, "get"):
            return bool(flags.get("from_contact_privacy_service"))
        return bool(getattr(flags, "from_contact_privacy_service", False))

    def before_insert(self):
        if not self._created_by_contact_service():
            frappe.throw(
                _("Contact Access Log entries must be created by the contact privacy service."),
                frappe.PermissionError,
            )

    def before_save(self):
        if not self.is_new():
            frappe.throw(_("Contact Access Log entries are immutable."))

    def before_delete(self):
        frappe.throw(_("Contact Access Log entries cannot be deleted."))
