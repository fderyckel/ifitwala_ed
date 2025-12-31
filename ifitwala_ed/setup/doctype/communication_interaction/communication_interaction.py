# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/communication_interaction/communication_interaction.py

import frappe
from frappe import _
from frappe.model.document import Document

MAX_NOTE_LENGTH = 300
DOCTYPE = "Communication Interaction"

class CommunicationInteraction(Document):
	def validate(self):
		self._normalize_note()
		self._ensure_single_row_per_user()
		self._infer_audience_type_if_missing()

		if self.note and not (self.intent_type or "").strip():
			self.intent_type = "Comment"

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
				DOCTYPE,
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
		allowed = {
			"Acknowledged",
			"Appreciated",
			"Question",
			"Concern",
			"Other",
			"Support",
			"Positive",
			"Celebration",
		}
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
				"Support": "heart",
				"Positive": "smile",
				"Celebration": "applause",
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

@frappe.whitelist()
def get_org_comm_interaction_summary(comm_names=None):
	"""
	Return interaction summary for a list of Org Communication names.
	Safe against missing/empty args (returns {}).
	"""
	# Allow comm_names passed as JSON string from the client
	if isinstance(comm_names, str):
		try:
			comm_names = frappe.parse_json(comm_names)
		except Exception:
			comm_names = None

	comm_names = comm_names or []
	if not isinstance(comm_names, (list, tuple)):
		comm_names = [comm_names]

	# Trim + de-dupe
	clean_names = []
	seen = set()
	for n in comm_names:
		if not n:
			continue
		n = str(n).strip()
		if not n or n in seen:
			continue
		seen.add(n)
		clean_names.append(n)

	if not clean_names:
		return {}

	user = frappe.session.user

	# Initialise summary with a clean shape
	summary = {
		name: {
			"counts": {},       # intent_type -> count
			"reaction_counts": {},  # reaction_code -> count
			"reactions_total": 0,   # total emoji/quick reactions
			"comments_total": 0,    # total thread entries (Comment + Question)
			"self": None,       # current user's row
		}
		for name in clean_names
	}

	comms_tuple = tuple(clean_names)

	# 1) counts per communication + intent
	rows = frappe.db.sql(
		"""
		SELECT org_communication, intent_type, COUNT(*) as cnt
		FROM `tabCommunication Interaction`
		WHERE org_communication IN %(comms)s
		GROUP BY org_communication, intent_type
		""",
		{"comms": comms_tuple},
		as_dict=True,
	)

	for r in rows:
		org_comm = r.get("org_communication")
		if org_comm not in summary:
			continue
		intent = (r.get("intent_type") or "Comment").strip() or "Comment"
		summary[org_comm]["counts"][intent] = int(r.get("cnt") or 0)

	# 2) reaction_counts per communication + reaction_code
	intent_to_reaction = {
		"Acknowledged": "like",
		"Appreciated": "thank",
		"Support": "heart",
		"Positive": "smile",
		"Celebration": "applause",
		"Question": "question",
		"Concern": "concern"
	}
	known_reaction_codes = set(intent_to_reaction.values())

	reaction_rows = frappe.db.sql(
		"""
		SELECT org_communication, reaction_code, intent_type, COUNT(*) as cnt
		FROM `tabCommunication Interaction`
		WHERE org_communication IN %(comms)s
		GROUP BY org_communication, reaction_code, intent_type
		""",
		{"comms": comms_tuple},
		as_dict=True,
	)

	for r in reaction_rows:
		org_comm = r.get("org_communication")
		if org_comm not in summary:
			continue
		raw_code = (r.get("reaction_code") or "").strip()
		intent = (r.get("intent_type") or "").strip()
		reaction_code = raw_code or intent_to_reaction.get(intent, "")
		if not reaction_code:
			continue

		reaction_counts = summary[org_comm]["reaction_counts"]
		reaction_counts[reaction_code] = reaction_counts.get(reaction_code, 0) + int(r.get("cnt") or 0)

	# Sum reaction totals
	for data in summary.values():
		reaction_counts = data.get("reaction_counts") or {}
		for code in known_reaction_codes:
			reaction_counts.setdefault(code, 0)
		data["reaction_counts"] = reaction_counts
		data["reactions_total"] = sum(int(v or 0) for v in reaction_counts.values())

	# 3) comments_total = interactions with non-empty note (thread entries)
	comments_rows = frappe.db.sql(
		"""
		SELECT org_communication, COUNT(*) as cnt
		FROM `tabCommunication Interaction`
		WHERE org_communication IN %(comms)s
			AND COALESCE(TRIM(note), '') != ''
			AND visibility != 'Hidden'
		GROUP BY org_communication
		""",
		{"comms": comms_tuple},
		as_dict=True,
	)

	for r in comments_rows:
		org_comm = r.get("org_communication")
		if org_comm in summary:
			summary[org_comm]["comments_total"] = int(r.get("cnt") or 0)


	# 4) current user's interaction (keep full row)
	self_rows = frappe.db.sql(
		"""
		SELECT *
		FROM `tabCommunication Interaction`
		WHERE org_communication IN %(comms)s
		  AND user = %(user)s
		""",
		{"comms": comms_tuple, "user": user},
		as_dict=True,
	)

	for r in self_rows:
		org_comm = r.get("org_communication")
		if org_comm in summary:
			summary[org_comm]["self"] = r

	return summary


