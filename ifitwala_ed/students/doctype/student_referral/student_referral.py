# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, now_datetime, add_to_date, cint
from frappe.desk.form.assign_to import add as assign_add  # native ToDo

# ─────────────────────────────────────────────────────────────────────────────
# Constants
CASE_MANAGER_TAG = "[CASE_MANAGER]"   # prefix in ToDo.description for manager ToDo
CASE_TASK_TAG = "[CASE_TASK]"         # reserved for task-style ToDos (Step 2)
SETTINGS_DTYPE = "Referral Settings"
ALLOWED_SUBMIT_ROLES_FOR_MANDATED = {"Counselor", "Academic Admin", "System Manager"}
# ─────────────────────────────────────────────────────────────────────────────

class StudentReferral(Document):
	# ── Lifecycle ────────────────────────────────────────────────────────────
	def after_insert(self):
		# Default referrer for staff-origin referrals
		if self.referral_source == "Staff" and not self.referrer:
			self.db_set("referrer", frappe.session.user, update_modified=False)

	def validate(self):
		# Source gating per settings (last-line guard)
		source = (self.referral_source or "").strip()
		if source == "Student (Self)" and not _get_setting_int("allow_student_self_referral", 1):
			frappe.throw(_("Student self-referrals are disabled by settings."))
		if source == "Guardian" and not _get_setting_int("allow_guardian_referral", 1):
			frappe.throw(_("Guardian referrals are disabled by settings."))

		# Consistency for immediate action / mandated reporting
		if cint(self.requires_immediate_action) and self.severity not in ("High", "Critical"):
			frappe.throw(_("When 'Requires Immediate Action' is checked, severity must be High or Critical."))
		if cint(self.mandated_reporting_triggered):
			if self.confidentiality_level not in ("Sensitive", "Restricted"):
				frappe.throw(_("When 'Mandated Reporting Triggered' is checked, confidentiality must be Sensitive or Restricted."))
			if self.severity in (None, "", "Low"):
				frappe.throw(_("Mandated reporting cannot be used with Low severity."))

	def before_save(self):
		# Compute initial triage SLA if empty (from settings; default 24h)
		if not self.sla_due:
			sla_hours = _get_setting_int("sla_hours_new_to_triaged", 24, positive_only=True)
			self.sla_due = add_to_date(now_datetime(), hours=sla_hours)	

	def before_submit(self):
		# 1) Ensure snapshot context is complete
		self._ensure_context_snapshot()
		# 2) Require core categorical fields on submit
		_required_on_submit(self, fields=("referral_category", "severity", "confidentiality_level"))
		# 3) Role gating for mandated reporting
		if cint(self.mandated_reporting_triggered) and not _user_has_any_role(ALLOWED_SUBMIT_ROLES_FOR_MANDATED):
			frappe.throw(_("Only Counselor or Academic Admin can submit a referral with Mandated Reporting."))

		# 4) Optional SLA tightening for critical/immediate (Triaged→First Action window)
		override_hours = _get_setting_int("sla_hours_triaged_to_first_action", None, positive_only=True)
		if override_hours and (self.severity == "Critical" or cint(self.requires_immediate_action)):
			self.sla_due = add_to_date(now_datetime(), hours=override_hours)

		# 5) Ensure a Case exists for high-risk items regardless of settings
		needs_case = cint(self.mandated_reporting_triggered) or cint(self.requires_immediate_action) or self.severity in ("High", "Critical")
		if needs_case:
			self._ensure_case_exists()


	def on_submit(self):
		"""Create/ensure Case and route via native assign_to, respecting settings."""
		auto_create_case = bool(_get_setting_int("auto_create_case", 0))
		case_name = frappe.db.get_value("Referral Case", {"referral": self.name}, "name")

		high_risk = self.severity in ("High", "Critical") or cint(self.requires_immediate_action) or cint(self.mandated_reporting_triggered)
		if not case_name and (high_risk or auto_create_case):
			case_name = self.open_case()

		# If still no case (low/moderate and auto-create disabled), nothing to assign
		if not case_name:
			return

		priority = "High" if high_risk else "Medium"
		intake_role = (_get_setting_str("default_intake_owner_role") or "Counselor").strip() or "Counselor"

		author = frappe.session.user
		roles = set(frappe.get_roles(author))
		notify = bool(_get_setting_int("notify_on_assignment", 1))

		if intake_role in roles:
			manager = author
			assign_case_manager(case_name, manager, description="Self-assigned (intake role author)", priority=priority, notify=notify)
		else:
			manager = pick_user_from_role_pool(intake_role)
			assign_case_manager(case_name, manager, description="Auto-routed from referral", priority=priority, notify=notify)

		# Stamp mirrors (safe even if already set by open_case / manager assignment)
		self.db_set("referral_case", case_name, update_modified=False)
		self.db_set("assigned_case_manager", manager, update_modified=False)

	# ── Internals ────────────────────────────────────────────────────────────
	def _ensure_context_snapshot(self):
		"""Guarantee Program, Academic Year, and School are set at submit time."""
		if not self.student:
			frappe.throw(_("Student is required."))

		# 1) Prefer selected Program Enrollment
		if self.program_enrollment:
			pe = frappe.db.get_value(
				"Program Enrollment",
				self.program_enrollment,
				["student", "program", "academic_year", "school", "docstatus"],
				as_dict=True,
			)
			if not pe:
				frappe.throw(_("Program Enrollment {0} not found.").format(self.program_enrollment))
			if pe.student != self.student:
				frappe.throw(_("Selected Program Enrollment belongs to another student."))
			self.program = self.program or pe.program
			self.academic_year = self.academic_year or pe.academic_year
			self.school = self.school or pe.school or frappe.db.get_value("Program", pe.program, "school")

		# 2) Otherwise, resolve best Program Enrollment by referral date
		if not (self.program and self.academic_year and self.school):
			on_date = getdate(self.get("date") or nowdate())
			best = self.get_student_active_enrollment(self.student, on_date)
			if isinstance(best, list):
				best = best[0] if best else None
			if best:
				self.program_enrollment = self.program_enrollment or best.get("name")
				self.program = self.program or best.get("program")
				self.academic_year = self.academic_year or best.get("academic_year")
				self.school = self.school or best.get("school") or (
					self.program and frappe.db.get_value("Program", self.program, "school")
				)

		# 3) Final check
		missing = [f for f in ("program", "academic_year", "school") if not self.get(f)]
		if missing:
			label = ", ".join([f.replace("_", " ").title() for f in missing])
			frappe.throw(_("Missing linked context on submit: {0}. Select a Program Enrollment or set Program/Academic Year/School.").format(label))

	@frappe.whitelist()
	def get_student_active_enrollment(self, student: str | None = None, on_date: str | None = None):
		student = student or self.student
		if not student:
			return []

		on_date = getdate(on_date) if on_date else getdate(self.get("date") or nowdate())
		q = """
			SELECT
				pe.name,
				pe.student,
				pe.program,
				pe.academic_year,
				COALESCE(pe.school, p.school) AS school,
				CASE WHEN ay.year_start_date IS NOT NULL
						AND ay.year_start_date <= %(on_date)s
						AND ay.year_end_date   >= %(on_date)s
						THEN 1 ELSE 0 END AS within_ay,
				IFNULL(pe.archived, 0) AS archived_flag,
				ay.year_start_date,
				pe.creation
			FROM `tabProgram Enrollment` pe
			LEFT JOIN `tabProgram` p ON p.name = pe.program
			LEFT JOIN `tabAcademic Year` ay ON ay.name = pe.academic_year
			WHERE pe.student = %(student)s
				AND pe.docstatus < 2
			ORDER BY
				within_ay DESC,
				archived_flag ASC,
				COALESCE(ay.year_start_date, '1900-01-01') DESC,
				pe.creation DESC
			LIMIT 5
		"""
		rows = frappe.db.sql(q, {"student": student, "on_date": on_date}, as_dict=True) or []
		if not rows:
			return []

		# Prefer unarchived within the academic-year window for on_date
		cand_unarch_within = [r for r in rows if not r.archived_flag and r.within_ay]
		if cand_unarch_within:
			if len(cand_unarch_within) == 1:
				r = cand_unarch_within[0]
				return {"name": r.name, "program": r.program, "academic_year": r.academic_year, "school": r.school}
			return [{"name": r.name, "program": r.program, "academic_year": r.academic_year, "school": r.school}
							for r in cand_unarch_within]

		# Next best: any unarchived PE (most recent)
		cand_unarch_any = [r for r in rows if not r.archived_flag]
		if cand_unarch_any:
			if len(cand_unarch_any) == 1:
				r = cand_unarch_any[0]
				return {"name": r.name, "program": r.program, "academic_year": r.academic_year, "school": r.school}
			return [{"name": r.name, "program": r.program, "academic_year": r.academic_year, "school": r.school}
							for r in cand_unarch_any]

		# Final fallback: archived (let the client show a warning or dialog if >1)
		if len(rows) == 1:
			r = rows[0]
			return {"name": r.name, "program": r.program, "academic_year": r.academic_year, "school": r.school}
		return [{"name": r.name, "program": r.program, "academic_year": r.academic_year, "school": r.school} for r in rows]


	@frappe.whitelist()
	def open_case(self):
		"""Create or fetch a Referral Case linked to this referral; return name."""
		existing = frappe.db.get_value("Referral Case", {"referral": self.name}, "name")
		if existing:
			# keep the mirror in sync if missing
			if frappe.db.get_value("Student Referral", self.name, "referral_case") != existing:
				frappe.db.set_value("Student Referral", self.name, "referral_case", existing, update_modified=False)
			return existing

		case = frappe.new_doc("Referral Case")
		case.referral = self.name
		case.student = self.student
		case.program = self.program
		case.academic_year = self.academic_year
		case.school = self.school
		case.confidentiality_level = self.confidentiality_level
		case.severity = self.severity
		case.opened_on = nowdate()
		case.insert(ignore_permissions=True)

		# mirror just the case link now; manager will be mirrored later when assigned
		frappe.db.set_value("Student Referral", self.name, "referral_case", case.name, update_modified=False)
		return case.name

	def _ensure_case_exists(self):
		if not frappe.db.exists("Referral Case", {"referral": self.name}):
			self.open_case()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers (pure functions)
