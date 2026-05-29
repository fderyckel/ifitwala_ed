from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
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
