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
		"""Populate the child table based on UI filters and mark duplicates (by student, program_offering, AY)."""
		students = self._fetch_students()
		if not students:
			frappe.throw(_("No students found with the given criteria."))

		# Pre-mark duplicates if target (new) offering + AY are chosen
		if self.new_program_offering and self.new_target_academic_year:
			dup_ids = set(
				frappe.get_all(
					"Program Enrollment",
					filters={
						"program_offering": self.new_program_offering,
						"academic_year": self.new_target_academic_year,
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
		"""Run (or enqueue) creation of Program Enrollment rows for listed students into the chosen offering + AY."""
		total = len(self.students)
		if total == 0:
			frappe.throw(_("No students in the list."))
		if not self.new_program_offering or not self.new_target_academic_year:
			frappe.throw(_("New Program Offering and New Target Academic Year are required."))

		# Enqueue if large batch
		if total > 100:
			frappe.enqueue(
				_enroll_batch,
				queue="long",
				job_name=f"Enroll {total} students PE Tool",
				tool_doctype=self.doctype,
				tool_name=self.name,
			)
			frappe.msgprint(_("{0} students queued for enrollment. You will be notified when the job completes.").format(total))
			return

		# Else run inline
		return self._run_enroll(batch_mode=False)

	# ----------------------------
	# INTERNALS
	# ----------------------------

	def _fetch_students(self):
		"""Return list of dicts with keys: student, student_name, student_cohort."""
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
			if not self.target_academic_year or not self.program_offering:
				frappe.throw(_("Please specify both Program Offering and Target Academic Year."))
			filters = {
				"program_offering": self.program_offering,
				"academic_year": self.target_academic_year,
			}
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
	def _run_enroll(self, batch_mode: bool = False):
		created, skipped, failed = [], [], []

		# Active vs archived flag (checked = Active → archived=0)
		archived_flag = 0 if cint(getattr(self, "mark_status_as_checked", 1)) else 1

		# Resolve & validate target AY window
		year_doc = frappe.get_doc("Academic Year", self.new_target_academic_year)
		if not getattr(year_doc, "year_start_date", None) or not getattr(year_doc, "year_end_date", None):
			frappe.throw(_("Selected Academic Year must have start and end dates."))
		ay_start = getdate(year_doc.year_start_date)
		ay_end = getdate(year_doc.year_end_date)

		# Enrollment date: default to AY start; if provided, must fall inside AY
		enr_date = self.new_enrollment_date or ay_start
		if self.new_enrollment_date:
			d = getdate(self.new_enrollment_date)
			if not (ay_start <= d <= ay_end):
				frappe.throw(_("New enrollment Date must fall inside the selected New Target Academic Year."))
			enr_date = d

		# Optional convenience: denormalized Program from Offering (single lookup)
		program = frappe.db.get_value("Program Offering", self.new_program_offering, "program")

		# Pre-compute existing enrollments to minimize DB round-trips
		student_ids = [row.student for row in (self.students or []) if getattr(row, "student", None)]
		existing = set()
		if student_ids:
			existing = set(
				frappe.get_all(
					"Program Enrollment",
					filters={
						"program_offering": self.new_program_offering,
						"academic_year": self.new_target_academic_year,
						"student": ["in", student_ids],
					},
					pluck="student",
				)
			)

		# Also guard against duplicates within the current list
		seen = set(existing)

		total = len(self.students or [])
		for idx, row in enumerate(self.students or []):
			try:
				if not row.student:
					skipped.append("(missing student)")
					continue

				# Skip if already enrolled (existing) or duplicated within this batch (seen)
				if row.student in seen:
					skipped.append(row.student)
					continue

				doc = frappe.get_doc({
					"doctype": "Program Enrollment",
					"student": row.student,
					"student_name": getattr(row, "student_name", None),
					"cohort": (getattr(row, "student_cohort", None) or getattr(self, "new_student_cohort", None)),
					"program": program,  # optional denormalized helper; OK if None
					"program_offering": self.new_program_offering,
					"academic_year": self.new_target_academic_year,
					"enrollment_date": enr_date,
					"archived": archived_flag,
				})
				doc.insert(ignore_permissions=True)
				created.append(row.student)
				seen.add(row.student)

			except Exception as e:
				# Keep going; capture failure detail
				failed.append(f"{getattr(row, 'student', '(unknown)')}: {e}")

			# Live progress only for inline runs
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

		# Attach failures CSV if any
		if failed:
			buf = io.StringIO()
			w = csv.writer(buf)
			for line in failed:
				w.writerow([line])
			fname = f"pe_tool_failures_{self.name}.csv"
			filedoc = save_file(fname, buf.getvalue(), self.doctype, self.name, is_private=1)
			summary["fail_link"] = filedoc.file_url

		# Notify/return
		if batch_mode:
			frappe.publish_realtime("program_enrollment_tool_done", summary, user=self.owner)
		else:
			frappe.msgprint(_("Created: {0}, Skipped: {1}, Failed: {2}").format(
				summary["created"], summary["skipped"], summary["failed"]
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



def _get_offering_window(program_offering: str):
	"""
	Return (start_date, end_date) as date objects for a Program Offering.
	We try a few common field names in ONE DB call and pick the first non-null
	values found for start and end, respectively.

	If neither start nor end is present, returns (None, None).
	"""
	if not program_offering:
		return None, None

	fields = [
		"start_date", "from_date", "offering_start_date", "head_start_date",
		"end_date", "to_date", "offering_end_date", "head_end_date",
	]
	row = frappe.db.get_value("Program Offering", program_offering, fields, as_dict=True)
	if not row:
		return None, None

	start_candidates = ("start_date", "from_date", "offering_start_date", "head_start_date")
	end_candidates   = ("end_date",   "to_date",   "offering_end_date",   "head_end_date")

	start_val = next((row[f] for f in start_candidates if row.get(f)), None)
	end_val   = next((row[f] for f in end_candidates   if row.get(f)), None)

	start = getdate(start_val) if start_val else None
	end   = getdate(end_val)   if end_val   else None
	return start, end


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def program_offering_target_ay_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	List Academic Years that overlap the given Program Offering's window.
	Ordering: most recent first (year_start_date DESC, then name DESC).

	Overlap logic (robust to partial info):
	- If both off_start & off_end: AY.start <= off_end AND AY.end >= off_start
	- If only off_start:            AY.end   >= off_start
	- If only off_end:              AY.start <= off_end
	- If neither is known:          return [] (no false positives)
	"""
	po = (filters or {}).get("program_offering")
	if not po:
		return []

	off_start, off_end = _get_offering_window(po)

	params = {
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len,
	}
	clauses = ["name LIKE %(txt)s"]

	# Build overlap predicate depending on what we know
	if off_start and off_end:
		clauses.append("COALESCE(year_start_date, '0001-01-01') <= %(off_end)s")
		clauses.append("COALESCE(year_end_date,   '9999-12-31') >= %(off_start)s")
		params.update({"off_start": off_start, "off_end": off_end})
	elif off_start and not off_end:
		clauses.append("COALESCE(year_end_date, '9999-12-31') >= %(off_start)s")
		params.update({"off_start": off_start})
	elif off_end and not off_start:
		clauses.append("COALESCE(year_start_date, '0001-01-01') <= %(off_end)s")
		params.update({"off_end": off_end})
	else:
		# No usable offering dates → no candidates (keeps UX honest)
		return []

	sql = f"""
		SELECT name
		FROM `tabAcademic Year`
		WHERE {' AND '.join(clauses)}
		ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
		LIMIT %(start)s, %(page_len)s
	"""
	return frappe.db.sql(sql, params)

