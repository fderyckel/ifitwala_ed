# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.governance.policy_utils import ensure_policy_applies_to_storage, ensure_policy_audience_records
from ifitwala_ed.tests.factories.organization import make_organization
from ifitwala_ed.tests.factories.users import make_user


class TestInstitutionalPolicy(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        ensure_policy_audience_records()
        self.created: list[tuple[str, str]] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self.created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def test_insert_normalizes_multi_audience_applies_to(self):
        organization = make_organization(prefix="IP Multi")
        self.created.append(("Organization", organization.name))

        policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"multi_audience_{frappe.generate_hash(length=6)}",
                "policy_title": f"Multi Audience {frappe.generate_hash(length=6)}",
                "policy_category": "Admissions",
                "applies_to": [
                    {"policy_audience": "Guardian"},
                    {"policy_audience": "Student"},
                ],
                "organization": organization.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", policy.name))

        self.assertEqual(
            [row.policy_audience for row in policy.applies_to],
            ["Guardian", "Student"],
        )

    def test_insert_rejects_unknown_applies_to_values(self):
        organization = make_organization(prefix="IP Invalid")
        self.created.append(("Organization", organization.name))

        policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"invalid_audience_{frappe.generate_hash(length=6)}",
                "policy_title": f"Invalid Audience {frappe.generate_hash(length=6)}",
                "policy_category": "Admissions",
                "applies_to": [
                    {"policy_audience": "Guardian"},
                    {"policy_audience": "Unknown"},
                ],
                "organization": organization.name,
                "is_active": 1,
            }
        )

        with self.assertRaises(frappe.ValidationError):
            policy.insert(ignore_permissions=True)

    def test_schema_check_rejects_missing_child_storage_even_when_meta_has_field(self):
        with (
            patch("ifitwala_ed.governance.policy_utils.frappe.db.table_exists", return_value=False),
            patch(
                "ifitwala_ed.governance.policy_utils.frappe.get_meta",
                return_value=type(
                    "Meta",
                    (),
                    {
                        "has_field": lambda self, fieldname: fieldname == "applies_to",
                        "get_field": lambda self, fieldname: type(
                            "Field",
                            (),
                            {"fieldtype": "Table MultiSelect", "options": "Institutional Policy Audience"},
                        )(),
                    },
                )(),
            ),
        ):
            result = ensure_policy_applies_to_storage(caller="test")

        self.assertFalse(result.get("ok"))
        self.assertIn("missing", (result.get("message") or "").lower())

    def test_save_explains_organization_transfer_is_blocked(self):
        parent_org = self._make_organization("Policy Parent", is_group=1)
        child_org = self._make_organization("Policy Child", parent=parent_org)
        policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"org_transfer_{frappe.generate_hash(length=6)}",
                "policy_title": f"Org Transfer {frappe.generate_hash(length=6)}",
                "policy_category": "Operations",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": parent_org,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", policy.name))

        user = make_user(
            email=f"policy-hr-{frappe.generate_hash(length=8)}@ifitwala.test",
            roles=["HR Manager"],
        )
        self.created.append(("User", user.name))
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Policy",
                "employee_last_name": f"HR-{frappe.generate_hash(length=5)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user.name,
                "date_of_joining": nowdate(),
                "employment_status": "Active",
                "organization": parent_org,
                "user_id": user.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee", employee.name))

        frappe.set_user(user.name)
        policy.reload()
        policy.organization = child_org

        with self.assertRaisesRegex(frappe.PermissionError, "Organization cannot be changed after creation"):
            policy.save()

    def test_parent_org_hr_manager_can_create_descendant_org_policy(self):
        parent_org = self._make_organization("Policy Parent", is_group=1)
        child_org = self._make_organization("Policy Child", parent=parent_org)
        child_school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"Policy School-{frappe.generate_hash(length=8)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": child_org,
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("School", child_school.name))

        user = self._make_policy_admin_user(parent_org, role="HR Manager", prefix="child-policy-hr")

        frappe.set_user(user)
        policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"descendant_org_{frappe.generate_hash(length=6)}",
                "policy_title": f"Descendant Org {frappe.generate_hash(length=6)}",
                "policy_category": "Academic",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": child_org,
                "school": child_school.name,
                "is_active": 1,
            }
        ).insert()
        self.created.append(("Institutional Policy", policy.name))

        self.assertEqual(policy.organization, child_org)
        self.assertEqual(policy.school, child_school.name)

    def test_insert_rejects_school_outside_policy_organization_lineage(self):
        parent_org = self._make_organization("Policy Parent", is_group=1)
        unrelated_org = self._make_organization("Policy Unrelated", is_group=1)
        child_school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"Policy Child Scope-{frappe.generate_hash(length=8)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": unrelated_org,
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("School", child_school.name))

        policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"org_school_mismatch_{frappe.generate_hash(length=6)}",
                "policy_title": f"Org School Mismatch {frappe.generate_hash(length=6)}",
                "policy_category": "Academic",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": parent_org,
                "school": child_school.name,
                "is_active": 1,
            }
        )

        with self.assertRaisesRegex(frappe.ValidationError, "must belong to the selected Organization"):
            policy.insert(ignore_permissions=True)

    def _make_policy_admin_user(self, organization: str, *, role: str, prefix: str) -> str:
        user = make_user(
            email=f"{prefix}-{frappe.generate_hash(length=8)}@ifitwala.test",
            roles=[role],
        )
        self.created.append(("User", user.name))
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Policy",
                "employee_last_name": f"{prefix}-{frappe.generate_hash(length=5)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user.name,
                "date_of_joining": nowdate(),
                "employment_status": "Active",
                "organization": organization,
                "user_id": user.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee", employee.name))
        return user.name

    def _make_organization(self, prefix: str, parent: str | None = None, is_group: int = 0) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix}-{frappe.generate_hash(length=8)}",
                "abbr": f"O{frappe.generate_hash(length=5)}",
                "is_group": int(is_group),
                "parent_organization": parent,
            }
        )
        doc.insert(ignore_permissions=True)
        self.created.append(("Organization", doc.name))
        return doc.name
