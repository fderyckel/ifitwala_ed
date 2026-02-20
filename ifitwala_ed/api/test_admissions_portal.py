# ifitwala_ed/api/test_admissions_portal.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.admissions_portal import (
    _portal_status_for,
    _read_only_for,
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
        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant = self._create_applicant(self.organization, self.school)

    def tearDown(self):
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_invite_applicant_creates_portal_user_and_marks_invited(self):
        email = f"applicant-{frappe.generate_hash(length=8)}@example.com"

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value="Administrator",
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email") as send_invite,
        ):
            payload = invite_applicant(student_applicant=self.applicant.name, email=email)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("user"), email)
        self.assertFalse(payload.get("resent"))
        self.assertEqual(send_invite.call_count, 1)

        self.applicant.reload()
        self.assertEqual(self.applicant.applicant_user, email)
        self.assertEqual(self.applicant.application_status, "Invited")
        self.assertTrue(bool(self.applicant.applicant_contact))
        self.assertEqual(self.applicant.portal_account_email, email)
        self.assertEqual(self.applicant.applicant_email, email)

        user_row = frappe.db.get_value("User", email, ["name", "enabled"], as_dict=True)
        self.assertTrue(bool(user_row))
        self.assertEqual(user_row.get("enabled"), 1)
        self._created.append(("User", email))

    def test_invite_applicant_resends_email_for_same_linked_user(self):
        email = f"applicant-{frappe.generate_hash(length=8)}@example.com"

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value="Administrator",
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
                return_value="Administrator",
            ),
            patch("ifitwala_ed.api.admissions_portal._send_applicant_invite_email") as send_invite,
        ):
            payload = invite_applicant(student_applicant=self.applicant.name, email=email)

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("user"), email)
        self.assertTrue(payload.get("resent"))
        self.assertEqual(send_invite.call_count, 1)

    def test_get_invite_email_options_includes_contact_emails(self):
        email = f"existing-{frappe.generate_hash(length=8)}@example.com"
        alt_email = f"alt-{frappe.generate_hash(length=8)}@example.com"
        contact = self._create_contact(primary_email=email, other_email=alt_email)

        self.applicant.flags.from_contact_sync = True
        self.applicant.applicant_contact = contact.name
        self.applicant.applicant_email = email
        self.applicant.save(ignore_permissions=True)

        with patch(
            "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
            return_value="Administrator",
        ):
            payload = get_invite_email_options(student_applicant=self.applicant.name)

        self.assertEqual(payload.get("contact"), contact.name)
        self.assertIn(email, payload.get("emails") or [])
        self.assertIn(alt_email, payload.get("emails") or [])

    def test_invite_applicant_rejects_email_linked_to_different_contact(self):
        applicant_contact = self._create_contact(primary_email=f"app-{frappe.generate_hash(length=8)}@example.com")
        other_contact_email = f"other-{frappe.generate_hash(length=8)}@example.com"
        self._create_contact(primary_email=other_contact_email)

        self.applicant.flags.from_contact_sync = True
        self.applicant.applicant_contact = applicant_contact.name
        self.applicant.applicant_email = frappe.db.get_value(
            "Contact Email", {"parent": applicant_contact.name, "is_primary": 1}, "email_id"
        )
        self.applicant.save(ignore_permissions=True)

        with (
            patch(
                "ifitwala_ed.api.admissions_portal.ensure_admissions_permission",
                return_value="Administrator",
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
                "abbr": f"SCH{frappe.generate_hash(length=4)}",
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