# ─────────────────────────────────────────────────────────────────────────────

def _required_on_submit(doc: Document, fields: tuple[str, ...]):
	for f in fields:
		if not doc.get(f):
			frappe.throw(_("{0} is required before submit.").format(f.replace("_", " ").title()))

def _user_has_any_role(roles: set[str]) -> bool:
	user_roles = set(frappe.get_roles())
	return bool(user_roles & roles)

def _get_setting_int(fieldname: str, default: int | None = None, *, positive_only: bool = False) -> int | None:
	try:
		val = frappe.db.get_single_value(SETTINGS_DTYPE, fieldname)
		# Treat None / "" as unset → use default
		if val is None or (isinstance(val, str) and val.strip() == ""):
			return default
		num = cint(val)
		if positive_only and (num is None or num <= 0):
			return default
		return num
	except Exception:
		return default


def _get_setting_str(fieldname: str) -> str | None:
	try:
		val = frappe.db.get_single_value(SETTINGS_DTYPE, fieldname)
		return (val or "").strip() or None
	except Exception:
		return None

# ── Native assignment glue (manager + pool) ──────────────────────────────────

def assign_case_manager(case_name: str, user: str, description: str = "Primary owner", priority: str = "Medium", notify: bool = True):
	"""Create/replace the special manager assignment for a case, and mirror to case_manager."""
	_close_manager_todos_only(case_name)  # do not touch task ToDos
	payload = {
		"doctype": "Referral Case",
		"name": case_name,
		"assign_to": [user],
		"priority": priority,
		"description": f"{CASE_MANAGER_TAG} {description}",
	}
	if notify:
		payload["notify"] = 1  # assign_to supports notify in v15+; ignored if not supported
	assign_add(payload)  # creates ToDo natively
	frappe.db.set_value("Referral Case", case_name, "case_manager", user, update_modified=False)

