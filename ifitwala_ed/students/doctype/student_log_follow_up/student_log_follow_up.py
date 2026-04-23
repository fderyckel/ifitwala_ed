# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student_log_follow_up/student_log_follow_up.py

import frappe
from frappe import _
from frappe.desk.form.assign_to import remove as assign_remove
from frappe.model.document import Document

ADMIN_ROLES = {"Academic Admin", "System Manager", "Administrator"}


def _current_log_assignee(log_name: str) -> str | None:
    if not log_name:
        return None
    return frappe.db.get_value(
        "ToDo",
        {"reference_type": "Student Log", "reference_name": log_name, "status": "Open"},
        "allocated_to",
    )


def _can_manage_follow_up(log_name: str, user: str | None = None) -> bool:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user) or [])
    if roles & ADMIN_ROLES:
        return True

    return (_current_log_assignee(log_name) or "").strip() == user


class StudentLogFollowUp(Document):
    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _close_open_todos_for_log(self, log_name: str):
        """
        Close ALL OPEN ToDo(s) for this Student Log.

        Policy:
        - Focus "action" items are driven by OPEN ToDos.
        - Submitting a follow-up means the assignee has acted.
        - We close all OPEN ToDos for the log (single-open policy, but defensive).
        """
        open_todos = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": "Student Log",
                "reference_name": log_name,
                "status": "Open",
            },
            fields=["name", "allocated_to"],
            limit=50,
        )

        for t in open_todos:
            allocated_to = t.get("allocated_to")
            if allocated_to:
                assign_remove("Student Log", log_name, allocated_to)
                continue

            if t.get("name"):
                frappe.db.set_value("ToDo", t["name"], "status", "Closed")

    # -----------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------
    def validate(self):
        # Guard: must point to a parent log
        if not self.student_log:
            frappe.throw(_("Please link a Student Log."))

        if not frappe.utils.strip_html(self.follow_up or "").strip():
            frappe.throw(_("Follow-up text is required."))

        # Server authoritative date (site timezone). Client should not send date.
        if not getattr(self, "date", None):
            self.date = frappe.utils.today()

        # Single read: parent status (only 'completed' is terminal now)
        status = (frappe.db.get_value("Student Log", self.student_log, "follow_up_status") or "").lower()
        if status == "completed":
            frappe.throw(_("Cannot add or edit a follow-up because the Student Log is already <b>Completed</b>."))

        if not _can_manage_follow_up(self.student_log, frappe.session.user):
            frappe.throw(
                _(
                    "Only the current assignee can submit a Student Log follow-up. Use Add Clarification for extra context."
                ),
                frappe.PermissionError,
            )

        # Ensure follow_up_author is set (read-only field in schema)
        if not self.follow_up_author:
            self.follow_up_author = frappe.utils.get_fullname(frappe.session.user)

    def on_update(self):
        if self.docstatus != 1:
            return

        # Mapping: parent status Open → In Progress when a follow-up is submitted
        log = frappe.get_doc("Student Log", self.student_log)
        if (log.follow_up_status or "") == "Open":
            log.db_set("follow_up_status", "In Progress")

    def on_submit(self):
        log = frappe.get_doc("Student Log", self.student_log)

        # Submission ≠ completion → ensure parent is In Progress
        if (log.follow_up_status or "").lower() != "in progress":
            log.db_set("follow_up_status", "In Progress")

        # Close OPEN ToDo(s) for this log (single-open policy)
        self._close_open_todos_for_log(log.name)

        # Resolve key users
        author_user = log.owner or None
        if not author_user and getattr(log, "author_name", None):
            author_user = frappe.db.get_value("Employee", {"employee_full_name": log.author_name}, "user_id")
        assignee_user = log.follow_up_person or None

        # Notify the parent author (bell + realtime), skip if it's me
        if author_user and author_user != frappe.session.user:
            try:
                frappe.get_doc(
                    {
                        "doctype": "Notification Log",
                        "subject": _("Follow-up ready to review"),
                        "email_content": _("Follow-up for {student} has been submitted. Click to review.").format(
                            student=log.student_name or log.name
                        ),
                        "type": "Alert",
                        "for_user": author_user,
                        "from_user": frappe.session.user,
                        "document_type": "Student Log",
                        "document_name": log.name,
                    }
                ).insert(ignore_permissions=True)
            except Exception:
                try:
                    frappe.publish_realtime(
                        event="inbox_notification",
                        message={
                            "type": "Alert",
                            "subject": _("Follow-up ready to review"),
                            "message": _("Follow-up for {student} has been submitted. Click to review.").format(
                                student=log.student_name or log.name
                            ),
                            "reference_doctype": "Student Log",
                            "reference_name": log.name,
                        },
                        user=author_user,
                    )
                except Exception:
                    pass

            # Optional lightweight toast in active sessions
            frappe.publish_realtime(
                event="follow_up_ready_to_review",
                message={"log_name": log.name, "student_name": log.student_name},
                user=author_user,
            )

        # Notify current assignee (follow_up_person) too; skip if self or same as author
        if assignee_user and assignee_user not in {frappe.session.user, author_user}:
            try:
                frappe.get_doc(
                    {
                        "doctype": "Notification Log",
                        "subject": _("New follow-up on assigned log"),
                        "email_content": _("A new follow-up was added for {student}. Click to review.").format(
                            student=log.student_name or log.name
                        ),
                        "type": "Alert",
                        "for_user": assignee_user,
                        "from_user": frappe.session.user,
                        "document_type": "Student Log",
                        "document_name": log.name,
                    }
                ).insert(ignore_permissions=True)
            except Exception:
                try:
                    frappe.publish_realtime(
                        event="inbox_notification",
                        message={
                            "type": "Alert",
                            "subject": _("New follow-up on assigned log"),
                            "message": _("A new follow-up was added for {student}. Click to review.").format(
                                student=log.student_name or log.name
                            ),
                            "reference_doctype": "Student Log",
                            "reference_name": log.name,
                        },
                        user=assignee_user,
                    )
                except Exception:
                    pass

        # Single concise timeline entry on the parent
        actor = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user
        log.add_comment(
            comment_type="Info",
            text=_("{actor} submitted a follow up — see {link}").format(
                actor=actor,
                link=frappe.utils.get_link_to_form(self.doctype, self.name),
            ),
        )


def get_permission_query_conditions(user: str | None = None) -> str | None:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "0=1"

    roles = set(frappe.get_roles(user) or [])
    if roles & ADMIN_ROLES:
        return None

    from ifitwala_ed.students.doctype.student_log.student_log import (
        _interpolate_sql_params,
        get_student_log_visibility_predicate,
    )

    visibility_sql, visibility_params = get_student_log_visibility_predicate(
        user=user,
        table_alias="sl",
        allow_aggregate_only=False,
    )
    if visibility_sql == "0=1":
        return "0=1"

    resolved_sql = _interpolate_sql_params(visibility_sql, visibility_params or {})
    return (
        "exists ("
        "select 1 from `tabStudent Log` sl "
        "where sl.name = `tabStudent Log Follow Up`.student_log "
        f"and {resolved_sql}"
        ")"
    )


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user) or [])
    if roles & ADMIN_ROLES:
        return True

    log_name = (getattr(doc, "student_log", None) or "").strip()
    if not log_name:
        return False

    if ptype in {"read", "select", "report"}:
        log_doc = frappe.get_doc("Student Log", log_name)
        return bool(frappe.has_permission("Student Log", ptype="read", doc=log_doc, user=user))

    if ptype in {"create", "write", "submit", "amend", "cancel", "delete"}:
        return _can_manage_follow_up(log_name, user)

    return False
