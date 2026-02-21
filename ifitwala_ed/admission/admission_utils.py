# ifitwala_ed/admission/admission_utils.py
# Copyright (c) 2025, Francois de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/admission/admission_utils.py

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment
from frappe.desk.form.assign_to import remove as remove_assignment
from frappe.utils import add_days, getdate, now, nowdate, validate_email_address
from frappe.utils.nestedset import get_ancestors_of, get_descendants_of

ADMISSIONS_ROLES = {"Admission Manager", "Admission Officer"}


APPLICANT_DOCUMENT_SLOT_MAP = {
    "passport": {
        "slot": "identity_passport",
        "data_class": "legal",
        "purpose": "identification_document",
        "retention_policy": "until_school_exit_plus_6m",
    },
    "birth_certificate": {
        "slot": "identity_birth_cert",
        "data_class": "legal",
        "purpose": "identification_document",
        "retention_policy": "until_school_exit_plus_6m",
    },
    "health_record": {
        "slot": "health_record",
        "data_class": "safeguarding",
        "purpose": "medical_record",
        "retention_policy": "until_school_exit_plus_6m",
    },
    "transcript": {
        "slot": "prior_transcript",
        "data_class": "academic",
        "purpose": "academic_report",
        "retention_policy": "until_program_end_plus_1y",
    },
    "report_card": {
        "slot": "prior_transcript",
        "data_class": "academic",
        "purpose": "academic_report",
        "retention_policy": "until_program_end_plus_1y",
    },
    "photo": {
        "slot": "family_photo",
        "data_class": "administrative",
        "purpose": "administrative",
        "retention_policy": "immediate_on_request",
    },
    "application_form": {
        "slot": "application_form",
        "data_class": "administrative",
        "purpose": "administrative",
        "retention_policy": "until_program_end_plus_1y",
    },
}


def get_applicant_document_slot_spec(doc_type_code: str) -> dict:
    """Return slot classification spec for an Applicant Document Type code."""
    if not doc_type_code:
        return {}
    return APPLICANT_DOCUMENT_SLOT_MAP.get(doc_type_code.strip())


def ensure_admissions_permission(user: str | None = None) -> str:
    """Ensure the caller has Admission Manager or Admission Officer role."""
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to perform this action."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & ADMISSIONS_ROLES:
        return user

    frappe.throw(_("You do not have permission to perform this action."), frappe.PermissionError)
    return user


def notify_admission_manager(doc):
    """Realtime notify Admission Managers of a new inquiry (from webform)."""
    if not frappe.flags.in_web_form:
        return

    state = (doc.workflow_state or "").strip()
    is_new_submission = (doc.doctype == "Inquiry" and state == "New") or (
        doc.doctype == "Registration of Interest" and state == "New Inquiry"
    )
    if not is_new_submission:
        return

    user_ids = frappe.db.get_values("Has Role", {"role": "Admission Manager"}, "parent", as_dict=False)
    if not user_ids:
        return
    enabled = frappe.db.get_values(
        "User", {"name": ["in", [u[0] for u in user_ids]], "enabled": 1}, "name", as_dict=False
    )
    for (user,) in enabled:
        frappe.publish_realtime(
            event="inbox_notification",
            message={
                "type": "Alert",
                "subject": "New Inquiry Submitted",
                "message": f"Inquiry {doc.name} has been submitted.",
                "reference_doctype": doc.doctype,
                "reference_name": doc.name,
            },
            user=user,
        )


