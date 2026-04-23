# ifitwala_ed/admission/doctype/student_applicant/student_applicant.py
# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

# ifiwala_ed/admission/doctype/student_applicant/student_applicant.py

import os

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime

from ifitwala_ed.admission.access import (
    ADMISSIONS_APPLICANT_ROLE,
    ADMISSIONS_FAMILY_ROLE,
    build_admissions_portal_access_exists_sql,
    user_can_access_student_applicant,
)
from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    READ_LIKE_PERMISSION_TYPES,
    build_admissions_file_scope_exists_sql,
    build_open_applicant_review_access_exists_sql,
    ensure_admissions_permission,
    ensure_contact_dynamic_link,
    ensure_contact_for_email,
    get_applicant_document_slot_spec,
    get_contact_primary_email,
    has_open_applicant_review_access,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
    normalize_email_value,
    sync_student_applicant_contact_binding,
)
from ifitwala_ed.admission.applicant_document_readiness import build_document_review_payload_for_applicant
from ifitwala_ed.admission.applicant_review_workflow import apply_review_decision
from ifitwala_ed.governance.policy_utils import (
    get_applicant_policy_status,
)
from ifitwala_ed.integrations.drive.authority import (
    get_current_drive_file_for_slot,
    get_current_drive_files_for_attachments,
    get_drive_file_for_file,
)
from ifitwala_ed.utilities.image_utils import ensure_guardian_profile_image
from ifitwala_ed.utilities.school_tree import get_school_scope_for_academic_year

FAMILY_ROLES = {ADMISSIONS_FAMILY_ROLE}
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
    ("student_first_language", "First Language"),
    ("student_nationality", "Nationality"),
    ("residency_status", "Residency Status"),
)


