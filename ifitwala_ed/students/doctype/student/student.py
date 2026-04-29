# ifitwala_ed/students/doctype/student/student.py
# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student/student.py

"""
Student DocType — Creation Modes & Invariants
---------------------------------------------

A Student record represents a canonical, operational learner.
Students may be created through TWO explicit, supported pathways:

1) Applicant Promotion (default, steady-state)
   - Created via StudentApplicant.promote_to_student()
   - `student_applicant` is set
   - profile links such as `cohort` and `student_house` are carried from the applicant when present
   - Student CRM contact binding executes synchronously at promotion handoff
   - heavier side effects (for example Student access/user provisioning) remain gated
   - Used for all future admissions flows

2) Data Import / Migration (explicit bypass)
   - Used for onboarding existing schools or legacy data
   - Allowed ONLY when one of the following paths is used:
       - Data Import (`frappe.flags.in_import`) with `allow_direct_creation = 1` on each imported row
       - Migration (`frappe.flags.in_migration`)
       - Patch execution (`frappe.flags.in_patch`)
   - `student_applicant` is NOT required
   - All standard Student behaviors DO execute:
       - User creation
       - Student Patient creation
       - Contact linking
       - Image syncing
       - Sibling synchronization

Invariant:
-----------
In steady state, Students MUST originate from Applicant promotion.
All other creation paths are explicit, auditable exceptions.

This file intentionally enforces that invariant in Python,
not at schema level, to preserve import and migration safety.
"""

import frappe
from frappe import _
from frappe.desk.form.linked_with import get_linked_doctypes
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate, today, validate_email_address

from ifitwala_ed.accounting.account_holder_utils import validate_account_holder_for_student


