# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student_support_guidance/student_support_guidance.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, cint, strip_html_tags
from frappe.desk.form.assign_to import add as assign_add

SSG = "Student Support Guidance"
SG = "Student Group"
SGS = "Student Group Student"
SGI = "Student Group Instructor"

ACK_TAG = "[ACK] Student Support Guidance"

class StudentSupportGuidance(Document):
	"""Lightweight lifecycle: publishing + snapshot caching is handled here."""

	def validate(self):
		# Keep counters defensively up to date (cheap – uses in-memory rows)
		self.high_priority_count = _has_any_high_priority(self)
		self.ack_required_count = _count_ack_required_items(self)

	def on_update(self):
		"""If the doc transitions to Published, ensure publish bookkeeping is applied.
		Note: counselors may also call publish(name) explicitly from the form button (recommended)."""
		# PERF: one cheap column lookup; avoid loading previous full doc
		prev_status = (frappe.db.get_value(SSG, self.name, "status") or "").strip() if not self.is_new() else ""
		if (self.status or "").strip() == "Published" and prev_status != "Published":
			_apply_publish(self, bump_version=True)

def on_doctype_update():
	# PERF: helpful single/compound indexes for frequent lookups
	frappe.db.add_index(SSG, ["student"])
	frappe.db.add_index(SSG, ["academic_year"])
	frappe.db.add_index(SSG, ["student", "academic_year"])
	frappe.db.add_index(SSG, ["student", "academic_year", "status"])
	frappe.db.add_index(SSG, ["last_published_on"])
	frappe.db.add_index("ToDo", ["reference_type", "reference_name", "allocated_to"])
	frappe.db.add_index("ToDo", ["reference_type", "reference_name", "status"])
	frappe.db.add_index("DocShare", ["share_doctype", "share_name", "user"])


# ─────────────────────────────────────────────────────────────────────────────
# Public API (whitelisted) used by Student modal
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_support_snapshot(student: str, academic_year: str) -> dict:
	ssg = _find_current_ssg(student, academic_year)
	if not ssg:
		# No SSG yet; return empty state (UI will show "No guidance yet.")
		return {"snapshot_html": ""}
	_enforce_view_permission(ssg.name if isinstance(ssg, Document) else ssg)

	# PERF: if snapshot_html already present, avoid full doc load
	if isinstance(ssg, Document):
		html = ssg.snapshot_html or _render_snapshot_html(ssg)
	else:
		html = frappe.db.get_value(SSG, ssg, "snapshot_html") or _render_snapshot_html(frappe.get_doc(SSG, ssg))
	return {"snapshot_html": html}

@frappe.whitelist()
def get_ack_status(student: str, academic_year: str) -> dict:
	# PERF: avoid full doc unless needed; fetch minimal fields
	name = _find_current_ssg_name(student, academic_year)
	if not name:
		return {"ack_required": False, "has_open_todo": False, "ack_required_count": 0, "ack_version": 0}

	_enforce_view_permission(name)
	row = frappe.db.get_value(
		SSG,
		name,
		["status", "ack_required_count", "ack_version"],
		as_dict=True,
	) or {}

	need_ack = cint(row.get("ack_required_count") or 0) > 0 and (row.get("status") or "") == "Published"
	if not need_ack:
		return {
			"ack_required": False,
			"has_open_todo": False,
			"ack_required_count": 0,
			"ack_version": cint(row.get("ack_version") or 0),
		}

	# PERF: single EXISTS check
	user = frappe.session.user
	has_open = frappe.db.exists(
		"ToDo",
		{
			"reference_type": SSG,
			"reference_name": name,
			"allocated_to": user,
			"status": "Open",
		},
	)
	return {
		"ack_required": True,
		"has_open_todo": bool(has_open),
		"ack_required_count": cint(row.get("ack_required_count") or 0),
		"ack_version": cint(row.get("ack_version") or 0),
	}

