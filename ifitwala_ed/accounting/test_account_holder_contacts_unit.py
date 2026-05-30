from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _Row(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __setattr__(self, name, value):
        self[name] = value


class _Student:
    def __init__(self):
        self.name = "STU-1"
        self.student_full_name = "Student One"
        self.anchor_school = "SCH-1"
        self.account_holder = ""
        self.guardians = [
            _Row({"guardian": "GRD-1", "relation": "Mother", "can_consent": 1, "idx": 1}),
            _Row({"guardian": "GRD-2", "relation": "Father", "can_consent": 1, "idx": 2}),
        ]

    def get(self, fieldname):
        return getattr(self, fieldname)


class _AccountHolder:
    name = "AH-1"
    organization = "ORG-1"
    primary_email = "payer@example.com"
    primary_phone = "+14155550100"

    def __init__(self):
        self.billing_contacts = [
            _Row(
                {
                    "name": "AHBC-1",
                    "guardian": "GRD-1",
                    "guardian_name": "Mother Guardian",
                    "relation": "Mother",
                    "source_student": "STU-1",
                    "is_primary": 1,
                    "receives_billing_follow_up": 1,
                }
            )
        ]

    def get(self, fieldname):
        return getattr(self, fieldname)


def _contact_privacy_stub() -> ModuleType:
    contact_privacy = ModuleType("ifitwala_ed.contacts.contact_privacy")
    contact_privacy.mask_email = lambda value: "m****@example.com" if value else ""
    contact_privacy.mask_phone = lambda value: "*** *** 1234" if value else ""
    contact_privacy.get_masked_contact_points_for_owner = lambda **kwargs: []
    contact_privacy.get_raw_contact_point_value = lambda **kwargs: ""
    contact_privacy.sync_guardian_contact_points = lambda *args, **kwargs: []
    return contact_privacy


def _account_holder_utils_stub() -> ModuleType:
    account_holder_utils = ModuleType("ifitwala_ed.accounting.account_holder_utils")
    account_holder_utils.get_school_organization = lambda school: "ORG-1" if school == "SCH-1" else ""
    return account_holder_utils


class TestAccountHolderContactsUnit(TestCase):
    def test_account_holder_raw_contact_fields_are_not_generic_export_surfaces(self):
        metadata_path = Path(__file__).parent / "doctype" / "account_holder" / "account_holder.json"
        metadata = json.loads(metadata_path.read_text())
        fields = {field["fieldname"]: field for field in metadata["fields"] if field.get("fieldname")}

        for fieldname in ("primary_email", "primary_phone"):
            field = fields[fieldname]
            self.assertNotEqual(field.get("in_list_view"), 1)
            self.assertEqual(field.get("report_hide"), 1)
            self.assertEqual(field.get("print_hide"), 1)
            self.assertEqual(field.get("no_copy"), 1)
            self.assertEqual(field.get("hidden"), 1)
        self.assertEqual(field.get("permlevel"), 1)

        self.assertEqual(metadata.get("index_web_pages_for_search"), 0)
        for permission in metadata["permissions"]:
            self.assertNotEqual(permission.get("export"), 1, permission.get("role"))

    def test_account_holder_summary_shows_raw_values_only_to_finance_actor(self):
        contact_privacy = ModuleType("ifitwala_ed.contacts.contact_privacy")
        contact_privacy.mask_email = lambda value: "m****@example.com" if value else ""
        contact_privacy.mask_phone = lambda value: "*** *** 0100" if value else ""
        contact_privacy.sync_guardian_contact_points = lambda *args, **kwargs: []
        raw_reads: list[dict] = []

        def fake_masked_points(**kwargs):
            channel_type = kwargs.get("channel_type")
            rows = {
                "email": {
                    "name": "CCP-EMAIL",
                    "channel_type": "email",
                    "masked_display": "m****@example.com",
                    "is_primary": 1,
                },
                "phone": {
                    "name": "CCP-PHONE",
                    "channel_type": "phone",
                    "masked_display": "*** *** 0100",
                    "is_primary": 1,
                },
            }
            if channel_type:
                return [rows[channel_type]]
            return list(rows.values())

        def fake_raw_contact_point_value(**kwargs):
            raw_reads.append(kwargs)
            if kwargs["contact_point"] == "CCP-EMAIL":
                return "mother@example.com"
            if kwargs["contact_point"] == "CCP-PHONE":
                return "+14155550100"
            return ""

        contact_privacy.get_masked_contact_points_for_owner = fake_masked_points
        contact_privacy.get_raw_contact_point_value = fake_raw_contact_point_value

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.accounting.account_holder_utils": _account_holder_utils_stub(),
                "ifitwala_ed.contacts.contact_privacy": contact_privacy,
            }
        ) as frappe:
            frappe_utils = sys.modules["frappe.utils"]
            frappe_utils.cint = lambda value=0: int(value or 0)

            account_holder = _AccountHolder()
            frappe.session.user = "finance@example.com"
            frappe.db.exists = lambda doctype, name=None: doctype == "Account Holder" and name == "AH-1"
            frappe.get_roles = lambda user=None: ["Accounts User"]
            frappe.has_permission = lambda *args, **kwargs: True

            def fake_get_doc(doctype, name=None):
                if doctype == "Account Holder":
                    return account_holder
                if doctype == "Organization":
                    return SimpleNamespace(name=name)
                raise AssertionError(doctype)

            def fake_get_all(doctype, **kwargs):
                if doctype == "Guardian":
                    return [
                        {
                            "name": "GRD-1",
                            "guardian_full_name": "Mother Guardian",
                            "guardian_first_name": "Mother",
                            "guardian_last_name": "Guardian",
                            "guardian_email": "mother@example.com",
                            "guardian_mobile_phone": "+14155550100",
                        }
                    ]
                if doctype == "Student":
                    return [{"name": "STU-1", "student_full_name": "Student One", "anchor_school": "SCH-1"}]
                return []

            frappe.get_doc = fake_get_doc
            frappe.get_all = fake_get_all
            service = import_fresh("ifitwala_ed.accounting.account_holder_contacts")

            finance_summary = service.get_account_holder_billing_contact_summary("AH-1")
            frappe.get_roles = lambda user=None: ["Academic Staff"]
            non_finance_summary = service.get_account_holder_billing_contact_summary("AH-1")

        finance_contact = finance_summary["contacts"][0]
        self.assertTrue(finance_summary["shows_raw_contact_values"])
        self.assertEqual(finance_contact["email_display"], "mother@example.com")
        self.assertEqual(finance_contact["phone_display"], "+14155550100")
        self.assertTrue(finance_contact["email_is_raw"])
        self.assertTrue(finance_contact["phone_is_raw"])
        self.assertEqual(
            [(row["contact_point"], row["purpose"], row["workflow"]) for row in raw_reads],
            [
                ("CCP-EMAIL", "billing", "account_holder_billing_follow_up"),
                ("CCP-PHONE", "billing", "account_holder_billing_follow_up"),
            ],
        )

        non_finance_contact = non_finance_summary["contacts"][0]
        self.assertFalse(non_finance_summary["shows_raw_contact_values"])
        self.assertEqual(non_finance_contact["email_display"], "m****@example.com")
        self.assertEqual(non_finance_contact["phone_display"], "*** *** 0100")
        self.assertFalse(non_finance_contact["email_is_raw"])
        self.assertFalse(non_finance_contact["phone_is_raw"])

    def test_student_guardian_proposal_prefers_financial_guardian_and_masks_values(self):
        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.accounting.account_holder_utils": _account_holder_utils_stub(),
                "ifitwala_ed.contacts.contact_privacy": _contact_privacy_stub(),
            }
        ) as frappe:
            frappe_utils = sys.modules["frappe.utils"]
            frappe_utils.cint = lambda value=0: int(value or 0)

            student = _Student()
            frappe.db.exists = lambda doctype, name=None: doctype == "Student" and name == "STU-1"
            frappe.get_doc = lambda doctype, name=None: student
            frappe.has_permission = lambda *args, **kwargs: True
            frappe.get_all = lambda doctype, **kwargs: (
                [
                    {
                        "name": "GRD-1",
                        "guardian_full_name": "Mother Guardian",
                        "guardian_first_name": "Mother",
                        "guardian_last_name": "Guardian",
                        "guardian_email": "mother@example.com",
                        "guardian_mobile_phone": "+14155551234",
                        "organization": "ORG-1",
                        "is_primary_guardian": 0,
                        "is_financial_guardian": 0,
                    },
                    {
                        "name": "GRD-2",
                        "guardian_full_name": "Father Guardian",
                        "guardian_first_name": "Father",
                        "guardian_last_name": "Guardian",
                        "guardian_email": "father@example.com",
                        "guardian_mobile_phone": "+14155559876",
                        "organization": "ORG-1",
                        "is_primary_guardian": 0,
                        "is_financial_guardian": 1,
                    },
                ]
                if doctype == "Guardian"
                else []
            )

            service = import_fresh("ifitwala_ed.accounting.account_holder_contacts")
            proposal = service.get_student_account_holder_guardian_proposal("STU-1")

        self.assertTrue(proposal["can_create"])
        self.assertEqual(proposal["organization"], "ORG-1")
        self.assertEqual(proposal["guardian_candidates"][0]["guardian"], "GRD-2")
        self.assertEqual(proposal["guardian_candidates"][0]["recommended"], 1)
        self.assertEqual(proposal["guardian_candidates"][0]["email_masked"], "m****@example.com")
        self.assertNotIn("father@example.com", str(proposal))
