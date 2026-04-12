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
   - Side effects (User, Student Patient, Contact) are GATED
     and intentionally NOT executed during Phase 1
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
       - Image renaming & syncing
       - Sibling synchronization

Invariant:
-----------
In steady state, Students MUST originate from Applicant promotion.
All other creation paths are explicit, auditable exceptions.

This file intentionally enforces that invariant in Python,
not at schema level, to preserve import and migration safety.
"""

import os
import random
import string

import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.desk.form.linked_with import get_linked_doctypes
from frappe.model.document import Document
from frappe.utils import get_files_path, get_link_to_form, getdate, today, validate_email_address

from ifitwala_ed.accounting.account_holder_utils import validate_account_holder_for_student
from ifitwala_ed.governance.policy_utils import (
    MEDIA_CONSENT_POLICY_KEY,
    has_applicant_policy_acknowledgement,
)


class Student(Document):
    def onload(self):
        load_address_and_contact(self)

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
        Phase-1 gating:
        - If created via Applicant promotion: NO side effects (no user, no patient, no contact).
        - For imported/onboarded Students: keep existing behavior.
        """
        if getattr(frappe.flags, "from_applicant_promotion", False):
            return
        self.create_student_user()
        self.create_student_patient()
        self.ensure_contact_and_link()

    def on_update(self):
        self.rename_student_image()
        self.ensure_contact_and_link()
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

    def _has_media_consent(self) -> bool:
        if not self.student_applicant:
            return False
        return has_applicant_policy_acknowledgement(
            policy_key=MEDIA_CONSENT_POLICY_KEY,
            student_applicant=self.student_applicant,
        )

    def rename_student_image(self):
        # Only proceed if there's a student_image
        if not self.student_image:
            return

        if not self._has_media_consent():
            return

        try:
            file_name = frappe.db.get_value(
                "File",
                {"file_url": self.student_image, "attached_to_doctype": "Student", "attached_to_name": self.name},
                "name",
            )
            if file_name and frappe.db.exists("File Classification", {"file": file_name}):
                return

            student_id = self.name
            current_file_name = os.path.basename(self.student_image)

            # Check if it already has "STU-XXXX_XXXXXX.jpg" format
            if (
                current_file_name.startswith(student_id + "_")
                and len(current_file_name.split("_")[1].split(".")[0]) == 6
                and current_file_name.split(".")[1].lower() in ["jpg", "jpeg", "png", "gif"]
                and self.student_image.startswith("/files/student/")
            ):
                return

            file_extension = os.path.splitext(self.student_image)[1]
            random_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=6))
            expected_file_name = f"{student_id}_{random_suffix}{file_extension}"

            student_folder_fm_path = "Home/student"
            expected_file_path = os.path.join(student_folder_fm_path, expected_file_name)

            # Check if a file with the new expected name already exists
            if frappe.db.exists("File", {"file_url": f"/files/{expected_file_path}"}):
                frappe.log_error(
                    title=_("Image Rename Skipped"),
                    message=_("Image {0} already exists for student {1}").format(expected_file_name, student_id),
                )
                return

            # Check if the original file doc exists
            file_name = frappe.db.get_value(
                "File",
                {"file_url": self.student_image, "attached_to_doctype": "Student", "attached_to_name": self.name},
                "name",
            )

            if not file_name:
                frappe.log_error(
                    title=_("Missing File Doc"),
                    message=_("No File doc found for {0}, attached_to=Student {1}").format(
                        self.student_image, self.name
                    ),
                )
                return

            file_doc = frappe.get_doc("File", file_name)

            # Ensure the "student" folder exists
            if not frappe.db.exists("File", {"file_name": "student", "folder": "Home"}):
                student_folder = frappe.get_doc(
                    {"doctype": "File", "file_name": "student", "is_folder": 1, "folder": "Home"}
                )
                student_folder.insert()

            # Rename the file on disk
            new_file_path = os.path.join(get_files_path(), "student", expected_file_name)
            os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

            old_rel_path = (file_doc.file_url or "").lstrip("/")
            if not old_rel_path:
                frappe.throw(_("Original file URL is missing."))
            old_file_path = frappe.utils.get_site_path(old_rel_path)

            if os.path.exists(old_file_path):
                os.rename(old_file_path, new_file_path)
                new_url = f"/files/student/{expected_file_name}"
                frappe.db.set_value(
                    "File",
                    file_doc.name,
                    {
                        "file_name": expected_file_name,
                        "file_url": new_url,
                        "folder": "Home/student",
                        "is_private": 0,
                    },
                    update_modified=False,
                )
            else:
                frappe.throw(_("Original file not found: {file_path}").format(file_path=old_file_path))

            # Update doc.student_image to reflect new URL
            frappe.db.set_value(
                "Student",
                self.name,
                "student_image",
                new_url,
                update_modified=False,
            )
            self.student_image = new_url

            from ifitwala_ed.utilities.image_utils import process_single_file

            file_doc.file_url = new_url
            process_single_file(file_doc)

            frappe.msgprint(
                _("Image renamed to {file_name} and moved to /files/student/").format(file_name=expected_file_name)
            )

        except Exception as e:
            frappe.log_error(
                title=_("Student Image Error"), message=f"Error handling student image for {self.name}: {e}"
            )
            frappe.msgprint(
                _("Error handling student image for {student_name}: {error}").format(
                    student_name=self.name,
                    error=e,
                )
            )

    # Sync the student image to the linked contact. This method is called after the student image is renamed
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
        """Idempotently ensure a Contact exists for this student's User and is linked back to the Student.
        No msgprint, safe to call from after_insert and on_update."""
        if not self.student_email:
            return

        # Require a User (created in after_insert)
        if not frappe.db.exists("User", self.student_email):
            return

        # 1) Find or create Contact bound to this user
        contact_name = frappe.db.get_value("Contact", {"user": self.student_email}, "name")
        if not contact_name:
            # Create a minimal Contact
            contact = frappe.get_doc(
                {
                    "doctype": "Contact",
                    "user": self.student_email,
                    "first_name": self.student_first_name
                    or self.student_preferred_name
                    or self.student_last_name
                    or self.name,
                    "last_name": self.student_last_name or "",
                    "image": self.student_image or None,
                }
            )
            contact.flags.ignore_permissions = True
            if hasattr(contact, "email_id") and self.student_email:
                contact.email_id = self.student_email
            try:
                contact.insert()
                contact_name = contact.name
            except Exception:
                # If another request created it concurrently, load it
                contact_name = frappe.db.get_value("Contact", {"user": self.student_email}, "name")
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
        frappe.throw(_("Invalid Student: {0}").format(student_name or _("missing")))
    student = frappe.get_doc("Student", student_name)
    if not frappe.has_permission("Student", doc=student, ptype=ptype):
        frappe.throw(_("You do not have permission to {0} this Student.").format(ptype))
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
        frappe.throw(_("Invalid Address: {0}").format(address_name or _("missing")))
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


