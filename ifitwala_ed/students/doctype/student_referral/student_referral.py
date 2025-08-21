# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class StudentReferral(Document):
	def after_insert(self):
		# convenience: referrer defaults to session user for Staff source
		if self.referral_source == "Staff" and not self.referrer:
				self.db_set("referrer", frappe.session.user, update_modified=False)

	def before_save(self):
		# set SLA due using settings (New → Triaged window)
		sla_hrs = frappe.db.get_single_value("Referral Setting", "sla_hours_new_to_triaged") or 24
		if not self.sla_due: 
			self.sla_due = add_to_date(self.date or nowdate(), hours=sla_hrs)				

	def before_submit(self):
		self._ensure_context_snapshot()

	def _ensure_context_snapshot(self):
		if not self.student:
			frappe.throw("Student is required.")

		# 1) prefer selected Program Enrollment
		if self.program_enrollment:
			pe = frappe.db.get_value("Program Enrollment", self.program_enrollment,
				["student", "program", "academic_year", "school", "docstatus"], as_dict=True)
			if not pe:
				frappe.throw(f"Program Enrollment {self.program_enrollment} not found.")
			if pe.student != self.student:
				frappe.throw("Selected Program Enrollment belongs to another student.")
			self.program = self.program or pe.program
			self.academic_year = self.academic_year or pe.academic_year
			self.school = self.school or pe.school or frappe.db.get_value("Program", pe.program, "school")

		# 2) if still missing, resolve best PE by referral date
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

		# 3) must have snapshot
		missing = [f for f in ("program", "academic_year", "school") if not self.get(f)]
		if missing:
			label = ", ".join([f.replace("_", " ").title() for f in missing])
			frappe.throw(f"Missing linked context on submit: {label}. Select a Program Enrollment or set Program/Academic Year/School.")

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

def on_doctype_update():
	frappe.db.add_index("Student Referral", ["student"])
	frappe.db.add_index("Student Referral", ["program_enrollment"])