@frappe.whitelist()
def acknowledge_current_guidance(student: str, academic_year: str) -> dict:
	# PERF: no full doc unless required
	name = _find_current_ssg_name(student, academic_year)
	if not name:
		frappe.throw(_("No current guidance is available to acknowledge."))
	_enforce_view_permission(name)

	# PERF: bulk close in one SQL instead of get_all + looped set_value
	frappe.db.sql(
		"""
		UPDATE `tabToDo`
		SET status = 'Closed'
		WHERE reference_type = %s
		  AND reference_name = %s
		  AND allocated_to = %s
		  AND status = 'Open'
		""",
		(SSG, name, frappe.session.user),
	)
	return {"ok": True}

@frappe.whitelist()
def publish(name: str, notify: int = 1) -> dict:
	"""Explicit publish action counselors can call from a button on the SSG form."""
	doc = frappe.get_doc(SSG, name)
	# Only counselors / admins can publish
	roles = set(frappe.get_roles())
	if not ({"Counselor", "Academic Admin", "System Manager"} & roles):
		frappe.throw(_("You are not permitted to publish support guidance."))

	# Set publish state and apply full publish workflow (bump version, assign acks)
	doc.status = "Published"
	_apply_publish(doc, bump_version=True, notify=bool(cint(notify)))
	return {"ok": True, "ack_version": cint(doc.ack_version or 0)}


# ─────────────────────────────────────────────────────────────────────────────
# Core publish, snapshot & assignment logic
# ─────────────────────────────────────────────────────────────────────────────

def _apply_publish(doc: "StudentSupportGuidance", bump_version: bool = True, notify: bool = True):
	# 1) Stamp publish metadata
	if bump_version:
		doc.ack_version = cint(doc.ack_version or 0) + 1
	doc.last_published_on = now_datetime()
	doc.published_items = 1
	doc.high_priority_count = _has_any_high_priority(doc)
	doc.ack_required_count = _count_ack_required_items(doc)

	# 2) Render fresh snapshot into the cached HTML field
	doc.snapshot_html = _render_snapshot_html(doc)

	# 3) Save without re-triggering publish loops
	doc.save(ignore_permissions=True)

	# 4) Sync acknowledgment ToDos to current teacher-of-record recipients
	_sync_ack_assignments(doc, notify=notify)

	# 5) Ensure Desk access via DocShare for the same recipients (auto, no button needed)
	teacher_users = _teacher_userids_for_student_year(doc.student, doc.academic_year)
	_sync_docshares_for_teachers(doc.name, teacher_users)

def _sync_ack_assignments(doc: "StudentSupportGuidance", notify: bool = True):
	recipients = _teacher_userids_for_student_year(doc.student, doc.academic_year)

	# PERF: read minimal open todos in one go
	open_rows = frappe.db.get_values(
		"ToDo",
		{
			"reference_type": SSG,
			"reference_name": doc.name,
			"status": "Open",
		},
		["name", "allocated_to"],
		as_dict=True,
	)
	open_by_user = {r["allocated_to"]: r["name"] for r in (open_rows or []) if r.get("allocated_to")}

	# If there are no items that require acknowledgement, close any remnants.
	if cint(doc.ack_required_count or 0) == 0 or (doc.status or "") != "Published":
		# PERF: bulk close any open todos for this SSG
		if open_by_user:
			frappe.db.sql(
				"""
				UPDATE `tabToDo`
				SET status = 'Closed'
				WHERE name IN %(names)s
				""",
				{"names": tuple(open_by_user.values())},
			)
		return

	desc = f"{ACK_TAG} v{cint(doc.ack_version or 0)} – {doc.student} ({doc.academic_year})"

	# Add missing ToDos
	for user in recipients:
		if user not in open_by_user:
			payload = {
				"doctype": SSG,
				"name": doc.name,
				"assign_to": [user],
				"priority": "Medium",
				"description": desc,
			}
			if notify:
				payload["notify"] = 1
			assign_add(payload)

	# Close ToDos for users who are no longer recipients
	stale = [todo_name for user, todo_name in open_by_user.items() if user not in recipients]
	if stale:
		frappe.db.sql(
			"""
			UPDATE `tabToDo`
			SET status = 'Closed'
			WHERE name IN %(names)s
			""",
			{"names": tuple(stale)},
		)

