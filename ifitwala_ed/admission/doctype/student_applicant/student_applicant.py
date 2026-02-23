# ifitwala_ed/admission/doctype/student_applicant/student_applicant.py
# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

# ifiwala_ed/admission/doctype/student_applicant/student_applicant.py

import os

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, nowdate

from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    ensure_admissions_permission,
    get_applicant_document_slot_spec,
    get_applicant_scope_ancestors,
    get_contact_primary_email,
    has_complete_applicant_document_type_classification,
    is_applicant_document_type_in_scope,
    normalize_email_value,
)
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import (
    MEDIA_CONSENT_POLICY_KEY,
    ensure_policy_applies_to_column,
    has_applicant_policy_acknowledgement,
)
from ifitwala_ed.utilities import file_dispatcher
from ifitwala_ed.utilities.school_tree import get_school_scope_for_academic_year

FAMILY_ROLES = {"Guardian"}
ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
GUARDIAN_ROLE = "Guardian"
STUDENT_ROLE = "Student"
SYSTEM_MANAGER_ROLE = "System Manager"
DECISION_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager"}
TERMINAL_STATUSES = {"Rejected", "Withdrawn", "Promoted"}

STATUS_SET = {
    "Draft",
    "Invited",
    "In Progress",
    "Submitted",
    "Under Review",
    "Missing Info",
    "Approved",
    "Rejected",
    "Withdrawn",
    "Promoted",
}

STATUS_TRANSITIONS = {
    "Draft": {"Invited"},
    "Invited": {"In Progress", "Withdrawn"},
    "In Progress": {"Submitted", "Withdrawn"},
    "Submitted": {"Under Review", "Withdrawn"},
    "Under Review": {"Missing Info", "Approved", "Rejected", "Withdrawn"},
    "Missing Info": {"In Progress"},
    "Approved": {"Promoted"},
}

EDIT_RULES = {
    "Draft": {"family": False, "staff": True},
    "Invited": {"family": True, "staff": True},
    "In Progress": {"family": True, "staff": True},
    "Submitted": {"family": False, "staff": True},
    "Under Review": {"family": False, "staff": True},
    "Missing Info": {"family": True, "staff": True},
    "Approved": {"family": False, "staff": True},
    "Rejected": {"family": False, "staff": False},
    "Withdrawn": {"family": False, "staff": False},
    "Promoted": {"family": False, "staff": False},
}

HEALTH_PROFILE_COPY_FIELDS = (
    "blood_group",
    "allergies",
    "food_allergies",
    "insect_bites",
    "medication_allergies",
    "asthma",
    "bladder__bowel_problems",
    "diabetes",
    "headache_migraine",
    "high_blood_pressure",
    "seizures",
    "bone_joints_scoliosis",
    "blood_disorder_info",
    "fainting_spells",
    "hearing_problems",
    "recurrent_ear_infections",
    "speech_problem",
    "birth_defect",
    "dental_problems",
    "g6pd",
    "heart_problems",
    "recurrent_nose_bleeding",
    "vision_problem",
    "diet_requirements",
    "medical_surgeries__hospitalizations",
    "other_medical_information",
)

HEALTH_PROFILE_VACCINATION_FIELDS = (
    "vaccine_name",
    "date",
    "vaccination_proof",
    "additional_notes",
)

STUDENT_PROFILE_FIELDS = (
    "student_preferred_name",
    "student_date_of_birth",
    "student_gender",
    "student_mobile_number",
    "student_joining_date",
    "student_first_language",
    "student_second_language",
    "student_nationality",
    "student_second_nationality",
    "residency_status",
)

STUDENT_PROFILE_REQUIRED_FIELD_LABELS = (
    ("student_date_of_birth", "Date of Birth"),
    ("student_gender", "Student Gender"),
    ("student_mobile_number", "Mobile Number"),
    ("student_joining_date", "Joining Date"),
    ("student_first_language", "First Language"),
    ("student_nationality", "Nationality"),
    ("residency_status", "Residency Status"),
)