def check_sla_breaches():
    """
    Recompute SLA statuses using efficient SQL updates.
    Applies to Inquiry + Registration of Interest.
    """
    logger = frappe.logger("sla_breaches", allow_site=True)
    today = getdate()

    contacted_states = ("Contacted", "Qualified", "Archived")
    doc_types = ["Inquiry", "Registration of Interest"]

    for doctype in doc_types:
        if not frappe.db.table_exists(doctype):
            continue

        params = {"today": today}

        # 1) Mark Overdue
        frappe.db.sql(
            f"""
            UPDATE `tab{doctype}`
               SET sla_status = '🔴 Overdue'
             WHERE docstatus = 0
               AND (
                 (workflow_state NOT IN {contacted_states}
                  AND first_contact_due_on IS NOT NULL
                  AND first_contact_due_on < %(today)s)
                 OR
                 (workflow_state = 'Assigned'
                  AND followup_due_on IS NOT NULL
                  AND followup_due_on < %(today)s)
               )
               AND sla_status != '🔴 Overdue'
        """,
            params,
        )

        # 2) Mark Due Today
        frappe.db.sql(
            f"""
            UPDATE `tab{doctype}`
               SET sla_status = '🟡 Due Today'
             WHERE docstatus = 0
               AND (
                 (workflow_state NOT IN {contacted_states}
                  AND first_contact_due_on = %(today)s)
                 OR
                 (workflow_state = 'Assigned'
                  AND followup_due_on = %(today)s)
               )
               AND sla_status != '🟡 Due Today'
        """,
            params,
        )

        # 3) Mark Upcoming
        frappe.db.sql(
            f"""
            UPDATE `tab{doctype}`
               SET sla_status = '⚪ Upcoming'
             WHERE docstatus = 0
               AND (
                 (workflow_state NOT IN {contacted_states}
                  AND first_contact_due_on > %(today)s)
                 OR
                 (workflow_state = 'Assigned'
                  AND followup_due_on > %(today)s)
               )
               AND sla_status != '⚪ Upcoming'
        """,
            params,
        )

        # 4) Everything else = On Track
        frappe.db.sql(f"""
            UPDATE `tab{doctype}`
               SET sla_status = '✅ On Track'
             WHERE docstatus = 0
               AND (
                 workflow_state IN {contacted_states}
                 OR (first_contact_due_on IS NULL AND followup_due_on IS NULL)
               )
               AND sla_status != '✅ On Track'
        """)

    frappe.db.commit()
    logger.info("SLA sweep done.")


def _create_native_assignment(
    doctype: str, name: str, user: str, description: str, due_date: str, color: str | None = None
) -> str | None:
    add_assignment(
        {
            "assign_to": [user],
            "doctype": doctype,
            "name": name,
            "description": description,
            "date": due_date,
            "due_date": due_date,
            "notify": 1,
            "priority": "Medium",
        }
    )
    todo_name = frappe.db.get_value(
        "ToDo",
        {"reference_type": doctype, "reference_name": name, "allocated_to": user, "status": "Open"},
        "name",
        order_by="creation desc",
    )
    if color and todo_name:
        frappe.db.set_value("ToDo", todo_name, "color", color)
    return todo_name


def notify_user(user, message, doc):
    frappe.publish_realtime(
        event="inbox_notification",
        message={
            "type": "Alert",
            "subject": f"Inquiry: {doc.name}",
            "message": message,
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
        },
        user=user,
    )


def _validate_admissions_assignee(user: str) -> None:
    if not user:
        frappe.throw(_("Assignee is required."))

    enabled = frappe.db.get_value("User", user, "enabled")
    if not enabled:
        frappe.throw(_("Assignee must be an active user with the 'Admission Officer' or 'Admission Manager' role."))

    has_allowed_role = frappe.db.exists("Has Role", {"parent": user, "role": ["in", list(ADMISSIONS_ROLES)]})
    if not has_allowed_role:
        frappe.throw(_("Assignee must be an active user with the 'Admission Officer' or 'Admission Manager' role."))


def _get_organization_scope(organization: str | None) -> list[str]:
    organization = (organization or "").strip()
    if not organization:
        return []

    if not frappe.db.exists("Organization", organization):
        return []

    descendants = get_descendants_of("Organization", organization) or []
    return [organization, *[org for org in descendants if org and org != organization]]


def normalize_email_value(email: str | None) -> str:
    return (email or "").strip().lower()


def get_contact_email_options(contact_name: str | None) -> list[str]:
    contact_name = (contact_name or "").strip()
    if not contact_name:
        return []

    rows = frappe.get_all(
        "Contact Email",
        filters={"parent": contact_name},
        fields=["email_id", "is_primary", "idx"],
        order_by="is_primary desc, idx asc, creation asc",
    )
    emails: list[str] = []
    seen: set[str] = set()
    for row in rows:
        normalized = normalize_email_value(row.get("email_id"))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        emails.append(normalized)
    return emails