@frappe.whitelist()
def get_communication_thread(org_communication: str, limit_start: int = 0, limit_page_length: int = 20):
	"""
	Return the visible interaction thread for a given Org Communication,
	for use on Staff Comments and Student Q&A surfaces.

	- Respects interaction_mode on Org Communication
	- Applies visibility rules based on audience and role
	- Orders pinned items first, then by creation time
	"""
	if not org_communication:
		return []

	try:
		limit_start = int(limit_start or 0)
		limit_page_length = int(limit_page_length or 20)
	except ValueError:
		limit_start = 0
		limit_page_length = 20

	user = frappe.session.user
	parent = frappe.get_cached_doc("Org Communication", org_communication)
	mode = (parent.interaction_mode or "None").strip() or "None"

	roles = set(frappe.get_roles(user))
	is_staff = any(r in roles for r in ("Academic Staff", "Academic Admin", "Employee", "System Manager"))
	is_student = "Student" in roles
	is_guardian = "Guardian" in roles

	# Structured Feedback → no public thread for non-staff
	if mode == "Structured Feedback" and not is_staff:
		return []

	# Base conditions
	conditions = ["i.org_communication = %(comm)s"]
	conditions.append("COALESCE(TRIM(i.note), '') != ''")
	conditions.append("i.visibility != 'Hidden'")
	params = {
		"comm": org_communication,
		"user": user,
		"limit_start": limit_start,
		"limit_page_length": limit_page_length,
	}

	# Visibility rules by mode
	if mode == "Staff Comments":
		# Staff-only thread
		if not is_staff:
			return []

	elif mode == "Student Q&A":
		if is_staff:
			# Teachers/staff: see everything except hidden
			pass
		else:
			# Students: see public + their own (even if private)
			conditions.append(
				"(i.visibility = 'Public to audience' OR i.user = %(user)s)"
			)

	elif mode == "Structured Feedback":
		# At this point we already know user is staff (non-staff returned above).
		# Staff can see everything except hidden.
		pass

	else:
		# Other modes: treat as no thread
		return []

	where_clause = " AND ".join(conditions)
	params["ts_fmt"] = "%Y-%m-%d %H:%i:%s"

	# Single SQL with join to get user full_name (no extra calls)
	rows = frappe.db.sql(
		f"""
		SELECT
			i.name,
			i.user,
			u.full_name,
			i.audience_type,
			i.intent_type,
			i.reaction_code,
			i.note,
			i.visibility,
			i.is_teacher_reply,
			i.is_pinned,
			i.is_resolved,
			DATE_FORMAT(CONVERT_TZ(i.creation, 'UTC', @@session.time_zone), %(ts_fmt)s) as creation,
			i.modified
		FROM `tabCommunication Interaction` i
		LEFT JOIN `tabUser` u ON u.name = i.user
		WHERE {where_clause}
		ORDER BY i.is_pinned DESC, i.creation ASC
		LIMIT %(limit_start)s, %(limit_page_length)s
		""",
		params,
		as_dict=True,
	)

	return rows

@frappe.whitelist()
def upsert_communication_interaction(
	org_communication: str,
	intent_type: str | None = None,
	reaction_code: str | None = None,
	note: str | None = None,
	surface: str | None = None,
	student_group: str | None = None,
	program: str | None = None,
	school: str | None = None,
):
	"""
	Create or update the current user's interaction on a given Org Communication.

	Single entry per (org_communication, user):
	- If an interaction exists, update it.
	- Otherwise, create a new one.

	Mode rules (Staff Comments / Structured Feedback / Student Q&A)
	are enforced in CommunicationInteraction.validate().
	"""
	user = frappe.session.user
	if not org_communication:
		frappe.throw(_("org_communication is required."))

	existing_name = frappe.db.get_value(
		DOCTYPE,
		{"org_communication": org_communication, "user": user},
		"name",
	)

	if existing_name:
		doc = frappe.get_doc(DOCTYPE, existing_name)
	else:
		doc = frappe.new_doc(DOCTYPE)
		doc.org_communication = org_communication
		doc.user = user

	parent = frappe.get_cached_doc("Org Communication", org_communication)
	mode = (parent.interaction_mode or "None").strip() or "None"

	reaction_intent_map = {
		"like": "Acknowledged",
		"thank": "Appreciated",
		"heart": "Support",
		"smile": "Positive",
		"applause": "Celebration",
		"question": "Question",
	}
	intent_reaction_map = {v: k for k, v in reaction_intent_map.items()}

	# Assign fields from payload (only if provided)
	if intent_type is not None:
		doc.intent_type = intent_type

	if reaction_code is not None:
		doc.reaction_code = reaction_code

	if note is not None:
		doc.note = note

	if surface is not None:
		doc.surface = surface

	if student_group is not None:
		doc.student_group = student_group
	if program is not None:
		doc.program = program
	if school is not None:
		doc.school = school

	# Infer intent from reaction or vice-versa when one side is missing
	if doc.reaction_code and not (doc.intent_type or "").strip():
		doc.intent_type = reaction_intent_map.get(doc.reaction_code, doc.intent_type)

	if (doc.intent_type or "").strip() and not (doc.reaction_code or "").strip():
		doc.reaction_code = intent_reaction_map.get(doc.intent_type, doc.reaction_code)

	# ✅ For Staff Comments: a note is a "Comment" unless explicitly a Question
	if mode == "Staff Comments":
		if doc.note and not (doc.intent_type or "").strip():
			doc.intent_type = "Comment"

	# ✅ Global normalization: note-only rows must have an intent for counting/thread consistency
	if doc.note and not (doc.intent_type or "").strip():
		doc.intent_type = "Comment"

	# Question always requires a note
	if doc.intent_type == "Question" and not doc.note:
		frappe.throw(_("Please add a short comment or question."))

	doc.save(ignore_permissions=False)
	return doc


def on_doctype_update():
	frappe.db.add_index(
		DOCTYPE,
		["org_communication", "intent_type"],
		index_name="idx_comm_intent",
	)
	frappe.db.add_index(
		DOCTYPE,
		["student_group", "intent_type"],
		index_name="idx_group_intent",
	)
