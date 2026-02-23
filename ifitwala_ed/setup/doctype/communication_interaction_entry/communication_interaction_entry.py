# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/communication_interaction_entry/communication_interaction_entry.py

import frappe
from frappe.model.document import Document

MAX_NOTE_LENGTH = 300


class CommunicationInteractionEntry(Document):
    def validate(self):
        if self.note:
            self.note = (self.note or "").strip()
            if len(self.note) > MAX_NOTE_LENGTH:
                self.note = self.note[:MAX_NOTE_LENGTH]


def on_doctype_update():
    frappe.db.add_index(
        "Communication Interaction Entry",
        ["org_communication", "creation"],
        index_name="idx_comm_interaction_entry_comm_creation",
    )