class Student(Document):
    def before_insert(self):
        self._validate_creation_source()

    def validate(self):
        validate_account_holder_for_student(self)
        self.student_full_name = " ".join(
            filter(None, [self.student_first_name, self.student_middle_name, self.student_last_name])
        )
        self.validate_email()
        self._validate_siblings_list()

        if frappe.get_value("Student", self.name, "student_full_name") != self.student_full_name:
            self.update_student_name_in_linked_doctype()

        if self.student_date_of_birth and getdate(self.student_date_of_birth) >= getdate(today()):
            frappe.throw(_("Check again student's birth date.  It cannot be after today."))

        if self.student_date_of_birth and getdate(self.student_date_of_birth) >= getdate(self.student_joining_date):
            frappe.throw(
                _("Check again student's birth date and or joining date. Birth date cannot be after joining date.")
            )

        if (
            self.student_joining_date
            and self.student_exit_date
            and getdate(self.student_joining_date) > getdate(self.student_exit_date)
        ):
            frappe.throw(_("Check again the exit date. The joining date has to be earlier than the exit date."))

        # Enforce unique student_full_name
        if frappe.db.exists("Student", {"student_full_name": self.student_full_name, "name": ["!=", self.name]}):
            frappe.throw(
                _("Student Full Name '{student_full_name}' must be unique. Please choose a different name.").format(
                    student_full_name=self.student_full_name
                )
            )

    def _validate_creation_source(self):
        # Data Import rows must explicitly acknowledge direct creation.
        if getattr(frappe.flags, "in_import", False):
            if int(self.allow_direct_creation or 0) != 1:
                frappe.throw(
                    _(
                        "Student Data Import requires allow_direct_creation=1 on each row. "
                        "Add the column in your import template and set value to 1."
                    )
                )
            return

        # Canonical path: Applicant promotion
        if self.student_applicant:
            return

        # Explicit bypass for migration / patch
        if getattr(frappe.flags, "in_migration", False):
            return
        if getattr(frappe.flags, "in_patch", False):
            return

        # Explicit, audited admin bypass
        if int(self.allow_direct_creation or 0) == 1:
            return

        frappe.throw(
            _(
                "Students must be created via Applicant promotion. "
                "Use Data Import with allow_direct_creation=1, or an explicit migration/patch context."
            )
        )

    def validate_email(self):
        if self.student_email:
            validate_email_address(self.student_email, True)

    def update_student_name_in_linked_doctype(self):
        linked_doctypes = get_linked_doctypes("Student")
        for d in linked_doctypes:
            meta = frappe.get_meta(d)
            if not meta.issingle:
                if "student_name" in [f.fieldname for f in meta.fields]:
                    frappe.db.sql(
                        """UPDATE `tab{0}` set student_name = %s where {1} = %s""".format(
                            d, linked_doctypes[d]["fieldname"][0]
                        ),
                        (self.student_full_name, self.name),
                    )

                if "child_doctype" in linked_doctypes[d].keys() and "student_name" in [
                    f.fieldname for f in frappe.get_meta(linked_doctypes[d]["child_doctype"]).fields
                ]:
                    frappe.db.sql(
                        """UPDATE `tab{0}` set student_name = %s where {1} = %s""".format(
                            linked_doctypes[d]["child_doctype"], linked_doctypes[d]["fieldname"][0]
                        ),
                        (self.student_full_name, self.name),
                    )

    def after_insert(self):
        """
        Creation ownership:
        - Applicant promotion still materializes the canonical Student -> Contact binding.
        - Imported/onboarded Students keep the broader side effects.
        """
        if getattr(frappe.flags, "from_applicant_promotion", False):
            self.ensure_contact_and_link()
            return
        self.create_student_user()
        self.create_student_patient()
        self.ensure_contact_and_link()

    def on_update(self):
        self.update_student_enabled_status()
        self.sync_student_contact_image()
        self.sync_reciprocal_siblings()

    # create student as website user
    def create_student_user(self):
        if not self.student_email:
            return
        if not frappe.db.exists("User", self.student_email):
            try:
                student_user = frappe.get_doc(
                    {
                        "doctype": "User",
                        "enabled": 1,
                        "first_name": self.student_first_name,
                        "middle_name": self.student_middle_name,
                        "last_name": self.student_last_name,
                        "email": self.student_email,
                        "username": self.student_email,
                        "gender": self.student_gender,
                        # "language": self.student_first_language,  # this create issue because our language is not the same as the frappe language.
                        "send_welcome_email": 0,  # Set to 0 to disable welcome email during import
                        "user_type": "Website User",
                    }
                )
                student_user.flags.ignore_permissions = True
                student_user.add_roles("Student")
                student_user.save()
                frappe.msgprint(
                    _("User {user_link} has been created").format(
                        user_link=get_link_to_form("User", self.student_email)
                    )
                )
            except Exception as e:
                frappe.log_error(f"Error creating user for student {self.name}: {e}")
                frappe.msgprint(f"Error creating user for student {self.name}. Check Error Log for details.")

    # Create student as patient
    def create_student_patient(self):
        if not frappe.db.exists("Student Patient", {"student_name": self.student_full_name}):
            student_patient = frappe.get_doc({"doctype": "Student Patient", "student": self.name})
            student_patient.save()
            frappe.msgprint(
                _("Student Patient {student_name} linked to this student has been created").format(
                    student_name=self.student_full_name
                )
            )

    ############################################
    ###### Update methods ######
    def update_student_enabled_status(self):
        patient = frappe.db.get_value("Student Patient", {"student": self.name}, "name")
        if not patient:
            # During Applicant promotion Phase-1, we intentionally do NOT create Patient.
            # Also allow missing patient when student_applicant exists.
            if getattr(frappe.flags, "from_applicant_promotion", False) or self.student_applicant:
                return
            frappe.throw(_("Student Patient record is missing for this student."))
        if self.enabled == 0:
            frappe.db.set_value("Student Patient", patient, "status", "Disabled")
        else:
            frappe.db.set_value("Student Patient", patient, "status", "Active")

    # Sync the student image to the linked contact.
    def sync_student_contact_image(self):
        if not self.student_image:
            return

        contact_name = frappe.db.get_value(
            "Dynamic Link",
            filters={"link_doctype": "Student", "link_name": self.name, "parenttype": "Contact"},
            fieldname="parent",
        )

        if contact_name:
            contact = frappe.get_doc("Contact", contact_name)
            if contact.image != self.student_image:
                contact.image = self.student_image
                contact.save(ignore_permissions=True)

    def _validate_siblings_list(self):
        """Prevent self-reference and duplicates in the child table before save."""
        seen = set()
        pruned = []
        for row in self.siblings or []:
            if not row.student:
                continue
            if row.student == self.name:
                frappe.throw(_("A student cannot be a sibling of themselves."))
            key = row.student
            if key in seen:
                # skip duplicate
                continue
            seen.add(key)
            pruned.append(row)
        # If we pruned anything, rebuild the child list
        if len(pruned) != len(self.siblings or []):
            self.set("siblings", pruned)

    def sync_reciprocal_siblings(self):
        """
        Make sibling links bidirectional without re-saving the other Student doc.
        - For each S in self.siblings, ensure a mirror row (student=self.name) exists under S.
        - For each S that *currently* points to self but is no longer in our list, remove that mirror row.
        Uses direct child table inserts/deletes to avoid triggering on_update on the other record.
        """
        # recursion guard
        if getattr(frappe.flags, "_in_sibling_sync", False):
            return
        frappe.flags._in_sibling_sync = True
        try:
            desired = {row.student for row in (self.siblings or []) if row.student and row.student != self.name}
            current_pointing_to_me = self._current_mirror_set(
                self.name
            )  # set of student names who have me in their siblings

            # Ensure mirrors for desired
            for sib in desired:
                self._ensure_mirror_row(parent_student=sib, sibling=self.name)

            # Remove stale mirrors
            for sib in current_pointing_to_me - desired:
                self._delete_mirror_row(parent_student=sib, sibling=self.name)
        finally:
            frappe.flags._in_sibling_sync = False

    def _current_mirror_set(self, me: str) -> set[str]:
        """Return set of Student names that currently have a child-row pointing to `me`."""
        rows = frappe.get_all(
            "Student Sibling",
            filters={"parenttype": "Student", "parentfield": "siblings", "student": me},
            fields=["parent"],
            limit=None,
        )
        # parent is the other student who lists `me` as a sibling
        return {r["parent"] for r in rows if r.get("parent") and r["parent"] != me}

    def _ensure_mirror_row(self, parent_student: str, sibling: str):
        """Create a mirror row under `parent_student` (if missing) that points to `sibling`."""
        exists = frappe.db.exists(
            "Student Sibling",
            {
                "parenttype": "Student",
                "parentfield": "siblings",
                "parent": parent_student,
                "student": sibling,
            },
        )
        if exists:
            return

        # Insert child row directly; don't save the parent Student to avoid event loops
        child = frappe.get_doc(
            {
                "doctype": "Student Sibling",
                "parenttype": "Student",
                "parentfield": "siblings",
                "parent": parent_student,
                "student": sibling,
                # convenience fields; fetch_from keeps them fresh too
                "sibling_name": self.student_full_name,
                "sibling_gender": self.student_gender,
                "sibling_date_of_birth": self.student_date_of_birth,
            }
        )
        child.insert(ignore_permissions=True)

    def _delete_mirror_row(self, parent_student: str, sibling: str):
        """Delete the mirror row under `parent_student` that points to `sibling` (if present)."""
        frappe.db.delete(
            "Student Sibling",
            {
                "parenttype": "Student",
                "parentfield": "siblings",
                "parent": parent_student,
                "student": sibling,
            },
        )

    def ensure_contact_and_link(self):
        """Idempotently ensure a canonical Contact exists and is linked back to the Student."""
        if not self.student_email:
            return

        contact_name = frappe.db.get_value(
            "Dynamic Link",
            {"link_doctype": "Student", "link_name": self.name, "parenttype": "Contact"},
            "parent",
        )
        if contact_name:
            return

        student_user = self.student_email if frappe.db.exists("User", self.student_email) else None

        # Prefer the canonical Contact bound to the student user when it exists,
        # otherwise reuse an existing primary-email Contact before creating one.
        if student_user:
            contact_name = frappe.db.get_value("Contact", {"user": student_user}, "name")
        if not contact_name:
            contact_name = frappe.db.get_value(
                "Contact Email",
                {"email_id": self.student_email, "is_primary": 1},
                "parent",
            )

        if not contact_name:
            # Create a minimal Contact
            contact_payload = {
                "doctype": "Contact",
                "first_name": self.student_first_name
                or self.student_preferred_name
                or self.student_last_name
                or self.name,
                "last_name": self.student_last_name or "",
                "image": self.student_image or None,
            }
            if student_user:
                contact_payload["user"] = student_user

            contact = frappe.get_doc(contact_payload)
            contact.flags.ignore_permissions = True
            if hasattr(contact, "email_id") and self.student_email:
                contact.email_id = self.student_email
            try:
                contact.insert()
                contact_name = contact.name
            except Exception:
                # If another request created it concurrently, load it
                contact_name = None
                if student_user:
                    contact_name = frappe.db.get_value("Contact", {"user": student_user}, "name")
                if not contact_name:
                    contact_name = frappe.db.get_value(
                        "Contact Email",
                        {"email_id": self.student_email, "is_primary": 1},
                        "parent",
                    )
                if not contact_name:
                    raise
                contact = frappe.get_doc("Contact", contact_name)
        else:
            contact = frappe.get_doc("Contact", contact_name)

        # 2) Ensure Dynamic Link → Student (idempotent)
        link_exists = frappe.db.exists(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parentfield": "links",
                "parent": contact.name,
                "link_doctype": "Student",
                "link_name": self.name,
            },
        )
        if link_exists:
            return

        contact.append("links", {"link_doctype": "Student", "link_name": self.name})
        contact.save(ignore_permissions=True)


