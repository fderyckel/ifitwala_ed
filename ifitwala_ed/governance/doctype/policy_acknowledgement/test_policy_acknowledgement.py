# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt
# ifitwala_ed/governance/doctype/policy_acknowledgement/test_policy_acknowledgement.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.governance.doctype.policy_acknowledgement import policy_acknowledgement as policy_ack_controller
from ifitwala_ed.governance.policy_utils import ensure_policy_audience_records
from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.tests.factories.users import make_user


class TestPolicyAcknowledgement(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        ensure_policy_audience_records()
        self.created: list[tuple[str, str]] = []

        self.organization = make_organization(prefix="PA Org")
        self.created.append(("Organization", self.organization.name))
        self.school = make_school(self.organization.name, prefix="PA School")
        self.created.append(("School", self.school.name))

        self.staff_user = make_user(roles=["Academic Staff"])
        self.created.append(("User", self.staff_user.name))
        self.employee = self._make_employee(self.staff_user.name)

        self.policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"policy_ack_{frappe.generate_hash(length=8)}",
                "policy_title": "Policy Acknowledgement Lifecycle",
                "policy_category": "Employment",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": self.organization.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", self.policy.name))

        self.policy_version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": self.policy.name,
                "version_label": "v1",
                "policy_text": "<p>Immutable acknowledgement policy text.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", self.policy_version.name))

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self.created):
            self._delete_created_doc(doctype, name)
        super().tearDown()

    def _delete_created_doc(self, doctype: str, name: str):
        if not frappe.db.exists(doctype, name):
            return
        if doctype == "Policy Acknowledgement":
            frappe.db.delete("Policy Acknowledgement", {"name": name})
            return
        frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def _make_employee(self, user: str):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Policy",
                "employee_last_name": f"Ack-{frappe.generate_hash(length=6)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user,
                "date_of_joining": nowdate(),
                "employment_status": "Active",
                "organization": self.organization.name,
                "school": self.school.name,
                "user_id": user,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee", employee.name))
        return employee

    def _insert_staff_ack(self):
        frappe.set_user(self.staff_user.name)
        ack = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": self.policy_version.name,
                "acknowledged_by": self.staff_user.name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": self.employee.name,
            }
        ).insert(ignore_permissions=True)
        frappe.set_user("Administrator")
        self.created.append(("Policy Acknowledgement", ack.name))
        return ack

    def test_acknowledgement_auto_submits_on_insert(self):
        ack = self._insert_staff_ack()
        self.assertEqual(int(ack.docstatus or 0), 1)
        self.assertTrue(bool(ack.acknowledged_at))

    def test_submitted_acknowledgement_cannot_be_edited(self):
        ack = self._insert_staff_ack()
        ack.context_name = self.employee.name

        with self.assertRaises(frappe.ValidationError):
            ack.save(ignore_permissions=True)

    def test_submitted_acknowledgement_cannot_be_cancelled(self):
        ack = self._insert_staff_ack()
        with self.assertRaises(frappe.ValidationError):
            ack.cancel()

    def test_duplicate_acknowledgement_still_rejected(self):
        self._insert_staff_ack()

        frappe.set_user(self.staff_user.name)
        duplicate = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": self.policy_version.name,
                "acknowledged_by": self.staff_user.name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": self.employee.name,
            }
        )
        with self.assertRaises(frappe.ValidationError):
            duplicate.insert(ignore_permissions=True)
        frappe.set_user("Administrator")

    def test_populate_policy_acknowledgement_evidence_records_clause_snapshot(self):
        self.policy_version.db_set("is_active", 0, update_modified=False)
        version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": self.policy.name,
                "version_label": "v2",
                "based_on_version": self.policy_version.name,
                "change_summary": "Added acknowledgement clauses.",
                "policy_text": "<p>Immutable acknowledgement policy text updated.</p>",
                "acknowledgement_clauses": [
                    {"clause_text": "I have read the handbook.", "is_required": 1},
                    {"clause_text": "I agree to optional reminders.", "is_required": 0},
                ],
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", version.name))

        ack = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": version.name,
                "acknowledged_by": self.staff_user.name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": self.employee.name,
            }
        )
        clause_name = version.acknowledgement_clauses[0].name
        policy_ack_controller.populate_policy_acknowledgement_evidence(
            ack,
            typed_signature_name="Policy Ack",
            attestation_confirmed=1,
            checked_clause_names=[clause_name],
        )

        snapshot = frappe.parse_json(ack.acknowledgement_clause_snapshot)
        self.assertEqual(ack.typed_signature_name, "Policy Ack")
        self.assertEqual(int(ack.attestation_confirmed or 0), 1)
        self.assertEqual(len(snapshot), 2)
        self.assertTrue(bool(snapshot[0].get("is_checked")))
        self.assertFalse(bool(snapshot[1].get("is_checked")))

    def test_guardian_context_organizations_include_student_applicant_links(self):
        doc = policy_ack_controller.PolicyAcknowledgement.__new__(policy_ack_controller.PolicyAcknowledgement)
        doc.context_doctype = "Guardian"
        doc.context_name = "GUARD-1"

        def fake_get_all(doctype, **kwargs):
            if doctype == "Student Guardian":
                return []
            if doctype == "Student Applicant Guardian":
                return ["APPL-1", "APPL-2"]
            if doctype == "Student Applicant":
                return ["ORG-1", "ORG-1", "ORG-2"]
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        with (
            patch.object(doc, "_organizations_for_students", return_value=[]),
            patch(
                "ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement.frappe.get_all",
                side_effect=fake_get_all,
            ),
        ):
            orgs = doc._resolve_context_organizations()

        self.assertEqual(orgs, ["ORG-1", "ORG-2"])

    def test_validate_context_allows_guardian_acknowledgement_on_student_context(self):
        doc = policy_ack_controller.PolicyAcknowledgement.__new__(policy_ack_controller.PolicyAcknowledgement)
        doc.acknowledged_for = "Guardian"
        doc.context_doctype = "Student"
        doc.context_name = "STU-0001"

        def fake_exists(doctype, name=None):
            if doctype == "DocType":
                return name == "Student"
            if doctype == "Student":
                return name == "STU-0001"
            raise AssertionError(f"Unexpected exists lookup: {doctype} {name}")

        with (
            patch.object(policy_ack_controller.frappe.db, "exists", side_effect=fake_exists),
            patch.object(doc, "_validate_policy_scope_for_context"),
        ):
            doc._validate_context()

    def test_guardian_role_validation_allows_student_context_when_signer_authorized(self):
        doc = policy_ack_controller.PolicyAcknowledgement.__new__(policy_ack_controller.PolicyAcknowledgement)
        doc.acknowledged_for = "Guardian"
        doc.context_doctype = "Student"
        doc.context_name = "STU-0001"

        with (
            patch(
                "ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement.has_guardian_role",
                return_value=True,
            ),
            patch(
                "ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement.has_admissions_family_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement.get_guardian_names_for_user",
                return_value=["GUARD-PRIMARY"],
            ),
            patch.object(doc, "_guardian_name_for_user", return_value="GUARD-PRIMARY"),
            patch.object(doc, "_guardian_linked_to_student", return_value=True),
        ):
            self.assertIsNone(doc._role_validation_error())

    def test_has_permission_rejects_non_primary_guardian_self_context(self):
        doc = frappe._dict(
            policy_version=self.policy_version.name,
            acknowledged_by="other@example.com",
            context_doctype="Guardian",
            context_name="GUARD-SECONDARY",
        )

        with (
            patch(
                "ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement.is_system_manager",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement.frappe.get_roles",
                return_value=["Guardian"],
            ),
            patch(
                "ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement._guardian_name_for_user",
                return_value="GUARD-SECONDARY",
            ),
            patch(
                "ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement._guardian_has_primary_signer_authority",
                return_value=False,
            ),
        ):
            allowed = policy_ack_controller.has_permission(doc, user="guardian@example.com")

        self.assertFalse(allowed)

    def test_on_doctype_update_adds_required_indexes(self):
        with (
            patch.object(policy_ack_controller.frappe.db, "add_unique") as add_unique,
            patch.object(policy_ack_controller.frappe.db, "add_index") as add_index,
        ):
            policy_ack_controller.on_doctype_update()

        add_unique.assert_called_once_with(
            "Policy Acknowledgement",
            ["policy_version", "acknowledged_by", "context_doctype", "context_name"],
            constraint_name=policy_ack_controller.POLICY_ACK_CONTEXT_UNIQUE_CONSTRAINT,
        )
        add_index.assert_called_once_with(
            "Policy Acknowledgement",
            ["policy_version", "acknowledged_for", "context_doctype", "context_name", "docstatus"],
            index_name="idx_policy_ack_audience_context_status",
        )