# Manual, idempotent re-sync of SSG → teachers-of-record access + current-ack ToDos
@frappe.whitelist()
def resync_access(ssg_name: str):
	"""
	Idempotently re-sync access/acks for a Student Support Guidance:
	- recompute teachers-of-record from student+academic_year
	- align DocShare read grants
	- ensure current ack-version ToDos exist for current teachers and are closed for stale ones

	Permissions:
	- allowed if caller has READ on the SSG doc
	"""
	if not ssg_name:
		frappe.throw("Missing SSG name")

	# cheap fields lookup; avoid full doc load unless needed
	row = frappe.db.get_value(
		SSG,
		ssg_name,
		["student", "academic_year", "ack_version", "ack_required_count"],
		as_dict=True,
	)
	if not row:
		frappe.throw("Student Support Guidance not found")

	# basic permission gate — only proceed if user can read this SSG
	if not frappe.has_permission(doctype=SSG, doc=ssg_name, ptype="read"):
		frappe.throw("Not permitted to re-sync this record")

	student = (row.get("student") or "").strip()
	ay = (row.get("academic_year") or "").strip()
	if not student or not ay:
		frappe.throw("SSG is missing student or academic year")

	# Import here to avoid circular imports on module load
	from ifitwala_ed.students.doctype.referral_case.referral_case import _sync_ssg_access_for, _get_teachers_of_record

	# Do the sync work (ack + shares) for this SSG
	_sync_ssg_access_for(student, ay, reason="ssg-manual-resync")

	# Return a compact summary
	teachers = _get_teachers_of_record(student, ay)
	return {
		"ok": True,
		"student": student,
		"academic_year": ay,
		"ack_version": cint(row.get("ack_version") or 0),
		"ack_required_count": cint(row.get("ack_required_count") or 0),
		"current_teachers_count": len(teachers),
	}



# ─────────────────────────────────────────────────────────────────────────────
# Snapshot rendering (defensive against evolving child schema)
# ─────────────────────────────────────────────────────────────────────────────

def _render_snapshot_html(doc: "StudentSupportGuidance") -> str:
	"""Teacher-facing snapshot: include only items visible to teachers-of-student."""
	items = doc.get("items") or []
	if not items:
		return '<div class="text-muted">' + _("No guidance yet.") + "</div>"

	lines = []
	for row in items:
		# Visibility: default allow, but respect confidentiality if present
		vis = ""
		if hasattr(row, "confidentiality") and getattr(row, "confidentiality"):
			vis = (getattr(row, "confidentiality") or "").strip()
		teacher_visible = (vis == "" or vis.lower() == "teachers-of-student".lower())
		if not teacher_visible:
			continue

		# Teacher-facing text
		text = (getattr(row, "teacher_text", "") or "").strip()
		text = frappe.utils.escape_html(strip_html_tags(text)) if text else ""

		# Badges: item_type and high_priority
		item_type = (getattr(row, "item_type", "") or "").strip()
		type_badge = f'<span class="badge bg-secondary ms-1">{frappe.utils.escape_html(item_type)}</span>' if item_type else ""

		high = False
		if hasattr(row, "high_priority"):
			try:
				high = bool(int(getattr(row, "high_priority") or 0))
			except Exception:
				high = bool(getattr(row, "high_priority"))
		high_badge = '<span class="badge bg-danger ms-1">High</span>' if high else ""

		if text:
			lines.append(f'<li class="mb-1">{frappe.utils.escape_html(text)}{type_badge}{high_badge}</li>')

	if not lines:
		return '<div class="text-muted">' + _("No guidance items are published.") + "</div>"

	return '<div class="ssg-snapshot"><ul class="ps-3 mb-0">' + "".join(lines) + "</ul></div>"