@frappe.whitelist()
def get_contact_linked_to_student(student_name):
    """Pure read: return Contact name linked to this Student, or None."""
    return frappe.db.get_value(
        "Dynamic Link", {"link_doctype": "Student", "link_name": student_name, "parenttype": "Contact"}, "parent"
    )


def _require_student_access(student_name: str, *, ptype: str = "read") -> "Student":
    student_name = (student_name or "").strip()
    if not student_name or not frappe.db.exists("Student", student_name):
        frappe.throw(_("Invalid Student: {student}").format(student=student_name or _("missing")))
    student = frappe.get_doc("Student", student_name)
    if not frappe.has_permission("Student", doc=student, ptype=ptype):
        frappe.throw(_("You do not have permission to {permission_type} this Student.").format(permission_type=ptype))
    return student


def _get_student_address_names(student_name: str) -> list[str]:
    rows = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": "Address",
            "link_doctype": "Student",
            "link_name": student_name,
        },
        fields=["parent"],
        order_by="creation asc",
        limit=0,
    )
    return [(row.get("parent") or "").strip() for row in rows if (row.get("parent") or "").strip()]


def _has_address_link(*, link_doctype: str, link_name: str, address_name: str | None = None) -> bool:
    filters = {
        "parenttype": "Address",
        "link_doctype": link_doctype,
        "link_name": link_name,
    }
    if address_name:
        filters["parent"] = address_name
    return bool(frappe.db.exists("Dynamic Link", filters))


