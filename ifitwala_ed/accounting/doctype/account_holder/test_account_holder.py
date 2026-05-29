# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.account_holder_contacts import (
    create_account_holder_from_student_guardians,
    get_account_holder_billing_contact_summary,
    get_student_account_holder_guardian_proposal,
)

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestAccountHolder(IntegrationTestCase):
    """
    Integration tests for AccountHolder.
    Use this class for testing interactions between multiple components.
    """

    pass


class TestAccountHolderBillingContacts(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self._previous_user = frappe.session.user
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user(self._previous_user)
        super().tearDown()

    def _make_organization(self):
        previous_skip = getattr(frappe.flags, "skip_org_coa_setup", False)
        frappe.flags.skip_org_coa_setup = True
        try:
            doc = frappe.get_doc(
                {
                    "doctype": "Organization",
                    "organization_name": f"Billing Contact Org {frappe.generate_hash(length=6)}",
                    "abbr": f"BC{frappe.generate_hash(length=4)}",
                }
            )
            doc.insert(ignore_permissions=True)
            return doc
        finally:
            frappe.flags.skip_org_coa_setup = previous_skip

    def _make_school(self, organization):
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"Billing Contact School {frappe.generate_hash(length=6)}",
                "abbr": f"BS{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def _make_guardian(self, organization, *, first_name="Billing", relation_seed="Guardian", financial=0):
        seed = frappe.generate_hash(length=8)
        phone_suffix = "".join(str(ord(ch) % 10) for ch in seed[:6])
        doc = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": first_name,
                "guardian_last_name": f"{relation_seed}{seed}",
                "guardian_email": f"billing-guardian-{seed}@example.com",
                "guardian_mobile_phone": f"+1415{phone_suffix}",
                "organization": organization,
                "is_financial_guardian": financial,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def _make_student(self, school):
        seed = frappe.generate_hash(length=8)
        previous_migration = getattr(frappe.flags, "in_migration", False)
        frappe.flags.in_migration = True
        try:
            doc = frappe.get_doc(
                {
                    "doctype": "Student",
                    "student_first_name": "Billing",
                    "student_last_name": f"Student{seed}",
                    "student_email": f"billing-student-{seed}@example.com",
                    "anchor_school": school,
                }
            )
            doc.insert(ignore_permissions=True)
            return doc
        finally:
            frappe.flags.in_migration = previous_migration

    def test_student_guardian_action_creates_account_holder_and_billing_contact(self):
        organization = self._make_organization()
        school = self._make_school(organization.name)
        student = self._make_student(school.name)
        guardian = self._make_guardian(organization.name, financial=1)

        student.append("guardians", {"guardian": guardian.name, "relation": "Mother", "can_consent": 1})
        student.save(ignore_permissions=True)

        proposal = get_student_account_holder_guardian_proposal(student.name)
        self.assertTrue(proposal.get("can_create"))
        self.assertEqual(proposal.get("guardian_candidates")[0].get("guardian"), guardian.name)
        self.assertIn("****@", proposal.get("guardian_candidates")[0].get("email_masked"))

        result = create_account_holder_from_student_guardians(student.name, guardians=[guardian.name])
        student.reload()
        account_holder = frappe.get_doc("Account Holder", result["account_holder"]["name"])

        self.assertTrue(result.get("created"))
        self.assertEqual(student.account_holder, account_holder.name)
        self.assertEqual(account_holder.primary_email, guardian.guardian_email)
        self.assertEqual(account_holder.primary_phone, guardian.guardian_mobile_phone)
        self.assertEqual(len(account_holder.get("billing_contacts") or []), 1)
        self.assertEqual(account_holder.billing_contacts[0].guardian, guardian.name)
        self.assertEqual(account_holder.billing_contacts[0].source_student, student.name)

        contact_points = frappe.get_all(
            "Communication Contact Point",
            filters={
                "owner_doctype": "Guardian",
                "owner_name": guardian.name,
                "purpose": "billing",
                "school": school.name,
                "disabled": 0,
            },
            fields=["channel_type"],
            limit=0,
            ignore_permissions=True,
        )
        self.assertEqual({row["channel_type"] for row in contact_points}, {"email", "phone"})

        summary = get_account_holder_billing_contact_summary(account_holder.name)
        self.assertEqual(summary.get("contacts")[0].get("guardian"), guardian.name)
        self.assertIn("****@", summary.get("contacts")[0].get("email_masked"))

    def test_student_guardian_action_reuses_existing_account_holder_without_duplicate_contacts(self):
        organization = self._make_organization()
        school = self._make_school(organization.name)
        student = self._make_student(school.name)
        guardian = self._make_guardian(organization.name, financial=1)

        student.append("guardians", {"guardian": guardian.name, "relation": "Father", "can_consent": 1})
        student.save(ignore_permissions=True)

        first = create_account_holder_from_student_guardians(student.name, guardians=[guardian.name])
        second = create_account_holder_from_student_guardians(student.name, guardians=[guardian.name])
        account_holder = frappe.get_doc("Account Holder", first["account_holder"]["name"])

        self.assertFalse(second.get("created"))
        self.assertEqual(second.get("billing_contacts_added"), 0)
        self.assertEqual(len(account_holder.get("billing_contacts") or []), 1)

    def test_guardian_update_refreshes_primary_account_holder_contact_snapshot(self):
        organization = self._make_organization()
        school = self._make_school(organization.name)
        student = self._make_student(school.name)
        guardian = self._make_guardian(organization.name, financial=1)

        student.append("guardians", {"guardian": guardian.name, "relation": "Mother", "can_consent": 1})
        student.save(ignore_permissions=True)
        result = create_account_holder_from_student_guardians(student.name, guardians=[guardian.name])

        guardian.guardian_mobile_phone = "+14155559999"
        guardian.save(ignore_permissions=True)

        account_holder = frappe.get_doc("Account Holder", result["account_holder"]["name"])
        self.assertEqual(account_holder.primary_phone, "+14155559999")
