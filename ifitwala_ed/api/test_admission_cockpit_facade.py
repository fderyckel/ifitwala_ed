# ifitwala_ed/api/test_admission_cockpit_facade.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import admission_cockpit


class TestAdmissionCockpitFacade(TestCase):
    def test_public_cockpit_methods_remain_whitelisted(self):
        methods = (
            admission_cockpit.get_or_create_admissions_cockpit_offer_plan,
            admission_cockpit.promote_admissions_cockpit_applicant,
            admission_cockpit.send_admissions_cockpit_offer,
            admission_cockpit.hydrate_admissions_cockpit_request,
            admission_cockpit.generate_admissions_cockpit_deposit_invoice,
            admission_cockpit.get_admissions_cockpit_data,
        )

        for method in methods:
            with self.subTest(method=method.__name__):
                self.assertIn(method, frappe.whitelisted)

    def test_cockpit_data_delegates_to_domain_implementation(self):
        with patch(
            "ifitwala_ed.api.admission_cockpit.get_admissions_cockpit_data_impl",
            return_value={"columns": []},
        ) as impl:
            self.assertEqual(
                admission_cockpit.get_admissions_cockpit_data(filters={"school": "SCH-1"}), {"columns": []}
            )

        impl.assert_called_once_with(filters={"school": "SCH-1"})