def _build_family_address_link_proposal(student: "Student", address_name: str) -> dict:
    eligible_guardians = []
    skipped_guardians = []
    eligible_siblings = []
    skipped_siblings = []

    for row in student.get("guardians") or []:
        guardian_name = (row.get("guardian") or "").strip()
        if not guardian_name:
            continue
        if _has_address_link(link_doctype="Guardian", link_name=guardian_name, address_name=address_name):
            continue
        if _has_address_link(link_doctype="Guardian", link_name=guardian_name):
            skipped_guardians.append(
                {
                    "guardian": guardian_name,
                    "guardian_name": row.get("guardian_name") or guardian_name,
                    "reason": "existing_address",
                }
            )
            continue
        eligible_guardians.append(
            {
                "guardian": guardian_name,
                "guardian_name": row.get("guardian_name") or guardian_name,
                "relation": row.get("relation") or "",
            }
        )

    for row in student.get("siblings") or []:
        sibling_name = (row.get("student") or "").strip()
        if not sibling_name or sibling_name == student.name:
            continue
        if _has_address_link(link_doctype="Student", link_name=sibling_name, address_name=address_name):
            continue
        if _has_address_link(link_doctype="Student", link_name=sibling_name):
            skipped_siblings.append(
                {
                    "student": sibling_name,
                    "sibling_name": row.get("sibling_name") or sibling_name,
                    "reason": "existing_address",
                }
            )
            continue
        eligible_siblings.append(
            {
                "student": sibling_name,
                "sibling_name": row.get("sibling_name") or sibling_name,
            }
        )

    return {
        "address": address_name,
        "eligible_guardians": eligible_guardians,
        "eligible_siblings": eligible_siblings,
        "skipped_guardians": skipped_guardians,
        "skipped_siblings": skipped_siblings,
        "has_candidates": bool(eligible_guardians or eligible_siblings),
    }