def _rebuild_snapshot(doc: "StudentSupportGuidance", save: bool = True) -> "StudentSupportGuidance":
	"""
	Lightweight rebuild used by external callers (e.g., Referral Case) after mutating items.
	- Recomputes counters (high_priority_count, ack_required_count)
	- Renders and caches snapshot_html
	- Does NOT bump ack_version
	- Does NOT (re)sync acknowledgment ToDos
	"""
	# Defensive: ensure we have a full doc
	ssg = frappe.get_doc(SSG, doc.name) if isinstance(doc, str) else doc

	# Recompute cheap counters from in-memory rows
	ssg.high_priority_count = _has_any_high_priority(ssg)
	ssg.ack_required_count = _count_ack_required_items(ssg)

	# Mark that we have published items if anything is present & published
	items = ssg.get("items") or []
	ssg.published_items = 1 if items else 0

	# Re-render teacher-facing snapshot HTML
	ssg.snapshot_html = _render_snapshot_html(ssg)

	if save:
		ssg.save(ignore_permissions=True)

	return ssg


# ─────────────────────────────────────────────────────────────────────────────
# Permission & audience helpers
# ─────────────────────────────────────────────────────────────────────────────

def _enforce_view_permission(doc_or_name):
	# PERF: avoid full doc load when a name is passed; fetch minimal keys
	if isinstance(doc_or_name, str):
		row = frappe.db.get_value(SSG, doc_or_name, ["student", "academic_year"], as_dict=True)
		if not row:
			frappe.throw(_("You are not permitted to view this support snapshot."))
		student, ay = (row.get("student") or ""), (row.get("academic_year") or "")
	else:
		student, ay = doc_or_name.student, doc_or_name.academic_year

	user = frappe.session.user
	if user == "Administrator":
		return
	roles = set(frappe.get_roles(user))
	# Counselors & academic admins may view
	if {"Counselor", "Academic Admin", "System Manager"} & roles:
		return
	# Instructors must be teacher-of-record for this student & year
	teacher_ids = _teacher_userids_for_student_year(student, ay)
	if user in teacher_ids:
		return
	frappe.throw(_("You are not permitted to view this support snapshot."))


def _teacher_userids_for_student_year(student: str, academic_year: str) -> set[str]:
	"""Return enabled User IDs of teachers-of-record for (student, AY) using a single, efficient query.
	Cached for 5 minutes via frappe.cache().
	"""
	if not student or not academic_year:
		return set()

	cache_key = f"ssg:teacher_users:{student}:{academic_year}"
	cache = frappe.cache()

	# Fast path: return cached set if present
	cached = cache.get_value(cache_key)
	if cached:
		try:
			# Values are pickled by frappe.cache(); normalize to set[str]
			return set(cached)
		except Exception:
			# Corrupt/legacy cache entry – ignore and refresh
			pass

	rows = frappe.db.sql(
		"""
		SELECT DISTINCT u.name AS user_id
		FROM `tabStudent Group` sg
		JOIN `tabStudent Group Student` sgs
		  ON sgs.parent = sg.name
		 AND IFNULL(sgs.active, 1) = 1
		JOIN `tabStudent Group Instructor` sgi
		  ON sgi.parent = sg.name
		LEFT JOIN `tabInstructor` ins
		  ON ins.name = sgi.instructor
		JOIN `tabUser` u
		  ON u.name = COALESCE(NULLIF(sgi.user_id, ''), NULLIF(ins.linked_user_id, ''))
		 AND u.enabled = 1
		WHERE sg.academic_year = %(ay)s
		  AND IFNULL(sg.status, 'Active') = 'Active'
		  AND sgs.student = %(student)s
		""",
		{"ay": academic_year, "student": student},
		as_dict=True,
	) or []

	users = {r["user_id"] for r in rows if r.get("user_id")}
	# Store as list for pickle/json safety; TTL 300s
	cache.set_value(cache_key, list(users), expires_in_sec=300)
	return users


