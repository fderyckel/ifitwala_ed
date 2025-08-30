# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, now_datetime, add_to_date, cint
from frappe.desk.form.assign_to import add as assign_add, remove as assign_remove

CASE_MANAGER_TAG = "[CASE_MANAGER]"   # prefix in ToDo.description to distinguish
CASE_TASK_TAG = "[CASE_TASK]"
ALLOWED_SUBMIT_ROLES_FOR_MANDATED = {"Counselor", "Academic Admin", "System Manager"}

class StudentReferral(Document):

	def validate(self):
		# Soft consistency checks allowed in draft
		if cint(self.requires_immediate_action):
			if self.severity not in ("High", "Critical"):
				frappe.throw(_("When 'Requires Immediate Action' is checked, severity must be High or Critical."))

		if cint(self.mandated_reporting_triggered):
			if self.confidentiality_level not in ("Sensitive", "Restricted"):
				frappe.throw(_("When 'Mandated Reporting Triggered' is checked, confidentiality must be Sensitive or Restricted."))
			if self.severity in (None, "", "Low"):
				frappe.throw(_("Mandated reporting cannot be used with Low severity."))

	def before_save(self):
		# Compute SLA due if empty. Use settings; fall back to 24h.
		if not self.sla_due:
			sla_hours = _get_setting_int("sla_hours_new_to_triaged", default=24)
			# Use current server datetime as anchor (more accurate than Date-only field)
			base_dt = now_datetime()
			self.sla_due = add_to_date(base_dt, hours=sla_hours)

	def after_insert(self):
		# convenience: referrer defaults to session user for Staff source
		if self.referral_source == "Staff" and not self.referrer:
			self.db_set("referrer", frappe.session.user, update_modified=False)

	def before_submit(self):
		# 1) Ensure snapshot context is complete
		self._ensure_context_snapshot()

		# 2) Require core categorical fields on submit
		_required_on_submit(self, fields=("referral_category", "severity", "confidentiality_level"))

		# 3) Role gating for mandated reporting (guardrails)
		if cint(self.mandated_reporting_triggered) and not _user_has_any_role(ALLOWED_SUBMIT_ROLES_FOR_MANDATED):
			frappe.throw(_("Only Counselor or Academic Admin can submit a referral with Mandated Reporting."))

		# 4) SLA tightening for critical/immediate (override)
		if self.severity == "Critical" or cint(self.requires_immediate_action):
			override_hours = _get_setting_int("sla_hours_critical_override", default=None)
			if override_hours:
				self.sla_due = add_to_date(now_datetime(), hours=override_hours)

		# 5) If mandated/critical/immediate, make sure a Case exists
		needs_case = cint(self.mandated_reporting_triggered) or cint(self.requires_immediate_action) or self.severity in ("High", "Critical")
		if needs_case:
			self._ensure_case_exists()

	def on_submit(self):
		"""Ensure a Case exists, then route via native assign_to."""
		# 1) Ensure case
		case_name = frappe.db.get_value("Referral Case", {"referral": self.name}, "name")
		if not case_name:
			case_name = self.open_case()

		# 2) Priority for ToDo based on severity/immediacy/mandated
		high = self.severity in ("High", "Critical") or cint(self.requires_immediate_action) or cint(self.mandated_reporting_triggered)
		priority = "High" if high else "Medium"

		# 3) Route to counselor (self-assign if author is counselor; else least-load pool)
		author = frappe.session.user
		roles = set(frappe.get_roles(author))
		if "Counselor" in roles:
			manager = author
			assign_case_manager(case_name, manager, description="Self-assigned (counselor author)", priority=priority)
		else:
			manager = pick_user_from_role_pool("Counselor")
			assign_case_manager(case_name, manager, description="Auto-routed from referral", priority=priority)

		# 4) Optional UX sugar (only if you added these fields on the Referral doctype)
		try:
			self.db_set("referral_case", case_name, update_modified=False)
			self.db_set("assigned_case_manager", manager, update_modified=False)
		except Exception:
			pass			

	def _ensure_context_snapshot(self):
		"""Guarantee Program, Academic Year, and School are set consistently at submit time."""
		if not self.student:
			frappe.throw(_("Student is required."))

		# 1) If Program Enrollment selected, validate & fill
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
		if len(rows) == 1:
			r = rows[0]
			return {"name": r.name, "program": r.program, "academic_year": r.academic_year, "school": r.school}
		return [{"name": r.name, "program": r.program, "academic_year": r.academic_year, "school": r.school} for r in rows]

	@frappe.whitelist()
	def open_case(self):
		"""Create or fetch a Referral Case linked to this referral; return name."""
		existing = frappe.db.get_value("Referral Case", {"referral": self.name}, "name")
		if existing:
			return existing
		case = frappe.new_doc("Referral Case")
		case.referral = self.name
		case.student = self.student
		case.program = self.program
		case.academic_year = self.academic_year
		case.school = self.school
		case.confidentiality_level = self.confidentiality_level
		case.severity = self.severity
		case.insert(ignore_permissions=True)
		return case.name

	def _ensure_case_exists(self):
		if not frappe.db.exists("Referral Case", {"referral": self.name}):
			self.open_case()