def _ensure_address_link(
    address_name: str, *, link_doctype: str, link_name: str, link_title: str | None = None
) -> bool:
    address_name = (address_name or "").strip()
    link_doctype = (link_doctype or "").strip()
    link_name = (link_name or "").strip()

    if not address_name or not frappe.db.exists("Address", address_name):
        frappe.throw(_("Invalid Address: {address}").format(address=address_name or _("missing")))
    if not link_doctype:
        frappe.throw(_("Link DocType is required."))
    if not link_name:
        frappe.throw(_("Link name is required."))
    if _has_address_link(link_doctype=link_doctype, link_name=link_name, address_name=address_name):
        return False

    links_field = frappe.get_meta("Address").get_field("links")
    if not links_field:
        frappe.throw(_("Address links field is missing from Address metadata."))

    frappe.get_doc(
        {
            "doctype": "Dynamic Link",
            "parenttype": "Address",
            "parentfield": links_field.fieldname,
            "parent": address_name,
            "link_doctype": link_doctype,
            "link_name": link_name,
            "link_title": (link_title or "").strip() or None,
        }
    ).insert(ignore_permissions=True)
    return True


def _parse_name_list(value) -> list[str]:
    parsed = frappe.parse_json(value) if isinstance(value, str) else value
    if not parsed:
        return []
    if not isinstance(parsed, list):
        frappe.throw(_("Expected a list payload."))
    names = []
    seen = set()
    for item in parsed:
        normalized = (item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        names.append(normalized)
    return names


def _has_native_doctype_role_permission(doctype: str, *, ptype: str = "read", user: str | None = None) -> bool:
    """Quiet role-permission probe for native open/edit affordances.

    Do not use this as a security gate for mutations; use frappe.has_permission there.
    This helper intentionally avoids frappe.has_permission because core Frappe may
    add a permission message while returning False, which is noisy during Student
    form read-only summary rendering.
    """
    doctype = (doctype or "").strip()
    ptype = (ptype or "read").strip()
    session = getattr(frappe, "session", None)
    user = user or getattr(session, "user", None)
    if not doctype or not user or user == "Guest":
        return False
    if user == "Administrator":
        return True

    roles = set(frappe.get_roles(user) or [])
    if "System Manager" in roles:
        return True
    if not roles:
        return False

    allowed_permission_fields = {"read", "write", "create", "delete", "email", "comment", "assign"}
    if ptype not in allowed_permission_fields:
        return False

    filters = {
        "parent": doctype,
        "permlevel": 0,
        "role": ["in", list(roles)],
        ptype: 1,
    }
    for permission_doctype in ("Custom DocPerm", "DocPerm"):
        if frappe.get_all(permission_doctype, filters=filters, fields=["name"], limit=1):
            return True
    return False


def _build_student_contact_summary(contact_name: str | None) -> dict | None:
    contact_name = (contact_name or "").strip()
    if not contact_name or not frappe.db.exists("Contact", contact_name):
        return None

    contact_row = (
        frappe.db.get_value(
            "Contact",
            contact_name,
            ["first_name", "last_name", "email_id", "mobile_no"],
            as_dict=True,
        )
        or {}
    )
    display_name = (
        " ".join(
            filter(
                None,
                [
                    (contact_row.get("first_name") or "").strip(),
                    (contact_row.get("last_name") or "").strip(),
                ],
            )
        ).strip()
        or contact_name
    )

    email_rows = frappe.get_all(
        "Contact Email",
        filters={"parent": contact_name},
        fields=["email_id", "is_primary", "idx"],
        order_by="is_primary desc, idx asc, creation asc",
        limit=0,
    )
    phone_rows = frappe.get_all(
        "Contact Phone",
        filters={"parent": contact_name},
        fields=["phone", "is_primary_mobile_no", "idx"],
        order_by="is_primary_mobile_no desc, idx asc, creation asc",
        limit=0,
    )

    emails = []
    seen_emails = set()
    for row in email_rows:
        value = (row.get("email_id") or "").strip()
        if not value or value in seen_emails:
            continue
        seen_emails.add(value)
        emails.append({"value": value, "is_primary": int(row.get("is_primary") or 0)})

    fallback_email = (contact_row.get("email_id") or "").strip()
    if fallback_email and fallback_email not in seen_emails:
        emails.insert(0, {"value": fallback_email, "is_primary": 1})

    phones = []
    seen_phones = set()
    for row in phone_rows:
        value = (row.get("phone") or "").strip()
        if not value or value in seen_phones:
            continue
        seen_phones.add(value)
        phones.append({"value": value, "is_primary": int(row.get("is_primary_mobile_no") or 0)})

    fallback_phone = (contact_row.get("mobile_no") or "").strip()
    if fallback_phone and fallback_phone not in seen_phones:
        phones.insert(0, {"value": fallback_phone, "is_primary": 1})

    return {
        "name": contact_name,
        "display_name": display_name,
        "emails": emails,
        "phones": phones,
    }


def _build_student_address_summaries(address_names: list[str]) -> list[dict]:
    if not address_names:
        return []

    rows = frappe.get_all(
        "Address",
        filters={"name": ["in", address_names]},
        fields=[
            "name",
            "address_title",
            "address_type",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "country",
            "pincode",
        ],
        order_by="creation asc",
        limit=0,
    )
    by_name = {(row.get("name") or "").strip(): row for row in rows if (row.get("name") or "").strip()}

    summaries = []
    for address_name in address_names:
        row = by_name.get(address_name)
        if not row:
            continue

        locality = ", ".join(
            part for part in [(row.get("city") or "").strip(), (row.get("state") or "").strip()] if part
        )
        if locality and (row.get("pincode") or "").strip():
            locality = f"{locality} {(row.get('pincode') or '').strip()}"
        elif not locality:
            locality = (row.get("pincode") or "").strip()

        lines = [
            (row.get("address_line1") or "").strip(),
            (row.get("address_line2") or "").strip(),
            locality,
            (row.get("country") or "").strip(),
        ]
        summaries.append(
            {
                "name": address_name,
                "display_title": (row.get("address_title") or address_name).strip() or address_name,
                "address_type": (row.get("address_type") or "").strip(),
                "lines": [line for line in lines if line],
            }
        )

    return summaries


@frappe.whitelist()
def get_student_crm_summary(student_name: str) -> dict:
    student = _require_student_access(student_name, ptype="read")
    contact_name = (get_contact_linked_to_student(student.name) or "").strip()
    address_names = _get_student_address_names(student.name)
    contact_summary = _build_student_contact_summary(contact_name)
    address_summaries = _build_student_address_summaries(address_names)
    resolved_address_names = [row["name"] for row in address_summaries]

    can_open_contact = bool(contact_name and _has_native_doctype_role_permission("Contact", ptype="read"))
    can_open_address = _has_native_doctype_role_permission("Address", ptype="read")
    readable_addresses = [address_name for address_name in resolved_address_names if can_open_address]

    return {
        "contact": contact_name if can_open_contact else None,
        "contact_summary": contact_summary,
        "has_hidden_contact": bool(contact_summary and not can_open_contact),
        "addresses": readable_addresses,
        "address_summaries": address_summaries,
        "address_count": len(address_summaries),
        "has_hidden_addresses": len(readable_addresses) != len(address_summaries),
    }


@frappe.whitelist()
def get_family_address_link_proposal(student_name: str, address_name: str | None = None) -> dict:
    student = _require_student_access(student_name, ptype="read")
    student_address_names = _get_student_address_names(student.name)

    resolved_address = (address_name or "").strip()
    if resolved_address:
        if resolved_address not in student_address_names:
            frappe.throw(
                _("Address {address} is not linked to Student {student}.").format(
                    address=resolved_address,
                    student=student.name,
                )
            )
    elif len(student_address_names) == 1:
        resolved_address = student_address_names[0]
    else:
        return {
            "address": None,
            "linked_addresses": student_address_names,
            "has_candidates": False,
            "reason": "requires_exactly_one_student_address",
        }

    if not _has_native_doctype_role_permission("Address", ptype="write"):
        return {
            "address": None,
            "linked_addresses": student_address_names,
            "has_candidates": False,
            "reason": "address_not_writable",
        }

    proposal = _build_family_address_link_proposal(student, resolved_address)
    proposal["linked_addresses"] = student_address_names
    return proposal


@frappe.whitelist()
def link_family_address(student_name: str, address_name: str, guardians=None, siblings=None) -> dict:
    student = _require_student_access(student_name, ptype="write")
    if not frappe.has_permission("Address", doc=address_name, ptype="write"):
        frappe.throw(_("You do not have permission to update this Address."))

    proposal = get_family_address_link_proposal(student.name, address_name)
    if proposal.get("reason"):
        frappe.throw(_("Address linking proposal is not available for this Student."))

    requested_guardians = set(_parse_name_list(guardians))
    requested_siblings = set(_parse_name_list(siblings))
    allowed_guardians = {row["guardian"] for row in proposal.get("eligible_guardians") or []}
    allowed_siblings = {row["student"] for row in proposal.get("eligible_siblings") or []}

    invalid_guardians = sorted(requested_guardians - allowed_guardians)
    invalid_siblings = sorted(requested_siblings - allowed_siblings)
    if invalid_guardians or invalid_siblings:
        frappe.throw(_("Address targets are stale. Refresh the Student form and try again."))
    if not requested_guardians and not requested_siblings:
        frappe.throw(_("Select at least one family record to link to this Address."))

    guardian_titles = {
        row["guardian"]: row.get("guardian_name") or row["guardian"] for row in proposal.get("eligible_guardians") or []
    }
    sibling_titles = {
        row["student"]: row.get("sibling_name") or row["student"] for row in proposal.get("eligible_siblings") or []
    }

    linked_guardians = []
    linked_siblings = []

    for guardian_name in sorted(requested_guardians):
        if _ensure_address_link(
            address_name,
            link_doctype="Guardian",
            link_name=guardian_name,
            link_title=guardian_titles.get(guardian_name),
        ):
            linked_guardians.append(guardian_name)

    for sibling_name in sorted(requested_siblings):
        if _ensure_address_link(
            address_name,
            link_doctype="Student",
            link_name=sibling_name,
            link_title=sibling_titles.get(sibling_name),
        ):
            linked_siblings.append(sibling_name)

    return {
        "address": address_name,
        "linked_guardians": linked_guardians,
        "linked_siblings": linked_siblings,
        "guardians_count": len(linked_guardians),
        "siblings_count": len(linked_siblings),
    }


@frappe.whitelist()
def get_student_guardians(student_id: str) -> list[dict]:
    """Return guardians for a given student. Used for sibling guardian sync."""
    if not student_id or not frappe.db.exists("Student", student_id):
        return []

    return frappe.get_all(
        "Student Guardian",
        filters={"parent": student_id, "parenttype": "Student", "parentfield": "guardians"},
        fields=["guardian", "guardian_name", "relation", "can_consent", "email", "phone"],
    )
