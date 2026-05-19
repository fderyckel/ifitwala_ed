from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestContactAccessLogController(TestCase):
    def test_manual_insert_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh("ifitwala_ed.contacts.doctype.contact_access_log.contact_access_log")
            doc = module.ContactAccessLog.__new__(module.ContactAccessLog)
            doc.flags = {}

            with self.assertRaises(frappe.PermissionError):
                doc.before_insert()

    def test_edit_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh("ifitwala_ed.contacts.doctype.contact_access_log.contact_access_log")
            doc = module.ContactAccessLog.__new__(module.ContactAccessLog)
            doc.is_new = lambda: False

            with self.assertRaises(frappe.ValidationError):
                doc.before_save()

    def test_delete_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh("ifitwala_ed.contacts.doctype.contact_access_log.contact_access_log")
            doc = module.ContactAccessLog.__new__(module.ContactAccessLog)

            with self.assertRaises(frappe.ValidationError):
                doc.before_delete()