class StudentApplicant(Document):
    def before_save(self):
        self._set_title_if_missing()

    def on_update(self):
        self._sync_applicant_user_lifecycle()

    # ---------------------------------------------------------------------
    # Core validation
    # ---------------------------------------------------------------------

    def validate(self):
        self._normalize_contact_identity_fields()
        before = self.get_doc_before_save() if not self.is_new() else None
        self._validate_institutional_anchor(before)
        self._validate_inquiry_link(before)
        self._validate_academic_year()
        self._validate_student_link(before)
        self._validate_applicant_user_link(before)
        self._validate_applicant_contact_link(before)
        self._validate_applicant_email_fields(before)
        self._validate_application_status(before)
        self._validate_edit_permissions(before)
        self._validate_attachment_guard()
        self._validate_academic_year_intent()

    # ---------------------------------------------------------------------
    # Link immutability
    # ---------------------------------------------------------------------

    def _validate_institutional_anchor(self, before):
        # Required fields
        if not self.organization or not self.school:
            frappe.throw(_("Organization and School are required for a Student Applicant."))

        # Immutability after creation
        if not before:
            return

        if before.organization != self.organization:
            frappe.throw(_("Organization is immutable once set."))

        if before.school != self.school:
            frappe.throw(_("School is immutable once set."))

    def _validate_inquiry_link(self, before):
        if not self.inquiry:
            return

        previous = before.inquiry if before else self.get_db_value("inquiry")
        if previous and previous != self.inquiry:
            frappe.throw(_("Inquiry link is immutable once set."))

        if not previous and not getattr(self.flags, "from_inquiry_invite", False):
            frappe.throw(_("Inquiry link can only be set via invite_to_apply."))

    def _validate_academic_year(self):
        if not self.academic_year or not self.school:
            return

        ay = frappe.db.get_value(
            "Academic Year", self.academic_year, ["archived", "visible_to_admission", "school"], as_dict=True
        )

        if not ay:
            frappe.throw(_("Invalid Academic Year"))

        if ay.archived:
            frappe.throw(_("This Academic Year is archived and cannot be used for admissions"))

        if not ay.visible_to_admission:
            frappe.throw(_("This Academic Year is not open for admissions"))

        valid_schools = get_school_scope_for_academic_year(self.school)

        if ay.school not in valid_schools:
            frappe.throw(_("This Academic Year is not valid for the selected school"))

    def _validate_student_link(self, before):
        if not self.student:
            return

        previous = before.student if before else self.get_db_value("student")
        if previous and previous != self.student:
            frappe.throw(_("Student link is immutable once set."))

        if not previous and not getattr(self.flags, "from_promotion", False):
            frappe.throw(_("Student link can only be set during promotion."))

    def _validate_applicant_user_link(self, before):
        if not self.applicant_user:
            return

        previous = before.applicant_user if before else self.get_db_value("applicant_user")
        if previous and previous != self.applicant_user:
            frappe.throw(_("Applicant User is immutable once set."))

        if not previous and not getattr(self.flags, "from_applicant_invite", False):
            frappe.throw(_("Applicant User can only be set via invite_applicant."))

    def _validate_applicant_contact_link(self, before):
        if not self.applicant_contact:
            return
        if not frappe.db.exists("Contact", self.applicant_contact):
            frappe.throw(_("Invalid Applicant Contact: {0}.").format(self.applicant_contact))

        previous = before.applicant_contact if before else self.get_db_value("applicant_contact")
        if previous and previous != self.applicant_contact:
            frappe.throw(_("Applicant Contact is immutable once set."))

        if not previous and not (
            getattr(self.flags, "from_inquiry_invite", False)
            or getattr(self.flags, "from_applicant_invite", False)
            or getattr(self.flags, "from_contact_sync", False)
        ):
            frappe.throw(_("Applicant Contact can only be set via invite flows."))

    def _validate_applicant_email_fields(self, before):
        if self.portal_account_email:
            previous = before.portal_account_email if before else self.get_db_value("portal_account_email")
            if previous and previous != self.portal_account_email:
                frappe.throw(_("Portal Account Email is immutable once set."))
            if not previous and not getattr(self.flags, "from_applicant_invite", False):
                frappe.throw(_("Portal Account Email can only be set via invite_applicant."))

        if self.applicant_email:
            previous = before.applicant_email if before else self.get_db_value("applicant_email")
            if previous and previous != self.applicant_email and not getattr(self.flags, "from_contact_sync", False):
                frappe.throw(_("Applicant Email is managed from Applicant Contact."))
            if not previous and not (
                getattr(self.flags, "from_inquiry_invite", False)
                or getattr(self.flags, "from_applicant_invite", False)
                or getattr(self.flags, "from_contact_sync", False)
            ):
                frappe.throw(_("Applicant Email can only be set via invite flows."))

        if self.applicant_user and self.portal_account_email:
            if normalize_email_value(self.applicant_user) != normalize_email_value(self.portal_account_email):
                frappe.throw(_("Portal Account Email must match Applicant User."))

    # ---------------------------------------------------------------------
    # Application status lifecycle
    # ---------------------------------------------------------------------

    def _validate_application_status(self, before):
        if not self.application_status:
            frappe.throw(_("Application Status is required."))

        if self.application_status not in STATUS_SET:
            frappe.throw(_("Invalid Application Status: {0}.").format(self.application_status))

        if self.is_new():
            if self.application_status == "Invited" and getattr(self.flags, "from_inquiry_invite", False):
                return
            if self.application_status != "Draft":
                frappe.throw(_("New Student Applicants must start in Draft."))
            return

        previous = before.application_status if before else self.get_db_value("application_status")
        if not previous or previous == self.application_status:
            return

        if not getattr(self.flags, "allow_status_change", False):
            frappe.throw(_("Application Status must be changed via lifecycle methods."))

        if getattr(self.flags, "status_change_source", None) != "lifecycle_method":
            frappe.throw(_("Application Status must be changed via lifecycle methods."))

        self._validate_status_transition(previous, self.application_status)

    def _validate_status_transition(self, from_status, to_status):
        allowed = STATUS_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            frappe.throw(_("Invalid Application Status transition from {0} to {1}.").format(from_status, to_status))

    # ---------------------------------------------------------------------
    # Edit permissions
    # ---------------------------------------------------------------------

    def _validate_edit_permissions(self, before):
        user = frappe.session.user
        roles = set(frappe.get_roles(user))
        is_admissions = bool(roles & ADMISSIONS_ROLES)
        is_family = bool(roles & FAMILY_ROLES)
        is_applicant = ADMISSIONS_APPLICANT_ROLE in roles
        is_system_manager = SYSTEM_MANAGER_ROLE in roles

        if self.is_new():
            if not is_admissions:
                frappe.throw(_("Only Admissions staff can create Student Applicants."))
            return

        if not before:
            return

        status_for_edit = self.application_status
        if before.application_status != self.application_status and getattr(self.flags, "allow_status_change", False):
            status_for_edit = before.application_status

        rules = EDIT_RULES.get(status_for_edit)
        if not rules:
            frappe.throw(_("Invalid Application Status: {0}.").format(status_for_edit))

        if status_for_edit in TERMINAL_STATUSES:
            if is_system_manager and getattr(self.flags, "system_manager_override", False):
                return
            if self._has_changes(before):
                frappe.throw(_("Edits are not allowed when status is {0}.").format(status_for_edit))
            return

        if not is_admissions and not is_family and not is_applicant:
            if self._has_changes(before):
                frappe.throw(_("You do not have permission to edit this Applicant."))
            return

        if is_applicant:
            if self.applicant_user != user and self._has_changes(before):
                frappe.throw(_("You do not have permission to edit this Applicant."))
            if not rules["family"] and self._has_changes(before):
                frappe.throw(_("Family edits are not allowed when status is {0}.").format(status_for_edit))
            return

        if is_family:
            if not rules["family"] and self._has_changes(before):
                frappe.throw(_("Family edits are not allowed when status is {0}.").format(status_for_edit))
            return

        if is_admissions and not rules["staff"]:
            if self._has_changes(before):
                if getattr(self.flags, "allow_status_change", False) and self._only_status_changed(before):
                    return
                frappe.throw(_("Edits are not allowed when status is {0}.").format(status_for_edit))

    def _has_changes(self, before, ignore_fields=None):
        ignore = set(ignore_fields or [])
        ignore.update({"modified", "modified_by", "creation", "owner", "idx", "docstatus"})
        for df in self.meta.fields:
            if not df.fieldname or df.fieldname in ignore:
                continue
            if self.get(df.fieldname) != before.get(df.fieldname):
                return True
        return False

    def _only_status_changed(self, before):
        return not self._has_changes(before, ignore_fields={"application_status"})

    def _validate_attachment_guard(self):
        if not self.name:
            return
        invalid = frappe.db.sql(
            """
            SELECT name
              FROM `tabFile`
             WHERE attached_to_doctype = 'Student Applicant'
               AND attached_to_name = %s
               AND (attached_to_field IS NULL OR attached_to_field = '' OR attached_to_field != 'applicant_image')
             LIMIT 1
            """,
            (self.name,),
            as_dict=True,
        )
        if invalid:
            frappe.throw(
                _(
                    "Only applicant_image can be attached directly to Student Applicant. Use Applicant Document for all other files."
                )
            )

    def _validate_academic_year_intent(self):
        if not self.academic_year:
            return
        if not self.school:
            frappe.throw(_("School is required before selecting an Academic Year."))

        ay_row = frappe.db.get_value(
            "Academic Year",
            self.academic_year,
            ["archived", "visible_to_admission", "school"],
            as_dict=True,
        )
        if not ay_row:
            frappe.throw(_("Selected Academic Year does not exist."))
        if ay_row.get("archived"):
            frappe.throw(_("Selected Academic Year is archived."))
        if not ay_row.get("visible_to_admission"):
            frappe.throw(_("Selected Academic Year is not visible to admissions."))

        scope = get_school_scope_for_academic_year(self.school)
        if ay_row.get("school") not in scope:
            frappe.throw(_("Selected Academic Year is outside the applicant's school scope."))

    def _set_title_if_missing(self):
        if (self.title or "").strip():
            return

        name_parts = [self.first_name, self.middle_name, self.last_name]
        normalized_parts = [part.strip() for part in name_parts if isinstance(part, str) and part.strip()]
        if not normalized_parts:
            return

        self.title = " ".join(normalized_parts)

    def _normalize_contact_identity_fields(self):
        self.applicant_contact = (self.applicant_contact or "").strip() or None
        self.applicant_email = normalize_email_value(self.applicant_email) or None
        self.portal_account_email = normalize_email_value(self.portal_account_email) or None

        if self.applicant_contact:
            primary_email = get_contact_primary_email(self.applicant_contact)
            if primary_email and primary_email != self.applicant_email:
                self.flags.from_contact_sync = True
                self.applicant_email = primary_email

    # ---------------------------------------------------------------------
    # Lifecycle helpers
    # ---------------------------------------------------------------------

    def _ensure_decision_permission(self):
        user = frappe.session.user
        roles = set(frappe.get_roles(user))
        if roles & DECISION_ROLES:
            return user
        frappe.throw(_("You do not have permission to perform this action."), frappe.PermissionError)

    def _set_status(
        self, new_status, action_label, permission_checker=ensure_admissions_permission, comment_suffix=None
    ):
        if permission_checker:
            permission_checker()

        if self.is_new():
            frappe.throw(_("Save the Student Applicant before changing status."))

        if self.application_status == new_status:
            return {"ok": True, "changed": False}

        self._validate_status_transition(self.application_status, new_status)

        previous = self.application_status
        self.flags.allow_status_change = True
        self.flags.status_change_source = "lifecycle_method"
        self.application_status = new_status
        self._apply_status_timestamps(previous_status=previous, new_status=new_status)
        self.save(ignore_permissions=True)

        comment_text = _("{0} by {1} on {2}. Status: {3} → {4}.").format(
            action_label,
            frappe.bold(frappe.session.user),
            now_datetime(),
            previous,
            new_status,
        )
        if comment_suffix:
            comment_text = f"{comment_text} {comment_suffix}"

        self.add_comment(
            "Comment",
            text=comment_text,
        )
        return {"ok": True, "changed": True}

    def _apply_status_timestamps(self, *, previous_status: str, new_status: str):
        if previous_status == new_status:
            return

        now_ts = now_datetime()
        if new_status == "Submitted" and not self.get("submitted_at"):
            self.submitted_at = now_ts
        if new_status in {"Approved", "Rejected", "Withdrawn"}:
            self.decision_at = now_ts

    def _ensure_applicant_actor(self):
        user = frappe.session.user
        roles = set(frappe.get_roles(user))
        if ADMISSIONS_APPLICANT_ROLE not in roles:
            frappe.throw(_("You do not have permission to perform this action."), frappe.PermissionError)
        if self.applicant_user != user:
            frappe.throw(_("You do not have permission to modify this Applicant."), frappe.PermissionError)
        return user

    def _sync_applicant_user_lifecycle(self):
        if not self.applicant_user:
            return

        before = self.get_doc_before_save()
        previous_status = before.application_status if before else self.get_db_value("application_status")
        if previous_status == self.application_status:
            return
        if self.application_status not in TERMINAL_STATUSES:
            return

        user_row = frappe.db.get_value("User", self.applicant_user, ["name", "enabled"], as_dict=True)
        if not user_row or not user_row.get("enabled"):
            return

        role_rows = frappe.get_all(
            "Has Role",
            filters={"parent": self.applicant_user},
            fields=["role"],
        )
        user_roles = {row.get("role") for row in role_rows if row.get("role")}
        non_portal_roles = user_roles - {ADMISSIONS_APPLICANT_ROLE, "All", "Guest"}
        if non_portal_roles:
            frappe.log_error(
                frappe.as_json(
                    {
                        "student_applicant": self.name,
                        "applicant_user": self.applicant_user,
                        "status": self.application_status,
                        "non_portal_roles": sorted(non_portal_roles),
                    },
                    indent=2,
                ),
                "Applicant User Disable Skipped",
            )
            return

        frappe.db.set_value("User", self.applicant_user, "enabled", 0, update_modified=False)
        self.add_comment(
            "Comment",
            text=_("Applicant portal user {0} disabled after status changed to {1}.").format(
                frappe.bold(self.applicant_user), frappe.bold(self.application_status)
            ),
        )

    @frappe.whitelist()
    def mark_in_progress(self):
        return self._set_status("In Progress", "Marked In Progress")

    def _submit_application(self, permission_checker=ensure_admissions_permission):
        # Portal users can submit directly from Invited/Missing Info; normalize
        # through In Progress so transition guards remain canonical.
        if self.application_status in {"Invited", "Missing Info"}:
            self._set_status("In Progress", "Marked In Progress", permission_checker=permission_checker)
        return self._set_status("Submitted", "Application submitted", permission_checker=permission_checker)

    @frappe.whitelist()
    def submit_application(self):
        return self._submit_application()

    @frappe.whitelist()
    def mark_under_review(self):
        return self._set_status("Under Review", "Marked Under Review")

    @frappe.whitelist()
    def mark_missing_info(self):
        return self._set_status("Missing Info", "Marked Missing Info")

    @frappe.whitelist()
    def withdraw_application(self, reason=None):
        suffix = None
        if reason:
            suffix = _("Reason: {0}.").format(reason)
        return self._set_status(
            "Withdrawn",
            "Application withdrawn",
            permission_checker=self._ensure_applicant_actor,
            comment_suffix=suffix,
        )

    @frappe.whitelist()
    def approve_application(self):
        self._ensure_decision_permission()
        self._validate_ready_for_approval()
        return self._set_status(
            "Approved",
            "Application approved",
            permission_checker=self._ensure_decision_permission,
        )

    @frappe.whitelist()
    def reject_application(self, reason=None):
        self._ensure_decision_permission()
        if not reason:
            frappe.throw(_("Rejection reason is required."))
        reason_text = _("Reason: {0}.").format(reason)
        return self._set_status(
            "Rejected",
            "Application rejected",
            permission_checker=self._ensure_decision_permission,
            comment_suffix=reason_text,
        )

    # ---------------------------------------------------------------------
    # Promotion
    # ---------------------------------------------------------------------

    @frappe.whitelist()
    def promote_to_student(self):
        ensure_admissions_permission()

        if self.application_status != "Approved":
            frappe.throw(_("Applicant must be Approved before promotion."))

        if self.student:
            self._copy_health_profile_to_student_patient(self.student, require_profile=False)
            self._set_status("Promoted", "Applicant promoted")
            return self.student

        existing = frappe.db.get_value("Student", {"student_applicant": self.name}, "name")
        if existing:
            self._copy_health_profile_to_student_patient(existing, require_profile=False)
            self.flags.from_promotion = True
            self.student = existing
            self.save(ignore_permissions=True)
            self._set_status("Promoted", "Applicant promoted")
            return existing

        prev_flag = getattr(frappe.flags, "from_applicant_promotion", False)
        frappe.flags.from_applicant_promotion = True
        try:
            fallback_email = (
                normalize_email_value(self.portal_account_email)
                or normalize_email_value(self.applicant_user)
                or normalize_email_value(self.applicant_email)
                or f"{frappe.scrub(self.name)}@applicant.local"
            )
            student = frappe.get_doc(
                {
                    "doctype": "Student",
                    "student_first_name": self.first_name,
                    "student_middle_name": self.middle_name,
                    "student_last_name": self.last_name,
                    "student_preferred_name": self.student_preferred_name or self.first_name,
                    "student_email": fallback_email,
                    "student_date_of_birth": self.student_date_of_birth,
                    "student_gender": self.student_gender,
                    "student_mobile_number": self.student_mobile_number,
                    "student_joining_date": self.student_joining_date or nowdate(),
                    "student_first_language": self.student_first_language,
                    "student_second_language": self.student_second_language,
                    "student_nationality": self.student_nationality,
                    "student_second_nationality": self.student_second_nationality,
                    "residency_status": self.residency_status,
                    "anchor_school": self.school,
                    "student_applicant": self.name,
                }
            )
            student.insert(ignore_permissions=True)
        finally:
            frappe.flags.from_applicant_promotion = prev_flag

        health_snapshot = self._copy_health_profile_to_student_patient(student.name)
        copied_docs = self._copy_promotable_documents_to_student(student)

        file_doc = self._copy_applicant_image_to_student(student)
        if file_doc and self._has_media_consent():
            try:
                student.student_image = file_doc.file_url
                student.rename_student_image()
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    "Applicant Image Publish Failed",
                )

        self.flags.from_promotion = True
        self.student = student.name
        self.save(ignore_permissions=True)
        self._set_status("Promoted", "Applicant promoted")
        self.add_comment(
            "Comment",
            text=_(
                "Promoted transfer completed: {0} Applicant Document file(s) copied; "
                "{1} vaccination row(s) synced to Student Patient {2}."
            ).format(copied_docs, health_snapshot["vaccinations"], health_snapshot["student_patient"]),
        )

        return student.name

    @frappe.whitelist()
    def upgrade_identity(self):
        ensure_admissions_permission()

        if self.application_status != "Promoted":
            frappe.throw(_("Identity Upgrade is only allowed once the applicant is Promoted."))

        student_name = (self.student or "").strip()
        if not student_name:
            frappe.throw(_("Promotion must create a Student before identity upgrade."))

        self._require_active_enrollment(student_name)
        student = frappe.get_doc("Student", student_name)

        guardian_specs = self._resolve_upgrade_guardians()
        touched_users = set()
        linked_guardians = []
        for spec in guardian_specs:
            guardian = spec["guardian"]
            relationship = spec["relationship"]
            user_name = self._ensure_guardian_user_and_roles(guardian)
            if user_name:
                touched_users.add(user_name)
            linked_guardians.append({"guardian": guardian, "relationship": relationship})

        added_guardians = self._ensure_student_guardian_links(student, linked_guardians)

        student_user = self._ensure_student_user_access(student)
        if student_user:
            touched_users.add(student_user)

        if self.applicant_user:
            self._ensure_user_roles(
                self.applicant_user,
                add_roles=set(),
                remove_roles={ADMISSIONS_APPLICANT_ROLE},
            )
            touched_users.add(self.applicant_user)

        user_list = ", ".join(sorted(touched_users)) if touched_users else _("none")
        guardian_list = (
            ", ".join(sorted({row["guardian"].name for row in linked_guardians})) if linked_guardians else _("none")
        )
        self.add_comment(
            "Comment",
            text=_(
                "Identity Upgrade completed by {0} on {1}. "
                "State: Promoted -> Identity Upgraded. "
                "Student: {2}. Guardians linked: {3} (new links: {4}). Users updated: {5}."
            ).format(
                frappe.bold(frappe.session.user),
                now_datetime(),
                frappe.bold(student_name),
                guardian_list,
                added_guardians,
                user_list,
            ),
        )
        return {
            "ok": True,
            "student": student_name,
            "guardians_linked": [row["guardian"].name for row in linked_guardians],
            "guardians_added": added_guardians,
            "users_updated": sorted(touched_users),
            "student_user": student_user,
        }

    def _require_active_enrollment(self, student_name: str):
        has_active = frappe.db.exists(
            "Program Enrollment",
            {
                "student": student_name,
                "archived": 0,
            },
        )
        if has_active:
            return
        frappe.throw(_("Identity Upgrade requires an active Program Enrollment for Student {0}.").format(student_name))

    def _resolve_upgrade_guardians(self) -> list[dict]:
        rows = self.get("guardians") or []
        resolved = []
        seen = set()
        for row in rows:
            guardian_name = (row.get("guardian") or "").strip()
            if not guardian_name or guardian_name in seen:
                continue
            if not frappe.db.exists("Guardian", guardian_name):
                frappe.throw(_("Guardian {0} does not exist.").format(guardian_name))
            seen.add(guardian_name)
            resolved.append(
                {
                    "guardian": frappe.get_doc("Guardian", guardian_name),
                    "relationship": row.get("relationship") or "Other",
                }
            )
        if resolved:
            return resolved
        fallback = self._create_or_reuse_guardian_from_contact()
        return [fallback]

    def _create_or_reuse_guardian_from_contact(self) -> dict:
        email = normalize_email_value(self.applicant_email) or normalize_email_value(self.portal_account_email)
        if self.applicant_contact and not email:
            email = get_contact_primary_email(self.applicant_contact)
        mobile = None
        contact_first_name = None
        contact_last_name = None
        if self.applicant_contact:
            contact_row = frappe.db.get_value(
                "Contact",
                self.applicant_contact,
                ["first_name", "last_name"],
                as_dict=True,
            )
            if contact_row:
                contact_first_name = contact_row.get("first_name")
                contact_last_name = contact_row.get("last_name")
            mobile = frappe.db.get_value(
                "Contact Phone",
                {"parent": self.applicant_contact, "is_primary_mobile_no": 1},
                "phone",
            )

        if not email:
            frappe.throw(
                _("Identity Upgrade requires a guardian email. Add a Guardian row or Applicant Contact email.")
            )
        if not mobile:
            frappe.throw(
                _("Identity Upgrade requires a guardian mobile phone. Add a Guardian row or Applicant Contact mobile.")
            )

        existing = frappe.db.get_value("Guardian", {"guardian_email": email}, "name")
        if existing:
            guardian = frappe.get_doc("Guardian", existing)
            if not guardian.guardian_mobile_phone:
                guardian.guardian_mobile_phone = mobile
                guardian.save(ignore_permissions=True)
            return {"guardian": guardian, "relationship": "Other"}

        first_name = (contact_first_name or "").strip() or (self.first_name or "").strip() or _("Guardian")
        last_name = (contact_last_name or "").strip() or (self.last_name or "").strip() or _("Contact")
        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": first_name,
                "guardian_last_name": last_name,
                "guardian_email": email,
                "guardian_mobile_phone": mobile,
            }
        ).insert(ignore_permissions=True)
        return {"guardian": guardian, "relationship": "Other"}

    def _ensure_guardian_user_and_roles(self, guardian):
        if not guardian.user:
            guardian.create_guardian_user()
            guardian.reload()
        if not guardian.user:
            frappe.throw(_("Guardian {0} must be linked to a User.").format(guardian.name))
        self._ensure_user_roles(
            guardian.user,
            add_roles={GUARDIAN_ROLE},
            remove_roles={ADMISSIONS_APPLICANT_ROLE},
        )
        return guardian.user

    def _ensure_student_guardian_links(self, student, guardian_specs: list[dict]) -> int:
        existing = {row.get("guardian") for row in (student.get("guardians") or []) if row.get("guardian")}
        added = 0
        for spec in guardian_specs:
            guardian_name = spec["guardian"].name
            if guardian_name in existing:
                continue
            student.append(
                "guardians",
                {
                    "guardian": guardian_name,
                    "relation": spec["relationship"] or "Other",
                },
            )
            existing.add(guardian_name)
            added += 1
        if added:
            student.save(ignore_permissions=True)
        return added

    def _ensure_student_user_access(self, student):
        email = normalize_email_value(student.student_email) or normalize_email_value(self.applicant_user)
        if not email:
            frappe.throw(_("Student email is required before identity upgrade can provision Student access."))

        student_user = None
        if frappe.db.exists("User", email):
            student_user = frappe.get_doc("User", email)
        else:
            student_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "enabled": 1,
                    "first_name": student.student_first_name,
                    "middle_name": student.student_middle_name,
                    "last_name": student.student_last_name,
                    "email": email,
                    "username": email,
                    "gender": student.student_gender,
                    "send_welcome_email": 0,
                    "user_type": "Website User",
                }
            )
            student_user.insert(ignore_permissions=True)

        self._ensure_user_roles(
            student_user.name,
            add_roles={STUDENT_ROLE},
            remove_roles={ADMISSIONS_APPLICANT_ROLE},
        )

        if student.student_email != email:
            frappe.db.set_value("Student", student.name, "student_email", email, update_modified=False)

        return student_user.name

    def _ensure_user_roles(self, user_name: str, *, add_roles: set[str], remove_roles: set[str]):
        if not user_name or not frappe.db.exists("User", user_name):
            return

        user_doc = frappe.get_doc("User", user_name)
        current_roles = []
        existing_roles = []
        seen = set()
        for row in user_doc.get("roles") or []:
            role = (row.role or "").strip()
            if not role:
                continue
            current_roles.append(role)
            if role in remove_roles or role in seen:
                continue
            seen.add(role)
            existing_roles.append(role)

        changed = current_roles != existing_roles
        for role in sorted(add_roles):
            if role in seen:
                continue
            existing_roles.append(role)
            seen.add(role)
            changed = True

        if changed:
            user_doc.set("roles", [{"role": role} for role in existing_roles])

        if (user_doc.user_type or "").strip() != "Website User":
            user_doc.user_type = "Website User"
            changed = True
        if not int(user_doc.enabled or 0):
            user_doc.enabled = 1
            changed = True

        if changed:
            user_doc.save(ignore_permissions=True)

    def _copy_health_profile_to_student_patient(self, student_name: str, *, require_profile: bool = True) -> dict:
        profile_name = frappe.db.get_value(
            "Applicant Health Profile",
            {"student_applicant": self.name},
            "name",
        )
        if not profile_name:
            if require_profile:
                frappe.throw(_("Applicant Health Profile is required before promotion."))
            return {"student_patient": "", "vaccinations": 0}

        profile = frappe.get_doc("Applicant Health Profile", profile_name)
        existing_patient = frappe.db.get_value("Student Patient", {"student": student_name}, "name")
        if existing_patient:
            student_patient = frappe.get_doc("Student Patient", existing_patient)
        else:
            student_patient = frappe.get_doc(
                {
                    "doctype": "Student Patient",
                    "student": student_name,
                }
            )

        for fieldname in HEALTH_PROFILE_COPY_FIELDS:
            student_patient.set(fieldname, profile.get(fieldname))

        student_patient.set("vaccinations", [])
        for index, row in enumerate(profile.get("vaccinations") or []):
            proof_url = self._copy_health_vaccination_proof_to_student(
                profile=profile,
                student_patient=student_patient,
                source_proof_url=row.get("vaccination_proof"),
                vaccination_row=row,
                index=index,
            )
            student_patient.append(
                "vaccinations",
                {
                    "vaccine_name": row.get("vaccine_name"),
                    "date": row.get("date"),
                    "vaccination_proof": proof_url,
                    "additional_notes": row.get("additional_notes"),
                },
            )

        student_patient.save(ignore_permissions=True)
        return {
            "student_patient": student_patient.name,
            "vaccinations": len(student_patient.get("vaccinations") or []),
        }

    def _copy_health_vaccination_proof_to_student(
        self,
        *,
        profile,
        student_patient,
        source_proof_url: str | None,
        vaccination_row,
        index: int,
    ) -> str:
        proof_url = (source_proof_url or "").strip()
        if not proof_url:
            return ""
        if proof_url.startswith("http"):
            return proof_url

        file_row = frappe.db.get_value(
            "File",
            {
                "file_url": proof_url,
                "attached_to_doctype": "Applicant Health Profile",
                "attached_to_name": profile.name,
            },
            ["name", "file_url", "file_name", "is_private"],
            as_dict=True,
        )
        if not file_row:
            return proof_url

        content = self._read_file_bytes(file_row)
        if not content:
            return proof_url

        vaccine = frappe.scrub(vaccination_row.get("vaccine_name") or "")
        date_value = frappe.scrub(str(vaccination_row.get("date") or ""))
        slot_key = "_".join(part for part in [vaccine, date_value] if part) or f"row_{index + 1}"
        slot = f"health_vaccination_proof_{slot_key[:80]}"
        filename = file_row.get("file_name") or os.path.basename(
            file_row.get("file_url") or f"vaccination_{index + 1}.png"
        )

        file_doc = file_dispatcher.create_and_classify_file(
            file_kwargs={
                "attached_to_doctype": "Student Patient",
                "attached_to_name": student_patient.name,
                "attached_to_field": "vaccinations",
                "file_name": filename,
                "content": content,
                "is_private": 1 if file_row.get("is_private") else 0,
            },
            classification={
                "primary_subject_type": "Student",
                "primary_subject_id": student_patient.student,
                "data_class": "safeguarding",
                "purpose": "medical_record",
                "retention_policy": "until_school_exit_plus_6m",
                "slot": slot,
                "organization": self.organization,
                "school": self.school,
                "source_file": file_row.get("name"),
                "upload_source": "API",
            },
            context_override={
                "root_folder": "Home/Students",
                "subfolder": f"{student_patient.student}/Health",
                "file_category": "Student Health",
                "logical_key": slot,
            },
        )
        return file_doc.file_url

    def _has_media_consent(self) -> bool:
        return has_applicant_policy_acknowledgement(
            policy_key=MEDIA_CONSENT_POLICY_KEY,
            student_applicant=self.name,
            organization=self.organization,
            school=self.school,
        )

    def _copy_applicant_image_to_student(self, student):
        if not self.applicant_image:
            return None

        file_row = frappe.db.get_value(
            "File",
            {
                "file_url": self.applicant_image,
                "attached_to_doctype": "Student Applicant",
                "attached_to_name": self.name,
            },
            ["name", "file_url", "file_name", "is_private"],
            as_dict=True,
        )
        if not file_row:
            frappe.log_error(
                frappe.as_json(
                    {
                        "error": "applicant_image_file_missing",
                        "student_applicant": self.name,
                        "file_url": self.applicant_image,
                    },
                    indent=2,
                ),
                "Applicant Image Copy Failed",
            )
            return None

        content = self._read_file_bytes(file_row)
        if not content:
            frappe.log_error(
                frappe.as_json(
                    {
                        "error": "applicant_image_missing_on_disk",
                        "student_applicant": self.name,
                        "file": file_row.get("name"),
                        "file_url": file_row.get("file_url"),
                    },
                    indent=2,
                ),
                "Applicant Image Copy Failed",
            )
            return None

        filename = file_row.get("file_name") or os.path.basename(file_row.get("file_url") or "applicant_image")
        file_doc = file_dispatcher.create_and_classify_file(
            file_kwargs={
                "attached_to_doctype": "Student",
                "attached_to_name": student.name,
                "attached_to_field": "student_image",
                "file_name": filename,
                "content": content,
                "is_private": 1,
            },
            classification={
                "primary_subject_type": "Student",
                "primary_subject_id": student.name,
                "data_class": "identity_image",
                "purpose": "student_profile_display",
                "retention_policy": "until_school_exit_plus_6m",
                "slot": "profile_image",
                "organization": self.organization,
                "school": self.school,
                "source_file": file_row.get("name"),
                "upload_source": "API",
            },
        )

        frappe.db.set_value(
            "Student",
            student.name,
            "student_image",
            file_doc.file_url,
            update_modified=False,
        )
        return file_doc

    def _copy_promotable_documents_to_student(self, student) -> int:
        docs = frappe.get_all(
            "Applicant Document",
            filters={
                "student_applicant": self.name,
                "review_status": "Approved",
            },
            fields=[
                "name",
                "document_type",
                "promotion_target",
            ],
        )
        if not docs:
            return 0

        doc_names = [row.get("name") for row in docs if row.get("name")]
        file_rows = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Applicant Document",
                "attached_to_name": ["in", doc_names],
            },
            fields=["name", "attached_to_name", "file_url", "file_name", "is_private", "creation"],
            order_by="creation desc",
        )
        latest_file_by_doc = {}
        for file_row in file_rows:
            parent = file_row.get("attached_to_name")
            if parent and parent not in latest_file_by_doc:
                latest_file_by_doc[parent] = file_row

        document_type_names = sorted({row.get("document_type") for row in docs if row.get("document_type")})
        document_type_map = {}
        if document_type_names:
            type_rows = frappe.get_all(
                "Applicant Document Type",
                filters={"name": ["in", document_type_names]},
                fields=["name", "code"],
            )
            document_type_map = {row.get("name"): (row.get("code") or row.get("name")) for row in type_rows}

        copied_count = 0
        copy_errors = []
        for doc_row in docs:
            if doc_row.get("promotion_target") and doc_row.get("promotion_target") != "Student":
                continue

            source = latest_file_by_doc.get(doc_row.get("name"))
            if not source:
                copy_errors.append(_("Missing file for Applicant Document {0}.").format(doc_row.get("name")))
                continue

            content = self._read_file_bytes(source)
            if not content:
                copy_errors.append(_("Could not read file for Applicant Document {0}.").format(doc_row.get("name")))
                continue

            doc_type_code = document_type_map.get(doc_row.get("document_type")) or doc_row.get("document_type")
            slot_spec = get_applicant_document_slot_spec(
                document_type=doc_row.get("document_type"),
                doc_type_code=doc_type_code,
            )
            if not slot_spec:
                copy_errors.append(
                    _("Applicant Document Type {0} is missing classification settings.").format(
                        doc_type_code or doc_row.get("document_type") or _("Unknown")
                    )
                )
                continue
            slot_key = f"admissions_{frappe.scrub(doc_type_code or 'document')}"
            filename = source.get("file_name") or os.path.basename(source.get("file_url") or "document")

            try:
                file_dispatcher.create_and_classify_file(
                    file_kwargs={
                        "attached_to_doctype": "Student",
                        "attached_to_name": student.name,
                        "file_name": filename,
                        "content": content,
                        "is_private": 1 if source.get("is_private") else 0,
                    },
                    classification={
                        "primary_subject_type": "Student",
                        "primary_subject_id": student.name,
                        "data_class": slot_spec["data_class"],
                        "purpose": slot_spec["purpose"],
                        "retention_policy": slot_spec["retention_policy"],
                        "slot": slot_key,
                        "organization": self.organization,
                        "school": self.school,
                        "source_file": source.get("name"),
                        "upload_source": "API",
                    },
                )
                copied_count += 1
            except Exception:
                copy_errors.append(_("Could not copy Applicant Document {0}.").format(doc_row.get("name")))
                frappe.log_error(frappe.get_traceback(), "Applicant Document Promotion Copy Failed")

        if copy_errors:
            frappe.throw("\n".join(copy_errors))

        return copied_count

    def _read_file_bytes(self, file_row):
        file_url = (file_row.get("file_url") or "").strip()
        if not file_url or file_url.startswith("http"):
            return None

        rel_path = file_url.lstrip("/")
        if rel_path.startswith("private/") or rel_path.startswith("public/"):
            abs_path = frappe.utils.get_site_path(rel_path)
        else:
            base = "private" if file_row.get("is_private") else "public"
            abs_path = frappe.utils.get_site_path(base, rel_path)

        if not os.path.exists(abs_path):
            return None

        with open(abs_path, "rb") as handle:
            return handle.read()

    # ---------------------------------------------------------------------
    # System Manager override (terminal states only)
    # ---------------------------------------------------------------------

    @frappe.whitelist()
    def apply_system_manager_override(self, updates=None, reason=None):
        user = frappe.session.user
        roles = set(frappe.get_roles(user))

        if SYSTEM_MANAGER_ROLE not in roles:
            frappe.throw(_("Only System Managers can override terminal state locks."))

        if self.application_status not in TERMINAL_STATUSES:
            frappe.throw(_("System Manager override is only allowed for terminal states."))

        if not reason:
            frappe.throw(_("Override reason is required."))

        if updates is None:
            updates = {}
        if not isinstance(updates, dict):
            updates = frappe.parse_json(updates)

        for blocked in ("application_status", "student", "inquiry"):
            if blocked in updates:
                frappe.throw(_("Field {0} cannot be changed via override.").format(blocked))

        self.flags.system_manager_override = True
        self.update(updates)
        self.save(ignore_permissions=True)

        self.add_comment(
            "Comment",
            text=_("System Manager override by {0} on {1}. Reason: {2}.").format(
                frappe.bold(user), now_datetime(), reason
            ),
        )
        return {"ok": True}

    def _validate_ready_for_approval(self):
        snapshot = self.get_readiness_snapshot()
        if snapshot.get("ready"):
            return
        issues = snapshot.get("issues") or []
        if not issues:
            issues = ["Applicant readiness requirements are not met."]
        frappe.throw("\n".join(issues))

    def has_required_policies(self):
        if not self.organization:
            return {"ok": False, "missing": [], "required": []}

        ancestor_orgs = get_organization_ancestors_including_self(self.organization)
        if not ancestor_orgs:
            return {"ok": True, "missing": [], "required": []}
        school_ancestors = get_school_ancestors_including_self(self.school)

        schema_check = ensure_policy_applies_to_column(caller="StudentApplicant.has_required_policies")
        if not schema_check.get("ok"):
            self.flags.policy_schema_error = schema_check.get("message")
            return {
                "ok": False,
                "missing": [],
                "required": [],
            }

        org_placeholders = ", ".join(["%s"] * len(ancestor_orgs))
        school_scope_sql = ""
        school_params: tuple[str, ...] = ()
        if school_ancestors:
            school_placeholders = ", ".join(["%s"] * len(school_ancestors))
            school_scope_sql = f" OR ip.school IN ({school_placeholders})"
            school_params = tuple(school_ancestors)
        rows = frappe.db.sql(
            f"""
            SELECT ip.name AS policy_name,
                   ip.policy_key AS policy_key,
                   ip.organization AS policy_organization,
                   ip.school AS policy_school,
                   pv.name AS policy_version
              FROM `tabInstitutional Policy` ip
              JOIN `tabPolicy Version` pv
                ON pv.institutional_policy = ip.name
             WHERE ip.is_active = 1
               AND pv.is_active = 1
               AND ip.organization IN ({org_placeholders})
               AND (ip.school IS NULL OR ip.school = ''{school_scope_sql})
               AND ip.applies_to LIKE %s
            """,
            (*ancestor_orgs, *school_params, "%Applicant%"),
            as_dict=True,
        )
        rows = select_nearest_policy_rows_by_key(
            rows=rows,
            context_organization=self.organization,
            context_school=self.school,
            policy_key_field="policy_key",
            policy_organization_field="policy_organization",
            policy_school_field="policy_school",
        )

        if not rows:
            return {"ok": True, "missing": [], "required": []}

        versions = [row["policy_version"] for row in rows]
        acknowledged = set(
            frappe.get_all(
                "Policy Acknowledgement",
                filters={
                    "policy_version": ["in", versions],
                    "acknowledged_for": "Applicant",
                    "context_doctype": "Student Applicant",
                    "context_name": self.name,
                },
                pluck="policy_version",
            )
        )

        required = [row["policy_key"] or row["policy_name"] for row in rows]
        missing = [row["policy_key"] or row["policy_name"] for row in rows if row["policy_version"] not in acknowledged]
        return {"ok": not missing, "missing": missing, "required": required}

    def has_required_documents(self):
        if not self.organization:
            return {"ok": False, "missing": [], "unapproved": [], "required": []}

        type_rows = frappe.get_all(
            "Applicant Document Type",
            filters={"is_required": 1, "is_active": 1},
            fields=[
                "name",
                "code",
                "document_type_name",
                "organization",
                "school",
                "classification_slot",
                "classification_data_class",
                "classification_purpose",
                "classification_retention_policy",
            ],
        )
        applicant_org_ancestors, applicant_school_ancestors = get_applicant_scope_ancestors(
            organization=self.organization,
            school=self.school,
        )
        applicant_org_ancestors = set(applicant_org_ancestors)
        applicant_school_ancestors = set(applicant_school_ancestors)
        required_types: list[dict] = []
        misconfigured_required_types: list[str] = []
        for row in type_rows:
            if not is_applicant_document_type_in_scope(
                document_type_organization=row.get("organization"),
                document_type_school=row.get("school"),
                applicant_org_ancestors=applicant_org_ancestors,
                applicant_school_ancestors=applicant_school_ancestors,
            ):
                continue
            if not has_complete_applicant_document_type_classification(row):
                misconfigured_required_types.append(row.get("code") or row.get("document_type_name") or row.get("name"))
                continue
            required_types.append(row)

        if misconfigured_required_types:
            frappe.logger("admissions_readiness", allow_site=True).warning(
                "Skipping misconfigured Applicant Document Types in readiness for %s: %s",
                self.name,
                ", ".join(sorted({item for item in misconfigured_required_types if item})),
            )

        if not required_types:
            return {"ok": True, "missing": [], "unapproved": [], "required": []}

        required_names = {
            row["name"]: (row["code"] or row["document_type_name"] or row["name"]) for row in required_types
        }

        rows = frappe.get_all(
            "Applicant Document",
            filters={"student_applicant": self.name, "document_type": ["in", list(required_names.keys())]},
            fields=["document_type", "review_status"],
        )
        status_map = {row["document_type"]: row["review_status"] for row in rows}

        missing = []
        unapproved = []
        for doc_type, label in required_names.items():
            if doc_type not in status_map:
                missing.append(label)
            elif status_map[doc_type] != "Approved":
                unapproved.append(label)

        return {
            "ok": not missing and not unapproved,
            "missing": missing,
            "unapproved": unapproved,
            "required": list(required_names.values()),
        }

    def has_required_profile_information(self):
        required_labels: list[str] = []
        missing_labels: list[str] = []
        for fieldname, label in STUDENT_PROFILE_REQUIRED_FIELD_LABELS:
            required_labels.append(label)
            value = self.get(fieldname)
            if value is None:
                missing_labels.append(label)
                continue
            if isinstance(value, str):
                if not value.strip():
                    missing_labels.append(label)
                continue
            if not str(value).strip():
                missing_labels.append(label)

        return {
            "ok": not missing_labels,
            "missing": missing_labels,
            "required": required_labels,
            "fields": {fieldname: self.get(fieldname) for fieldname in STUDENT_PROFILE_FIELDS},
        }

    def health_review_complete(self):
        status = frappe.db.get_value(
            "Applicant Health Profile",
            {"student_applicant": self.name},
            "review_status",
        )
        if not status:
            return {"ok": False, "status": "missing"}
        if status == "Cleared":
            return {"ok": True, "status": "complete"}
        if status == "Needs Follow-Up":
            return {"ok": False, "status": "needs_follow_up"}
        return {"ok": False, "status": "missing"}

    def has_required_interviews(self):
        rows = frappe.get_all(
            "Applicant Interview",
            filters={"student_applicant": self.name},
            fields=["name", "interview_date", "interview_type"],
            order_by="interview_date desc, modified desc",
            limit_page_length=5,
        )
        count = frappe.db.count("Applicant Interview", {"student_applicant": self.name})
        return {"ok": count >= 1, "count": count, "items": rows}

    @frappe.whitelist()
    def get_readiness_snapshot(self):
        policies = self.has_required_policies()
        documents = self.has_required_documents()
        health = self.health_review_complete()
        interviews = self.has_required_interviews()
        profile = self.has_required_profile_information()

        ready = all([policies.get("ok"), documents.get("ok"), health.get("ok"), profile.get("ok")])
        issues = []
        if not policies.get("ok"):
            policy_schema_error = getattr(self.flags, "policy_schema_error", None)
            if policy_schema_error:
                issues.append(policy_schema_error)
            else:
                missing = policies.get("missing") or []
                if missing:
                    issues.append(_("Missing policy acknowledgements: {0}.").format(", ".join(missing)))
                else:
                    issues.append(_("Missing required policy acknowledgements."))
        if not health.get("ok"):
            status = health.get("status") or "missing"
            if status == "needs_follow_up":
                issues.append(_("Health review requires follow-up."))
            else:
                issues.append(_("Health profile is missing or not cleared."))
        if not documents.get("ok"):
            missing = documents.get("missing") or []
            unapproved = documents.get("unapproved") or []
            if missing:
                issues.append(_("Missing required documents: {0}.").format(", ".join(missing)))
            if unapproved:
                issues.append(_("Required documents not approved: {0}.").format(", ".join(unapproved)))
        if not profile.get("ok"):
            missing = profile.get("missing") or []
            if missing:
                issues.append(_("Missing profile information: {0}.").format(", ".join(missing)))
            else:
                issues.append(_("Missing required profile information."))

        return {
            "policies": policies,
            "documents": documents,
            "health": health,
            "interviews": interviews,
            "profile": profile,
            "ready": bool(ready),
            "issues": issues,
        }


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_intent_query(doctype, txt, searchfield, start, page_len, filters):
    filters = filters or {}
    school = filters.get("school")
    if not school:
        return []

    scope = get_school_scope_for_academic_year(school)
    if not scope:
        return []

    search_txt = f"%{txt or ''}%"
    placeholders = ", ".join(["%s"] * len(scope))
    return frappe.db.sql(
        f"""
        SELECT name
          FROM `tabAcademic Year`
         WHERE archived = 0
           AND visible_to_admission = 1
           AND school IN ({placeholders})
           AND name LIKE %s
         ORDER BY year_start_date DESC, name DESC
         LIMIT %s, %s
        """,
        [*scope, search_txt, start, page_len],
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def school_by_organization_query(doctype, txt, searchfield, start, page_len, filters):
    filters = filters or {}
    organization = filters.get("organization")
    if not organization:
        return []

    search_txt = f"%{txt or ''}%"
    return frappe.db.sql(
        """
        SELECT name
          FROM `tabSchool`
         WHERE organization = %s
           AND name LIKE %s
         ORDER BY name ASC
         LIMIT %s, %s
        """,
        (organization, search_txt, start, page_len),
    )