def get_contact_primary_email(contact_name: str | None) -> str | None:
    options = get_contact_email_options(contact_name)
    if not options:
        return None
    return options[0]


def upsert_contact_email(contact_name: str, email: str, *, set_primary_if_missing: bool = True) -> str:
    contact_name = (contact_name or "").strip()
    if not contact_name:
        frappe.throw(_("Contact is required."))

    email = normalize_email_value(email)
    if not email:
        frappe.throw(_("Email is required."))
    validate_email_address(email, True)

    existing_parent = frappe.db.get_value("Contact Email", {"email_id": email}, "parent")
    if existing_parent and existing_parent != contact_name:
        frappe.throw(_("Email {0} is already linked to another Contact.").format(frappe.bold(email)))

    contact = frappe.get_doc("Contact", contact_name)
    has_primary = False
    matching_row = None
    for row in contact.get("email_ids") or []:
        row_email = normalize_email_value(row.email_id)
        if row_email == email:
            matching_row = row
        if int(row.is_primary or 0) == 1:
            has_primary = True

    changed = False
    if matching_row:
        if set_primary_if_missing and not has_primary and int(matching_row.is_primary or 0) != 1:
            matching_row.is_primary = 1
            changed = True
    else:
        contact.append(
            "email_ids",
            {
                "email_id": email,
                "is_primary": 1 if set_primary_if_missing and not has_primary else 0,
            },
        )
        changed = True

    if changed:
        contact.save(ignore_permissions=True)

    return email


def ensure_contact_for_email(
    *,
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    phone: str | None = None,
    preferred_contact: str | None = None,
) -> str:
    normalized_email = normalize_email_value(email)
    if normalized_email:
        validate_email_address(normalized_email, True)

    preferred_contact = (preferred_contact or "").strip()
    contact_name = ""

    email_parent = ""
    if normalized_email:
        email_parent = frappe.db.get_value("Contact Email", {"email_id": normalized_email}, "parent") or ""

    if preferred_contact:
        if email_parent and email_parent != preferred_contact:
            frappe.throw(_("Email {0} is already linked to another Contact.").format(frappe.bold(normalized_email)))
        contact_name = preferred_contact
    elif email_parent:
        contact_name = email_parent
    elif phone:
        contact_name = frappe.db.get_value("Contact Phone", {"phone": phone, "is_primary_mobile_no": 1}, "parent") or ""

    if not contact_name:
        if not (first_name or "").strip() and not (last_name or "").strip():
            frappe.throw(_("Contact name is required to create a Contact."))
        contact = frappe.new_doc("Contact")
        contact.first_name = (first_name or "").strip() or _("Applicant")
        if (last_name or "").strip():
            contact.last_name = (last_name or "").strip()
        if phone:
            contact.append("phone_nos", {"phone": phone, "is_primary_mobile_no": 1})
        if normalized_email:
            contact.append("email_ids", {"email_id": normalized_email, "is_primary": 1})
        contact.insert(ignore_permissions=True)
        return contact.name

    if normalized_email:
        upsert_contact_email(contact_name, normalized_email, set_primary_if_missing=True)

    return contact_name


def ensure_inquiry_contact(inquiry_doc) -> str | None:
    contact_name = (inquiry_doc.get("contact") or "").strip()
    if not contact_name:
        inquiry_doc.create_contact_from_inquiry()
        inquiry_doc.reload()
        contact_name = (inquiry_doc.get("contact") or "").strip()

    inquiry_email = normalize_email_value(inquiry_doc.get("email"))
    if contact_name and inquiry_email:
        upsert_contact_email(contact_name, inquiry_email, set_primary_if_missing=True)

    return contact_name or None


def _school_belongs_to_organization_scope(school: str | None, organization: str | None) -> bool:
    school = (school or "").strip()
    organization = (organization or "").strip()
    if not school or not organization:
        return False

    school_org = (frappe.db.get_value("School", school, "organization") or "").strip()
    if not school_org:
        return False

    if school_org == organization:
        return True

    return organization in (get_ancestors_of("Organization", school_org) or [])


