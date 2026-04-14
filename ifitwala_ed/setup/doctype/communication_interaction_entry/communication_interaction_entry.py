# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/communication_interaction_entry/communication_interaction_entry.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

MAX_NOTE_LENGTH = 300
DOCTYPE = "Communication Interaction Entry"

REACTION_INTENT_MAP = {
    "like": "Acknowledged",
    "thank": "Appreciated",
    "heart": "Support",
    "smile": "Positive",
    "applause": "Celebration",
    "question": "Question",
    "concern": "Concern",
}
INTENT_REACTION_MAP = {value: key for key, value in REACTION_INTENT_MAP.items()}
STRUCTURED_FEEDBACK_INTENTS = {
    "Acknowledged",
    "Appreciated",
    "Question",
    "Concern",
    "Other",
    "Support",
    "Positive",
    "Celebration",
}


class CommunicationInteractionEntry(Document):
    def validate(self):
        self._normalize_note()
        self._infer_intent_and_reaction_defaults()
        self._ensure_has_payload()
        self._infer_audience_type_if_missing()
        self._apply_mode_constraints()

    def _normalize_note(self):
        self.note = (self.note or "").strip()
        if len(self.note) > MAX_NOTE_LENGTH:
            self.note = self.note[:MAX_NOTE_LENGTH]

    def _infer_intent_and_reaction_defaults(self):
        if self.reaction_code and not (self.intent_type or "").strip():
            self.intent_type = REACTION_INTENT_MAP.get((self.reaction_code or "").strip(), self.intent_type)

        if self.note and not (self.intent_type or "").strip():
            self.intent_type = "Comment"

        if (self.intent_type or "").strip() and not (self.reaction_code or "").strip():
            self.reaction_code = INTENT_REACTION_MAP.get((self.intent_type or "").strip(), self.reaction_code)

    def _ensure_has_payload(self):
        if (self.note or "").strip():
            return
        if (self.reaction_code or "").strip():
            return
        if (self.intent_type or "").strip():
            return
        frappe.throw(_("Interaction entries require a note, reaction, or intent."))

    def _infer_audience_type_if_missing(self):
        if self.audience_type:
            return

        roles = set(frappe.get_roles(self.user))
        if "Guardian" in roles:
            self.audience_type = "Guardian"
        elif "Student" in roles:
            self.audience_type = "Student"
        elif roles & {"Employee", "Academic Staff", "Academic Admin", "System Manager", "Academic Assistant"}:
            self.audience_type = "Staff"

    def _apply_mode_constraints(self):
        parent = frappe.get_cached_doc("Org Communication", self.org_communication)
        mode = (parent.interaction_mode or "None").strip() or "None"

        if mode == "None":
            frappe.throw(_("Interactions are disabled for this communication."))

        if mode == "Staff Comments":
            self._apply_staff_comments_constraints(parent)
            return

        if mode == "Structured Feedback":
            self._apply_structured_feedback_constraints(parent)
            return

        if mode == "Student Q&A":
            self._apply_student_qa_constraints(parent)
            return

        frappe.throw(_("Unknown interaction mode: {interaction_mode}").format(interaction_mode=mode))

    def _apply_staff_comments_constraints(self, parent):
        if self.audience_type != "Staff":
            frappe.throw(_("Only staff can interact on this communication."))

        if self.note and not (self.intent_type or "").strip():
            self.intent_type = "Comment"

        self.visibility = "Public to audience"

        if parent.allow_private_notes:
            self.visibility = "Public to audience"

    def _apply_structured_feedback_constraints(self, parent):
        intent_type = (self.intent_type or "").strip()
        if intent_type not in STRUCTURED_FEEDBACK_INTENTS:
            frappe.throw(_("Invalid intent type for structured feedback."))

        if intent_type in {"Question", "Concern"}:
            self.visibility = "Private to school" if parent.allow_private_notes else "Hidden"
        elif not self.visibility:
            self.visibility = "Public to audience"

        if not parent.allow_public_thread and self.note and self.visibility == "Public to audience":
            self.visibility = "Private to school"

    def _apply_student_qa_constraints(self, parent):
        roles = set(frappe.get_roles(self.user))
        is_teacher = bool(roles & {"Academic Staff", "Academic Admin", "Employee", "System Manager"})

        self.is_teacher_reply = 1 if is_teacher else 0

        if not is_teacher:
            if not (self.intent_type or "").strip():
                self.intent_type = "Question"
            if not self.note:
                frappe.throw(_("Please add a short question or comment."))
            self.visibility = "Public to audience" if parent.allow_public_thread else "Private to school"
            return

        if not self.note:
            frappe.throw(_("Teacher replies must include a note."))


def on_doctype_update():
    frappe.db.add_index(
        DOCTYPE,
        ["org_communication", "creation"],
        index_name="idx_comm_interaction_entry_comm_creation",
    )
    frappe.db.add_index(
        DOCTYPE,
        ["org_communication", "user", "creation"],
        index_name="idx_comm_interaction_entry_comm_user_creation",
    )
