from __future__ import annotations

import types
from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillGuardianContactLinks(TestCase):
    def test_execute_backfills_only_guardians_with_deterministic_contact_resolution(self):
        guardian_module = types.ModuleType("ifitwala_ed.students.doctype.guardian.guardian")

        class Guardian:
            pass

        guardian_module.Guardian = Guardian

        guardian_docs = {
            "GRD-USER": self._guardian_doc(Guardian),
            "GRD-EMAIL": self._guardian_doc(Guardian),
            "GRD-FALLBACK": self._guardian_doc(Guardian),
        }

        def table_exists(doctype: str) -> bool:
            return doctype in {"Guardian", "Contact", "Dynamic Link", "Contact Email"}

        def get_all(doctype: str, filters=None, fields=None, limit=None):
            if doctype == "Guardian":
                return [
                    {"name": "GRD-USER", "user": "user@example.com", "guardian_email": "user@example.com"},
                    {"name": "GRD-EMAIL", "user": "", "guardian_email": "email@example.com"},
                    {"name": "GRD-FALLBACK", "user": "fallback@example.com", "guardian_email": "fallback@example.com"},
                    {
                        "name": "GRD-AMB-USER",
                        "user": "ambiguous@example.com",
                        "guardian_email": "ambiguous@example.com",
                    },
                    {"name": "GRD-AMB-EMAIL", "user": "", "guardian_email": "duplicate@example.com"},
                    {"name": "GRD-NO-MATCH", "user": "", "guardian_email": "missing@example.com"},
                ]
            if doctype == "Contact":
                user = (filters or {}).get("user")
                if user == "user@example.com":
                    return [{"name": "CONTACT-USER"}]
                if user == "fallback@example.com":
                    return []
                if user == "ambiguous@example.com":
                    return [{"name": "CONTACT-A"}, {"name": "CONTACT-B"}]
                return []
            if doctype == "Contact Email":
                email = (filters or {}).get("email_id")
                if email == "email@example.com":
                    return [{"parent": "CONTACT-EMAIL"}]
                if email == "fallback@example.com":
                    return [{"parent": "CONTACT-FALLBACK"}]
                if email == "duplicate@example.com":
                    return [{"parent": "CONTACT-X"}, {"parent": "CONTACT-Y"}]
                return []
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        def get_doc(doctype: str, name: str):
            assert doctype == "Guardian"
            return guardian_docs[name]

        with stubbed_frappe(
            extra_modules={"ifitwala_ed.students.doctype.guardian.guardian": guardian_module}
        ) as frappe:
            frappe.db.table_exists = table_exists
            frappe.get_all = get_all
            frappe.get_doc = get_doc
            module = import_fresh("ifitwala_ed.patches.backfill_guardian_contact_links")

            module.execute()

        guardian_docs["GRD-USER"]._ensure_contact_link.assert_called_once_with("CONTACT-USER")
        guardian_docs["GRD-EMAIL"]._ensure_contact_link.assert_called_once_with("CONTACT-EMAIL")
        guardian_docs["GRD-FALLBACK"]._ensure_contact_link.assert_called_once_with("CONTACT-FALLBACK")

    def test_execute_returns_when_required_tables_are_missing(self):
        guardian_module = types.ModuleType("ifitwala_ed.students.doctype.guardian.guardian")

        class Guardian:
            pass

        guardian_module.Guardian = Guardian

        with stubbed_frappe(
            extra_modules={"ifitwala_ed.students.doctype.guardian.guardian": guardian_module}
        ) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_guardian_contact_links")

            module.execute()

    @staticmethod
    def _guardian_doc(guardian_class):
        doc = guardian_class()
        doc._ensure_contact_link = Mock()
        return doc
