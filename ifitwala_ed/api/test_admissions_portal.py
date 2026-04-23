# ifitwala_ed/api/test_admissions_portal.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

import base64
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import admissions_portal as admissions_portal_api
from ifitwala_ed.api.admissions_portal import (
    _derive_next_actions,
    _portal_status_for,
    _read_only_for,
    _send_applicant_invite_email,
    accept_enrollment_offer,
    acknowledge_policy,
    decline_enrollment_offer,
    get_applicant_enrollment_choices,
    get_applicant_policies,
    get_applicant_profile,
    get_applicant_snapshot,
    get_family_invite_options,
    get_invite_email_options,
    invite_applicant,
    invite_family_collaborator,
    submit_application,
    update_applicant_enrollment_choices,
    update_applicant_health,
    update_applicant_profile,
    upload_applicant_guardian_image,
    upload_applicant_profile_image,
)
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


class TestAdmissionsPortalAuthGuards(FrappeTestCase):
    def test_require_admissions_applicant_rejects_none_literal_as_unauthenticated(self):
        with patch("ifitwala_ed.api.admissions_portal._session_user", return_value=""):
            with self.assertRaises(frappe.PermissionError):
                admissions_portal_api._require_admissions_applicant()

    def test_portal_session_endpoint_is_whitelisted(self):
        self.assertIn(admissions_portal_api.get_admissions_session, frappe.whitelisted)

    def test_get_applicant_for_user_uses_canonical_applicant_user_only(self):
        def fake_get_all(doctype, **kwargs):
            self.assertEqual(doctype, "Student Applicant")
            filters = kwargs.get("filters") or {}
            if filters == {"name": ["in", ["APP-CANONICAL"]]}:
                return [{"name": "APP-CANONICAL"}]
            return []

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.get_admissions_portal_applicant_names_for_user",
                return_value=["APP-CANONICAL"],
            ) as mocked_names,
            patch("ifitwala_ed.api.admissions_portal.frappe.get_all", side_effect=fake_get_all),
        ):
            row = admissions_portal_api._get_applicant_for_user(
                "applicant@example.com",
                fields=["name"],
            )

        mocked_names.assert_called_once_with(user="applicant@example.com", include_promoted=False)
        self.assertEqual(row.get("name"), "APP-CANONICAL")

    def test_get_applicant_for_user_rejects_email_only_matches(self):
        with (
            patch(
                "ifitwala_ed.api.admissions_portal.get_admissions_portal_applicant_names_for_user",
                return_value=[],
            ) as mocked_names,
            patch(
                "ifitwala_ed.api.admissions_portal.frappe.get_all",
                side_effect=AssertionError(
                    "no applicant row lookup should run when canonical access resolution is empty"
                ),
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                admissions_portal_api._get_applicant_for_user(
                    "applicant@example.com",
                    fields=["name"],
                )

        mocked_names.assert_called_once_with(user="applicant@example.com", include_promoted=False)


class TestAdmissionsPortalContracts(FrappeTestCase):
    def test_withdrawn_status_maps_to_portal_withdrawn(self):
        self.assertEqual(_portal_status_for("Withdrawn"), "Withdrawn")

    def test_withdrawn_status_is_read_only_with_reason(self):
        is_read_only, reason = _read_only_for("Withdrawn")
        self.assertTrue(is_read_only)
        self.assertTrue(bool(reason))

    def test_next_actions_documents_missing_is_blocking_upload(self):
        actions = _derive_next_actions(
            "In Progress",
            {
                "profile": {"ok": True},
                "policies": {"ok": True},
                "health": {"ok": True},
                "documents": {"ok": False, "missing": ["ID & Passport"], "unapproved": []},
            },
        )
        upload_actions = [row for row in actions if row.get("route_name") == "admissions-documents"]
        self.assertEqual(len(upload_actions), 1)
        self.assertEqual(upload_actions[0].get("label"), "Upload required documents")
        self.assertTrue(bool(upload_actions[0].get("is_blocking")))

    def test_next_actions_documents_under_review_is_not_blocking_upload(self):
        actions = _derive_next_actions(
            "In Progress",
            {
                "profile": {"ok": True},
                "policies": {"ok": True},
                "health": {"ok": True},
                "documents": {"ok": False, "missing": [], "unapproved": ["Transcripts"]},
            },
        )
        upload_actions = [row for row in actions if row.get("route_name") == "admissions-documents"]
        self.assertEqual(len(upload_actions), 1)
        self.assertEqual(upload_actions[0].get("label"), "Documents under review")
        self.assertFalse(bool(upload_actions[0].get("is_blocking")))

    def test_next_actions_recommendation_status_is_blocking_when_required(self):
        actions = _derive_next_actions(
            "In Progress",
            {
                "profile": {"ok": True},
                "policies": {"ok": True},
                "health": {"ok": True},
                "documents": {"ok": True, "missing": [], "unapproved": []},
                "recommendations": {"ok": False, "required_total": 1},
            },
        )
        recommendation_actions = [row for row in actions if row.get("route_name") == "admissions-status"]
        self.assertEqual(len(recommendation_actions), 1)
        self.assertTrue(bool(recommendation_actions[0].get("is_blocking")))


class TestInviteApplicant(FrappeTestCase):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Admissions Family")
        self._ensure_admin_admissions_role("Admission Manager")
        self._admissions_access_mode_before = (
            frappe.db.get_single_value("Admission Settings", "admissions_access_mode")
            if _admission_settings_has_field("admissions_access_mode")
            else None
        )
        frappe.clear_cache(user="Administrator")
        self.staff_user = self._create_admissions_staff_user()
        frappe.set_user(self.staff_user)
        if _admission_settings_has_field("admissions_access_mode"):
            self._set_admissions_access_mode("Single Applicant Workspace")
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self._create_employee_for_user(self.staff_user, self.organization, self.school)
        self.applicant = self._create_applicant(self.organization, self.school)

    def tearDown(self):
        frappe.set_user("Administrator")
        if _admission_settings_has_field("admissions_access_mode"):
            frappe.db.set_single_value(
                "Admission Settings",
                "admissions_access_mode",
                self._admissions_access_mode_before or "Single Applicant Workspace",
            )
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def test_invite_applicant_creates_portal_user_and_marks_invited(self):
        email = f"applicant-{frappe.generate_hash(length=8)}@example.com"

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email") as send_invite,
        ):
            payload = invite_applicant(student_applicant=self.applicant.name, email=email)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("user"), email)
        self.assertFalse(payload.get("resent"))
        self.assertTrue(payload.get("email_sent"))
        self.assertEqual(send_invite.call_count, 1)

        self.applicant.reload()
        self.assertEqual(self.applicant.applicant_user, email)
        self.assertEqual(self.applicant.application_status, "Invited")
        self.assertTrue(bool(self.applicant.applicant_contact))
        self.assertEqual(self.applicant.portal_account_email, email)
        self.assertEqual(self.applicant.applicant_email, email)
        self.assertTrue(
            bool(
                frappe.db.exists(
                    "Dynamic Link",
                    {
                        "parenttype": "Contact",
                        "parentfield": "links",
                        "parent": self.applicant.applicant_contact,
                        "link_doctype": "Student Applicant",
                        "link_name": self.applicant.name,
                    },
                )
            )
        )
        contact_emails = set(
            frappe.get_all(
                "Contact Email",
                filters={"parent": self.applicant.applicant_contact},
                pluck="email_id",
            )
            or []
        )
        self.assertIn(email, contact_emails)

        user_row = frappe.db.get_value("User", email, ["name", "enabled", "user_type"], as_dict=True)
        self.assertTrue(bool(user_row))
        self.assertEqual(user_row.get("enabled"), 1)
        self.assertEqual(user_row.get("user_type"), "Website User")
        roles = set(frappe.get_roles(email))
        self.assertIn("Admissions Applicant", roles)
        self.assertNotIn("Desk User", roles)
        self._created.append(("User", email))

    def test_invite_applicant_resends_email_for_same_linked_user(self):
        email = f"applicant-{frappe.generate_hash(length=8)}@example.com"

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email"),
        ):
            invite_applicant(student_applicant=self.applicant.name, email=email)
        self._created.append(("User", email))
        self.applicant.reload()
        self.assertTrue(bool(self.applicant.applicant_contact))
        self.assertEqual(self.applicant.portal_account_email, email)

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email") as send_invite,
        ):
            payload = invite_applicant(student_applicant=self.applicant.name, email=email)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("user"), email)
        self.assertTrue(payload.get("resent"))
        self.assertTrue(payload.get("email_sent"))
        self.assertEqual(send_invite.call_count, 1)

    def test_invite_applicant_reenables_existing_user_and_assigns_role(self):
        email = f"disabled-{frappe.generate_hash(length=8)}@example.com"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Disabled",
                "last_name": "Applicant",
                "enabled": 0,
                "send_welcome_email": 0,
                "send_password_notification": 0,
                "user_type": "Website User",
            }
        )
        user.flags.no_welcome_mail = True
        user.insert(ignore_permissions=True)
        self._created.append(("User", user.name))

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email", return_value=True),
        ):
            payload = invite_applicant(student_applicant=self.applicant.name, email=email)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("user"), email)
        self.assertTrue(payload.get("email_sent"))

        user.reload()
        self.assertEqual(user.enabled, 1)
        roles = {row.role for row in user.roles or []}
        self.assertIn("Admissions Applicant", roles)
        self.assertNotIn("Desk User", roles)
        self.assertEqual((user.user_type or "").strip(), "Website User")

    def test_invite_applicant_resend_normalizes_existing_user_to_website_user(self):
        email = f"normalize-{frappe.generate_hash(length=8)}@example.com"

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email", return_value=True),
        ):
            invite_applicant(student_applicant=self.applicant.name, email=email)
        self._created.append(("User", email))

        user = frappe.get_doc("User", email)
        user.user_type = "System User"
        if "Desk User" not in {row.role for row in user.roles or []}:
            if not frappe.db.exists("Role", "Desk User"):
                frappe.get_doc({"doctype": "Role", "role_name": "Desk User"}).insert(ignore_permissions=True)
                self._created.append(("Role", "Desk User"))
            user.append("roles", {"role": "Desk User"})
        user.save(ignore_permissions=True)

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email", return_value=True),
        ):
            payload = invite_applicant(student_applicant=self.applicant.name, email=email)

        self.assertTrue(payload.get("ok"))
        user.reload()
        self.assertEqual((user.user_type or "").strip(), "Website User")
        self.assertEqual(user.enabled, 1)
        roles = {row.role for row in user.roles or []}
        self.assertIn("Admissions Applicant", roles)
        self.assertNotIn("Desk User", roles)

    def test_send_invite_email_handles_non_callable_user_flags(self):
        class DummyUser:
            send_welcome_email = 1
            send_password_notification = 1

        with patch("ifitwala_ed.api.admissions_portal.frappe.sendmail") as mocked_sendmail:
            result = _send_applicant_invite_email(DummyUser(), "dummy@example.com")

        self.assertTrue(result)
        self.assertEqual(mocked_sendmail.call_count, 1)

    def test_get_invite_email_options_includes_contact_emails(self):
        email = f"existing-{frappe.generate_hash(length=8)}@example.com"
        alt_email = f"alt-{frappe.generate_hash(length=8)}@example.com"
        contact = self._create_contact(primary_email=email, other_email=alt_email)

        self.applicant.db_set("applicant_contact", contact.name, update_modified=False)
        self.applicant.db_set("applicant_email", email, update_modified=False)
        self.applicant.reload()

        with patch(
            "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
            return_value=self.staff_user,
        ):
            payload = get_invite_email_options(student_applicant=self.applicant.name)

        self.assertEqual(payload.get("contact"), contact.name)
        self.assertIn(email, payload.get("emails") or [])
        self.assertIn(alt_email, payload.get("emails") or [])

    def test_invite_applicant_rejects_email_linked_to_different_contact(self):
        applicant_contact = self._create_contact(primary_email=f"app-{frappe.generate_hash(length=8)}@example.com")
        other_contact_email = f"other-{frappe.generate_hash(length=8)}@example.com"
        self._create_contact(primary_email=other_contact_email)

        self.applicant.db_set("applicant_contact", applicant_contact.name, update_modified=False)
        self.applicant.db_set(
            "applicant_email",
            frappe.db.get_value("Contact Email", {"parent": applicant_contact.name, "is_primary": 1}, "email_id"),
            update_modified=False,
        )
        self.applicant.reload()

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email"),
        ):
            with self.assertRaises(frappe.ValidationError):
                invite_applicant(student_applicant=self.applicant.name, email=other_contact_email)

    def test_invite_family_collaborator_creates_guardian_user_and_links_row(self):
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")

        self._set_admissions_access_mode("Family Workspace")
        invite_email = f"family-{frappe.generate_hash(length=8)}@example.com"
        self.applicant.append(
            "guardians",
            {
                "relationship": "Mother",
                "can_consent": 1,
                "is_primary": 1,
                "is_primary_guardian": 1,
                "guardian_first_name": "Family",
                "guardian_last_name": "Collaborator",
                "guardian_email": invite_email,
                "guardian_mobile_phone": "+14155550123",
                "guardian_image": "/private/files/family-collaborator.png",
            },
        )
        self.applicant.save(ignore_permissions=True)
        guardian_row_name = self.applicant.get("guardians")[0].name

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email", return_value=True),
        ):
            options = get_family_invite_options(student_applicant=self.applicant.name)
            payload = invite_family_collaborator(
                student_applicant=self.applicant.name,
                guardian_row=guardian_row_name,
                email=invite_email,
            )

        eligible_rows = [row for row in (options.get("guardians") or []) if row.get("eligible")]
        self.assertEqual(len(eligible_rows), 1)
        self.assertEqual(eligible_rows[0].get("email"), invite_email)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("user"), invite_email)
        self.assertTrue(payload.get("email_sent"))
        self._created.append(("User", invite_email))

        self.applicant.reload()
        guardian_row = self.applicant.get("guardians")[0]
        self.assertEqual((guardian_row.user or "").strip(), invite_email)
        self.assertTrue(bool((guardian_row.guardian or "").strip()))
        self.assertTrue(bool((guardian_row.contact or "").strip()))

        guardian_doc = frappe.get_doc("Guardian", guardian_row.guardian)
        self.assertEqual((guardian_doc.user or "").strip(), invite_email)
        user_roles = set(frappe.get_roles(invite_email))
        self.assertIn("Admissions Family", user_roles)
        self.assertNotIn("Desk User", user_roles)

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

    def _create_applicant(self, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Portal",
                "last_name": f"Invite-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        return doc

    def _create_contact(self, *, primary_email: str, other_email: str | None = None):
        doc = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": "Portal",
                "last_name": f"Contact-{frappe.generate_hash(length=6)}",
                "email_ids": [{"email_id": primary_email, "is_primary": 1}],
            }
        )
        if other_email:
            doc.append("email_ids", {"email_id": other_email, "is_primary": 0})
        doc.insert(ignore_permissions=True)
        self._created.append(("Contact", doc.name))
        return doc

    def _create_employee_for_user(self, user: str, organization: str, school: str):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Admissions",
                "employee_last_name": "Staff",
                "employee_gender": "Male",
                "employee_professional_email": user,
                "date_of_joining": "2025-01-01",
                "employment_status": "Active",
                "organization": organization,
                "school": school,
                "user_id": user,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", employee.name))
        frappe.clear_cache(user=user)
        return employee

    def _create_admissions_staff_user(self) -> str:
        email = f"admissions-staff-{frappe.generate_hash(length=8)}@example.com"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Admissions",
                "last_name": "Staff",
                "enabled": 1,
                "send_welcome_email": 0,
                "send_password_notification": 0,
                "roles": [{"role": "Admission Manager"}],
            }
        )
        user.flags.no_welcome_mail = True
        user.insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        frappe.clear_cache(user=user.name)
        return user.name

    def _ensure_admin_admissions_role(self, role_name: str):
        if not frappe.db.exists("Role", role_name):
            role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
            self._created.append(("Role", role.name))
        if not frappe.db.exists("Has Role", {"parent": "Administrator", "role": role_name}):
            frappe.get_doc(
                {
                    "doctype": "Has Role",
                    "parent": "Administrator",
                    "parenttype": "User",
                    "parentfield": "roles",
                    "role": role_name,
                }
            ).insert(ignore_permissions=True)
        frappe.clear_cache(user="Administrator")

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

    def _set_admissions_access_mode(self, value: str):
        frappe.db.set_single_value("Admission Settings", "admissions_access_mode", value)