def pick_user_from_role_pool(role: str) -> str:
	"""Return enabled user with this role using least open-case-load strategy; safe fallbacks."""
	cands = frappe.get_all("Has Role", filters={"role": role}, fields=["parent"]) or []
	if not cands:
		cands = frappe.get_all("Has Role", filters={"role": "Academic Admin"}, fields=["parent"]) or []
	users = [c.parent for c in cands]

	enabled = set(frappe.get_all("User", filters={"name": ["in", users], "enabled": 1}, pluck="name")) if users else set()
	if enabled:
		load = {u: 0 for u in enabled}
		open_todos = frappe.db.sql(
			"""
			SELECT allocated_to, COUNT(*) AS n
			FROM `tabToDo`
			WHERE reference_type='Referral Case'
			  AND status='Open'
			  AND allocated_to IN %(users)s
			GROUP BY allocated_to
			""",
			{"users": tuple(enabled)},
			as_dict=True,
		) or []
		for row in open_todos:
			if row.allocated_to in load:
				load[row.allocated_to] = cint(row.n)
		return sorted(load.items(), key=lambda kv: (kv[1], kv[0]))[0][0]

	# Final fallback: pick an enabled System Manager, else Administrator
	sys_mgrs = set(frappe.get_all("Has Role", filters={"role": "System Manager"}, pluck="parent"))
	sys_mgrs_enabled = frappe.get_all("User", filters={"name": ["in", list(sys_mgrs)], "enabled": 1}, pluck="name")
	if sys_mgrs_enabled:
		return sorted(sys_mgrs_enabled)[0]
	return "Administrator"

