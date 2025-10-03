# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py

import csv
import io
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, cint
from frappe.utils.file_manager import save_file

# ----------------------------
# Helper for large batch enqueue
# ----------------------------

def _enroll_batch(tool_doctype, tool_name):
	tool = frappe.get_doc(tool_doctype, tool_name)
	tool._run_enroll(batch_mode=True)

class ProgramEnrollmentTool(Document):

	@frappe.whitelist()
	def get_students(self):
		"""Populate the child table based on UI filters and mark duplicates."""
		students = self._fetch_students()
		if not students:
			frappe.throw(_("No students found with the given criteria."))

		# Mark duplicates for UI preview (already enrolled in target AY+Program)
		if self.new_program and self.new_academic_year:
			dup_ids = set(
				frappe.get_all(
					"Program Enrollment",
					filters={
						"program": self.new_program,
						"academic_year": self.new_academic_year,
						"student": ["in", [s["student"] for s in students]],
					},
					pluck="student",
				)
			)
			for s in students:
				s["already_enrolled"] = 1 if s["student"] in dup_ids else 0

		return students

	@frappe.whitelist()
	def enroll_students(self):
		"""Kick off enrollment – async if >100, else sync."""
		total = len(self.students)
		if total == 0:
			frappe.throw(_("No students in the list."))
		if not self.new_program or not self.new_academic_year:
			frappe.throw(_("New Program and New Academic Year are required."))

		# Enqueue if large batch
		if total > 100:
			frappe.enqueue(
				_enroll_batch,
				queue="long",
				job_name=f"Enroll {total} students PE Tool",
				tool_doctype=self.doctype,
				tool_name=self.name,
			)
			frappe.msgprint(_(
				"{0} students queued for enrollment. You will be notified when the job completes."
			).format(total))
			return

		# Else run inline
		summary = self._run_enroll(batch_mode=False)
		return summary

	# ----------------------------
	# INTERNALS
	# ----------------------------

	def _fetch_students(self):
		"""Return list of dicts with keys: student, student_name, student_cohort"""
		out = []
		if self.get_students_from == "Cohort":
			if not self.student_cohort:
				frappe.throw(_("Please specify the Student Cohort."))
			out = frappe.get_all(
				"Student",
				filters={"cohort": self.student_cohort, "enabled": 1},
				fields=["name as student", "student_full_name as student_name", "cohort as student_cohort"],
			)
		elif self.get_students_from == "Program Enrollment":
			if not self.academic_year or not self.program:
				frappe.throw(_("Please specify both Program and Academic Year."))
			filters = {"program": self.program, "academic_year": self.academic_year}
			if self.student_cohort:
				filters["cohort"] = self.student_cohort
			out = frappe.get_all(
				"Program Enrollment",
				filters=filters,
				fields=["student", "student_name", "cohort as student_cohort"],
			)
			# remove disabled students
			ids = [s["student"] for s in out]
			if ids:
				disabled = set(
					frappe.get_all("Student", filters={"name": ["in", ids], "enabled": 0}, pluck="name")
				)
				out = [s for s in out if s["student"] not in disabled]
		else:
			frappe.throw(_(f"Unsupported option {self.get_students_from}"))
		return out

	# Core enrollment routine (batch_mode true = called by worker)
	def _run_enroll(self, batch_mode=False):
		created, skipped, failed = [], [], []

		# map "Mark new enrollments as Active" (checked=1) to archived=0; else archived=1
		archived_flag = 0 if cint(getattr(self, "mark_status_as_checked", 1)) else 1

		year_doc = frappe.get_doc("Academic Year", self.new_academic_year)
		enr_date = self.new_enrollment_date or getdate(year_doc.year_start_date)

		total = len(self.students)
		for idx, row in enumerate(self.students):
			try:
				if frappe.db.exists(
					"Program Enrollment",
					{
						"student": row.student,
						"program": self.new_program,
						"academic_year": self.new_academic_year,
					},
				):
					skipped.append(row.student)
					continue

				pe = frappe.get_doc({
					"doctype": "Program Enrollment",
					"student": row.student,
					"student_name": row.student_name,
					"cohort": row.student_cohort or self.new_student_cohort,
					"program": self.new_program,
					"academic_year": self.new_academic_year,
					"enrollment_date": enr_date,
					"archived": archived_flag,
				})
				pe.insert(ignore_permissions=True)
				created.append(row.student)
			except Exception as e:
				failed.append(f"{row.student}: {e}")

			if not batch_mode:
				frappe.publish_realtime(
					"program_enrollment_tool",
					dict(progress=[idx + 1, total]),
					user=frappe.session.user,
				)

		# Build summary
		summary = {
			"created": len(created),
			"skipped": len(skipped),
			"failed": len(failed),
		}

		# Write CSV for failures if any
		if failed:
			csv_buf = io.StringIO()
			csv.writer(csv_buf).writerows([[f] for f in failed])
			fname = f"pe_tool_failures_{self.name}.csv"
			filedoc = save_file(fname, csv_buf.getvalue(), self.doctype, self.name, is_private=1)
			summary["fail_link"] = filedoc.file_url  # e.g., "/private/files/pe_tool_failures_....csv"

		# Notify user when background job finishes
		if batch_mode:
			frappe.publish_realtime(
				"program_enrollment_tool_done",
				summary,
				user=self.owner,
			)
		else:
			frappe.msgprint(_(
				"Created: {0}, Skipped: {1}, Failed: {2}".format(*summary.values())
			))
		return summary



@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""
		SELECT name
		FROM `tabAcademic Year`
		WHERE name LIKE %(txt)s
		ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
		LIMIT %(start)s, %(page_len)s
		""",
		{"txt": f"%{txt}%", "start": start, "page_len": page_len}
	)