class TestSubmitApplication(FrappeTestCase):
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

    def test_submit_application_accepts_invited_state(self):
        frappe.set_user(self.applicant_user)
        payload = submit_application(student_applicant=self.applicant.name)
        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("changed"))

        self.applicant.reload()
        self.assertEqual(self.applicant.application_status, "Submitted")
        self.assertTrue(bool(self.applicant.submitted_at))

    def test_submit_application_accepts_missing_info_state(self):
        self.applicant.db_set("application_status", "Missing Info", update_modified=False)
        self.applicant.reload()

        frappe.set_user(self.applicant_user)
        payload = submit_application(student_applicant=self.applicant.name)
        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("changed"))

        self.applicant.reload()
        self.assertEqual(self.applicant.application_status, "Submitted")
        self.assertTrue(bool(self.applicant.submitted_at))

    def test_get_applicant_snapshot_includes_profile_and_application_context(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for readiness snapshot tests.")
        frappe.set_user(self.applicant_user)
        payload = get_applicant_snapshot(student_applicant=self.applicant.name)
        self.assertIn("profile", payload)
        self.assertIn("application_context", payload)
        self.assertIn("profile", payload.get("completeness") or {})
        self.assertIn("recommendations", payload.get("completeness") or {})
        self.assertIn("recommendations_summary", payload)

    def test_offer_sent_snapshot_surfaces_offer_response_action(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for admissions offer snapshot tests.")
        self._create_offer_plan(status="Offer Sent", offer_message="Review your place.")

        frappe.set_user(self.applicant_user)
        session_payload = admissions_portal_api.get_admissions_session()
        snapshot = get_applicant_snapshot(student_applicant=self.applicant.name)

        self.assertEqual((session_payload.get("applicant") or {}).get("portal_status"), "Offer Sent")
        self.assertEqual((snapshot.get("enrollment_offer") or {}).get("status"), "Offer Sent")
        self.assertTrue(bool((snapshot.get("enrollment_offer") or {}).get("can_accept")))
        self.assertTrue(bool((snapshot.get("enrollment_offer") or {}).get("can_decline")))
        self.assertEqual((snapshot.get("next_actions") or [])[0].get("route_name"), "admissions-status")
        self.assertTrue(bool((snapshot.get("next_actions") or [])[0].get("is_blocking")))

    def test_offer_sent_snapshot_surfaces_course_choice_action_when_choices_are_incomplete(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for admissions offer snapshot tests.")
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        self._create_offer_plan(
            status="Offer Sent",
            optional_course_basket_groups=[humanities_group],
            enrollment_rules=[{"rule_type": "REQUIRE_GROUP_COVERAGE", "basket_group": humanities_group}],
        )

        frappe.set_user(self.applicant_user)
        snapshot = get_applicant_snapshot(student_applicant=self.applicant.name)

        actions = snapshot.get("next_actions") or []
        self.assertEqual(actions[0].get("route_name"), "admissions-course-choices")
        self.assertEqual(actions[1].get("route_name"), "admissions-status")
        self.assertFalse(bool((snapshot.get("enrollment_offer") or {}).get("course_choices_ready")))

    def test_get_admissions_session_family_workspace_returns_all_linked_applicants(self):
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")

        self._set_admissions_access_mode("Family Workspace")
        family_user = self._create_family_user()
        guardian = self._create_guardian_record(user=family_user.name, is_primary_guardian=True)
        second_applicant = self._create_applicant(self.organization, self.school, self._create_applicant_user())

        self._link_family_guardian(self.applicant, guardian_name=guardian.name, user=family_user.name)
        self._link_family_guardian(second_applicant, guardian_name=guardian.name, user=family_user.name)

        frappe.set_user(family_user.name)
        payload = admissions_portal_api.get_admissions_session(student_applicant=second_applicant.name)

        self.assertEqual(payload.get("access_mode"), "Family Workspace")
        self.assertTrue(bool(payload.get("family_workspace_enabled")))
        self.assertEqual(payload.get("selected_applicant"), second_applicant.name)
        self.assertEqual((payload.get("applicant") or {}).get("name"), second_applicant.name)
        self.assertEqual(set((payload.get("user") or {}).get("roles") or []), {"Admissions Family"})
        self.assertEqual(
            {row.get("name") for row in (payload.get("available_applicants") or [])},
            {self.applicant.name, second_applicant.name},
        )

    def test_get_applicant_enrollment_choices_exposes_required_and_optional_offering_rows(self):
        core_group = f"Core Basket {frappe.generate_hash(length=6)}"
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        sciences_group = f"Group 4 Sciences {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Offer Sent",
            required_course_basket_groups=[core_group],
            optional_course_basket_groups=[humanities_group, sciences_group],
        )

        frappe.set_user(self.applicant_user)
        payload = get_applicant_enrollment_choices(student_applicant=self.applicant.name)

        self.assertEqual((payload.get("plan") or {}).get("status"), "Offer Sent")
        self.assertEqual((payload.get("summary") or {}).get("required_course_count"), 1)
        self.assertEqual((payload.get("summary") or {}).get("optional_course_count"), 1)

        rows_by_course = {row.get("course"): row for row in (payload.get("courses") or [])}
        self.assertTrue(bool(rows_by_course.get(context["required_course"].name, {}).get("required")))
        self.assertEqual(
            rows_by_course.get(context["optional_course"].name, {}).get("basket_groups"),
            [humanities_group, sciences_group],
        )

    def test_update_applicant_enrollment_choices_persists_selection_and_required_group_resolution(self):
        required_group_one = f"Group 1 {frappe.generate_hash(length=6)}"
        required_group_two = f"Group 2 {frappe.generate_hash(length=6)}"
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Offer Sent",
            required_course_basket_groups=[required_group_one, required_group_two],
            optional_course_basket_groups=[humanities_group],
        )

        frappe.set_user(self.applicant_user)
        payload = update_applicant_enrollment_choices(
            student_applicant=self.applicant.name,
            courses=[
                {
                    "course": context["required_course"].name,
                    "applied_basket_group": required_group_one,
                },
                {
                    "course": context["optional_course"].name,
                    "applied_basket_group": humanities_group,
                    "choice_rank": 1,
                },
            ],
        )

        self.assertTrue(payload.get("ok"))
        self.assertEqual((payload.get("summary") or {}).get("selected_optional_count"), 1)

        context["plan"].reload()
        rows_by_course = {row.course: row for row in context["plan"].get("courses") or []}
        self.assertEqual(
            (rows_by_course[context["required_course"].name].applied_basket_group or "").strip(),
            required_group_one,
        )
        self.assertEqual(
            (rows_by_course[context["optional_course"].name].applied_basket_group or "").strip(),
            humanities_group,
        )
        self.assertEqual(rows_by_course[context["optional_course"].name].choice_rank, 1)

    def test_accept_enrollment_offer_requires_complete_course_choices(self):
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Offer Sent",
            optional_course_basket_groups=[humanities_group],
            enrollment_rules=[{"rule_type": "REQUIRE_GROUP_COVERAGE", "basket_group": humanities_group}],
        )

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            accept_enrollment_offer(student_applicant=self.applicant.name)

        update_applicant_enrollment_choices(
            student_applicant=self.applicant.name,
            courses=[
                {
                    "course": context["optional_course"].name,
                    "applied_basket_group": humanities_group,
                }
            ],
        )

        payload = accept_enrollment_offer(student_applicant=self.applicant.name)
        self.assertTrue(payload.get("ok"))
        self.assertEqual((payload.get("result") or {}).get("status"), "Offer Accepted")

    def test_accept_enrollment_offer_is_idempotent(self):
        self._create_offer_plan(status="Offer Sent")

        frappe.set_user(self.applicant_user)
        first = accept_enrollment_offer(student_applicant=self.applicant.name)
        second = accept_enrollment_offer(student_applicant=self.applicant.name)
        session_payload = admissions_portal_api.get_admissions_session()

        self.assertTrue(first.get("ok"))
        self.assertTrue(second.get("ok"))
        self.assertEqual((first.get("result") or {}).get("status"), "Offer Accepted")
        self.assertEqual((second.get("result") or {}).get("status"), "Offer Accepted")
        self.assertEqual((session_payload.get("applicant") or {}).get("portal_status"), "Accepted")

    def test_decline_enrollment_offer_is_idempotent_and_visible_after_decline(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for admissions offer snapshot tests.")
        self._create_offer_plan(status="Offer Sent")

        frappe.set_user(self.applicant_user)
        first = decline_enrollment_offer(student_applicant=self.applicant.name)
        second = decline_enrollment_offer(student_applicant=self.applicant.name)
        session_payload = admissions_portal_api.get_admissions_session()
        snapshot = get_applicant_snapshot(student_applicant=self.applicant.name)

        self.assertTrue(first.get("ok"))
        self.assertTrue(second.get("ok"))
        self.assertEqual((first.get("result") or {}).get("status"), "Offer Declined")
        self.assertEqual((second.get("result") or {}).get("status"), "Offer Declined")
        self.assertEqual((session_payload.get("applicant") or {}).get("portal_status"), "Declined")
        self.assertEqual((snapshot.get("enrollment_offer") or {}).get("status"), "Offer Declined")

    def test_get_applicant_policies_includes_expected_signature_name(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")
        frappe.set_user(self.applicant_user)
        payload = get_applicant_policies(student_applicant=self.applicant.name)
        policies = payload.get("policies") or []
        self.assertTrue(bool(policies))

        expected_name = f"{self.applicant.first_name} {self.applicant.last_name}".strip()
        target = next(
            (row for row in policies if row.get("policy_version") == self.policy_version),
            None,
        )
        self.assertTrue(bool(target))
        self.assertEqual(target.get("expected_signature_name"), expected_name)

    def test_get_applicant_policies_includes_acknowledgement_clauses(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")

        version = self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            acknowledgement_clauses=[
                {"clause_text": "I confirm the information is accurate.", "is_required": 1},
                {"clause_text": "I agree to optional reminders.", "is_required": 0},
            ],
        )

        frappe.set_user(self.applicant_user)
        payload = get_applicant_policies(student_applicant=self.applicant.name)
        target = next((row for row in (payload.get("policies") or []) if row.get("policy_version") == version), None)

        self.assertTrue(bool(target))
        clauses = target.get("acknowledgement_clauses") or []
        self.assertEqual(len(clauses), 2)
        self.assertEqual(clauses[0].get("clause_text"), "I confirm the information is accurate.")
        self.assertTrue(bool(clauses[0].get("is_required")))

    def test_get_applicant_policies_sanitizes_policy_html(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")

        version = self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            policy_text='<h1>Applicant Policy</h1><p>Allowed</p><script>alert(1)</script><img src="x" onerror="alert(2)">',
        )

        frappe.set_user(self.applicant_user)
        payload = get_applicant_policies(student_applicant=self.applicant.name)
        target = next((row for row in (payload.get("policies") or []) if row.get("policy_version") == version), None)

        self.assertTrue(bool(target))
        self.assertIn("<h2>Applicant Policy</h2>", target.get("content_html") or "")
        self.assertIn("<p>Allowed</p>", target.get("content_html") or "")
        self.assertNotIn("<script", target.get("content_html") or "")
        self.assertNotIn("onerror", target.get("content_html") or "")

    def test_acknowledge_policy_requires_attestation_confirmation(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")
        frappe.set_user(self.applicant_user)
        expected_name = f"{self.applicant.first_name} {self.applicant.last_name}".strip()

        with self.assertRaises(frappe.ValidationError):
            acknowledge_policy(
                student_applicant=self.applicant.name,
                policy_version=self.policy_version,
                typed_signature_name=expected_name,
                attestation_confirmed=0,
            )

    def test_acknowledge_policy_requires_matching_typed_signature(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")
        frappe.set_user(self.applicant_user)

        with self.assertRaises(frappe.ValidationError):
            acknowledge_policy(
                student_applicant=self.applicant.name,
                policy_version=self.policy_version,
                typed_signature_name="Wrong Name",
                attestation_confirmed=1,
            )

    def test_acknowledge_policy_requires_required_clauses(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")

        version = self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            acknowledgement_clauses=[
                {"clause_text": "I confirm the information is accurate.", "is_required": 1},
            ],
        )
        frappe.set_user(self.applicant_user)
        expected_name = f"{self.applicant.first_name} {self.applicant.last_name}".strip()

        with self.assertRaises(frappe.ValidationError):
            acknowledge_policy(
                student_applicant=self.applicant.name,
                policy_version=version,
                typed_signature_name=expected_name,
                attestation_confirmed=1,
                checked_clause_names=[],
            )

    def test_acknowledge_policy_creates_row_for_valid_signature(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")
        frappe.set_user(self.applicant_user)
        expected_name = f"{self.applicant.first_name} {self.applicant.last_name}".strip()

        payload = acknowledge_policy(
            student_applicant=self.applicant.name,
            policy_version=self.policy_version,
            typed_signature_name=expected_name,
            attestation_confirmed=1,
        )
        self.assertTrue(payload.get("ok"))
        self.assertTrue(bool(payload.get("acknowledged_at")))

        ack = frappe.db.get_value(
            "Policy Acknowledgement",
            {
                "policy_version": self.policy_version,
                "acknowledged_for": "Applicant",
                "context_doctype": "Student Applicant",
                "context_name": self.applicant.name,
            },
            ["name", "acknowledged_by"],
            as_dict=True,
        )
        self.assertTrue(bool(ack))
        self.assertEqual(ack.get("acknowledged_by"), self.applicant_user)
        self._created.append(("Policy Acknowledgement", ack.get("name")))

    def test_acknowledge_policy_family_mode_creates_guardian_context(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for family acknowledgement tests.")
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")
        if not institutional_policy_db_has_column("admissions_acknowledgement_mode"):
            self.skipTest(
                "Institutional Policy.admissions_acknowledgement_mode is required for family acknowledgement tests."
            )

        self._set_admissions_access_mode("Family Workspace")
        family_user = self._create_family_user()
        guardian = self._create_guardian_record(user=family_user.name, is_primary_guardian=True)
        self._link_family_guardian(self.applicant, guardian_name=guardian.name, user=family_user.name)
        family_policy_version = self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            admissions_acknowledgement_mode="Family Acknowledgement",
        )

        frappe.set_user(family_user.name)
        policies = get_applicant_policies(student_applicant=self.applicant.name)
        target = next(
            (
                row
                for row in (policies.get("policies") or [])
                if (row.get("policy_version") or "").strip() == family_policy_version
            ),
            None,
        )
        self.assertTrue(bool(target))

        payload = acknowledge_policy(
            student_applicant=self.applicant.name,
            policy_version=family_policy_version,
            typed_signature_name=target.get("expected_signature_name"),
            attestation_confirmed=1,
        )
        self.assertTrue(payload.get("ok"))

        ack = frappe.db.get_value(
            "Policy Acknowledgement",
            {
                "policy_version": family_policy_version,
                "acknowledged_for": "Guardian",
                "context_doctype": "Guardian",
                "context_name": guardian.name,
            },
            ["name", "acknowledged_by"],
            as_dict=True,
        )
        self.assertTrue(bool(ack))
        self._created.append(("Policy Acknowledgement", ack.get("name")))
        self.assertEqual((ack.get("acknowledged_by") or "").strip(), family_user.name)

    def test_acknowledge_policy_family_mode_rejects_non_primary_guardian(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for family acknowledgement tests.")
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")
        if not institutional_policy_db_has_column("admissions_acknowledgement_mode"):
            self.skipTest(
                "Institutional Policy.admissions_acknowledgement_mode is required for family acknowledgement tests."
            )

        self._set_admissions_access_mode("Family Workspace")
        family_user = self._create_family_user()
        guardian = self._create_guardian_record(user=family_user.name, is_primary_guardian=False)
        self._link_family_guardian(
            self.applicant,
            guardian_name=guardian.name,
            user=family_user.name,
            is_primary_guardian=False,
        )
        self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            admissions_acknowledgement_mode="Family Acknowledgement",
        )

        frappe.set_user(family_user.name)
        with self.assertRaises(frappe.PermissionError):
            get_applicant_policies(student_applicant=self.applicant.name)

    def test_update_applicant_profile_persists_values(self):
        language = self._get_or_create_language_xtra()
        country = self._get_any_country()
        if not country:
            self.skipTest("Country records are required for applicant profile update test.")

        frappe.set_user(self.applicant_user)
        payload = update_applicant_profile(
            student_applicant=self.applicant.name,
            student_preferred_name="Portal Preferred",
            student_date_of_birth="2013-03-01",
            student_gender="Female",
            student_mobile_number="+14155551234",
            student_first_language=language,
            student_second_language=language,
            student_nationality=country,
            student_second_nationality=country,
            residency_status="Local Resident",
        )
        self.assertTrue(payload.get("ok"))
        self.assertTrue((payload.get("completeness") or {}).get("ok"))

        profile_payload = get_applicant_profile(student_applicant=self.applicant.name)
        profile = profile_payload.get("profile") or {}
        self.assertEqual(profile.get("student_preferred_name"), "Portal Preferred")
        self.assertEqual(profile.get("student_nationality"), country)
        self.assertEqual(profile.get("student_first_language"), language)

    def test_update_applicant_profile_rejects_stale_expected_modified(self):
        frappe.set_user(self.applicant_user)
        initial = get_applicant_profile(student_applicant=self.applicant.name)
        initial_modified = initial.get("record_modified") or ""

        fresh = update_applicant_profile(
            student_applicant=self.applicant.name,
            expected_modified=initial_modified,
            student_preferred_name="Fresh Save",
        )
        self.assertTrue(bool(fresh.get("record_modified")))

        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                expected_modified=initial_modified,
                student_preferred_name="Stale Save",
            )

    def test_update_applicant_profile_persists_guardians_when_enabled(self):
        self._set_guardians_section_setting(1)
        guardian_email = f"guardian-{frappe.generate_hash(length=8)}@example.com"

        frappe.set_user(self.applicant_user)
        payload = update_applicant_profile(
            student_applicant=self.applicant.name,
            guardians=[
                {
                    "relationship": "Mother",
                    "can_consent": 1,
                    "is_primary": 1,
                    "is_primary_guardian": 1,
                    "use_applicant_contact": 0,
                    "guardian_first_name": "Mina",
                    "guardian_last_name": "Portal",
                    "guardian_email": guardian_email,
                    "guardian_mobile_phone": "+14155550101",
                    "guardian_gender": "Female",
                    "guardian_image": "/private/files/guardian-mina.png",
                }
            ],
        )
        self.assertTrue(payload.get("ok"))
        self.assertTrue(bool(payload.get("guardian_section_enabled")))
        guardians = payload.get("guardians") or []
        self.assertEqual(len(guardians), 1)
        self.assertEqual((guardians[0].get("guardian_email") or "").strip(), guardian_email)
        self.assertTrue(bool(guardians[0].get("can_consent")))
        self.assertTrue(bool((guardians[0].get("contact") or "").strip()))

        self.applicant.reload()
        rows = self.applicant.get("guardians") or []
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].guardian_first_name, "Mina")
        self.assertEqual(rows[0].guardian_last_name, "Portal")
        self.assertEqual((rows[0].guardian_email or "").strip(), guardian_email)
        self.assertEqual(int(rows[0].can_consent or 0), 1)
        self.assertTrue(bool((rows[0].contact or "").strip()))

        self.assertTrue(
            bool(
                frappe.db.exists(
                    "Dynamic Link",
                    {
                        "parenttype": "Contact",
                        "parentfield": "links",
                        "parent": rows[0].contact,
                        "link_doctype": "Student Applicant",
                        "link_name": self.applicant.name,
                    },
                )
            )
        )

    def test_update_applicant_profile_rejects_unlinked_contact_email_for_guardian(self):
        self._set_guardians_section_setting(1)
        foreign_email = f"foreign-{frappe.generate_hash(length=8)}@example.com"
        contact = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": "Foreign",
                "last_name": "Contact",
                "email_ids": [{"email_id": foreign_email, "is_primary": 1}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Contact", contact.name))

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "relationship": "Father",
                        "guardian_first_name": "Other",
                        "guardian_last_name": "Family",
                        "guardian_email": foreign_email,
                        "guardian_mobile_phone": "+14155550102",
                        "guardian_image": "/private/files/guardian-other.png",
                    }
                ],
            )

    def test_update_applicant_profile_forces_non_primary_guardian_to_non_signing(self):
        self._set_guardians_section_setting(1)
        guardian_email = f"secondary-{frappe.generate_hash(length=8)}@example.com"

        frappe.set_user(self.applicant_user)
        payload = update_applicant_profile(
            student_applicant=self.applicant.name,
            guardians=[
                {
                    "relationship": "Aunt",
                    "can_consent": 1,
                    "is_primary": 0,
                    "is_primary_guardian": 0,
                    "use_applicant_contact": 0,
                    "guardian_first_name": "Secondary",
                    "guardian_last_name": "Guardian",
                    "guardian_email": guardian_email,
                    "guardian_mobile_phone": "+14155550109",
                    "guardian_gender": "Female",
                    "guardian_image": "/private/files/guardian-secondary.png",
                }
            ],
        )

        self.assertTrue(payload.get("ok"))
        guardians = payload.get("guardians") or []
        self.assertEqual(len(guardians), 1)
        self.assertFalse(bool(guardians[0].get("can_consent")))

        self.applicant.reload()
        rows = self.applicant.get("guardians") or []
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0].can_consent or 0), 0)

    def test_update_applicant_health_rejects_stale_expected_modified(self):
        frappe.set_user(self.applicant_user)
        initial = admissions_portal_api.get_applicant_health(student_applicant=self.applicant.name)
        initial_modified = initial.get("record_modified") or ""

        fresh = update_applicant_health(
            student_applicant=self.applicant.name,
            expected_modified=initial_modified,
            vaccinations=[],
        )
        self.assertTrue(bool(fresh.get("record_modified")))

        with self.assertRaises(frappe.ValidationError):
            update_applicant_health(
                student_applicant=self.applicant.name,
                expected_modified=initial_modified,
                vaccinations=[],
            )

    def test_update_applicant_profile_rejects_invalid_guardian_email(self):
        self._set_guardians_section_setting(1)

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "relationship": "Mother",
                        "guardian_first_name": "Mina",
                        "guardian_last_name": "Portal",
                        "guardian_email": "not-an-email",
                        "guardian_mobile_phone": "+14155550102",
                        "guardian_image": "/private/files/guardian.png",
                    }
                ],
            )

    def test_update_applicant_profile_rejects_invalid_guardian_phone(self):
        self._set_guardians_section_setting(1)

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "relationship": "Father",
                        "guardian_first_name": "Jean",
                        "guardian_last_name": "Portal",
                        "guardian_email": f"guardian-{frappe.generate_hash(length=8)}@example.com",
                        "guardian_mobile_phone": "bad-phone",
                        "guardian_image": "/private/files/guardian.png",
                    }
                ],
            )

    def test_update_applicant_profile_rejects_missing_guardian_image(self):
        self._set_guardians_section_setting(1)

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "relationship": "Mother",
                        "guardian_first_name": "Mina",
                        "guardian_last_name": "Portal",
                        "guardian_email": f"guardian-{frappe.generate_hash(length=8)}@example.com",
                        "guardian_mobile_phone": "+14155550102",
                        "guardian_image": "",
                    }
                ],
            )

    def test_update_applicant_profile_preserves_guardian_image_attachment_scope_on_guardian_row(self):
        self._set_guardians_section_setting(1)

        contact = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": "Applicant",
                "last_name": "Contact",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Contact", contact.name))
        self.applicant.db_set("applicant_contact", contact.name, update_modified=False)
        self.applicant.reload()

        guardian_email = f"guardian-{frappe.generate_hash(length=8)}@example.com"
        guardian_row = self.applicant.append(
            "guardians",
            {
                "relationship": "Mother",
                "use_applicant_contact": 1,
                "can_consent": 1,
                "is_primary": 1,
                "is_primary_guardian": 1,
                "guardian_first_name": "Mina",
                "guardian_last_name": "Portal",
                "guardian_email": guardian_email,
                "guardian_mobile_phone": "+14155550101",
            },
        )
        self.applicant.save(ignore_permissions=True)
        guardian_row_name = guardian_row.name

        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Student Applicant Guardian",
                "attached_to_name": guardian_row_name,
                "attached_to_field": "guardian_image",
                "file_name": "guardian.png",
                "content": base64.b64decode(self._tiny_png_base64()),
                "is_private": 1,
            }
        )
        file_doc.flags.governed_upload = True
        file_doc.insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.admission.doctype.student_applicant.student_applicant.ensure_guardian_profile_image",
                return_value=file_doc.file_url,
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.get_drive_file_for_file",
                return_value={
                    "name": "DRV-GUARDIAN-1",
                    "file": file_doc.name,
                    "canonical_ref": f"drv:{self.organization}:DRV-GUARDIAN-1",
                    "primary_subject_type": "Student Applicant",
                    "primary_subject_id": self.applicant.name,
                },
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.get_drive_file_thumbnail_ready_map",
                return_value={"DRV-GUARDIAN-1": True},
            ),
        ):
            payload = update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "name": guardian_row_name,
                        "relationship": "Mother",
                        "use_applicant_contact": 1,
                        "can_consent": 1,
                        "is_primary": 1,
                        "is_primary_guardian": 1,
                        "guardian_first_name": "Mina",
                        "guardian_last_name": "Portal",
                        "guardian_email": guardian_email,
                        "guardian_mobile_phone": "+14155550101",
                        "guardian_image": file_doc.file_url,
                    }
                ],
            )

        self.assertTrue(payload.get("ok"))
        guardian_payload = (payload.get("guardians") or [{}])[0]
        self.assertIn("thumbnail_admissions_file", guardian_payload.get("guardian_image") or "")
        self.assertIn("download_admissions_file", guardian_payload.get("guardian_image_open_url") or "")
        file_row = frappe.db.get_value(
            "File",
            file_doc.name,
            ["attached_to_doctype", "attached_to_name", "attached_to_field"],
            as_dict=True,
        )
        self.assertEqual(file_row.get("attached_to_doctype"), "Student Applicant Guardian")
        self.assertEqual(file_row.get("attached_to_name"), guardian_row_name)
        self.assertEqual((file_row.get("attached_to_field") or "").strip(), "guardian_image")

    def test_get_applicant_profile_includes_applicant_image(self):
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Student Applicant",
                "attached_to_name": self.applicant.name,
                "attached_to_field": "applicant_image",
                "file_name": f"applicant-{frappe.generate_hash(length=6)}.png",
                "is_private": 1,
                "content": base64.b64decode(self._tiny_png_base64()),
            }
        )
        file_doc.flags.governed_upload = True
        file_doc.insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))
        self.applicant.db_set("applicant_image", file_doc.file_url, update_modified=False)
        self.applicant.reload()

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.api.admissions_portal.get_drive_file_for_file",
                return_value={
                    "name": "DRV-APP-1",
                    "file": file_doc.name,
                    "canonical_ref": f"drv:{self.organization}:DRV-APP-1",
                    "primary_subject_type": "Student Applicant",
                    "primary_subject_id": self.applicant.name,
                },
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.get_drive_file_thumbnail_ready_map",
                return_value={"DRV-APP-1": True},
            ),
        ):
            profile_payload = get_applicant_profile(student_applicant=self.applicant.name)
        secure_url = str(profile_payload.get("applicant_image") or "").strip()
        self.assertTrue(secure_url)
        self.assertNotIn("/private/files/", secure_url)
        self.assertIn("thumbnail_admissions_file", secure_url)
        self.assertIn(f"file={file_doc.name}", secure_url)
        self.assertIn(
            "download_admissions_file",
            str(profile_payload.get("applicant_image_open_url") or ""),
        )

    def test_upload_applicant_profile_image_denies_other_applicant(self):
        other = self._create_applicant(self.organization, self.school, applicant_user="")

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.PermissionError):
            upload_applicant_profile_image(
                student_applicant=other.name,
                file_name="student.png",
                content=self._tiny_png_base64(),
            )

    def test_upload_applicant_profile_image_denies_read_only_status(self):
        self.applicant.db_set("application_status", "Submitted", update_modified=False)
        self.applicant.reload()

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.PermissionError):
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.png",
                content=self._tiny_png_base64(),
            )

    def test_upload_applicant_profile_image_creates_governed_file(self):
        captured: dict = {}
        drive_file_id = "DRV-FILE-0001"
        canonical_ref = f"drv:{self.organization}:{drive_file_id}"

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            return {
                "file": "FILE-UP-APP-1",
                "file_url": f"/private/files/applicant-{frappe.generate_hash(length=6)}.jpg",
                "drive_file_id": drive_file_id,
                "canonical_ref": canonical_ref,
                "student_applicant": kwargs.get("student_applicant"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.api.admissions_portal.admission_api.upload_applicant_profile_image",
                side_effect=_capture_drive_upload,
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.get_drive_file_thumbnail_ready_map",
                return_value={drive_file_id: True},
            ),
        ):
            payload = upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.png",
                content=self._tiny_png_base64(),
            )

        self.assertTrue(payload.get("ok"))
        self.assertIn("thumbnail_admissions_file", str(payload.get("image_url") or ""))
        self.assertIn("download_admissions_file", str(payload.get("open_url") or ""))
        self.assertEqual(str(payload.get("drive_file_id") or ""), drive_file_id)
        self.assertEqual(str(payload.get("canonical_ref") or ""), canonical_ref)
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["upload_source"], "SPA")
        self.assertTrue(captured["file_name"].startswith("applicant_profile_image_"))
        self.assertTrue(captured["file_name"].endswith(".jpg"))
        self.assertTrue(captured["content"].startswith(b"\xff\xd8\xff"))

    def test_upload_applicant_profile_image_reads_json_request_payload_when_bound_kwargs_are_blank_strings(self):
        captured: dict = {}
        drive_file_id = "DRV-FILE-JSON-1"
        canonical_ref = f"drv:{self.organization}:{drive_file_id}"
        request_payload = {
            "student_applicant": self.applicant.name,
            "file_name": "student.png",
            "content": self._tiny_png_base64(),
        }

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            return {
                "file": "FILE-UP-APP-JSON-1",
                "file_url": f"/private/files/applicant-{frappe.generate_hash(length=6)}.jpg",
                "drive_file_id": drive_file_id,
                "canonical_ref": canonical_ref,
                "student_applicant": kwargs.get("student_applicant"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch.object(frappe, "form_dict", frappe._dict(), create=True),
            patch.object(
                frappe,
                "request",
                SimpleNamespace(
                    get_json=lambda silent=True: request_payload,
                    data=frappe.as_json(request_payload),
                    files=None,
                    mimetype="application/json",
                ),
                create=True,
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.admission_api.upload_applicant_profile_image",
                side_effect=_capture_drive_upload,
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.get_drive_file_thumbnail_ready_map",
                return_value={drive_file_id: True},
            ),
        ):
            payload = upload_applicant_profile_image(
                student_applicant="",
                file_name="",
                content="",
            )

        self.assertTrue(payload.get("ok"))
        self.assertEqual(str(payload.get("drive_file_id") or ""), drive_file_id)
        self.assertEqual(str(payload.get("canonical_ref") or ""), canonical_ref)
        self.assertIn("thumbnail_admissions_file", str(payload.get("image_url") or ""))
        self.assertIn("download_admissions_file", str(payload.get("open_url") or ""))
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["upload_source"], "SPA")
        self.assertTrue(captured["file_name"].startswith("applicant_profile_image_"))
        self.assertTrue(captured["content"].startswith(b"\xff\xd8\xff"))

    def test_upload_applicant_profile_image_rejects_heic_extension(self):
        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError) as error_context:
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="IMG_1157.HEIC",
                content=self._tiny_png_base64(),
            )

        self.assertIn("Only JPG, JPEG, PNG image files are accepted", str(error_context.exception))

    def test_upload_applicant_profile_image_rejects_extension_content_mismatch(self):
        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError) as error_context:
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.jpg",
                content=self._tiny_png_base64(),
            )

        self.assertIn("extension does not match", str(error_context.exception))

    def test_upload_applicant_profile_image_rejects_files_larger_than_limit(self):
        oversized_content = base64.b64encode(b"\xff\xd8\xff" + b"a" * (11 * 1024 * 1024)).decode()

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError) as error_context:
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.jpg",
                content=oversized_content,
            )

        self.assertIn("Max file size is 10 MB", str(error_context.exception))

    def test_upload_applicant_profile_image_rejects_images_over_pixel_limit(self):
        frappe.set_user(self.applicant_user)
        with (
            patch.object(admissions_portal_api, "PROFILE_IMAGE_MAX_PIXELS", 0),
            self.assertRaises(frappe.ValidationError) as error_context,
        ):
            upload_applicant_profile_image(
                student_applicant=self.applicant.name,
                file_name="student.png",
                content=self._tiny_png_base64(),
            )

        self.assertIn("Max image size is", str(error_context.exception))

    def test_upload_applicant_guardian_image_creates_governed_file(self):
        guardian_row = self.applicant.append(
            "guardians",
            {
                "relationship": "Mother",
                "guardian_first_name": "Mina",
                "guardian_last_name": "Guardian",
                "guardian_email": f"guardian-{frappe.generate_hash(length=6)}@example.com",
                "guardian_mobile_phone": "+14155550121",
            },
        )
        self.applicant.save(ignore_permissions=True)
        guardian_row_name = guardian_row.name

        captured: dict = {}
        drive_file_id = "DRV-GUARDIAN-UP-1"
        canonical_ref = f"drv:{self.organization}:{drive_file_id}"

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            return {
                "file": "FILE-UP-GUARDIAN-1",
                "file_url": f"/private/files/guardian-{frappe.generate_hash(length=6)}.jpg",
                "drive_file_id": drive_file_id,
                "canonical_ref": canonical_ref,
                "student_applicant": kwargs.get("student_applicant"),
                "guardian_row_name": kwargs.get("guardian_row_name"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.api.admissions_portal.admission_api.upload_applicant_guardian_image",
                side_effect=_capture_drive_upload,
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.get_drive_file_thumbnail_ready_map",
                return_value={drive_file_id: True},
            ),
        ):
            payload = upload_applicant_guardian_image(
                student_applicant=self.applicant.name,
                guardian_row_name=guardian_row_name,
                file_name="guardian.png",
                content=self._tiny_png_base64(),
            )

        self.assertTrue(payload.get("ok"))
        self.assertIn("thumbnail_admissions_file", str(payload.get("image_url") or ""))
        self.assertIn("download_admissions_file", str(payload.get("open_url") or ""))
        self.assertEqual(str(payload.get("drive_file_id") or ""), drive_file_id)
        self.assertEqual(str(payload.get("canonical_ref") or ""), canonical_ref)
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["guardian_row_name"], guardian_row_name)
        self.assertEqual(captured["upload_source"], "SPA")
        self.assertTrue(captured["file_name"].startswith("guardian_profile_image_"))
        self.assertTrue(captured["file_name"].endswith(".jpg"))
        self.assertTrue(captured["content"].startswith(b"\xff\xd8\xff"))

    def test_upload_applicant_guardian_image_reads_json_request_payload_when_bound_kwargs_are_blank_strings(self):
        guardian_row = self.applicant.append(
            "guardians",
            {
                "relationship": "Mother",
                "guardian_first_name": "Mina",
                "guardian_last_name": "Guardian",
                "guardian_email": f"guardian-{frappe.generate_hash(length=6)}@example.com",
                "guardian_mobile_phone": "+14155550121",
            },
        )
        self.applicant.save(ignore_permissions=True)
        guardian_row_name = guardian_row.name

        captured: dict = {}
        drive_file_id = "DRV-GUARDIAN-JSON-1"
        canonical_ref = f"drv:{self.organization}:{drive_file_id}"
        request_payload = {
            "student_applicant": self.applicant.name,
            "guardian_row_name": guardian_row_name,
            "file_name": "guardian.png",
            "content": self._tiny_png_base64(),
        }

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            return {
                "file": "FILE-UP-GUARDIAN-JSON-1",
                "file_url": f"/private/files/guardian-{frappe.generate_hash(length=6)}.jpg",
                "drive_file_id": drive_file_id,
                "canonical_ref": canonical_ref,
                "student_applicant": kwargs.get("student_applicant"),
                "guardian_row_name": kwargs.get("guardian_row_name"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch.object(frappe, "form_dict", frappe._dict(), create=True),
            patch.object(
                frappe,
                "request",
                SimpleNamespace(
                    get_json=lambda silent=True: request_payload,
                    data=frappe.as_json(request_payload),
                    files=None,
                    mimetype="application/json",
                ),
                create=True,
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.admission_api.upload_applicant_guardian_image",
                side_effect=_capture_drive_upload,
            ),
            patch(
                "ifitwala_ed.api.admissions_portal.get_drive_file_thumbnail_ready_map",
                return_value={drive_file_id: True},
            ),
        ):
            payload = upload_applicant_guardian_image(
                student_applicant="",
                guardian_row_name="",
                file_name="",
                content="",
            )

        self.assertTrue(payload.get("ok"))
        self.assertEqual(str(payload.get("drive_file_id") or ""), drive_file_id)
        self.assertEqual(str(payload.get("canonical_ref") or ""), canonical_ref)
        self.assertIn("thumbnail_admissions_file", str(payload.get("image_url") or ""))
        self.assertIn("download_admissions_file", str(payload.get("open_url") or ""))
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["guardian_row_name"], guardian_row_name)
        self.assertEqual(captured["upload_source"], "SPA")
        self.assertTrue(captured["file_name"].startswith("guardian_profile_image_"))
        self.assertTrue(captured["content"].startswith(b"\xff\xd8\xff"))

    def test_update_applicant_profile_rejects_changing_admission_date(self):
        self.applicant.db_set("student_joining_date", "2026-01-10", update_modified=False)
        self.applicant.reload()

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.PermissionError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                student_joining_date="2026-02-10",
            )

    def test_update_applicant_health_vaccination_upload_attaches_with_persisted_profile_name(self):
        captured: dict = {}

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            drive_file_id = f"DRV-FILE-{frappe.generate_hash(length=6)}"
            return {
                "file": f"FILE-{frappe.generate_hash(length=8)}",
                "file_url": f"/private/files/health-proof-{frappe.generate_hash(length=6)}.png",
                "drive_file_id": drive_file_id,
                "canonical_ref": f"drv:{self.organization}:{drive_file_id}",
                "student_applicant": kwargs.get("student_applicant"),
                "applicant_health_profile": kwargs.get("applicant_health_profile"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.api.admissions_portal.admission_api.upload_applicant_health_vaccination_proof",
                side_effect=_capture_drive_upload,
            ),
            patch("ifitwala_ed.api.admissions_portal.materialize_health_review_assignments"),
        ):
            payload = update_applicant_health(
                student_applicant=self.applicant.name,
                blood_group="O Positive",
                allergies=True,
                food_allergies="No nuts",
                applicant_health_declared_complete=False,
                vaccinations=[
                    {
                        "vaccine_name": "MMR",
                        "date": "2020-03-04",
                        "vaccination_proof": "",
                        "additional_notes": "",
                        "vaccination_proof_content": self._tiny_png_base64(),
                        "vaccination_proof_file_name": "mmr-proof.png",
                    }
                ],
            )

        self.assertTrue(payload.get("ok"))
        self.assertIn("applicant_health_profile", captured)

        health_name = frappe.db.get_value(
            "Applicant Health Profile",
            {"student_applicant": self.applicant.name},
            "name",
        )
        self.assertTrue(bool(health_name))
        self.assertIsInstance(captured["applicant_health_profile"], str)
        self.assertEqual(captured["applicant_health_profile"], health_name)
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["vaccine_name"], "MMR")
        self.assertEqual(captured["date"], "2020-03-04")
        self.assertEqual(captured["row_index"], 0)
        self.assertEqual(captured["file_name"], "mmr-proof.png")
        self.assertEqual(captured["upload_source"], "SPA")

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
                "send_welcome_email": 0,
                "send_password_notification": 0,
                "roles": [{"role": "Admissions Applicant"}],
            }
        )
        user.flags.no_welcome_mail = True
        user.insert(ignore_permissions=True)
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
                "send_welcome_email": 0,
                "send_password_notification": 0,
                "roles": [{"role": "Admissions Family"}],
            }
        )
        user.flags.no_welcome_mail = True
        user.insert(ignore_permissions=True)
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