def _sync_docshares_for_teachers(ssg_name: str, teacher_users: set[str]):
	"""
	Align DocShare (read-only) for SSG with current teachers-of-record.
	- Single read of existing shares
	- Bulk delete stale users
	- Insert only missing shares
	"""
	users = {(u or "").strip() for u in (teacher_users or set()) if u and u.strip()}
	if not ssg_name:
		return

	# Existing user-specific shares for this SSG
	rows = frappe.db.sql(
		"""
		SELECT user
		FROM `tabDocShare`
		WHERE share_doctype = %s
		  AND share_name = %s
		  AND IFNULL(user, '') != ''
		""",
		(SSG, ssg_name),
		as_dict=True,
	)
	existing = {(r["user"] or "").strip() for r in rows if r.get("user")}

	to_remove = existing - users
	to_add = users - existing

	# Bulk delete stale shares (user-specific only)
	if to_remove:
		frappe.db.sql(
			"""
			DELETE FROM `tabDocShare`
			WHERE share_doctype = %s
			  AND share_name = %s
			  AND user IN %(users)s
			""",
			(SSG, ssg_name, {"users": tuple(to_remove)}),
		)

	# Insert missing shares (small N)
	for user in sorted(to_add):
		frappe.get_doc({
			"doctype": "DocShare",
			"user": user,
			"share_doctype": SSG,
			"share_name": ssg_name,
			"read": 1, "write": 0, "share": 0, "submit": 0,
		}).insert(ignore_permissions=True)


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers (safe against evolving child schema)
# ─────────────────────────────────────────────────────────────────────────────

def _has_any_high_priority(doc: Document) -> int:
	items = doc.get("items") or []
	for row in items:
		# respect confidentiality: only count teacher-visible items
		vis = (getattr(row, "confidentiality", "") or "").strip()
		if vis and vis.lower() != "teachers-of-student".lower():
			continue
		val = getattr(row, "high_priority", 0)
		try:
			if int(val):
				return 1
		except Exception:
			if bool(val):
				return 1
	return 0


def _count_ack_required_items(doc: Document) -> int:
	items = doc.get("items") or []
	count = 0
	for row in items:
		# only items that teachers can see require teacher acknowledgements
		vis = (getattr(row, "confidentiality", "") or "").strip()
		if vis and vis.lower() != "teachers-of-student".lower():
			continue

		# Your schema uses "requires_ack" (string/Data). Treat truthy values as 1.
		if hasattr(row, "requires_ack"):
			val = (getattr(row, "requires_ack") or "").strip().lower()
			if val in {"1", "yes", "true", "y", "on"}:
				count += 1
		else:
			# If the flag is missing, default to requiring ack for visible items (matches prior behavior).
			count += 1
	return count


def _child_has(row, fname: str) -> bool:
	try:
		return bool(getattr(row, "meta").get_field(fname))
	except Exception:
		# Row may not carry meta in some contexts; fallback to hasattr
		return hasattr(row, fname)

def _first_present(row, fields: list[str]) -> str | None:
	for f in fields:
		if hasattr(row, f) and getattr(row, f):
			return getattr(row, f)
	return None


# ─────────────────────────────────────────────────────────────────────────────
# Selection of the “current” SSG document for (student, AY)
# ─────────────────────────────────────────────────────────────────────────────

def _find_current_ssg(student: str, academic_year: str) -> Document | None:
	"""Return full doc only for the chosen candidate (1 query for name + 1 doc load)."""
	name = _find_current_ssg_name(student, academic_year)
	return frappe.get_doc(SSG, name) if name else None

def _find_current_ssg_name(student: str, academic_year: str) -> str | None:
	if not (student and academic_year):
		return None

	# PERF: one SQL with UNION to prefer latest Published; else latest any status
	# (keeps the original semantics: prefer Published by most recent publish time;
	# otherwise fall back to latest modified draft)
	rows = frappe.db.sql(
		"""
		(
			SELECT name, COALESCE(last_published_on, modified) AS sort_key, 1 AS pref
			FROM `tabStudent Support Guidance`
			WHERE student = %(stu)s AND academic_year = %(ay)s AND status = 'Published'
			ORDER BY sort_key DESC
			LIMIT 1
		)
		UNION ALL
		(
			SELECT name, modified AS sort_key, 2 AS pref
			FROM `tabStudent Support Guidance`
			WHERE student = %(stu)s AND academic_year = %(ay)s
			ORDER BY modified DESC
			LIMIT 1
		)
		ORDER BY pref ASC
		LIMIT 1
		""",
		{"stu": student, "ay": academic_year},
		as_dict=True,
	)
	return rows[0]["name"] if rows else None
