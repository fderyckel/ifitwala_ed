# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/org_communication_interactions/org_communication_interactions.py

import frappe
from frappe import _
from frappe.model.document import Document

MAX_NOTE_LENGTH = 300

class OrgCommunicationInteraction(Document):
	def validate(self):
		self._normalize_note()
		self._ensure_single_row_per_user()
		self._infer_audience_type_if_missing()
		self._apply_mode_constraints()

	def _normalize_note(self):
		if self.note:
			self.note = (self.note or "").strip()
			if len(self.note) > MAX_NOTE_LENGTH:
				self.note = self.note[:MAX_NOTE_LENGTH]

	def _ensure_single_row_per_user(self):
		"""Guarantee at most one interaction per (org_communication, user)."""
		if not self.org_communication or not self.user:
			return

		# Only check when new / renamed to avoid useless queries
		if self.is_new():
			existing_name = frappe.db.get_value(
				"Org Communication Interaction",
				{
					"org_communication": self.org_communication,
					"user": self.user,
				},
				"name",
			)
			if existing_name and existing_name != self.name:
				# Instead of creating duplicates, we ask caller to use 'upsert' API
				frappe.throw(
					_("You already interacted with this communication. Please update the existing interaction."),
					title=_("Duplicate Interaction"),
				)

	def _infer_audience_type_if_missing(self):
		if self.audience_type:
			return

		roles = set(frappe.get_roles(self.user))
		if "Guardian" in roles:
			self.audience_type = "Guardian"
		elif "Student" in roles:
			self.audience_type = "Student"
		elif "Employee" in roles or "Academic Staff" in roles or "Academic Admin" in roles:
			self.audience_type = "Staff"
		else:
			self.audience_type = "Community"

	def _apply_mode_constraints(self):
		parent = frappe.get_cached_doc("Org Communication", self.org_communication)
		mode = (parent.interaction_mode or "None").strip() or "None"

		if mode == "None":
			frappe.throw(_("Interactions are disabled for this communication."))

		if mode == "Staff Comments":
			self._apply_staff_comments_constraints(parent)
		elif mode == "Structured Feedback":
			self._apply_structured_feedback_constraints(parent)
		elif mode == "Student Q&A":
			self._apply_student_qa_constraints(parent)
		else:
			frappe.throw(_("Unknown interaction mode: {0}").format(mode))

	def _apply_staff_comments_constraints(self, parent):
		# Staff-only, public thread, short comments
		if self.audience_type != "Staff":
			frappe.throw(_("Only staff can interact on this communication."))

		self.visibility = "Public to audience"

		# reaction_code optional, note optional but must be short (already normalized)
		# No private notes in this mode
		if parent.allow_private_notes:
			# For safety, we still force public
			self.visibility = "Public to audience"

	def _apply_structured_feedback_constraints(self, parent):
		allowed = {"Acknowledged", "Appreciated", "Question", "Concern", "Other"}
		if self.intent_type not in allowed:
			frappe.throw(_("Invalid intent type for structured feedback."))

		# Map intent to default visibility
		if self.intent_type in {"Question", "Concern"}:
			self.visibility = "Private to school" if parent.allow_private_notes else "Hidden"
		else:
			# Acknowledged / Appreciated: we can keep as public-to-audience if we ever
			# want to show aggregates per audience; individual notes stay private in UI.
			if not self.visibility:
				self.visibility = "Public to audience"

		# Enforce no public comment thread if not allowed
		if not parent.allow_public_thread and self.note:
			# Note is allowed but will not be exposed as a visible thread to others;
			# UI will treat it like a private message to school.
			if self.visibility == "Public to audience":
				self.visibility = "Private to school"

		# reaction_code can mirror intent_type if not explicitly set
		if not self.reaction_code:
			mapper = {
				"Acknowledged": "like",
				"Appreciated": "thank",
				"Question": "question",
				"Concern": "concern",
			}
			self.reaction_code = mapper.get(self.intent_type, "other")

	def _apply_student_qa_constraints(self, parent):
		roles = set(frappe.get_roles(self.user))
		is_teacher = any(r in roles for r in ("Academic Staff", "Academic Admin"))

		self.is_teacher_reply = 1 if is_teacher else 0

		# Students: must be able to ask questions; short text required
		if not is_teacher:
			# Treat anything from student as Question/Other
			if not self.intent_type:
				self.intent_type = "Question"
			if not self.note:
				frappe.throw(_("Please add a short question or comment."))
			# Visibility: usually public within group
			if parent.allow_public_thread:
				self.visibility = "Public to audience"
			else:
				self.visibility = "Private to school"

		# Teachers: can reply, pin, resolve
		if is_teacher:
			if not self.note:
				frappe.throw(_("Teacher replies must include a note."))
			# If teacher marks resolved, that's allowed
			# Pinning handled by UI / separate action

		# Optionally enforce that Student Q&A only makes sense with a student_group
		if not self.student_group and parent.interaction_mode == "Student Q&A":
			# Soft guard: you can tighten this later if needed
			pass
