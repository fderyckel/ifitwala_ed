from __future__ import annotations
import __future__

import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import stubbed_frappe


@contextmanager
def _guardian_module():
    frappe_contacts = ModuleType("frappe.contacts")
    frappe_contacts_address = ModuleType("frappe.contacts.address_and_contact")
    frappe_contacts_address.load_address_and_contact = lambda doc: None
    frappe_contacts.address_and_contact = frappe_contacts_address

    account_holder_utils = ModuleType("ifitwala_ed.accounting.account_holder_utils")
    account_holder_utils.get_school_organization = lambda school_name: None

    routing_policy = ModuleType("ifitwala_ed.routing.policy")
    routing_policy.has_staff_portal_access = lambda user=None, roles=None: False

    with stubbed_frappe(
        extra_modules={
            "frappe.contacts": frappe_contacts,
            "frappe.contacts.address_and_contact": frappe_contacts_address,
            "ifitwala_ed.accounting.account_holder_utils": account_holder_utils,
            "ifitwala_ed.routing.policy": routing_policy,
        }
    ) as frappe:
        frappe_utils = sys.modules["frappe.utils"]
        frappe_utils.get_link_to_form = lambda doctype, name: f"{doctype}:{name}"

        frappe.clear_cache = lambda *args, **kwargs: None
        frappe.log_error = lambda *args, **kwargs: None
        frappe.get_traceback = lambda: "traceback"
        frappe.msgprint = lambda *args, **kwargs: None
        frappe.flags = SimpleNamespace(skip_contact_to_guardian_sync=False)
        frappe.db.exists = lambda *args, **kwargs: False
        frappe.db.get_value = lambda *args, **kwargs: None

        module = ModuleType("ifitwala_ed.students.doctype.guardian.guardian")
        module.__file__ = str(Path(__file__).with_name("guardian.py"))
        module.__package__ = "ifitwala_ed.students.doctype.guardian"

        source = Path(module.__file__).read_text(encoding="utf-8")
        code = compile(
            source,
            module.__file__,
            "exec",
            flags=__future__.annotations.compiler_flag,
            dont_inherit=True,
        )
        exec(code, module.__dict__)

        yield module