@frappe.whitelist()
def get_student_crm_summary(student_name: str) -> dict:
    student = _require_student_access(student_name, ptype="read")
    contact_name = (get_contact_linked_to_student(student.name) or "").strip()
    address_names = _get_student_address_names(student.name)

    can_open_contact = bool(contact_name and frappe.has_permission("Contact", doc=contact_name, ptype="read"))
    readable_addresses = [
        address_name
        for address_name in address_names
        if frappe.has_permission("Address", doc=address_name, ptype="read")
    ]

    return {
        "contact": contact_name if can_open_contact else None,
        "addresses": readable_addresses,
        "address_count": len(address_names),
        "has_hidden_addresses": len(readable_addresses) != len(address_names),
    }


@frappe.whitelist()
def get_family_address_link_proposal(student_name: str, address_name: str | None = None) -> dict:
    student = _require_student_access(student_name, ptype="read")
    student_address_names = _get_student_address_names(student.name)

    resolved_address = (address_name or "").strip()
    if resolved_address:
        if resolved_address not in student_address_names:
            frappe.throw(_("Address {0} is not linked to Student {1}.").format(resolved_address, student.name))
    elif len(student_address_names) == 1:
        resolved_address = student_address_names[0]
    else:
        return {
            "address": None,
            "linked_addresses": student_address_names,
            "has_candidates": False,
            "reason": "requires_exactly_one_student_address",
        }

    if not frappe.has_permission("Address", doc=resolved_address, ptype="read"):
        return {
            "address": None,
            "linked_addresses": student_address_names,
            "has_candidates": False,
            "reason": "address_not_readable",
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