def _get_first_contact_sla_days_default():
    return frappe.get_cached_value("Admission Settings", None, "first_contact_sla_days") or 7


def set_inquiry_deadlines(doc):
    if not getattr(doc, "first_contact_due_on", None):
        base = getdate(doc.submitted_at) if getattr(doc, "submitted_at", None) else getdate(nowdate())
        doc.first_contact_due_on = add_days(base, _get_first_contact_sla_days_default())


def update_sla_status(doc):
    """This per-doc method remains for form-level updates (Assign/Save)."""
    today = getdate()
    state = (doc.workflow_state or "New").strip()
    contacted_states = {"Contacted", "Qualified", "Archived"}

    active = []
    if state not in contacted_states and getattr(doc, "first_contact_due_on", None):
        active.append(getdate(doc.first_contact_due_on))
    if state == "Assigned" and getattr(doc, "followup_due_on", None):
        active.append(getdate(doc.followup_due_on))

    if not active:
        doc.sla_status = "✅ On Track"
    elif any(d < today for d in active):
        doc.sla_status = "🔴 Overdue"
    elif any(d == today for d in active):
        doc.sla_status = "🟡 Due Today"
    else:
        doc.sla_status = "⚪ Upcoming"


@frappe.whitelist()
def assign_inquiry(doctype, docname, assigned_to):
    ensure_admissions_permission()
    doc = frappe.get_doc(doctype, docname)

    _validate_admissions_assignee(assigned_to)

    # Prevent double-assign in our custom field
    if doc.assigned_to:
        frappe.throw(
            _("{0} is already assigned to this inquiry. Please use the Reassign button instead.").format(
                doc.assigned_to
            )
        )

    # Load settings
    settings = frappe.get_cached_doc("Admission Settings")

    # Ensure first_contact_due_on exists for legacy rows
    if not getattr(doc, "first_contact_due_on", None):
        base = getdate(doc.submitted_at) if getattr(doc, "submitted_at", None) else getdate(nowdate())
        doc.first_contact_due_on = add_days(base, settings.first_contact_sla_days or 7)

    # Compute follow-up due and update Inquiry (in-memory only)
    followup_due = add_days(nowdate(), settings.followup_sla_days or 1)
    doc.assigned_to = assigned_to
    doc.followup_due_on = followup_due

    doc.mark_assigned(add_comment=False)

    # SLA + single save (avoid db_set before this)
    update_sla_status(doc)
    doc.save(ignore_permissions=True)

    # Native assignment (creates ToDo, may add comment/modify doc server-side)
    todo_name = _create_native_assignment(
        doctype=doctype,
        name=docname,
        user=assigned_to,
        description=f"Follow up inquiry {docname}",
        due_date=followup_due,
        color=(settings.todo_color or "blue"),
    )

    # Timeline + realtime (no further save)
    if todo_name:
        todo_link = frappe.utils.get_link_to_form("ToDo", todo_name)
        doc.add_comment(
            "Comment",
            text=frappe._(
                f"Assigned to <b>{assigned_to}</b> by <b>{frappe.session.user}</b> on {frappe.utils.formatdate(now())}. "
                f"See follow-up task: {todo_link}"
            ),
        )
    else:
        doc.add_comment(
            "Comment",
            text=frappe._(
                f"Assigned to <b>{assigned_to}</b> by <b>{frappe.session.user}</b> on {frappe.utils.formatdate(now())}."
            ),
        )

    notify_user(assigned_to, "🆕 You have been assigned a new inquiry.", doc)

    return {"assigned_to": assigned_to, "todo": todo_name}


