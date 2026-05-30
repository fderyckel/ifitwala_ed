# ifitwala_ed/admission/api/test_portal_invites.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt


from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.api.portal.guardians import APPLICANT_CONTACT_GUARDIAN_ROW
from ifitwala_ed.admission.api.portal.invites import (
    _send_applicant_invite_email,
)
from ifitwala_ed.admission.api.portal.invites import (
    get_admissions_portal_invite_options_impl as get_admissions_portal_invite_options,
)
from ifitwala_ed.admission.api.portal.invites import (
    get_family_invite_options_impl as get_family_invite_options,
)
from ifitwala_ed.admission.api.portal.invites import (
    get_invite_email_options_impl as get_invite_email_options,
)
from ifitwala_ed.admission.api.portal.invites import (
    invite_applicant_impl as invite_applicant,
)
from ifitwala_ed.admission.api.portal.invites import (
    invite_family_collaborator_impl as invite_family_collaborator,
)
from ifitwala_ed.admission.api.portal_test_helpers import (
    _admission_settings_has_field,
    _insert_user_without_notifications,
    _policy_schema_available,
)
from ifitwala_ed.governance.policy_utils import ensure_policy_audience_records, institutional_policy_db_has_column


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
                "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email") as send_invite,
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
                "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email"),
        ):
            invite_applicant(student_applicant=self.applicant.name, email=email)
        self._created.append(("User", email))
        self.applicant.reload()
        self.assertTrue(bool(self.applicant.applicant_contact))
        self.assertEqual(self.applicant.portal_account_email, email)

        with (
            patch(
                "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email") as send_invite,
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
                "user_type": "Website User",
            }
        )
        user.flags.no_welcome_mail = True
        _insert_user_without_notifications(user)
        self._created.append(("User", user.name))

        with (
            patch(
                "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email", return_value=True),
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
                "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email", return_value=True),
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
                "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email", return_value=True),
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

        with patch("ifitwala_ed.admission.api.portal.invites.frappe.sendmail") as mocked_sendmail:
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
            "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
            return_value=self.staff_user,
        ):
            payload = get_invite_email_options(student_applicant=self.applicant.name)

        self.assertEqual(payload.get("contact"), contact.name)
        self.assertIn(email, payload.get("emails") or [])
        self.assertIn(alt_email, payload.get("emails") or [])

    def test_get_invite_email_options_rejects_out_of_scope_applicant(self):
        outside_organization = self._create_organization()
        outside_school = self._create_school(outside_organization)
        outside_applicant = self._create_applicant(outside_organization, outside_school)
        contact_email = f"outside-{frappe.generate_hash(length=8)}@example.com"
        contact = self._create_contact(primary_email=contact_email)
        outside_applicant.db_set("applicant_contact", contact.name, update_modified=False)

        with self.assertRaises(frappe.PermissionError):
            get_invite_email_options(student_applicant=outside_applicant.name)

    def test_invite_applicant_rejects_out_of_scope_applicant(self):
        outside_organization = self._create_organization()
        outside_school = self._create_school(outside_organization)
        outside_applicant = self._create_applicant(outside_organization, outside_school)
        invite_email = f"outside-invite-{frappe.generate_hash(length=8)}@example.com"

        with (
            patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email") as send_invite,
            self.assertRaises(frappe.PermissionError),
        ):
            invite_applicant(student_applicant=outside_applicant.name, email=invite_email)

        send_invite.assert_not_called()
        outside_applicant.reload()
        self.assertFalse(bool((outside_applicant.applicant_user or "").strip()))

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
                "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email"),
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
                "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
                return_value=self.staff_user,
            ),
            patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email", return_value=True),
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

    def test_family_invite_options_bootstrap_from_inquiry_contact_without_applicant_contact(self):
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")

        self._set_admissions_access_mode("Family Workspace")
        invite_email = f"father-{frappe.generate_hash(length=8)}@example.com"
        contact = self._create_contact(
            primary_email=invite_email,
            first_name="Father",
            last_name="Inquiry",
            phone="+14155550124",
        )
        inquiry = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Father",
                "last_name": "Inquiry",
                "email": invite_email,
                "phone_number": "+14155550124",
                "type_of_inquiry": "Admission",
                "organization": self.organization,
                "school": self.school,
                "contact": contact.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Inquiry", inquiry.name))
        self.applicant.db_set("inquiry", inquiry.name, update_modified=False)
        self.applicant.db_set("applicant_contact", "", update_modified=False)

        options = get_admissions_portal_invite_options(student_applicant=self.applicant.name)

        family_invite = options.get("family_invite") or {}
        guardians = family_invite.get("guardians") or []
        self.assertTrue(bool(family_invite.get("enabled")))
        self.assertEqual(len(guardians), 1)
        self.assertEqual(guardians[0].get("name"), APPLICANT_CONTACT_GUARDIAN_ROW)
        self.assertEqual(guardians[0].get("email"), invite_email)
        self.assertTrue(bool(guardians[0].get("bootstrap_from_applicant_contact")))

        self.applicant.reload()
        self.assertFalse(bool((self.applicant.applicant_contact or "").strip()))
        self.assertEqual(len(self.applicant.get("guardians") or []), 0)

    def test_invite_family_collaborator_bootstraps_guardian_row_from_inquiry_contact(self):
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")

        self._set_admissions_access_mode("Family Workspace")
        invite_email = f"family-bootstrap-{frappe.generate_hash(length=8)}@example.com"
        contact = self._create_contact(
            primary_email=invite_email,
            first_name="Father",
            last_name="Bootstrap",
            phone="+14155550125",
        )
        inquiry = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Father",
                "last_name": "Bootstrap",
                "email": invite_email,
                "phone_number": "+14155550125",
                "type_of_inquiry": "Admission",
                "organization": self.organization,
                "school": self.school,
                "contact": contact.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Inquiry", inquiry.name))
        self.applicant.db_set("inquiry", inquiry.name, update_modified=False)
        self.applicant.db_set("applicant_contact", "", update_modified=False)

        payload = invite_family_collaborator(
            student_applicant=self.applicant.name,
            guardian_row=APPLICANT_CONTACT_GUARDIAN_ROW,
            email=invite_email,
        )
        self._created.append(("User", invite_email))

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("user"), invite_email)

        self.applicant.reload()
        self.assertEqual(self.applicant.applicant_contact, contact.name)
        rows = self.applicant.get("guardians") or []
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.contact, contact.name)
        self.assertEqual(row.guardian_first_name, "Father")
        self.assertEqual(row.guardian_last_name, "Bootstrap")
        self.assertEqual(row.guardian_email, invite_email)
        self.assertEqual(row.guardian_mobile_phone, "+14155550125")
        self.assertEqual(int(row.use_applicant_contact or 0), 1)
        self.assertEqual(int(row.is_primary_guardian or 0), 1)
        self.assertEqual(int(row.can_consent or 0), 1)
        self.assertFalse(bool((row.guardian_image or "").strip()))
        self.assertTrue(bool((row.guardian or "").strip()))
        self.assertEqual((row.user or "").strip(), invite_email)
        self._created.append(("Guardian", row.guardian))

        self.assertTrue(
            bool(
                frappe.db.exists(
                    "Dynamic Link",
                    {
                        "parenttype": "Contact",
                        "parentfield": "links",
                        "parent": contact.name,
                        "link_doctype": "Student Applicant",
                        "link_name": self.applicant.name,
                    },
                )
            )
        )

    def test_family_invite_reuses_applicant_contact_for_existing_signer_row(self):
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")

        self._ensure_role("Admissions Applicant")
        self._set_admissions_access_mode("Family Workspace")
        invite_email = f"father-existing-{frappe.generate_hash(length=8)}@example.com"
        contact = self._create_contact(
            primary_email=invite_email,
            first_name="Marcus",
            last_name="Vance",
            phone="+14155550126",
        )
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": invite_email,
                "first_name": "Marcus",
                "last_name": "Vance",
                "enabled": 1,
                "roles": [{"role": "Admissions Applicant"}],
            }
        )
        user.flags.no_welcome_mail = True
        _insert_user_without_notifications(user)
        self._created.append(("User", user.name))

        self.applicant.db_set("applicant_contact", contact.name, update_modified=False)
        self.applicant.db_set("applicant_user", invite_email, update_modified=False)
        self.applicant.db_set("portal_account_email", invite_email, update_modified=False)
        self.applicant.append(
            "guardians",
            {
                "relationship": "Father",
                "can_consent": 1,
                "is_primary": 1,
                "is_primary_guardian": 1,
                "user": invite_email,
            },
        )
        self.applicant.save(ignore_permissions=True)
        guardian_row_name = self.applicant.get("guardians")[0].name

        with patch("ifitwala_ed.admission.api.portal.invites._send_applicant_invite_email", return_value=True):
            options = get_admissions_portal_invite_options(student_applicant=self.applicant.name)
            payload = invite_family_collaborator(
                student_applicant=self.applicant.name,
                guardian_row=guardian_row_name,
                email=invite_email,
            )

        family_rows = options.get("family_invite", {}).get("guardians") or []
        self.assertEqual(family_rows[0].get("email"), invite_email)
        self.assertTrue(bool(family_rows[0].get("eligible")))
        self.assertTrue(bool(family_rows[0].get("bootstrap_from_applicant_contact")))
        self.assertTrue(bool(payload.get("converted_applicant_login")))

        self.applicant.reload()
        self.assertFalse(bool((self.applicant.applicant_user or "").strip()))
        self.assertFalse(bool((self.applicant.portal_account_email or "").strip()))
        row = self.applicant.get("guardians")[0]
        self.assertEqual(row.contact, contact.name)
        self.assertEqual(row.guardian_first_name, "Marcus")
        self.assertEqual(row.guardian_last_name, "Vance")
        self.assertEqual(row.guardian_email, invite_email)
        self.assertEqual(row.guardian_mobile_phone, "+14155550126")
        self.assertEqual((row.user or "").strip(), invite_email)
        self._created.append(("Guardian", row.guardian))

        roles = set(frappe.get_roles(invite_email))
        self.assertIn("Admissions Family", roles)
        self.assertNotIn("Admissions Applicant", roles)

    def test_applicant_self_invite_blocks_family_acknowledgement_policy_in_single_mode(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for family acknowledgement tests.")
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")
        if not institutional_policy_db_has_column("admissions_acknowledgement_mode"):
            self.skipTest(
                "Institutional Policy.admissions_acknowledgement_mode is required for family acknowledgement tests."
            )

        self._set_admissions_access_mode("Single Applicant Workspace")
        self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            admissions_acknowledgement_mode="Family Acknowledgement",
        )

        with patch(
            "ifitwala_ed.admission.api.portal.invites.ensure_admissions_permission",
            return_value=self.staff_user,
        ):
            options = get_admissions_portal_invite_options(student_applicant=self.applicant.name)
            with self.assertRaises(frappe.ValidationError) as exc:
                invite_applicant(
                    student_applicant=self.applicant.name,
                    email=f"applicant-{frappe.generate_hash(length=8)}@example.com",
                )

        applicant_invite = options.get("applicant_invite") or {}
        family_invite = options.get("family_invite") or {}
        self.assertFalse(bool(applicant_invite.get("enabled")))
        self.assertIn("Family Acknowledgement", applicant_invite.get("disabled_reason") or "")
        self.assertFalse(bool(family_invite.get("enabled")))
        self.assertIn("Family Workspace", family_invite.get("disabled_reason") or "")
        self.assertIn("Family Acknowledgement", str(exc.exception))

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

    def _create_required_applicant_policy_version(
        self,
        *,
        organization: str,
        school: str,
        admissions_acknowledgement_mode: str,
    ) -> str:
        ensure_policy_audience_records()
        policy_payload = {
            "doctype": "Institutional Policy",
            "policy_key": f"invite_policy_{frappe.generate_hash(length=8)}",
            "policy_title": f"Invite Policy {frappe.generate_hash(length=6)}",
            "policy_category": "Admissions",
            "applies_to": [{"policy_audience": "Applicant"}],
            "organization": organization,
            "school": school,
            "is_active": 1,
        }
        if institutional_policy_db_has_column("admissions_acknowledgement_mode"):
            policy_payload["admissions_acknowledgement_mode"] = admissions_acknowledgement_mode

        policy = frappe.get_doc(policy_payload).insert(ignore_permissions=True)
        self._created.append(("Institutional Policy", policy.name))

        version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": policy.name,
                "version_label": "v1",
                "policy_text": "<p>Applicant family acknowledgement text.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Policy Version", version.name))
        return version.name

    def _create_contact(
        self,
        *,
        primary_email: str,
        other_email: str | None = None,
        first_name: str = "Portal",
        last_name: str | None = None,
        phone: str | None = None,
    ):
        doc = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": first_name,
                "last_name": last_name or f"Contact-{frappe.generate_hash(length=6)}",
                "email_ids": [{"email_id": primary_email, "is_primary": 1}],
            }
        )
        if other_email:
            doc.append("email_ids", {"email_id": other_email, "is_primary": 0})
        if phone:
            doc.mobile_no = phone
            doc.append("phone_nos", {"phone": phone, "is_primary_mobile_no": 1})
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
                "roles": [{"role": "Admission Manager"}],
            }
        )
        user.flags.no_welcome_mail = True
        _insert_user_without_notifications(user)
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
