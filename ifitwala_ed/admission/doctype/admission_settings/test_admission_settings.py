# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAdmissionSettings(FrappeTestCase):
    def test_admission_settings_is_single(self):
        self.assertEqual(frappe.get_meta("Admission Settings").issingle, 1)

    def test_admission_settings_get_and_set(self):
        settings = frappe.get_single("Admission Settings")
        original_sla = settings.sla_enabled

        frappe.db.set_single_value("Admission Settings", "sla_enabled", 1)

        updated_settings = frappe.get_single("Admission Settings")
        self.assertEqual(updated_settings.sla_enabled, 1)

        frappe.db.set_single_value("Admission Settings", "sla_enabled", original_sla)
