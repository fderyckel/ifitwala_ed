# ifitwala_ed/api/test_admissions_portal.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.admissions_portal import (
    _portal_status_for,
    _read_only_for,
    _send_applicant_invite_email,
    get_invite_email_options,
    invite_applicant,
)


class TestAdmissionsPortalContracts(FrappeTestCase):
    def test_withdrawn_status_maps_to_portal_withdrawn(self):
        self.assertEqual(_portal_status_for("Withdrawn"), "Withdrawn")

    def test_withdrawn_status_is_read_only_with_reason(self):
        is_read_only, reason = _read_only_for("Withdrawn")
        self.assertTrue(is_read_only)
        self.assertTrue(bool(reason))


class TestInviteApplicant(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_admin_admissions_role("Admission Manager")
        frappe.clear_cache(user="Administrator")
        self.staff_user = self._create_admissions_staff_user()
        frappe.set_user(self.staff_user)
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant = self._create_applicant(self.organization, self.school)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

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
            }
        ).insert(ignore_permissions=True)
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
        ).insert(ignore_permissions=True)
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