def on_doctype_update():
	# Helpful indexes
	frappe.db.add_index("Student Referral", ["student"])
	frappe.db.add_index("Student Referral", ["program_enrollment"])
	frappe.db.add_index("Student Referral", ["school"])
	# (child/other indexes added later if profiling requires)

# ---------------------
# Helpers
# ---------------------

def _required_on_submit(doc: Document, fields: tuple[str, ...]):
	for f in fields:
		if not doc.get(f):
			frappe.throw(_("{0} is required before submit.").format(f.replace("_", " ").title()))

def _user_has_any_role(roles: set[str]) -> bool:
	user_roles = set(frappe.get_roles())
	return bool(user_roles & roles)

def _get_setting_int(fieldname: str, default: int | None = None) -> int | None:
	try:
		val = frappe.db.get_single_value("Referral Settings", fieldname)
		if val is None:
			return default
		return cint(val)
	except Exception:
		return default


def assign_case_manager(case_name: str, user: str, description: str = "Primary owner", priority: str = "Medium"):
	"""Create/replace the special manager assignment for a case, and mirror to case_manager."""
	_remove_manager_assignments(case_name)
	# Add new manager assignment (native)
	if assign_add:
		assign_add({
			"doctype": "Referral Case",
			"name": case_name,
			"assign_to": [user],
			"priority": priority,
			"description": f"{CASE_MANAGER_TAG} {description}",
		})
	# Mirror to link field for fast filters (no modified bump)
	frappe.db.set_value("Referral Case", case_name, "case_manager", user, update_modified=False)

def add_case_task_assignment(case_name: str, user: str, note: str, priority: str = "Medium", due_date: str | None = None):
	"""Assign a specific task on the case (not the child row), tagged distinctly."""
	payload = {
		"doctype": "Referral Case",
		"name": case_name,
		"assign_to": [user],
		"priority": priority,
		"description": f"{CASE_TASK_TAG} {note}",
	}
	if due_date:
		payload["date"] = due_date
	if assign_add:
		assign_add(payload)

def pick_user_from_role_pool(role: str) -> str:
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

	# Final fallback: pick any enabled System Manager (if present), else Administrator
	sys_mgrs = set(frappe.get_all("Has Role", filters={"role": "System Manager"}, pluck="parent"))
	sys_mgrs_enabled = frappe.get_all("User", filters={"name": ["in", list(sys_mgrs)], "enabled": 1}, pluck="name")
	if sys_mgrs_enabled:
		return sorted(sys_mgrs_enabled)[0]

	return "Administrator"


def _remove_manager_assignments(case_name: str):
	"""Close only ToDos tagged as CASE_MANAGER for this case (leave task ToDos intact)."""
	rows = frappe.get_all(
		"ToDo",
		filters={"reference_type": "Referral Case", "reference_name": case_name, "status": "Open"},
		fields=["name", "description"],
	)
	for r in rows:
		desc = (r.description or "").strip()
		if desc.startswith(CASE_MANAGER_TAG):
			# Close only this specific row to avoid nuking task ToDos
			frappe.db.set_value("ToDo", r.name, "status", "Closed", update_modified=False)

