# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/setup/doctype/org_communication/test_org_communication.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.doctype.org_communication import org_communication as org_communication_controller


class TestOrgCommunication(FrappeTestCase):
    def test_resolve_user_base_org_uses_user_default_only(self):
        with patch(
            "ifitwala_ed.setup.doctype.org_communication.org_communication._get_user_default_from_db",
            return_value="ORG-ROOT",
        ):
            self.assertEqual(org_communication_controller._resolve_user_base_org("staff@example.com"), "ORG-ROOT")

        with patch(
            "ifitwala_ed.setup.doctype.org_communication.org_communication._get_user_default_from_db",
            return_value=None,
        ):
            self.assertIsNone(org_communication_controller._resolve_user_base_org("staff@example.com"))

    def test_get_allowed_schools_prefers_default_school_scope(self):
        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=("SCH-ROOT", ["SCH-ROOT", "SCH-CHILD"]),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_org_scope_schools_for_user",
                return_value=["SCH-ORG"],
            ) as org_scope_schools,
        ):
            schools = org_communication_controller._get_allowed_schools_for_user("staff@example.com")

        self.assertEqual(schools, ["SCH-ROOT", "SCH-CHILD"])
        org_scope_schools.assert_not_called()

    def test_get_allowed_schools_falls_back_to_org_scope_without_default_school(self):
        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=(None, []),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_org_scope_schools_for_user",
                return_value=["SCH-ORG-A", "SCH-ORG-B"],
            ),
        ):
            schools = org_communication_controller._get_allowed_schools_for_user("staff@example.com")

        self.assertEqual(schools, ["SCH-ORG-A", "SCH-ORG-B"])

    def test_validate_non_privileged_without_default_school_accepts_org_scoped_school(self):
        doc = frappe._dict(school="SCH-ORG-A")

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=(None, []),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_allowed_schools_for_user",
                return_value=["SCH-ORG-A", "SCH-ORG-B"],
            ),
        ):
            org_communication_controller.OrgCommunication._validate_and_enforce_issuing_school_scope(doc)

        self.assertEqual(doc.school, "SCH-ORG-A")

    def test_validate_non_privileged_without_default_school_rejects_out_of_scope_school(self):
        doc = frappe._dict(school="SCH-OTHER")

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=(None, []),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_allowed_schools_for_user",
                return_value=["SCH-ORG-A", "SCH-ORG-B"],
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                org_communication_controller.OrgCommunication._validate_and_enforce_issuing_school_scope(doc)

    def test_context_uses_org_scope_schools_when_default_school_missing(self):
        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=(None, []),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_org_scope_schools_for_user",
                return_value=["SCH-ORG-A"],
            ),
        ):
            ctx = org_communication_controller.get_org_communication_context()

        self.assertEqual(ctx.get("default_school"), None)
        self.assertEqual(ctx.get("allowed_schools"), ["SCH-ORG-A"])
        self.assertEqual(ctx.get("lock_to_default_school"), False)
        self.assertEqual(ctx.get("can_select_school"), True)
