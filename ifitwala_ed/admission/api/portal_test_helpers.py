# ifitwala_ed/admission/api/portal_test_helpers.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt


from unittest.mock import patch

import frappe

from ifitwala_ed.governance.policy_utils import (
    ensure_policy_applies_to_column,
    ensure_policy_audience_records,
    institutional_policy_db_has_column,
)


def _admission_settings_has_field(fieldname: str) -> bool:
    if not frappe.db.exists("DocType", "Admission Settings"):
        return False
    return bool(frappe.get_meta("Admission Settings").has_field(fieldname))


def _policy_schema_available() -> bool:
    return bool(ensure_policy_applies_to_column(caller="test_admissions_portal").get("ok"))


def _insert_user_without_notifications(user):
    # User field values can shadow same-named methods on the document instance.
    with (
        patch.object(user, "send_password_notification"),
        patch.object(user, "send_welcome_mail_to_user"),
        patch("frappe.core.doctype.user.user.User.send_password_notification"),
        patch("frappe.core.doctype.user.user.User.send_welcome_mail_to_user"),
    ):
        return user.insert(ignore_permissions=True)


class AdmissionsPortalScenarioMixin:
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Admissions Applicant")
        self._ensure_role("Admissions Family")
        self._guardians_setting_before = frappe.db.get_single_value(
            "Admission Settings",
            "show_guardians_in_admissions_profile",
        )
        self._admissions_access_mode_before = (
            frappe.db.get_single_value("Admission Settings", "admissions_access_mode")
            if _admission_settings_has_field("admissions_access_mode")
            else None
        )
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant_user = self._create_applicant_user()
        self.applicant = self._create_applicant(self.organization, self.school, self.applicant_user)
        self.policy_version = None
        if _policy_schema_available():
            self.policy_version = self._create_required_applicant_policy_version(
                organization=self.organization,
                school=self.school,
            )

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value(
            "Admission Settings",
            "show_guardians_in_admissions_profile",
            self._guardians_setting_before or 0,
        )
        if _admission_settings_has_field("admissions_access_mode"):
            frappe.db.set_single_value(
                "Admission Settings",
                "admissions_access_mode",
                self._admissions_access_mode_before or "Single Applicant Workspace",
            )
        for doctype, name in reversed(self._created):
            if not frappe.db.exists(doctype, name):
                continue
            if doctype == "Policy Acknowledgement":
                frappe.db.delete("Policy Acknowledgement", {"name": name})
                continue
            frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

    def _create_organization(self) -> str:
        organization_name = f"Org {frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": organization_name,
                "abbr": f"ORG{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(self, organization: str) -> str:
        school_name = f"School {frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": school_name,
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name

    def _create_required_applicant_policy_version(
        self,
        *,
        organization: str,
        school: str,
        admissions_acknowledgement_mode: str | None = None,
        acknowledgement_clauses: list[dict] | None = None,
        policy_text: str | None = None,
    ) -> str:
        ensure_policy_audience_records()
        policy_payload = {
            "doctype": "Institutional Policy",
            "policy_key": f"applicant_policy_{frappe.generate_hash(length=8)}",
            "policy_title": f"Applicant Portal Policy {frappe.generate_hash(length=6)}",
            "policy_category": "Admissions",
            "applies_to": [{"policy_audience": "Applicant"}],
            "organization": organization,
            "school": school,
            "is_active": 1,
        }
        if admissions_acknowledgement_mode is not None and institutional_policy_db_has_column(
            "admissions_acknowledgement_mode"
        ):
            policy_payload["admissions_acknowledgement_mode"] = admissions_acknowledgement_mode

        policy = frappe.get_doc(policy_payload).insert(ignore_permissions=True)
        self._created.append(("Institutional Policy", policy.name))

        version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": policy.name,
                "version_label": "v1",
                "policy_text": policy_text or "<p>Applicant consent text.</p>",
                "acknowledgement_clauses": acknowledgement_clauses or [],
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Policy Version", version.name))
        return version.name

    def _create_applicant_user(self) -> str:
        email = f"portal-applicant-{frappe.generate_hash(length=8)}@example.com"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Portal",
                "last_name": "Applicant",
                "enabled": 1,
                "roles": [{"role": "Admissions Applicant"}],
            }
        )
        user.flags.no_welcome_mail = True
        _insert_user_without_notifications(user)
        self._created.append(("User", user.name))
        frappe.clear_cache(user=user.name)
        return user.name

    def _create_applicant(self, organization: str, school: str, applicant_user: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Portal",
                "last_name": f"Submit-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        doc.db_set("applicant_user", applicant_user, update_modified=False)
        doc.db_set("application_status", "Invited", update_modified=False)
        doc.reload()
        self._created.append(("Student Applicant", doc.name))
        return doc

    def _create_applicant_contact(self, *, first_name: str, last_name: str, email: str, phone: str):
        contact_payload = {
            "doctype": "Contact",
            "first_name": first_name,
            "last_name": last_name,
        }
        if email:
            contact_payload["email_ids"] = [{"email_id": email, "is_primary": 1}]
        if phone:
            contact_payload["phone_nos"] = [{"phone": phone, "is_primary_mobile_no": 1}]
            contact_payload["mobile_no"] = phone
        contact = frappe.get_doc(contact_payload).insert(ignore_permissions=True)
        self._created.append(("Contact", contact.name))
        return contact

    def _set_guardians_section_setting(self, value: int):
        frappe.db.set_single_value(
            "Admission Settings",
            "show_guardians_in_admissions_profile",
            1 if int(value or 0) else 0,
        )

    def _set_admissions_access_mode(self, value: str):
        frappe.db.set_single_value("Admission Settings", "admissions_access_mode", value)

    def _create_family_user(self):
        email = f"family-{frappe.generate_hash(length=8)}@example.com"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Family",
                "last_name": "Portal",
                "enabled": 1,
                "roles": [{"role": "Admissions Family"}],
            }
        )
        user.flags.no_welcome_mail = True
        _insert_user_without_notifications(user)
        self._created.append(("User", user.name))
        frappe.clear_cache(user=user.name)
        return user

    def _create_guardian_record(self, *, user: str | None = None, is_primary_guardian: bool = False):
        email = user or f"guardian-{frappe.generate_hash(length=8)}@example.com"
        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": "Family",
                "guardian_last_name": "Guardian",
                "guardian_email": email,
                "guardian_mobile_phone": "+14155550121",
                "is_primary_guardian": 1 if is_primary_guardian else 0,
                "user": user,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Guardian", guardian.name))
        return guardian

    def _link_family_guardian(self, applicant, *, guardian_name: str, user: str, is_primary_guardian: bool = True):
        applicant.append(
            "guardians",
            {
                "guardian": guardian_name,
                "user": user,
                "relationship": "Mother",
                "can_consent": 1 if is_primary_guardian else 0,
                "is_primary": 1,
                "is_primary_guardian": 1 if is_primary_guardian else 0,
                "guardian_first_name": "Family",
                "guardian_last_name": "Guardian",
                "guardian_email": user,
                "guardian_mobile_phone": "+14155550121",
                "guardian_image": "/private/files/family-guardian.png",
            },
        )
        applicant.save(ignore_permissions=True)

    def _create_basket_group(self, basket_group_name: str):
        doc = frappe.get_doc(
            {
                "doctype": "Basket Group",
                "basket_group_name": basket_group_name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Basket Group", doc.name))
        return doc

    def _create_offer_plan(
        self,
        *,
        status: str,
        offer_message: str | None = None,
        required_course_basket_groups: list[str] | None = None,
        optional_course_basket_groups: list[str] | None = None,
        enrollment_rules: list[dict] | None = None,
    ):
        academic_year = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
                "school": self.school,
                "year_start_date": "2025-08-01",
                "year_end_date": "2026-06-30",
                "archived": 0,
                "visible_to_admission": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Academic Year", academic_year.name))

        grade_scale = frappe.get_doc(
            {
                "doctype": "Grade Scale",
                "grade_scale_name": f"Scale {frappe.generate_hash(length=6)}",
                "boundaries": [
                    {"grade_code": "B-", "boundary_interval": 70},
                    {"grade_code": "C", "boundary_interval": 60},
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Grade Scale", grade_scale.name))

        required_course = frappe.get_doc(
            {
                "doctype": "Course",
                "course_name": f"Offer Course {frappe.generate_hash(length=6)}",
                "status": "Active",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Course", required_course.name))

        optional_course = None
        if optional_course_basket_groups is not None:
            optional_course = frappe.get_doc(
                {
                    "doctype": "Course",
                    "course_name": f"Optional Offer Course {frappe.generate_hash(length=6)}",
                    "status": "Active",
                }
            ).insert(ignore_permissions=True)
            self._created.append(("Course", optional_course.name))

        for basket_group in sorted(
            {
                *set(required_course_basket_groups or []),
                *set(optional_course_basket_groups or []),
                *{
                    (row.get("basket_group") or "").strip()
                    for row in (enrollment_rules or [])
                    if (row.get("basket_group") or "").strip()
                },
            }
        ):
            self._create_basket_group(basket_group)

        program = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Program {frappe.generate_hash(length=6)}",
                "grade_scale": grade_scale.name,
                "courses": [
                    {"course": required_course.name, "level": "None"},
                    *([{"course": optional_course.name, "level": "None"}] if optional_course else []),
                ],
                "course_basket_groups": [
                    *[
                        {"course": required_course.name, "basket_group": basket_group}
                        for basket_group in (required_course_basket_groups or [])
                    ],
                    *[
                        {"course": optional_course.name, "basket_group": basket_group}
                        for basket_group in (optional_course_basket_groups or [])
                    ],
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program", program.name))

        offering = frappe.get_doc(
            {
                "doctype": "Program Offering",
                "program": program.name,
                "school": self.school,
                "offering_title": f"Offering {frappe.generate_hash(length=6)}",
                "offering_academic_years": [{"academic_year": academic_year.name}],
                "offering_courses": [
                    {
                        "course": required_course.name,
                        "course_name": required_course.course_name,
                        "required": 1,
                        "start_academic_year": academic_year.name,
                        "end_academic_year": academic_year.name,
                    },
                    *(
                        [
                            {
                                "course": optional_course.name,
                                "course_name": optional_course.course_name,
                                "required": 0,
                                "start_academic_year": academic_year.name,
                                "end_academic_year": academic_year.name,
                            }
                        ]
                        if optional_course
                        else []
                    ),
                ],
                "offering_course_basket_groups": [
                    *[
                        {"course": required_course.name, "basket_group": basket_group}
                        for basket_group in (required_course_basket_groups or [])
                    ],
                    *[
                        {"course": optional_course.name, "basket_group": basket_group}
                        for basket_group in (optional_course_basket_groups or [])
                    ],
                ],
                "enrollment_rules": enrollment_rules or [],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Program Offering", offering.name))

        self.applicant.db_set("application_status", "Approved", update_modified=False)
        self.applicant.db_set("academic_year", academic_year.name, update_modified=False)
        self.applicant.db_set("program", program.name, update_modified=False)
        self.applicant.db_set("program_offering", offering.name, update_modified=False)
        self.applicant.reload()

        plan = frappe.get_doc(
            {
                "doctype": "Applicant Enrollment Plan",
                "student_applicant": self.applicant.name,
                "academic_year": academic_year.name,
                "program": program.name,
                "program_offering": offering.name,
                "status": status,
                "offer_message": offer_message or "",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Enrollment Plan", plan.name))
        return {
            "plan": plan,
            "academic_year": academic_year,
            "program": program,
            "offering": offering,
            "required_course": required_course,
            "optional_course": optional_course,
        }

    def _get_or_create_language_xtra(self) -> str:
        existing = frappe.get_all("Language Xtra", filters={"enabled": 1}, fields=["name"], limit=1)
        if existing:
            return existing[0]["name"]

        code = f"lng_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Language Xtra",
                "language_name": f"Language {code}",
                "language_code": code,
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Language Xtra", doc.name))
        return doc.name

    def _get_any_country(self) -> str | None:
        existing = frappe.get_all("Country", fields=["name"], limit=1, order_by="name asc")
        if not existing:
            return None
        return existing[0]["name"]

    def _tiny_png_base64(self) -> str:
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+tmxoAAAAASUVORK5CYII="
