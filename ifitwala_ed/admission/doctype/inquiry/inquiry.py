# ifitwala_ed/admission/doctype/inquiry/inquiry.py
# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/admission/doctype/inquiry/inquiry.py

from datetime import datetime

import frappe
from frappe import _
from frappe.desk.form.assign_to import remove as remove_assignment
from frappe.model.document import Document
from frappe.utils import cint, escape_html, get_datetime, now_datetime

from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    ensure_admissions_permission,
    notify_admission_manager,
    set_inquiry_deadlines,
    update_sla_status,
)
from ifitwala_ed.admission.inquiry_acknowledgement import queue_inquiry_family_acknowledgement

CANONICAL_INQUIRY_STATES = {"New", "Assigned", "Contacted", "Qualified", "Archived"}


def _normalize_inquiry_state(state: str | None) -> str:
    normalized = str(state or "").strip()
    return normalized or "New"


class Inquiry(Document):
    def validate(self):
        self._validate_org_consistency()
        self._validate_public_web_form_school_visibility()
        self._validate_state_change()
        self._validate_archive_reason()
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

    def _validate_public_web_form_school_visibility(self):
        if not frappe.flags.in_web_form or not self.school:
            return

        school_row = frappe.db.get_value(
            "School",
            self.school,
            ["show_in_inquiry", "organization"],
            as_dict=True,
        )
        if not school_row or not int(school_row.get("show_in_inquiry") or 0):
            frappe.throw(_("Selected School is not available for public inquiries."))

        organization_row = frappe.db.get_value(
            "Organization",
            school_row.get("organization"),
            ["get_inquiry", "archived"],
            as_dict=True,
        )
        if (
            not organization_row
            or not int(organization_row.get("get_inquiry") or 0)
            or int(organization_row.get("archived") or 0)
        ):
            frappe.throw(_("Selected School is not available for public inquiries."))

    def _validate_state_change(self):
        previous_raw = self.get_db_value("workflow_state")
        current_raw = self.workflow_state
        previous = _normalize_inquiry_state(previous_raw)
        current = _normalize_inquiry_state(current_raw)

        if not previous_raw and not current_raw:
            return

        if current not in CANONICAL_INQUIRY_STATES:
            frappe.throw(_("Invalid workflow state: {workflow_state}.").format(workflow_state=current_raw or current))

        # Keep stored value canonical (trimmed/defaulted).
        if current_raw != current:
            self.workflow_state = current

        if previous == current:
            return

        if self.flags.get("allow_workflow_state_change"):
            return

        if not previous_raw:
            if current != "New":
                frappe.throw(_("Workflow state must start at New."))
            return

        self._ensure_transition_allowed(previous, current)

    def _validate_student_applicant_link(self):
        if not self.student_applicant:
            return

        previous = self.get_db_value("student_applicant")
        if previous and previous != self.student_applicant:
            frappe.throw(_("Student Applicant link is immutable once set."))

    def _validate_archive_reason(self):
        state = _normalize_inquiry_state(self.workflow_state)
        reason = (self.archive_reason or "").strip()
        if self.archive_reason and self.archive_reason != reason:
            self.archive_reason = reason

        if state == "Archived" and not reason:
            frappe.throw(_("Archive reason is required when archiving an Inquiry."))

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
            frappe.throw(
                _("Invalid workflow state transition from {from_state} to {to_state}.").format(
                    from_state=from_state,
                    to_state=to_state,
                )
            )

    def _ensure_contact_action_permission(self) -> str:
        user = frappe.session.user
        if not user or user == "Guest":
            frappe.throw(_("You need to sign in to perform this action."), frappe.PermissionError)

        roles = set(frappe.get_roles(user))
        if user == "Administrator" or "System Manager" in roles or roles & ADMISSIONS_ROLES:
            return user
        if (self.assigned_to or "").strip() == user:
            return user

        frappe.throw(
            _("Only the assigned user or Admissions/System staff can mark this Inquiry as contacted."),
            frappe.PermissionError,
        )
        return user

    def _set_workflow_state(self, target_state: str, comment: str | None = None) -> bool:
        current = _normalize_inquiry_state(self.workflow_state)
        target = _normalize_inquiry_state(target_state)

        if current == target:
            return False

        if target not in CANONICAL_INQUIRY_STATES:
            frappe.throw(_("Invalid workflow state: {workflow_state}.").format(workflow_state=target))

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
                text=_("Inquiry marked as <b>Assigned</b> by {user} on {timestamp}.").format(
                    user=frappe.bold(frappe.session.user), timestamp=now_datetime()
                ),
            )
        return {"ok": True}

    @frappe.whitelist()
    def mark_qualified(self):
        ensure_admissions_permission()
        changed = self._set_workflow_state(
            "Qualified",
            comment=_("Inquiry marked as <b>Qualified</b> by {user} on {timestamp}.").format(
                user=frappe.bold(frappe.session.user), timestamp=now_datetime()
            ),
        )
        return {"ok": True, "changed": changed}

    @frappe.whitelist()
    def archive(self, reason: str | None = None):
        ensure_admissions_permission()
        archive_reason = (reason or self.archive_reason or "").strip()
        if not archive_reason:
            frappe.throw(_("Archive reason is required when archiving an Inquiry."))

        current = _normalize_inquiry_state(self.workflow_state)
        if current != "Archived":
            self._ensure_transition_allowed(current, "Archived")

        if (self.archive_reason or "").strip() != archive_reason:
            self.archive_reason = archive_reason
            self.db_set("archive_reason", archive_reason, update_modified=False)

        changed = self._set_workflow_state(
            "Archived",
            comment=_("Inquiry marked as <b>Archived</b> by {user} on {timestamp}. Reason: {reason}.").format(
                user=frappe.bold(frappe.session.user),
                timestamp=now_datetime(),
                reason=frappe.bold(escape_html(archive_reason)),
            ),
        )
        return {"ok": True, "changed": changed}

    def before_insert(self):
        if not self.submitted_at:
            self.submitted_at = frappe.utils.now()
        if frappe.flags.in_web_form and not (self.source or "").strip():
            self.source = "Website"

    def after_insert(self):
        if not self.workflow_state:
            self.workflow_state = "New"
            self.db_set("workflow_state", "New")
        notify_admission_manager(self)
        queue_inquiry_family_acknowledgement(self)

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

        # 4) Hours from current resolver assignment -> first contact (lane KPI snapshot)
        if self.resolver_assigned_at and not self.resolver_response_hours:
            resolver_ok = get_datetime(self.resolver_assigned_at) <= get_datetime(self.first_contacted_at)
            if resolver_ok:
                h3 = self._hours_between(self.resolver_assigned_at, self.first_contacted_at)
                self.resolver_response_hours = h3
                self.db_set("resolver_response_hours", h3, update_modified=False)

    @frappe.whitelist()
    def create_contact_from_inquiry(self):
        if self.contact:
            frappe.msgprint(_("This Inquiry is already linked to Contact: {contact}").format(contact=self.contact))
            return

        # Check for existing email or phone match
        existing_contact = None
        if self.email:
            existing_contact = frappe.db.get_value("Contact Email", {"email_id": self.email, "is_primary": 1}, "parent")

        if not existing_contact and self.phone_number:
            existing_contact = frappe.db.get_value(
                "Contact Phone", {"phone": self.phone_number, "is_primary_mobile_no": 1}, "parent"
            )

        if existing_contact:
            self.contact = existing_contact
            self.db_set("contact", existing_contact)
        else:
            contact = frappe.new_doc("Contact")
            contact.first_name = self.first_name
            if self.last_name:
                contact.last_name = self.last_name
            if self.email:
                contact.append("email_ids", {"email_id": self.email, "is_primary": 1})
            if self.phone_number:
                contact.append("phone_nos", {"phone": self.phone_number, "is_primary_mobile_no": 1})
            contact.append("links", {"link_doctype": "Inquiry", "link_name": self.name})
            contact.insert(ignore_permissions=True)
            self.contact = contact.name
            self.db_set("contact", contact.name)

        # ✅ Add comment to Inquiry, not Contact
        self.add_comment(
            "Comment",
            text=_("Linked to Contact <b>{contact}</b> on {date}.").format(
                contact=frappe.bold(self.contact),
                date=frappe.utils.nowdate(),
            ),
        )

    @frappe.whitelist()
    def mark_contacted(self, complete_todo=False):
        self._ensure_contact_action_permission()
        prev_assignee = self.assigned_to

        self.add_comment(
            "Comment",
            text=_("Inquiry marked as <b>Contacted</b> by {user} on {timestamp}.").format(
                user=frappe.bold(frappe.session.user), timestamp=now_datetime()
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

        # Keep assigned_to as persistent assignee history for reporting/distribution analytics.
        # complete_todo controls ToDo closure only, not assignee field erasure.

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

            # Keep assignment history on Inquiry even when native assignment cleanup runs.
            self.db_set("assigned_to", prev_assignee, update_modified=False)
            self.assigned_to = prev_assignee

        return {"ok": True}


def _is_inquiry_privileged_user(user: str) -> bool:
    roles = set(frappe.get_roles(user))
    return (
        user == "Administrator"
        or "System Manager" in roles
        or "Academic Admin" in roles
        or bool(roles & ADMISSIONS_ROLES)
    )


def get_permission_query_conditions(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "1=0"
    if _is_inquiry_privileged_user(user):
        return None

    escaped_user = frappe.db.escape(user)
    return f"`tabInquiry`.`assigned_to` = {escaped_user}"


def has_permission(doc, user=None, permission_type="read"):
    user = user or frappe.session.user
    permission_type = (permission_type or "read").lower()
    if not user or user == "Guest":
        return False
    if _is_inquiry_privileged_user(user):
        return True
    if permission_type != "read":
        return False
    if doc:
        return (doc.assigned_to or "").strip() == user
    # Allow doctype-level read check; row filtering is enforced by permission_query_conditions.
    return True