def _close_manager_todos_only(case_name: str):
	"""Close only manager-tagged ToDos for this case (leave task ToDos intact)."""
	rows = frappe.get_all(
		"ToDo",
		filters={"reference_type": "Referral Case", "reference_name": case_name, "status": "Open"},
		fields=["name", "description"],
	)
	for r in rows:
		desc = (r.description or "").strip()
		if desc.startswith(CASE_MANAGER_TAG):
			frappe.db.set_value("ToDo", r.name, "status", "Closed", update_modified=False)




@frappe.whitelist()
def breaching_sla_count():
	now_str = now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	overdue = frappe.db.count(
		"Student Referral",
		filters={
			"docstatus": 1,
			"referral_case": ["is", "not set"],
			"sla_due": ["<", now_str],
		},
	)

	return {
		"value": overdue,
		"fieldtype": "Int",
		"route": ["List", "Student Referral"],
		"route_options": {
			"filters": [
				["Student Referral", "docstatus", "=", 1],
				["Student Referral", "referral_case", "is", "not set"],
				["Student Referral", "sla_due", "<", now_str],
			]
		}
	}


@frappe.whitelist()
def card_srf_new_today():
	"""Count submitted Student Referrals dated today with no linked Referral Case.

	Returns a Number Card payload:
	  {
	    "value": <int>,
	    "fieldtype": "Int",
	    "route": ["List", "Student Referral"],
	    "route_options": { "filters": [...] }
	  }
	"""
	today = nowdate()

	count = frappe.db.count(
		"Student Referral",
		filters={
			"docstatus": 1,
			"date": ["=", today],
			"referral_case": ["is", "not set"],
		},
	)

	# Click-through opens the filtered list
	return {
		"value": cint(count),
		"fieldtype": "Int",
		"route": ["List", "Student Referral"],
		"route_options": {
			"filters": [
				["Student Referral", "docstatus", "=", 1],
				["Student Referral", "date", "=", today],
				["Student Referral", "referral_case", "is", "not set"],
			]
		},
	}


def on_doctype_update():
	# Helpful indexes
	frappe.db.add_index("Student Referral", ["student"])
	frappe.db.add_index("Student Referral", ["program_enrollment"])
	frappe.db.add_index("Student Referral", ["school"])
	frappe.db.add_index("Student Referral", ["referral_case"])
	frappe.db.add_index("Student Referral", ["assigned_case_manager"])
	frappe.db.add_index("Student Referral", ["docstatus", "referral_case"])
	frappe.db.add_index("Student Referral", ["sla_due"])