class TestGuardianUnit(TestCase):
    def test_create_guardian_user_builds_silent_website_user(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.name = "GRD-0001"
            guardian.guardian_email = "guardian@example.com"
            guardian.guardian_first_name = "Guardian"
            guardian.guardian_last_name = "User"
            guardian.guardian_mobile_phone = "5550000001"
            guardian.user = None
            guardian.db_set = lambda fieldname, value, update_modified=False: setattr(guardian, fieldname, value)

            captured = {}
            fake_user = SimpleNamespace(
                name="guardian@example.com",
                flags=SimpleNamespace(ignore_permissions=False, no_welcome_mail=False),
            )

            def fake_insert(ignore_permissions=True):
                captured["skip_user_contact_sync_during_insert"] = guardian_module.frappe.flags.skip_user_contact_sync
                return fake_user

            fake_user.insert = fake_insert

            guardian_module.frappe.db.exists = lambda doctype, name=None: False
            guardian_module.frappe.db.set_value = lambda *args, **kwargs: None

            def fake_get_doc(payload):
                captured["payload"] = payload
                return fake_user

            guardian_module.frappe.get_doc = fake_get_doc

            user_name = guardian.create_guardian_user()

        self.assertEqual(user_name, "guardian@example.com")
        self.assertEqual(captured["payload"]["send_welcome_email"], 0)
        self.assertNotIn("send_password_notification", captured["payload"])
        self.assertEqual(captured["payload"]["user_type"], "Website User")
        self.assertTrue(captured["skip_user_contact_sync_during_insert"])
        self.assertFalse(guardian_module.frappe.flags.skip_user_contact_sync)
        self.assertTrue(fake_user.flags.ignore_permissions)
        self.assertTrue(fake_user.flags.no_welcome_mail)
        self.assertEqual(guardian.user, "guardian@example.com")

    def test_after_insert_only_updates_portal_routing(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.user = "guardian@example.com"

            with patch.object(guardian, "_ensure_guardian_portal_routing") as ensure_portal_routing:
                guardian.after_insert()

        self.assertFalse(hasattr(guardian_module.Guardian, "_get_or_create_contact"))
        self.assertFalse(hasattr(guardian_module.Guardian, "_ensure_contact_link"))
        ensure_portal_routing.assert_called_once_with("guardian@example.com")

    def test_on_update_does_not_self_heal_missing_contact_link(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.user = "guardian@example.com"

            with (
                patch.object(guardian, "_has_user_changed", return_value=False),
                patch.object(guardian, "_has_contact_point_data_changed", return_value=False),
                patch.object(guardian, "_has_billing_contact_data_changed", return_value=False),
                patch.object(guardian, "_ensure_guardian_portal_routing") as ensure_portal_routing,
                patch.object(guardian, "sync_contact_points_for_linked_students") as sync_contact_points,
                patch.object(guardian, "sync_account_holder_billing_contacts") as sync_billing_contacts,
            ):
                guardian.on_update()

        ensure_portal_routing.assert_not_called()
        sync_contact_points.assert_not_called()
        sync_billing_contacts.assert_not_called()

    def test_on_update_still_updates_portal_routing_when_user_changes(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.user = "guardian@example.com"

            with (
                patch.object(guardian, "_has_user_changed", return_value=True),
                patch.object(guardian, "_has_contact_point_data_changed", return_value=False),
                patch.object(guardian, "_has_billing_contact_data_changed", return_value=False),
                patch.object(guardian, "_ensure_guardian_portal_routing") as ensure_portal_routing,
                patch.object(guardian, "sync_contact_points_for_linked_students") as sync_contact_points,
                patch.object(guardian, "sync_account_holder_billing_contacts") as sync_billing_contacts,
            ):
                guardian.on_update()

        ensure_portal_routing.assert_called_once_with("guardian@example.com")
        sync_contact_points.assert_not_called()
        sync_billing_contacts.assert_not_called()

    def test_on_update_syncs_contact_points_when_guardian_contact_data_changes(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.user = "guardian@example.com"

            with (
                patch.object(guardian, "_has_user_changed", return_value=False),
                patch.object(guardian, "_has_contact_point_data_changed", return_value=True),
                patch.object(guardian, "_has_billing_contact_data_changed", return_value=False),
                patch.object(guardian, "_ensure_guardian_portal_routing") as ensure_portal_routing,
                patch.object(guardian, "sync_contact_points_for_linked_students") as sync_contact_points,
                patch.object(guardian, "sync_account_holder_billing_contacts") as sync_billing_contacts,
            ):
                guardian.on_update()

        ensure_portal_routing.assert_not_called()
        sync_contact_points.assert_called_once_with()
        sync_billing_contacts.assert_not_called()

    def test_on_update_syncs_account_holder_billing_contacts_when_identity_changes(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.user = "guardian@example.com"

            with (
                patch.object(guardian, "_has_user_changed", return_value=False),
                patch.object(guardian, "_has_contact_point_data_changed", return_value=False),
                patch.object(guardian, "_has_billing_contact_data_changed", return_value=True),
                patch.object(guardian, "_ensure_guardian_portal_routing") as ensure_portal_routing,
                patch.object(guardian, "sync_contact_points_for_linked_students") as sync_contact_points,
                patch.object(guardian, "sync_account_holder_billing_contacts") as sync_billing_contacts,
            ):
                guardian.on_update()

        ensure_portal_routing.assert_not_called()
        sync_contact_points.assert_not_called()
        sync_billing_contacts.assert_called_once_with()

    def test_sync_contact_points_for_linked_students_uses_linked_student_schools(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.name = "GRD-0001"
            guardian.guardian_email = "guardian@example.com"
            guardian.guardian_mobile_phone = "+66 812 345 678"
            guardian.organization = "ORG-1"

            def fake_get_all(doctype, filters=None, fields=None, limit=None):
                if doctype == "Student Guardian":
                    return [{"parent": "STU-0001"}]
                if doctype == "Guardian Student":
                    return [{"student": "STU-0002"}]
                if doctype == "Student":
                    return [{"anchor_school": "SCH-1"}, {"anchor_school": "SCH-2"}]
                return []

            guardian_module.frappe.get_all = fake_get_all
            sync_calls: list[dict] = []
            contact_privacy = ModuleType("ifitwala_ed.contacts.contact_privacy")

            def fake_sync(guardian_doc, **kwargs):
                sync_calls.append({"guardian": guardian_doc.name, **kwargs})
                return [f"CCP-{kwargs['school']}"]

            contact_privacy.sync_guardian_contact_points = fake_sync

            with patch.dict(sys.modules, {"ifitwala_ed.contacts.contact_privacy": contact_privacy}):
                synced = guardian.sync_contact_points_for_linked_students()

        self.assertEqual(synced, ["CCP-SCH-1", "CCP-SCH-2"])
        self.assertEqual(
            sync_calls,
            [
                {
                    "guardian": "GRD-0001",
                    "school": "SCH-1",
                    "purpose": "school_communication",
                    "workflow": "guardian_linked_student_contact_point_sync",
                },
                {
                    "guardian": "GRD-0001",
                    "school": "SCH-2",
                    "purpose": "school_communication",
                    "workflow": "guardian_linked_student_contact_point_sync",
                },
            ],
        )

    def test_create_guardian_user_endpoint_rejects_unwritable_guardian(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.name = "GRD-0001"
            guardian_module.frappe.db.exists = lambda doctype, name=None: doctype == "Guardian" and name == "GRD-0001"
            guardian_module.frappe.get_doc = lambda doctype, name: guardian
            guardian_module.frappe.has_permission = lambda *args, **kwargs: False

            with self.assertRaises(guardian_module.frappe.PermissionError):
                guardian_module.create_guardian_user("GRD-0001")