class StudentApplicant(Document):
    def after_insert(self):
        self._sync_contact_binding()

    def before_save(self):
        self._set_title_if_missing()

    def on_update(self):
        self._sync_contact_binding()
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
        is_family_role = bool(roles & FAMILY_ROLES)
        is_applicant = ADMISSIONS_APPLICANT_ROLE in roles
        is_system_manager = SYSTEM_MANAGER_ROLE in roles

        if self.is_new():
            if not is_admissions:
                frappe.throw(_("Only Admissions staff can create Student Applicants."))
            return

        if not before:
            return

        if is_admissions_file_staff_user(user):
            if not has_scoped_staff_access_to_student_applicant(user=user, student_applicant=self.name):
                frappe.throw(_("You do not have permission to edit this Applicant."), frappe.PermissionError)

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

        # Staff precedence: if a user has admissions roles, evaluate against staff rules
        # even when they also carry family/applicant roles (common in test/dev admins).
        if is_admissions:
            if not rules["staff"] and self._has_changes(before):
                if getattr(self.flags, "allow_status_change", False) and self._only_status_changed(before):
                    return
                frappe.throw(_("Edits are not allowed when status is {0}.").format(status_for_edit))
            return

        has_family_access = is_family_role and user_can_access_student_applicant(user=user, student_applicant=self.name)

        if not is_admissions and not has_family_access and not is_applicant:
            if self._has_changes(before):
                frappe.throw(_("You do not have permission to edit this Applicant."))
            return

        if is_applicant:
            if self.applicant_user != user and self._has_changes(before):
                frappe.throw(_("You do not have permission to edit this Applicant."))
            if not rules["family"] and self._has_changes(before):
                frappe.throw(_("Family edits are not allowed when status is {0}.").format(status_for_edit))
            return

        if is_family_role:
            if not has_family_access and self._has_changes(before):
                frappe.throw(_("You do not have permission to edit this Applicant."))
            if not rules["family"] and self._has_changes(before):
                frappe.throw(_("Family edits are not allowed when status is {0}.").format(status_for_edit))
            return

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
                    "Only applicant_image can be attached directly to Student Applicant. Use the governed admissions evidence upload so files attach to the submitted-file record."
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
            if not has_scoped_staff_access_to_student_applicant(user=user, student_applicant=self.name):
                frappe.throw(_("You do not have permission to perform this action."), frappe.PermissionError)
            return user
        frappe.throw(_("You do not have permission to perform this action."), frappe.PermissionError)

    def _set_status(
        self, new_status, action_label, permission_checker=ensure_admissions_permission, comment_suffix=None
    ):
        if permission_checker:
            permission_checker()

        if is_admissions_file_staff_user(frappe.session.user):
            if not has_scoped_staff_access_to_student_applicant(
                user=frappe.session.user,
                student_applicant=self.name,
            ):
                frappe.throw(_("You do not have permission to perform this action."), frappe.PermissionError)

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

        if new_status == "Submitted":
            from ifitwala_ed.admission.applicant_review_workflow import materialize_application_review_assignments

            materialize_application_review_assignments(
                student_applicant=self.name,
                source_event="application_submitted",
            )

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
        if not user_can_access_student_applicant(user=user, student_applicant=self.name):
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

    def _sync_contact_binding(self):
        if not self.applicant_contact:
            return
        sync_student_applicant_contact_binding(
            student_applicant=self.name,
            contact_name=self.applicant_contact,
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
        if not self.student_joining_date:
            frappe.throw(_("Joining Date is required before promotion to Student."))
        self._validate_enrollment_plan_for_promotion()

        if self.student:
            self._carry_guardians_to_promoted_student(self.student)
            hydrated_request = self._maybe_auto_hydrate_enrollment_request_after_promotion(self.student)
            self._copy_health_profile_to_student_patient(self.student, require_profile=False)
            self._set_status("Promoted", "Applicant promoted")
            if hydrated_request:
                self.add_comment(
                    "Comment",
                    text=_("Draft Program Enrollment Request {0} auto-hydrated after promotion.").format(
                        frappe.bold(hydrated_request)
                    ),
                )
            return self.student

        existing = frappe.db.get_value("Student", {"student_applicant": self.name}, "name")
        if existing:
            self._carry_guardians_to_promoted_student(existing)
            self._copy_health_profile_to_student_patient(existing, require_profile=False)
            self.flags.from_promotion = True
            self.student = existing
            self.save(ignore_permissions=True)
            hydrated_request = self._maybe_auto_hydrate_enrollment_request_after_promotion(existing)
            self._set_status("Promoted", "Applicant promoted")
            if hydrated_request:
                self.add_comment(
                    "Comment",
                    text=_("Draft Program Enrollment Request {0} auto-hydrated after promotion.").format(
                        frappe.bold(hydrated_request)
                    ),
                )
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
                    "student_joining_date": self.student_joining_date,
                    "student_first_language": self.student_first_language,
                    "student_second_language": self.student_second_language,
                    "student_nationality": self.student_nationality,
                    "student_second_nationality": self.student_second_nationality,
                    "residency_status": self.residency_status,
                    "cohort": self.cohort,
                    "student_house": self.student_house,
                    "anchor_school": self.school,
                    "student_applicant": self.name,
                }
            )
            student.insert(ignore_permissions=True)
        finally:
            frappe.flags.from_applicant_promotion = prev_flag

        self._carry_guardians_to_promoted_student(student.name)
        health_snapshot = self._copy_health_profile_to_student_patient(student.name)
        copied_docs = self._copy_promotable_documents_to_student(student)

        self._copy_applicant_image_to_student(student)

        self.flags.from_promotion = True
        self.student = student.name
        self.save(ignore_permissions=True)
        hydrated_request = self._maybe_auto_hydrate_enrollment_request_after_promotion(student.name)
        self._set_status("Promoted", "Applicant promoted")
        self.add_comment(
            "Comment",
            text=_(
                "Promoted transfer completed: {0} Applicant Document file(s) copied; "
                "{1} vaccination row(s) synced to Student Patient {2}."
            ).format(copied_docs, health_snapshot["vaccinations"], health_snapshot["student_patient"]),
        )
        if hydrated_request:
            self.add_comment(
                "Comment",
                text=_("Draft Program Enrollment Request {0} auto-hydrated after promotion.").format(
                    frappe.bold(hydrated_request)
                ),
            )

        return student.name

    @frappe.whitelist()
    def upgrade_identity(self):
        return self._run_identity_upgrade()

    def _run_identity_upgrade(self, *, trigger_detail: str | None = None):
        ensure_admissions_permission()
        return self._run_identity_upgrade_without_permission(trigger_detail=trigger_detail)

    def _run_identity_upgrade_without_permission(self, *, trigger_detail: str | None = None):
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
            contact_name = (spec.get("contact") or "").strip() or None
            user_name = self._ensure_guardian_user_and_roles(guardian)
            if user_name:
                touched_users.add(user_name)
            self._ensure_guardian_contact_links(
                guardian=guardian,
                student=student,
                contact_name=contact_name,
            )
            linked_guardians.append(
                {
                    "guardian": guardian,
                    "relationship": relationship,
                    "contact": contact_name,
                    "can_consent": cint(spec.get("can_consent") or 0),
                }
            )

        added_guardians = self._ensure_student_guardian_links(student, linked_guardians)
        added_siblings = self._sync_student_siblings_from_shared_guardians(student)

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
        trigger_suffix = ""
        if (trigger_detail or "").strip():
            trigger_suffix = _(" Trigger: {0}.").format(trigger_detail.strip())
        self.add_comment(
            "Comment",
            text=_(
                "Identity Upgrade completed by {0} on {1}. "
                "State: Promoted -> Identity Upgraded. "
                "Student: {2}. Guardians linked: {3} (new links: {4}). "
                "Sibling links added: {5}. Users updated: {6}.{7}"
            ).format(
                frappe.bold(frappe.session.user),
                now_datetime(),
                frappe.bold(student_name),
                guardian_list,
                added_guardians,
                added_siblings,
                user_list,
                trigger_suffix,
            ),
        )
        return {
            "ok": True,
            "student": student_name,
            "guardians_linked": [row["guardian"].name for row in linked_guardians],
            "guardians_added": added_guardians,
            "siblings_added": added_siblings,
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

    def _validate_enrollment_plan_for_promotion(self):
        from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
            get_latest_applicant_enrollment_plan,
        )

        plan = get_latest_applicant_enrollment_plan(self.name)
        if not plan:
            return
        if (plan.status or "").strip() in {"Offer Accepted", "Hydrated"}:
            return
        frappe.throw(_("Applicant Enrollment Plan must be Offer Accepted before promotion."))

    def _maybe_auto_hydrate_enrollment_request_after_promotion(self, student_name: str) -> str | None:
        try:
            auto_hydrate = frappe.db.get_single_value(
                "Admission Settings", "auto_hydrate_enrollment_request_after_promotion"
            )
        except Exception:
            auto_hydrate = 0
        if not int(auto_hydrate or 0):
            return None

        from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
            get_latest_applicant_enrollment_plan,
            hydrate_program_enrollment_request_from_applicant_plan,
        )

        plan = get_latest_applicant_enrollment_plan(self.name)
        if not plan:
            return None
        if (plan.status or "").strip() == "Hydrated" and (plan.program_enrollment_request or "").strip():
            return (plan.program_enrollment_request or "").strip()
        if (plan.status or "").strip() != "Offer Accepted":
            return None
        if not student_name:
            return None

        result = hydrate_program_enrollment_request_from_applicant_plan(plan.name)
        return (result or {}).get("name")

    def _resolve_upgrade_guardians(self) -> list[dict]:
        rows = self.get("guardians") or []
        resolved = []
        seen = set()
        for row in rows:
            guardian_name = (row.get("guardian") or "").strip()
            relationship = (row.get("relationship") or "").strip() or "Other"
            contact_name = (row.get("contact") or "").strip() or None
            row_primary_guardian = cint(row.get("is_primary_guardian") or 0)

            if guardian_name:
                if not frappe.db.exists("Guardian", guardian_name):
                    frappe.throw(_("Guardian {0} does not exist.").format(guardian_name))
                guardian_doc = frappe.get_doc("Guardian", guardian_name)
                key = guardian_doc.name
                if key in seen:
                    continue
                seen.add(key)
                resolved.append(
                    {
                        "guardian": guardian_doc,
                        "relationship": relationship,
                        "contact": contact_name,
                        "can_consent": 1
                        if (row_primary_guardian or cint(guardian_doc.get("is_primary_guardian") or 0))
                        else 0,
                    }
                )
                continue

            if self._is_empty_applicant_guardian_row(row):
                continue

            row_spec = self._create_or_reuse_guardian_from_profile_row(row)
            key = row_spec["guardian"].name
            if key in seen:
                continue
            seen.add(key)
            row_spec["relationship"] = relationship
            row_spec["can_consent"] = 1 if cint(row.get("is_primary_guardian") or 0) else 0
            if contact_name and not row_spec.get("contact"):
                row_spec["contact"] = contact_name
            resolved.append(row_spec)

        return resolved

    def _is_empty_applicant_guardian_row(self, row) -> bool:
        fields = (
            "guardian_first_name",
            "guardian_last_name",
            "guardian_email",
            "guardian_mobile_phone",
            "salutation",
            "guardian_work_email",
            "guardian_work_phone",
            "employment_sector",
            "work_place",
            "guardian_designation",
            "guardian_image",
        )
        return not any((row.get(field) or "").strip() for field in fields)

    def _create_or_reuse_guardian_from_profile_row(self, row) -> dict:
        first_name = (row.get("guardian_first_name") or "").strip()
        last_name = (row.get("guardian_last_name") or "").strip()
        email = normalize_email_value(row.get("guardian_email"))
        mobile = (row.get("guardian_mobile_phone") or "").strip()
        source_guardian_image = (row.get("guardian_image") or "").strip()
        source_file_name = self._resolve_applicant_guardian_image_source_file_name(
            guardian_row_name=(row.get("name") or "").strip(),
            guardian_image=source_guardian_image,
        )

        if not first_name:
            frappe.throw(_("Guardian first name is required in applicant guardians."))
        if not last_name:
            frappe.throw(_("Guardian last name is required in applicant guardians."))
        if not email:
            frappe.throw(_("Guardian personal email is required in applicant guardians."))
        if not mobile:
            frappe.throw(_("Guardian mobile phone is required in applicant guardians."))

        existing = frappe.db.get_value("Guardian", {"guardian_email": email}, "name")
        if existing:
            guardian = frappe.get_doc("Guardian", existing)
            changed = False
            if (guardian.guardian_first_name or "").strip() != first_name:
                guardian.guardian_first_name = first_name
                changed = True
            if (guardian.guardian_last_name or "").strip() != last_name:
                guardian.guardian_last_name = last_name
                changed = True
            if not (guardian.guardian_mobile_phone or "").strip():
                guardian.guardian_mobile_phone = mobile
                changed = True

            profile_field_map = (
                ("salutation", "salutation"),
                ("guardian_gender", "guardian_gender"),
                ("guardian_work_email", "guardian_work_email"),
                ("guardian_work_phone", "guardian_work_phone"),
                ("employment_sector", "employment_sector"),
                ("work_place", "work_place"),
                ("guardian_designation", "guardian_designation"),
                ("guardian_image", "guardian_image"),
            )
            for row_field, guardian_field in profile_field_map:
                incoming = (row.get(row_field) or "").strip()
                if incoming and not (guardian.get(guardian_field) or "").strip():
                    guardian.set(guardian_field, incoming)
                    changed = True

            incoming_primary = cint(row.get("is_primary_guardian") or 0)
            if incoming_primary and cint(guardian.get("is_primary_guardian") or 0) != 1:
                guardian.is_primary_guardian = 1
                changed = True

            incoming_financial = cint(row.get("is_financial_guardian") or 0)
            if incoming_financial and cint(guardian.get("is_financial_guardian") or 0) != 1:
                guardian.is_financial_guardian = 1
                changed = True

            if changed:
                guardian.save(ignore_permissions=True)

            self._sync_guardian_profile_image_from_applicant_row(
                guardian=guardian,
                source_guardian_image=source_guardian_image,
                source_file_name=source_file_name,
            )

            contact_name = (row.get("contact") or "").strip() or None
            if not contact_name:
                contact_name = (
                    frappe.db.get_value(
                        "Contact Email",
                        {"email_id": email},
                        "parent",
                    )
                    or None
                )
            return {"guardian": guardian, "relationship": row.get("relationship") or "Other", "contact": contact_name}

        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "salutation": (row.get("salutation") or "").strip() or None,
                "guardian_first_name": first_name,
                "guardian_last_name": last_name,
                "guardian_gender": (row.get("guardian_gender") or "").strip() or None,
                "guardian_email": email,
                "guardian_mobile_phone": mobile,
                "guardian_work_email": (row.get("guardian_work_email") or "").strip() or None,
                "guardian_work_phone": (row.get("guardian_work_phone") or "").strip() or None,
                "employment_sector": (row.get("employment_sector") or "").strip() or None,
                "work_place": (row.get("work_place") or "").strip() or None,
                "guardian_designation": (row.get("guardian_designation") or "").strip() or None,
                "guardian_image": (row.get("guardian_image") or "").strip() or None,
                "is_primary_guardian": cint(row.get("is_primary_guardian") or 0),
                "is_financial_guardian": cint(row.get("is_financial_guardian") or 0),
            }
        ).insert(ignore_permissions=True)

        self._sync_guardian_profile_image_from_applicant_row(
            guardian=guardian,
            source_guardian_image=source_guardian_image,
            source_file_name=source_file_name,
        )

        return {
            "guardian": guardian,
            "relationship": row.get("relationship") or "Other",
            "contact": (row.get("contact") or "").strip() or None,
        }

    def _resolve_applicant_guardian_image_source_file_name(
        self,
        *,
        guardian_row_name: str | None,
        guardian_image: str | None,
    ) -> str | None:
        resolved_row_name = (guardian_row_name or "").strip()
        resolved_image = (guardian_image or "").strip()
        if not resolved_row_name or not resolved_image:
            return None

        file_name = frappe.db.get_value(
            "File",
            {
                "attached_to_doctype": "Student Applicant Guardian",
                "attached_to_name": resolved_row_name,
                "file_url": resolved_image,
            },
            "name",
        )
        resolved_file_name = (file_name or "").strip()
        return resolved_file_name or None

    def _sync_guardian_profile_image_from_applicant_row(
        self,
        *,
        guardian,
        source_guardian_image: str | None,
        source_file_name: str | None,
    ) -> None:
        if not (source_guardian_image or "").strip():
            return

        try:
            synced_url = ensure_guardian_profile_image(
                guardian.name,
                original_url=source_guardian_image,
                source_file_name=source_file_name,
                organization=self.organization,
                upload_source="API",
            )
            if synced_url:
                guardian.guardian_image = synced_url
                if self.organization:
                    guardian.organization = self.organization
        except Exception:
            frappe.log_error(
                frappe.as_json(
                    {
                        "error": "guardian_profile_image_sync_failed",
                        "student_applicant": self.name,
                        "guardian": getattr(guardian, "name", None),
                        "source_guardian_image": source_guardian_image,
                        "source_file_name": source_file_name,
                    },
                    indent=2,
                ),
                "Guardian Profile Image Sync Failed",
            )

    def _ensure_guardian_contact_links(self, *, guardian, student, contact_name: str | None = None):
        resolved_contact = (contact_name or "").strip()
        if not resolved_contact:
            resolved_contact = (
                frappe.db.get_value(
                    "Contact Email",
                    {"email_id": normalize_email_value(guardian.guardian_email)},
                    "parent",
                )
                or ""
            ).strip()
        if not resolved_contact:
            resolved_contact = ensure_contact_for_email(
                first_name=guardian.guardian_first_name,
                last_name=guardian.guardian_last_name,
                email=guardian.guardian_email,
                phone=guardian.guardian_mobile_phone,
            )
        if not resolved_contact:
            return

        ensure_contact_dynamic_link(
            contact_name=resolved_contact,
            link_doctype="Student Applicant",
            link_name=self.name,
        )
        ensure_contact_dynamic_link(
            contact_name=resolved_contact,
            link_doctype="Guardian",
            link_name=guardian.name,
        )
        ensure_contact_dynamic_link(
            contact_name=resolved_contact,
            link_doctype="Student",
            link_name=student.name,
        )

    def _ensure_guardian_user_and_roles(self, guardian):
        if not guardian.user:
            guardian.create_guardian_user()
            guardian.reload()
        if not guardian.user:
            frappe.throw(_("Guardian {0} must be linked to a User.").format(guardian.name))
        if (guardian.user or "").strip() == (self.applicant_user or "").strip():
            frappe.throw(_("Guardian user cannot match Applicant User. Applicant User is reserved for the student."))
        self._ensure_user_roles(
            guardian.user,
            add_roles={GUARDIAN_ROLE},
            remove_roles={ADMISSIONS_APPLICANT_ROLE},
        )
        return guardian.user

    def _ensure_student_guardian_links(self, student, guardian_specs: list[dict]) -> int:
        existing_rows = {
            (row.get("guardian") or "").strip(): row
            for row in (student.get("guardians") or [])
            if (row.get("guardian") or "").strip()
        }
        added = 0
        changed = 0
        for spec in guardian_specs:
            guardian_name = spec["guardian"].name
            can_consent = cint(spec.get("can_consent") or 0)
            existing_row = existing_rows.get(guardian_name)
            if existing_row:
                if cint(existing_row.get("can_consent") or 0) != can_consent:
                    existing_row.can_consent = can_consent
                    changed += 1
                continue
            student.append(
                "guardians",
                {
                    "guardian": guardian_name,
                    "relation": spec["relationship"] or "Other",
                    "can_consent": can_consent,
                },
            )
            existing_rows[guardian_name] = student.get("guardians")[-1]
            added += 1
        if added or changed:
            student.save(ignore_permissions=True)
        return added

    def _carry_guardians_to_promoted_student(self, student_name: str) -> dict:
        resolved_student = (student_name or "").strip()
        if not resolved_student:
            return {"guardians_added": 0, "siblings_added": 0}

        student = frappe.get_doc("Student", resolved_student)
        guardian_specs = self._resolve_upgrade_guardians()
        linked_guardians = []
        for spec in guardian_specs:
            guardian = spec["guardian"]
            relationship = spec["relationship"]
            contact_name = (spec.get("contact") or "").strip() or None
            self._ensure_guardian_contact_links(
                guardian=guardian,
                student=student,
                contact_name=contact_name,
            )
            linked_guardians.append(
                {
                    "guardian": guardian,
                    "relationship": relationship,
                    "contact": contact_name,
                    "can_consent": cint(spec.get("can_consent") or 0),
                }
            )

        added_guardians = self._ensure_student_guardian_links(student, linked_guardians)
        added_siblings = self._sync_student_siblings_from_shared_guardians(student)
        return {"guardians_added": added_guardians, "siblings_added": added_siblings}

    def _sync_student_siblings_from_shared_guardians(self, student) -> int:
        guardian_names = sorted(
            {
                (row.get("guardian") or "").strip()
                for row in (student.get("guardians") or [])
                if (row.get("guardian") or "").strip()
            }
        )
        if not guardian_names:
            return 0

        sibling_rows = frappe.get_all(
            "Student Guardian",
            filters={
                "guardian": ["in", guardian_names],
                "parenttype": "Student",
                "parentfield": "guardians",
            },
            fields=["parent"],
            limit=max(20, len(guardian_names) * 8),
        )
        sibling_names = sorted(
            {
                (row.get("parent") or "").strip()
                for row in sibling_rows
                if (row.get("parent") or "").strip() and (row.get("parent") or "").strip() != student.name
            }
        )
        if not sibling_names:
            return 0

        existing = {
            (row.get("student") or "").strip()
            for row in (student.get("siblings") or [])
            if (row.get("student") or "").strip()
        }
        added = 0
        for sibling_name in sibling_names:
            if sibling_name in existing:
                continue
            student.append("siblings", {"student": sibling_name})
            existing.add(sibling_name)
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

        # File attachments require a persisted parent name; ensure new patients are inserted first.
        if not student_patient.name:
            student_patient.insert(ignore_permissions=True)

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

        vaccine = frappe.scrub(vaccination_row.get("vaccine_name") or "")
        date_value = frappe.scrub(str(vaccination_row.get("date") or ""))
        slot_key = "_".join(part for part in [vaccine, date_value] if part) or f"row_{index + 1}"
        slot = f"health_vaccination_proof_{slot_key[:80]}"
        drive_file = get_current_drive_file_for_slot(
            primary_subject_type="Student Applicant",
            primary_subject_id=self.name,
            slot=slot,
            organization=self.organization,
            school=self.school,
            attached_doctype="Applicant Health Profile",
            attached_name=profile.name,
            fields=["file"],
            statuses=("active", "processing", "blocked"),
        )
        file_name = str((drive_file or {}).get("file") or "").strip()
        file_row = (
            frappe.db.get_value("File", file_name, ["name", "file_url", "file_name", "is_private"], as_dict=True)
            if file_name
            else None
        )
        if not file_row:
            return ""

        content = self._read_file_bytes(file_row)
        if not content:
            return ""

        filename = file_row.get("file_name") or os.path.basename(
            file_row.get("file_url") or f"vaccination_{index + 1}.png"
        )

        from ifitwala_ed.integrations.drive.content_uploads import upload_content_via_drive

        _session_response, _finalize_response, file_doc = upload_content_via_drive(
            workflow_id="student_patient.vaccination_proof",
            workflow_payload={
                "student_patient": student_patient.name,
                "vaccine_name": vaccination_row.get("vaccine_name"),
                "date": vaccination_row.get("date"),
                "row_index": index,
            },
            file_name=filename,
            content=content,
        )
        return file_doc.file_url

    def _copy_applicant_image_to_student(self, student):
        if not self.applicant_image:
            return None

        drive_file = get_current_drive_file_for_slot(
            primary_subject_type="Student Applicant",
            primary_subject_id=self.name,
            slot="profile_image",
            organization=self.organization,
            school=self.school,
            attached_doctype="Student Applicant",
            attached_name=self.name,
            fields=["file"],
            statuses=("active", "processing", "blocked"),
        )
        file_name = str((drive_file or {}).get("file") or "").strip()
        file_row = (
            frappe.db.get_value("File", file_name, ["name", "file_url", "file_name", "is_private"], as_dict=True)
            if file_name
            else None
        )
        if not file_row:
            file_rows = frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": "Student Applicant",
                    "attached_to_name": self.name,
                    "attached_to_field": "applicant_image",
                },
                fields=["name", "file_url", "file_name", "is_private"],
                order_by="modified desc, creation desc",
                limit=1,
            )
            file_row = file_rows[0] if file_rows else None
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
                        "error": "applicant_image_source_unreadable",
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
        from ifitwala_drive.api import media as drive_media_api

        from ifitwala_ed.integrations.drive.content_uploads import upload_content_via_drive

        _session_response, _finalize_response, file_doc = upload_content_via_drive(
            create_session_callable=drive_media_api.upload_student_image,
            session_payload={
                "student": student.name,
                "upload_source": "API",
            },
            file_name=filename,
            content=content,
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
        item_rows = []
        if doc_names:
            item_rows = frappe.get_all(
                "Applicant Document Item",
                filters={
                    "applicant_document": ["in", doc_names],
                    "review_status": "Approved",
                },
                fields=["name", "applicant_document", "item_key", "item_label", "review_status"],
                order_by="modified desc",
            )
        items_by_doc = {}
        for row_item in item_rows:
            items_by_doc.setdefault(row_item.get("applicant_document"), []).append(row_item)

        item_names = [row_item.get("name") for row_item in item_rows if row_item.get("name")]
        current_file_by_item = {}
        if item_names:
            drive_rows = get_current_drive_files_for_attachments(
                attached_doctype="Applicant Document Item",
                attached_names=item_names,
                fields=["attached_name", "file"],
                statuses=("active", "processing", "blocked"),
            )
            file_names = []
            file_name_by_item = {}
            for drive_row in drive_rows:
                parent = drive_row.get("attached_name")
                file_name = drive_row.get("file")
                if not (parent and file_name) or parent in file_name_by_item:
                    continue
                file_name_by_item[parent] = file_name
                file_names.append(file_name)

            if file_names:
                file_rows = frappe.get_all(
                    "File",
                    filters={"name": ["in", file_names]},
                    fields=["name", "file_url", "file_name", "is_private"],
                )
                file_row_by_name = {row.get("name"): row for row in file_rows if row.get("name")}
                for parent, file_name in file_name_by_item.items():
                    file_row = file_row_by_name.get(file_name)
                    if file_row:
                        current_file_by_item[parent] = file_row

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

            item_group = items_by_doc.get(doc_row.get("name"), [])
            if not item_group:
                copy_errors.append(
                    _("Approved Applicant Document {0} has no approved submissions to copy.").format(
                        doc_row.get("name") or _("Unknown")
                    )
                )
                continue

            for item in item_group:
                source = current_file_by_item.get(item.get("name"))
                if not source:
                    copy_errors.append(
                        _("Missing file for Applicant Document Item {0}.").format(item.get("name") or _("Unknown"))
                    )
                    continue
                content = self._read_file_bytes(source)
                if not content:
                    copy_errors.append(
                        _("Could not read file for Applicant Document Item {0}.").format(
                            item.get("name") or _("Unknown")
                        )
                    )
                    continue
                filename = source.get("file_name") or os.path.basename(source.get("file_url") or "document")

                try:
                    from ifitwala_ed.integrations.drive.content_uploads import upload_content_via_drive

                    upload_content_via_drive(
                        workflow_id="student.promoted_admissions_document",
                        workflow_payload={
                            "student": student.name,
                            "student_applicant": self.name,
                            "source_applicant_document_item": item.get("name"),
                        },
                        file_name=filename,
                        content=content,
                    )
                    copied_count += 1
                except Exception:
                    copy_errors.append(
                        _("Could not copy Applicant Document Item {0}.").format(item.get("name") or _("Unknown"))
                    )
                    frappe.log_error(frappe.get_traceback(), "Applicant Document Item Promotion Copy Failed")
            continue

        if copy_errors:
            frappe.throw("\n".join(copy_errors))

        return copied_count

    def _read_file_bytes(self, file_row):
        file_name = str(file_row.get("name") or "").strip()
        if not file_name:
            return None

        drive_file = get_drive_file_for_file(
            file_name,
            fields=["storage_backend", "storage_object_key"],
            statuses=("active", "processing", "blocked", "superseded"),
        )
        if not drive_file or not str(drive_file.get("storage_object_key") or "").strip():
            return None

        try:
            from ifitwala_drive.services.storage.base import get_storage_backend
        except ImportError:
            return None

        storage = get_storage_backend(drive_file.get("storage_backend"))
        try:
            return storage.read_final_object(object_key=drive_file.get("storage_object_key"))
        except Exception:
            return None

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

    def _is_health_required_for_approval(self) -> bool:
        school_name = (self.school or "").strip()
        if not school_name:
            return True

        required_value = frappe.get_cached_value("School", school_name, "require_health_profile_for_approval")
        if required_value is None:
            return True
        return bool(cint(required_value))

    def has_required_policies(self):
        payload = get_applicant_policy_status(
            student_applicant=self.name,
            organization=self.organization,
            school=self.school,
        )
        schema_error = payload.get("schema_error")
        if schema_error:
            self.flags.policy_schema_error = schema_error
        return payload

    def has_required_documents(self):
        return build_document_review_payload_for_applicant(
            student_applicant=self.name,
            organization=self.organization,
            school=self.school,
        )

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
        profile_row = frappe.db.get_value(
            "Applicant Health Profile",
            {"student_applicant": self.name},
            [
                "name",
                "review_status",
                "reviewed_by",
                "reviewed_on",
                "applicant_health_declared_complete",
                "applicant_health_declared_by",
                "applicant_health_declared_on",
            ],
            as_dict=True,
        )
        if not profile_row:
            return {
                "ok": False,
                "status": "missing",
                "profile_name": None,
                "review_status": None,
                "reviewed_by": None,
                "reviewed_on": None,
                "declared_complete": False,
                "declared_by": None,
                "declared_on": None,
            }
        status = profile_row.get("review_status")
        if status == "Cleared":
            health_status = "complete"
            is_ok = True
        elif status == "Needs Follow-Up":
            health_status = "needs_follow_up"
            is_ok = False
        else:
            health_status = "pending"
            is_ok = False
        return {
            "ok": is_ok,
            "status": health_status,
            "profile_name": profile_row.get("name"),
            "review_status": status,
            "reviewed_by": profile_row.get("reviewed_by"),
            "reviewed_on": profile_row.get("reviewed_on"),
            "declared_complete": bool(profile_row.get("applicant_health_declared_complete")),
            "declared_by": profile_row.get("applicant_health_declared_by"),
            "declared_on": profile_row.get("applicant_health_declared_on"),
        }

    def has_required_interviews(self):
        rows = frappe.get_all(
            "Applicant Interview",
            filters={"student_applicant": self.name},
            fields=[
                "name",
                "interview_date",
                "interview_start",
                "interview_end",
                "interview_type",
            ],
            order_by="modified desc",
            limit=20,
        )
        rows.sort(
            key=lambda row: (
                get_datetime(row.get("interview_start"))
                if row.get("interview_start")
                else get_datetime(f"{row.get('interview_date')} 00:00:00")
                if row.get("interview_date")
                else get_datetime("1900-01-01 00:00:00")
            ),
            reverse=True,
        )
        count = frappe.db.count("Applicant Interview", {"student_applicant": self.name})
        recent_rows = rows[:5]
        interview_names = [row.get("name") for row in recent_rows if row.get("name")]

        interviewer_rows = []
        if interview_names:
            interviewer_rows = frappe.get_all(
                "Applicant Interviewer",
                filters={
                    "parent": ["in", interview_names],
                    "parenttype": "Applicant Interview",
                    "parentfield": "interviewers",
                },
                fields=["parent", "interviewer", "idx"],
                order_by="parent asc, idx asc",
            )

        feedback_rows = []
        if interview_names and frappe.db.table_exists("Applicant Interview Feedback"):
            feedback_rows = frappe.get_all(
                "Applicant Interview Feedback",
                filters={
                    "applicant_interview": ["in", interview_names],
                    "feedback_status": "Submitted",
                },
                fields=["applicant_interview", "interviewer_user"],
                limit=max(20, len(interview_names) * 4),
            )

        interviewer_ids = sorted(
            {
                (row.get("interviewer") or "").strip()
                for row in interviewer_rows
                if (row.get("interviewer") or "").strip()
            }
        )
        interviewer_name_by_user: dict[str, str] = {}
        if interviewer_ids:
            user_rows = frappe.get_all(
                "User",
                filters={"name": ["in", interviewer_ids]},
                fields=["name", "full_name"],
            )
            for user_row in user_rows:
                user_id = (user_row.get("name") or "").strip()
                if not user_id:
                    continue
                full_name = (user_row.get("full_name") or "").strip()
                interviewer_name_by_user[user_id] = full_name or user_id

        interviewers_by_interview: dict[str, list[dict]] = {}
        for interviewer_row in interviewer_rows:
            interview_name = (interviewer_row.get("parent") or "").strip()
            user_id = (interviewer_row.get("interviewer") or "").strip()
            if not interview_name or not user_id:
                continue
            label = interviewer_name_by_user.get(user_id) or user_id
            interviewers_by_interview.setdefault(interview_name, []).append(
                {
                    "user": user_id,
                    "label": label,
                }
            )

        submitted_users_by_interview: dict[str, set[str]] = {}
        for feedback_row in feedback_rows:
            interview_name = (feedback_row.get("applicant_interview") or "").strip()
            interviewer_user = (feedback_row.get("interviewer_user") or "").strip()
            if not interview_name or not interviewer_user:
                continue
            submitted_users_by_interview.setdefault(interview_name, set()).add(interviewer_user)

        items = []
        for row in recent_rows:
            interview_name = (row.get("name") or "").strip()
            interviewers = list(interviewers_by_interview.get(interview_name, []))
            assigned_users = {entry.get("user") for entry in interviewers if entry.get("user")}
            submitted_users = submitted_users_by_interview.get(interview_name, set())
            submitted_count = len(assigned_users & submitted_users)
            expected_count = len(assigned_users)
            item = dict(row)
            item["interviewers"] = interviewers
            item["interviewer_labels"] = [entry.get("label") for entry in interviewers if entry.get("label")]
            item["feedback_submitted_count"] = submitted_count
            item["feedback_expected_count"] = expected_count
            item["feedback_complete"] = bool(expected_count and submitted_count >= expected_count)
            item["feedback_status_label"] = (
                _("{0}/{1} submitted").format(submitted_count, expected_count)
                if expected_count
                else _("No interviewers assigned")
            )
            items.append(item)

        return {"ok": count >= 1, "count": count, "items": items}

    def has_required_recommendations(self):
        default_payload = {
            "ok": False,
            "required_total": 0,
            "received_total": 0,
            "requested_total": 0,
            "missing": [_("Recommendation readiness could not be evaluated.")],
            "rows": [],
            "state": "pending",
            "counts": {
                "Expired": 0,
                "Opened": 0,
                "Revoked": 0,
                "Sent": 0,
                "Submitted": 0,
            },
        }
        try:
            from ifitwala_ed.api.recommendation_intake import get_recommendation_status_for_applicant

            return get_recommendation_status_for_applicant(
                student_applicant=self.name,
                include_confidential=True,
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Student Applicant Recommendation Readiness Failed")
            return default_payload

    def get_review_assignments_summary(self):
        from ifitwala_ed.admission.applicant_review_workflow import get_review_assignments_summary

        return get_review_assignments_summary(student_applicant=self.name)

    @frappe.whitelist()
    def get_readiness_snapshot(self):
        policies = self.has_required_policies()
        documents = self.has_required_documents()
        health = self.health_review_complete()
        health_required_for_approval = self._is_health_required_for_approval()
        health_payload = dict(health or {})
        health_payload["required_for_approval"] = health_required_for_approval
        interviews = self.has_required_interviews()
        profile = self.has_required_profile_information()
        recommendations = self.has_required_recommendations()
        review_assignments = self.get_review_assignments_summary()

        health_ok_for_approval = bool(health_payload.get("ok")) if health_required_for_approval else True
        ready = all(
            [
                policies.get("ok"),
                documents.get("ok"),
                health_ok_for_approval,
                profile.get("ok"),
                recommendations.get("ok"),
            ]
        )
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
        if health_required_for_approval and not health_payload.get("ok"):
            status = health_payload.get("status") or "missing"
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
        if not recommendations.get("ok"):
            missing_recommendations = recommendations.get("missing") or []
            required_total = cint(recommendations.get("required_total") or 0)
            received_total = cint(recommendations.get("received_total") or 0)
            if missing_recommendations:
                issues.append(_("Missing required recommendations: {0}.").format(", ".join(missing_recommendations)))
            elif required_total > 0:
                issues.append(
                    _("Required recommendations received: {0} of {1}.").format(received_total, required_total)
                )

        return {
            "policies": policies,
            "documents": documents,
            "health": health_payload,
            "interviews": interviews,
            "profile": profile,
            "recommendations": recommendations,
            "review_assignments": review_assignments,
            "ready": bool(ready),
            "issues": issues,
        }

    def _assert_document_review_workspace_access(self):
        roles = set(frappe.get_roles(frappe.session.user))
        if not roles & DECISION_ROLES:
            frappe.throw(
                _(
                    "Only Admission Officer, Admission Manager, Academic Admin, or System Manager can review evidence here."
                ),
                frappe.PermissionError,
            )

        if self.application_status in TERMINAL_STATUSES:
            frappe.throw(_("Applicant is read-only in terminal states."))

        if not has_scoped_staff_access_to_student_applicant(user=frappe.session.user, student_applicant=self.name):
            frappe.throw(_("You do not have permission to review evidence for this applicant."), frappe.PermissionError)

    def _resolve_document_submission_review_context(self, applicant_document_item: str | None) -> tuple[dict, dict]:
        item_name = (applicant_document_item or "").strip()
        if not item_name:
            frappe.throw(_("Submitted file is required."))

        item_row = frappe.db.get_value(
            "Applicant Document Item",
            item_name,
            ["name", "applicant_document", "item_key", "item_label"],
            as_dict=True,
        )
        if not item_row:
            frappe.throw(_("Applicant Document Item {0} was not found.").format(item_name), frappe.DoesNotExistError)

        document_row = frappe.db.get_value(
            "Applicant Document",
            item_row.get("applicant_document"),
            ["name", "student_applicant", "document_type", "document_label"],
            as_dict=True,
        )
        if not document_row or (document_row.get("student_applicant") or "").strip() != self.name:
            frappe.throw(_("Submitted file does not belong to this Student Applicant."), frappe.PermissionError)

        return item_row, document_row

    def review_document_submission(
        self,
        applicant_document_item: str | None = None,
        decision: str | None = None,
        notes: str | None = None,
    ):
        self._assert_document_review_workspace_access()
        item_row, document_row = self._resolve_document_submission_review_context(applicant_document_item)

        resolved_decision = (decision or "").strip()
        if resolved_decision not in {"Approved", "Needs Follow-Up", "Rejected"}:
            frappe.throw(_("Invalid evidence decision: {0}.").format(resolved_decision or _("(empty)")))

        clean_notes = (notes or "").strip() or None
        if resolved_decision in {"Needs Follow-Up", "Rejected"} and not clean_notes:
            frappe.throw(_("Notes are required when requesting changes or rejecting a submitted file."))

        apply_review_decision(
            target_type="Applicant Document Item",
            target_name=item_row.get("name"),
            decision=resolved_decision,
            notes=clean_notes,
            decided_by=frappe.session.user,
        )

        document_label = (
            (document_row.get("document_label") or "").strip()
            or (
                frappe.db.get_value("Applicant Document Type", document_row.get("document_type"), "document_type_name")
                or ""
            ).strip()
            or (document_row.get("document_type") or "").strip()
            or _("Document")
        )
        item_label = (
            (item_row.get("item_label") or "").strip()
            or (item_row.get("item_key") or "").strip()
            or (item_row.get("name") or "").strip()
        )
        self.add_comment(
            "Comment",
            text=_("Evidence review updated: {0} / {1} -> {2} by {3} on {4}.").format(
                frappe.bold(document_label),
                frappe.bold(item_label or _("Submission")),
                frappe.bold(resolved_decision),
                frappe.bold(frappe.session.user),
                now_datetime(),
            ),
        )

        return {
            "ok": True,
            "applicant_document": document_row.get("name"),
            "applicant_document_item": item_row.get("name"),
            "decision": resolved_decision,
            "documents": self.has_required_documents(),
        }

    @frappe.whitelist()
    def set_document_requirement_override(
        self,
        applicant_document: str | None = None,
        document_type: str | None = None,
        requirement_override: str | None = None,
        override_reason: str | None = None,
    ):
        roles = set(frappe.get_roles(frappe.session.user))
        if not roles & {"Admission Manager", "Academic Admin", "System Manager"}:
            frappe.throw(
                _(
                    "Only Admission Manager, Academic Admin, or System Manager can set a requirement waiver or exception."
                ),
                frappe.PermissionError,
            )

        if self.application_status in TERMINAL_STATUSES:
            frappe.throw(_("Applicant is read-only in terminal states."))

        target_document_name = (applicant_document or "").strip()
        target_document_type = (document_type or "").strip()
        override_value = (requirement_override or "").strip()
        override_reason = (override_reason or "").strip()

        if target_document_name:
            document_doc = frappe.get_doc("Applicant Document", target_document_name)
            if document_doc.student_applicant != self.name:
                frappe.throw(_("Applicant Document does not belong to this Student Applicant."))
        else:
            if not target_document_type:
                frappe.throw(_("Document Type is required when Applicant Document is not provided."))
            existing = frappe.db.get_value(
                "Applicant Document",
                {"student_applicant": self.name, "document_type": target_document_type},
                "name",
            )
            if existing:
                document_doc = frappe.get_doc("Applicant Document", existing)
            else:
                if not override_value:
                    return {
                        "ok": True,
                        "applicant_document": None,
                        "documents": self.has_required_documents(),
                    }
                document_doc = frappe.get_doc(
                    {
                        "doctype": "Applicant Document",
                        "student_applicant": self.name,
                        "document_type": target_document_type,
                    }
                )
                document_doc.insert(ignore_permissions=True)

        document_doc.requirement_override = override_value or None
        document_doc.override_reason = override_reason or None
        document_doc.override_by = None
        document_doc.override_on = None
        document_doc.save(ignore_permissions=True)

        return {
            "ok": True,
            "applicant_document": document_doc.name,
            "documents": self.has_required_documents(),
        }


def auto_upgrade_identity_for_student(*, student_name: str, program_enrollment: str | None = None):
    resolved_student = (student_name or "").strip()
    if not resolved_student:
        return None

    applicant_name = frappe.db.get_value("Student", resolved_student, "student_applicant") or frappe.db.get_value(
        "Student Applicant", {"student": resolved_student}, "name"
    )
    if not applicant_name:
        return None

    applicant_row = (
        frappe.db.get_value(
            "Student Applicant",
            applicant_name,
            ["name", "application_status", "student"],
            as_dict=True,
        )
        or {}
    )
    if (applicant_row.get("application_status") or "").strip() != "Promoted":
        return None
    if (applicant_row.get("student") or "").strip() != resolved_student:
        return None

    applicant = frappe.get_doc("Student Applicant", applicant_name)
    trigger_detail = _("Automatic trigger from active Program Enrollment {0}").format(
        frappe.bold(program_enrollment or _("unknown"))
    )
    return applicant._run_identity_upgrade_without_permission(trigger_detail=trigger_detail)


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


def get_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        return "1=0"

    conditions: list[str] = []
    if is_admissions_file_staff_user(resolved_user):
        staff_condition = build_admissions_file_scope_exists_sql(
            user=resolved_user,
            student_applicant_expr_sql="`tabStudent Applicant`.`name`",
        )
        if staff_condition is None:
            return None
        if staff_condition != "1=0":
            conditions.append(f"({staff_condition})")

    portal_condition = build_admissions_portal_access_exists_sql(
        user=resolved_user,
        student_applicant_expr_sql="`tabStudent Applicant`.`name`",
    )
    if portal_condition != "1=0":
        conditions.append(f"({portal_condition})")

    reviewer_condition = build_open_applicant_review_access_exists_sql(
        user=resolved_user,
        student_applicant_expr_sql="`tabStudent Applicant`.`name`",
    )
    if reviewer_condition != "1=0":
        conditions.append(f"({reviewer_condition})")

    return " OR ".join(conditions) if conditions else "1=0"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = (user or frappe.session.user or "").strip()
    op = (ptype or "read").lower()

    if not resolved_user or resolved_user == "Guest":
        return False

    if is_admissions_file_staff_user(resolved_user):
        staff_ops = READ_LIKE_PERMISSION_TYPES | {"write", "create", "delete", "submit", "cancel", "amend"}
        if op not in staff_ops:
            return False
        if op == "create":
            roles = set(frappe.get_roles(resolved_user))
            return resolved_user == "Administrator" or "System Manager" in roles or bool(roles & ADMISSIONS_ROLES)
        if not doc:
            return True
        applicant_name = _resolve_student_applicant_name(doc)
        return has_scoped_staff_access_to_student_applicant(user=resolved_user, student_applicant=applicant_name)

    if op in READ_LIKE_PERMISSION_TYPES and doc:
        applicant_name = _resolve_student_applicant_name(doc)
        if has_open_applicant_review_access(user=resolved_user, student_applicant=applicant_name):
            return True

    roles = set(frappe.get_roles(resolved_user))
    if not roles & {ADMISSIONS_APPLICANT_ROLE, ADMISSIONS_FAMILY_ROLE}:
        return False

    applicant_ops = READ_LIKE_PERMISSION_TYPES | {"write"}
    if op not in applicant_ops:
        return False

    if not doc:
        return op in READ_LIKE_PERMISSION_TYPES

    return user_can_access_student_applicant(user=resolved_user, student_applicant=_resolve_student_applicant_name(doc))


def _resolve_student_applicant_name(doc) -> str:
    if isinstance(doc, str):
        return (doc or "").strip()
    if isinstance(doc, dict):
        return (doc.get("name") or "").strip()
    return (getattr(doc, "name", None) or "").strip()


def _is_applicant_self_user(user: str, doc) -> bool:
    return user_can_access_student_applicant(user=user, student_applicant=_resolve_student_applicant_name(doc))
