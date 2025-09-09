# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student_support_guidance/student_support_guidance.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, cint, strip_html_tags
from frappe.desk.form.assign_to import add as assign_add

SSG = "Student Support Guidance"
ACK_TAG = "[ACK] Student Support Guidance"

class StudentSupportGuidance(Document):
	"""Lightweight lifecycle: publishing + snapshot caching is handled here."""
	def validate(self):
		self.high_priority_count = _has_any_high_priority(self)
		self.ack_required_count = _count_ack_required_items(self)

	def onload(self):
		"""Emulate load_address_and_contact pattern: inject snapshot into __onload."""
		self.set_onload("snapshot_html", _render_snapshot_html(self))

	def on_update(self):
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
    """Used in Student modal – always return rendered snapshot HTML."""
    ssg = _find_current_ssg(student, academic_year)
    if not ssg:
        return {"snapshot_html": '<div class="text-muted">' + _("No guidance yet.") + "</div>"}

    _enforce_view_permission(ssg)
    return {"snapshot_html": _render_snapshot_html(ssg)}

@frappe.whitelist()
def get_ack_status(student: str, academic_year: str) -> dict:
    name = _find_current_ssg_name(student, academic_year)
    if not name:
        return {"ack_required": False, "has_open_todo": False, "ack_required_count": 0, "ack_version": 0}

    _enforce_view_permission(name)
    row = frappe.db.get_value(
        SSG, name, ["status", "ack_required_count", "ack_version"], as_dict=True
    ) or {}

    need_ack = cint(row.get("ack_required_count") or 0) > 0 and (row.get("status") or "") == "Published"
    if not need_ack:
        return {
            "ack_required": False,
            "has_open_todo": False,
            "ack_required_count": cint(row.get("ack_required_count") or 0),
            "ack_version": cint(row.get("ack_version") or 0),
        }

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
    name = _find_current_ssg_name(student, academic_year)
    if not name:
        frappe.throw(_("No current guidance is available to acknowledge."))
    _enforce_view_permission(name)

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
    doc = frappe.get_doc(SSG, name)
    roles = set(frappe.get_roles())
    if not ({"Counselor", "Academic Admin", "System Manager"} & roles):
        frappe.throw(_("You are not permitted to publish support guidance."))

    doc.status = "Published"
    _apply_publish(doc, bump_version=True, notify=bool(cint(notify)))
    return {"ok": True, "ack_version": cint(doc.ack_version or 0)}


# ─────────────────────────────────────────────────────────────────────────────
# Core publish, snapshot & assignment logic
# ─────────────────────────────────────────────────────────────────────────────

def _apply_publish(doc: "StudentSupportGuidance", bump_version=True, notify=True):
    if bump_version:
        doc.ack_version = cint(doc.ack_version or 0) + 1
    doc.last_published_on = now_datetime()
    doc.published_items = 1
    doc.high_priority_count = _has_any_high_priority(doc)
    doc.ack_required_count = _count_ack_required_items(doc)
    doc.save(ignore_permissions=True)
    _sync_ack_assignments(doc, notify=notify)

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
    items = doc.get("items") or []
    if not items:
        return '<div class="text-muted">' + _("No guidance yet.") + "</div>"

    lines = []
    for row in items:
        if not _teacher_visible(row):
            continue
        raw = getattr(row, "teacher_text", "") or ""
        plain = (strip_html_tags(raw) or "").strip()
        if not plain:
            continue
        text = frappe.utils.escape_html(plain)
        type_badge = f'<span class="badge bg-secondary ms-1">{frappe.utils.escape_html(row.item_type or "")}</span>' if row.item_type else ""
        high_badge = '<span class="badge bg-danger ms-1">High</span>' if _truthy(getattr(row, "high_priority", 0)) else ""
        lines.append(f'<li class="mb-1">{text}{type_badge}{high_badge}</li>')

    if not lines:
        return '<div class="text-muted">' + _("No guidance items are published.") + "</div>"
    return '<div class="ssg-snapshot"><ul class="ps-3 mb-0">' + "".join(lines) + "</ul></div>"



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

def _truthy(val) -> bool:
	"""Accepts 1/0, True/False, 'yes/no', 'on/off', etc."""
	if isinstance(val, bool):
		return val
	if isinstance(val, (int, float)):
		return int(val) != 0
	s = (str(val) if val is not None else "").strip().lower()
	return s in {"1", "true", "yes", "y", "on"}

def _teacher_visible(row) -> bool:
	"""Only show/count items meant for teachers-of-student."""
	vis = (getattr(row, "confidentiality", "") or "").strip().lower()
	return (vis == "" or vis == "teachers-of-student")


def _has_any_high_priority(doc: Document) -> int:
	items = doc.get("items") or []
	for row in items:
		if not _teacher_visible(row):
			continue
		if _truthy(getattr(row, "high_priority", 0)):
			return 1
	return 0


def _count_ack_required_items(doc: Document) -> int:
	items = doc.get("items") or []
	count = 0
	for row in items:
		if not _teacher_visible(row):
			continue
		# Your schema uses 'requires_ack' (Data today, but RPC sends ints too)
		if hasattr(row, "requires_ack"):
			if _truthy(getattr(row, "requires_ack")):
				count += 1
		else:
			# Default to requiring ack for teacher-visible items when flag absent
			count += 1
	return count


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