@frappe.whitelist()
def reassign_inquiry(doctype, docname, new_assigned_to):
    ensure_admissions_permission()
    doc = frappe.get_doc(doctype, docname)

    # Must be currently assigned
    if not doc.assigned_to:
        frappe.throw("This inquiry is not currently assigned. Please use the Assign button instead.")
    if doc.assigned_to == new_assigned_to:
        frappe.throw("This inquiry is already assigned to this user.")

    _validate_admissions_assignee(new_assigned_to)

    settings = frappe.get_cached_doc("Admission Settings")
    prev_assigned = doc.assigned_to

    # Ensure first_contact_due_on exists for legacy rows
    if not getattr(doc, "first_contact_due_on", None):
        base = getdate(doc.submitted_at) if getattr(doc, "submitted_at", None) else getdate(nowdate())
        doc.first_contact_due_on = add_days(base, settings.first_contact_sla_days or 7)

    # Compute new follow-up due and update Inquiry (in-memory only)
    followup_due = add_days(nowdate(), settings.followup_sla_days or 1)
    doc.assigned_to = new_assigned_to
    doc.followup_due_on = followup_due

    doc.mark_assigned(add_comment=False)

    # SLA + single save BEFORE messing with native assignments/comments
    update_sla_status(doc)
    doc.save(ignore_permissions=True)

    # Remove previous native assignment (closes its ToDo)
    try:
        remove_assignment(doctype=doctype, name=docname, assign_to=prev_assigned)
    except Exception:
        # Fallback: close any leftover ToDo rows defensively
        open_todos = frappe.get_all(
            "ToDo",
            filters={"reference_type": doctype, "reference_name": docname, "status": "Open"},
            pluck="name",
        )
        for t in open_todos:
            td = frappe.get_doc("ToDo", t)
            td.status = "Closed"
            td.save(ignore_permissions=True)

    # Notify previous assignee
    notify_user(prev_assigned, "🔁 Inquiry reassigned. You are no longer responsible.", doc)

    # Create native assignment for the new assignee
    new_todo = _create_native_assignment(
        doctype=doctype,
        name=docname,
        user=new_assigned_to,
        description=f"Follow up inquiry {docname} (reassigned)",
        due_date=followup_due,
        color=(settings.todo_color or "blue"),
    )

    # Timeline + realtime (no additional save)
    if new_todo:
        todo_link = frappe.utils.get_link_to_form("ToDo", new_todo)
        doc.add_comment(
            "Comment",
            text=frappe._(
                f"Reassigned to <b>{new_assigned_to}</b> by <b>{frappe.session.user}</b> on {frappe.utils.formatdate(now())}. "
                f"New follow-up task: {todo_link}"
            ),
        )
    else:
        doc.add_comment(
            "Comment",
            text=frappe._(
                f"Reassigned to <b>{new_assigned_to}</b> by <b>{frappe.session.user}</b> on {frappe.utils.formatdate(now())}."
            ),
        )

    notify_user(new_assigned_to, "🆕 You have been assigned a new inquiry (reassignment).", doc)

    return {"reassigned_to": new_assigned_to, "todo": new_todo}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_admission_officers(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(
        """
        SELECT DISTINCT u.name
        FROM `tabUser` u
        JOIN `tabHas Role` r ON r.parent = u.name
        WHERE r.role IN ('Admission Officer', 'Admission Manager')
            AND u.enabled = 1
            AND u.name LIKE %s
        ORDER BY u.name ASC
        LIMIT %s OFFSET %s
    """,
        (f"%{txt}%", page_len, start),
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def school_by_organization_scope_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    ensure_admissions_permission()
    filters = filters or {}
    organization = (filters.get("organization") or "").strip()
    if not organization:
        return []

    organization_scope = _get_organization_scope(organization)
    if not organization_scope:
        return []

    schools = frappe.get_all(
        "School",
        filters={
            "organization": ["in", organization_scope],
            "name": ["like", f"%{txt or ''}%"],
        },
        pluck="name",
        order_by="lft asc, name asc",
        limit_start=int(start or 0),
        limit_page_length=int(page_len or 20),
    )
    return [(school,) for school in schools]


def on_todo_update_close_marks_contacted(doc, method=None):
    # Only when ToDo is Closed
    if doc.status != "Closed":
        return
    # Only for our doctypes
    if doc.reference_type not in ("Inquiry", "Registration of Interest"):
        return
    if not doc.reference_name:
        return

    try:
        ref = frappe.get_doc(doc.reference_type, doc.reference_name)
    except frappe.DoesNotExistError:
        return

    state = (ref.workflow_state or "New").strip()
    if ref.doctype == "Inquiry":
        pre_contact_states = {"New", "Assigned"}
    else:
        pre_contact_states = {"New Inquiry", "New", "Assigned"}

    # Only flip from pre-contact states
    if state not in pre_contact_states:
        return

    # Only if the closing user is the current assignee on the document
    if not getattr(ref, "assigned_to", None):
        return
    if ref.assigned_to != doc.allocated_to:
        return

    # Reuse the doc's method; don't try to close ToDo again (avoid loops)
    ref.mark_contacted(complete_todo=False)


@frappe.whitelist()
def from_inquiry_invite(
    inquiry_name: str,
    school: str,
    organization: str | None = None,
) -> str:
    """
    Create a Student Applicant from an Inquiry via an explicit invite-to-apply action.

    Architectural invariants:
    - Inquiry remains generic (no school/org forced onto it)
    - School is REQUIRED at invite time
    - Organization is REQUIRED (explicit or derived from School)
    - Applicant becomes institutionally anchored
    - No enrollment logic
    - No Student creation
    """

    # ------------------------------------------------------------------
    # Permission
    # ------------------------------------------------------------------
    ensure_admissions_permission()

    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    if not inquiry_name:
        frappe.throw(_("Inquiry name is required."))

    if not school:
        frappe.throw(_("School is required to invite an applicant."))

    if not frappe.db.exists("School", school):
        frappe.throw(_("Invalid School: {0}").format(school))

    school_org = (frappe.db.get_value("School", school, "organization") or "").strip()
    if not school_org:
        frappe.throw(_("Selected School does not have an Organization."))

    # ------------------------------------------------------------------
    # Load Inquiry (READ-ONLY usage)
    # ------------------------------------------------------------------
    inquiry = frappe.get_doc("Inquiry", inquiry_name)
    inquiry_contact = ensure_inquiry_contact(inquiry)
    inquiry_email = get_contact_primary_email(inquiry_contact)

    # ------------------------------------------------------------------
    # Prevent duplicate Applicants per Inquiry
    # ------------------------------------------------------------------
    existing = frappe.db.get_value(
        "Student Applicant",
        {"inquiry": inquiry.name},
        "name",
    )
    if existing:
        return existing

    # ------------------------------------------------------------------
    # Resolve organization (explicit or derived)
    # ------------------------------------------------------------------
    if not organization:
        organization = school_org

    organization = (organization or "").strip()

    if not organization:
        frappe.throw(_("Organization must be provided or derivable from the selected School."))

    if not frappe.db.exists("Organization", organization):
        frappe.throw(_("Invalid Organization: {0}").format(organization))

    if not _school_belongs_to_organization_scope(school, organization):
        frappe.throw(_("Selected School does not belong to the selected Organization."))

    # ------------------------------------------------------------------
    # Create Student Applicant (institutional commitment point)
    # ------------------------------------------------------------------
    applicant = frappe.get_doc(
        {
            "doctype": "Student Applicant",
            # Identity (best-effort, editable later)
            "first_name": inquiry.get("first_name"),
            "last_name": inquiry.get("last_name"),
            # Institutional anchoring (IMMUTABLE after creation)
            "school": school,
            "organization": organization,
            # Admissions intent (NOT enrollment)
            "program": inquiry.get("program"),
            "academic_year": inquiry.get("academic_year"),
            "term": inquiry.get("term"),
            # Traceability
            "inquiry": inquiry.name,
            # Contact anchor
            "applicant_contact": inquiry_contact,
            "applicant_email": inquiry_email,
            # Lifecycle
            "application_status": "Invited",
        }
    )

    # Explicit lifecycle flags (used by Applicant controller)
    applicant.flags.from_inquiry_invite = True
    applicant.flags.allow_status_change = True
    applicant.flags.status_change_source = "from_inquiry_invite"
    applicant.flags.from_contact_sync = True

    applicant.insert(ignore_permissions=True)

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------
    applicant.add_comment(
        "Comment",
        text=_("Applicant invited from Inquiry {0} for School {1} by {2}.").format(
            frappe.bold(inquiry.name),
            frappe.bold(school),
            frappe.bold(frappe.session.user),
        ),
    )

    return applicant.name
