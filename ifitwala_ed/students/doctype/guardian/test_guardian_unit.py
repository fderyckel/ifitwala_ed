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
    def test_after_insert_still_links_contact_and_updates_portal_routing(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.user = "guardian@example.com"

            with (
                patch.object(guardian, "_get_or_create_contact", return_value="CONTACT-0001"),
                patch.object(guardian, "_ensure_contact_link") as ensure_contact_link,
                patch.object(guardian, "_ensure_guardian_portal_routing") as ensure_portal_routing,
            ):
                guardian.after_insert()

        ensure_contact_link.assert_called_once_with("CONTACT-0001")
        ensure_portal_routing.assert_called_once_with("guardian@example.com")

    def test_on_update_does_not_self_heal_missing_contact_link(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.user = "guardian@example.com"

            with (
                patch.object(guardian, "_find_contact_name") as find_contact_name,
                patch.object(guardian, "_ensure_contact_link") as ensure_contact_link,
                patch.object(guardian, "_has_user_changed", return_value=False),
                patch.object(guardian, "_ensure_guardian_portal_routing") as ensure_portal_routing,
            ):
                guardian.on_update()

        find_contact_name.assert_not_called()
        ensure_contact_link.assert_not_called()
        ensure_portal_routing.assert_not_called()

    def test_on_update_still_updates_portal_routing_when_user_changes(self):
        with _guardian_module() as guardian_module:
            guardian = guardian_module.Guardian.__new__(guardian_module.Guardian)
            guardian.user = "guardian@example.com"

            with (
                patch.object(guardian, "_find_contact_name") as find_contact_name,
                patch.object(guardian, "_ensure_contact_link") as ensure_contact_link,
                patch.object(guardian, "_has_user_changed", return_value=True),
                patch.object(guardian, "_ensure_guardian_portal_routing") as ensure_portal_routing,
            ):
                guardian.on_update()

        find_contact_name.assert_not_called()
        ensure_contact_link.assert_not_called()
        ensure_portal_routing.assert_called_once_with("guardian@example.com")
