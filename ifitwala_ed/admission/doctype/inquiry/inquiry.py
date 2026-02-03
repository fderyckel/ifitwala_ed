# ifitwala_ed/admission/doctype/inquiry/inquiry.py
# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/admission/doctype/inquiry/inquiry.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, cint, get_datetime
from frappe.desk.form.assign_to import remove as remove_assignment
from ifitwala_ed.admission.admission_utils import (
	ensure_admissions_permission,
	notify_admission_manager,
	set_inquiry_deadlines,
	update_sla_status,
)
from datetime import datetime


CANONICAL_INQUIRY_STATES = {"New", "Assigned", "Contacted", "Qualified", "Archived"}


def _normalize_inquiry_state(state: str | None) -> str:
	if not state:
		return "New"
	return state


class Inquiry(Document):
	def validate(self):
		self._validate_org_consistency()
		self._validate_state_change()
		self._validate_student_applicant_link()

	def _validate_org_consistency(self):
		if not self.school:
			return

		school_org = frappe.db.get_value("School", self.school, "organization")
		if not school_org:
			frappe.throw(_("Selected School does not have an Organization."))

		if not self.organization:
			self.organization = school_org
			return

		if self.organization == school_org:
			return

		org_bounds = frappe.db.get_value("Organization", self.organization, ["lft", "rgt"], as_dict=True)
		school_org_bounds = frappe.db.get_value("Organization", school_org, ["lft", "rgt"], as_dict=True)
		if not org_bounds or not school_org_bounds:
			frappe.throw(_("Selected School does not belong to the selected Organization."))

		if not (org_bounds.lft <= school_org_bounds.lft and org_bounds.rgt >= school_org_bounds.rgt):
			frappe.throw(_("Selected School does not belong to the selected Organization."))

	def _validate_state_change(self):
		previous_raw = self.get_db_value("workflow_state")
		current_raw = self.workflow_state

		if not previous_raw and not current_raw:
			return

		if current_raw and current_raw not in CANONICAL_INQUIRY_STATES:
			frappe.throw(_("Invalid workflow state: {0}.").format(current_raw))

		if previous_raw == current_raw:
			return

		if self.flags.get("allow_workflow_state_change"):
			return

		if not previous_raw:
			if current_raw != "New":
				frappe.throw(_("Workflow state must start at New."))
			return

		previous = _normalize_inquiry_state(previous_raw)
		current = _normalize_inquiry_state(current_raw)
		self._ensure_transition_allowed(previous, current)

	def _validate_student_applicant_link(self):
		if not self.student_applicant:
			return

		previous = self.get_db_value("student_applicant")
		if previous and previous != self.student_applicant:
			frappe.throw(_("Student Applicant link is immutable once set."))

	def _ensure_transition_allowed(self, from_state: str, to_state: str):
		if from_state == to_state:
			return

		if to_state == "Archived":
			if from_state == "Archived":
				frappe.throw(_("Inquiry is already Archived."))
			return

		allowed = {
			"New": {"Assigned", "Contacted"},
			"Assigned": {"Contacted"},
			"Contacted": {"Qualified"},
			"Qualified": set(),
		}

		if from_state not in allowed or to_state not in allowed[from_state]:
			frappe.throw(_("Invalid workflow state transition from {0} to {1}.").format(from_state, to_state))

	def _set_workflow_state(self, target_state: str, comment: str | None = None) -> bool:
		current = _normalize_inquiry_state(self.workflow_state)
		target = _normalize_inquiry_state(target_state)

		if current == target:
			return False

		if target not in CANONICAL_INQUIRY_STATES:
			frappe.throw(_("Invalid workflow state: {0}.").format(target))

		self._ensure_transition_allowed(current, target)

		self.db_set("workflow_state", target, update_modified=False)
		self.workflow_state = target

		if comment:
			self.add_comment("Comment", text=comment)
		return True

	def mark_assigned(self, add_comment: bool = True):
		ensure_admissions_permission()
		current_state = _normalize_inquiry_state(self.workflow_state)
		if current_state == "Assigned":
			return {"ok": True}

		self._ensure_transition_allowed(current_state, "Assigned")
		self.db_set("workflow_state", "Assigned", update_modified=False)
		self.workflow_state = "Assigned"

		if not self.assigned_at:
			ts = now_datetime()
			self.assigned_at = ts
			self.db_set("assigned_at", ts, update_modified=False)

		if add_comment:
			self.add_comment(
				"Comment",
				text=_("Inquiry marked as <b>Assigned</b> by {0} on {1}.").format(
					frappe.bold(frappe.session.user), now_datetime()
				),
			)
		return {"ok": True}

	@frappe.whitelist()
	def mark_qualified(self):
		ensure_admissions_permission()
		changed = self._set_workflow_state(
			"Qualified",
			comment=_("Inquiry marked as <b>Qualified</b> by {0} on {1}.").format(
				frappe.bold(frappe.session.user), now_datetime()
			),
		)
		return {"ok": True, "changed": changed}

	@frappe.whitelist()
	def archive(self):
		ensure_admissions_permission()
		changed = self._set_workflow_state(
			"Archived",
			comment=_("Inquiry marked as <b>Archived</b> by {0} on {1}.").format(
				frappe.bold(frappe.session.user), now_datetime()
			),
		)
		return {"ok": True, "changed": changed}

	@frappe.whitelist()
	def invite_to_apply(self) -> str:
		ensure_admissions_permission()

		current_state = _normalize_inquiry_state(self.workflow_state)
		if current_state != "Qualified":
			frappe.throw(_("Inquiry must be in the Qualified state before inviting to apply."))

		if self.student_applicant:
			return self.student_applicant

		existing = frappe.db.get_value("Student Applicant", {"inquiry": self.name}, "name")
		if existing:
			self.db_set("student_applicant", existing, update_modified=False)
			self.student_applicant = existing
			return existing

		applicant = frappe.new_doc("Student Applicant")
		applicant.flags.from_inquiry_invite = True
		applicant.first_name = self.first_name
		applicant.last_name = self.last_name
		applicant.inquiry = self.name
		applicant.application_status = "Invited"
		applicant.insert(ignore_permissions=True)

		self.db_set("student_applicant", applicant.name, update_modified=False)
		self.student_applicant = applicant.name

		self.add_comment(
			"Comment",
			text=_("Applicant invited by {0}.").format(frappe.bold(frappe.session.user)),
		)
		return applicant.name

	def before_insert(self):
		if not self.submitted_at:
			self.submitted_at = frappe.utils.now()

	def after_insert(self):
		if not self.workflow_state:
			self.workflow_state = "New"
			self.db_set("workflow_state", "New")
		notify_admission_manager(self)


	def before_save(self):
		# Only sets first_contact_due_on if missing; followup_due_on is set on (re)assignment.
		set_inquiry_deadlines(self)
		update_sla_status(self)

	@staticmethod
	def _hours_between(start_dt, end_dt) -> float:
		"""Return hours between two datetimes using only stdlib."""
		start = get_datetime(start_dt) if not isinstance(start_dt, datetime) else start_dt
		end = get_datetime(end_dt) if not isinstance(end_dt, datetime) else end_dt
		return round((end - start).total_seconds() / 3600.0, 2)

	def set_contact_metrics(self):
		# Only stamp when in Contacted; idempotent
		if self.workflow_state != "Contacted":
			return

		# 1) First contacted timestamp (once)
		if not self.first_contacted_at:
			ts = now_datetime()
			self.first_contacted_at = ts
			self.db_set("first_contacted_at", ts, update_modified=False)

		# 2) Hours from inquiry creation -> first contact (once)
		if not self.response_hours_first_contact:
			base = self.submitted_at or self.creation
			h1 = self._hours_between(base, self.first_contacted_at)
			self.response_hours_first_contact = h1
			self.db_set("response_hours_first_contact", h1, update_modified=False)

		# 3) Hours from first assignment -> first contact (once, if assigned_at exists)
		if self.assigned_at and not self.response_hours_from_assign:
			# Guard against bad data (assignment after contact)
			assign_ok = get_datetime(self.assigned_at) <= get_datetime(self.first_contacted_at)
			if assign_ok:
				h2 = self._hours_between(self.assigned_at, self.first_contacted_at)
				self.response_hours_from_assign = h2
				self.db_set("response_hours_from_assign", h2, update_modified=False)

	@frappe.whitelist()
	def create_contact_from_inquiry(self):
		if self.contact:
			frappe.msgprint(_("This Inquiry is already linked to Contact: {0}").format(self.contact))
			return

		# Check for existing email or phone match
		existing_contact = None
		if self.email:
			existing_contact = frappe.db.get_value("Contact Email", {
				"email_id": self.email,
				"is_primary": 1
			}, "parent")

		if not existing_contact and self.phone_number:
			existing_contact = frappe.db.get_value("Contact Phone", {
				"phone": self.phone_number,
				"is_primary_mobile_no": 1
			}, "parent")

		if existing_contact:
			self.contact = existing_contact
			self.db_set("contact", existing_contact)
		else:
			contact = frappe.new_doc("Contact")
			contact.first_name = self.first_name
			if self.last_name:
				contact.last_name = self.last_name
			if self.email:
				contact.append("email_ids", {
					"email_id": self.email,
					"is_primary": 1
				})
			if self.phone_number:
				contact.append("phone_nos", {
					"phone": self.phone_number,
					"is_primary_mobile_no": 1
				})
			contact.append("links", {
				"link_doctype": "Inquiry",
				"link_name": self.name
			})
			contact.insert(ignore_permissions=True)
			self.contact = contact.name
			self.db_set("contact", contact.name)

		# ✅ Add comment to Inquiry, not Contact
		self.add_comment("Comment", text=_("Linked to Contact <b>{0}</b> on {1}.").format(
			frappe.bold(self.contact),
			frappe.utils.nowdate()
		))

	@frappe.whitelist()
	def mark_contacted(self, complete_todo=False):
		ensure_admissions_permission()
		prev_assignee = self.assigned_to

		self.add_comment(
			"Comment",
			text=_("Inquiry marked as <b>Contacted</b> by {0} on {1}.").format(
				frappe.bold(frappe.session.user), now_datetime()
			),
		)

		# Update fields
		current_state = _normalize_inquiry_state(self.workflow_state)
		if current_state != "Contacted":
			self._ensure_transition_allowed(current_state, "Contacted")
			self.db_set("workflow_state", "Contacted", update_modified=False)
			self.workflow_state = "Contacted"  # keep in-memory doc in sync

		if self.get("followup_due_on"):
			self.db_set("followup_due_on", None, update_modified=False)

		# 🔎 Stamp response-time metrics immediately after state flip
		self.set_contact_metrics()

		# Optionally clear assignment on the doc
		if cint(complete_todo) and prev_assignee:
			self.db_set("assigned_to", None, update_modified=False)

		# Recompute SLA and persist
		update_sla_status(self)
		self.db_set("sla_status", self.sla_status, update_modified=False)

		# Close only the correct ToDo
		if cint(complete_todo) and prev_assignee:
			try:
				# 1) Remove native assignment (typically sets ToDo -> Cancelled)
				remove_assignment(doctype=self.doctype, name=self.name, assign_to=prev_assignee)
				# 2) Normalize only the cancelled assignment ToDo(s) to Closed
				frappe.db.sql(
					"""
					UPDATE `tabToDo`
						SET status = 'Closed'
					WHERE reference_type = %s
						AND reference_name = %s
						AND allocated_to = %s
						AND status = 'Cancelled'
					""",
					(self.doctype, self.name, prev_assignee),
				)
			except Exception:
				# Fallback: close only the most recent open ToDo for this assignee+doc
				todo_name = frappe.db.get_value(
					"ToDo",
					{
						"reference_type": self.doctype,
						"reference_name": self.name,
						"allocated_to": prev_assignee,
						"status": "Open",
					},
					"name",
					order_by="creation desc",
				)
				if todo_name:
					frappe.db.set_value("ToDo", todo_name, "status", "Closed", update_modified=False)

		return {"ok": True}
