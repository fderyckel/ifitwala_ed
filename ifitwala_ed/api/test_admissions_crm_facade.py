# ifitwala_ed/api/test_admissions_crm_facade.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import admissions_crm


class TestAdmissionsCrmFacade(TestCase):
    def test_public_crm_methods_remain_whitelisted(self):
        methods = (
            admissions_crm.log_admission_message,
            admissions_crm.record_admission_crm_activity,
            admissions_crm.link_admission_conversation,
            admissions_crm.confirm_admission_external_identity,
            admissions_crm.create_admissions_intake,
            admissions_crm.assign_admission_conversation,
            admissions_crm.update_admission_conversation_status,
            admissions_crm.create_inquiry_from_admission_conversation,
            admissions_crm.assign_inquiry_from_inbox,
            admissions_crm.archive_inquiry_from_inbox,
            admissions_crm.mark_inquiry_contacted_from_inbox,
            admissions_crm.qualify_inquiry_from_inbox,
            admissions_crm.invite_inquiry_to_apply_from_inbox,
        )

        for method in methods:
            with self.subTest(method=method.__name__):
                self.assertIn(method, frappe.whitelisted)

    def test_inbox_assignment_delegates_to_domain_implementation(self):
        with patch(
            "ifitwala_ed.api.admissions_crm.assign_inquiry_from_inbox_impl",
            return_value={"inquiry": "INQ-1"},
        ) as impl:
            self.assertEqual(
                admissions_crm.assign_inquiry_from_inbox(
                    inquiry="INQ-1",
                    assigned_to="staff@example.com",
                    assignment_lane="Admissions",
                    client_request_id="REQ-1",
                ),
                {"inquiry": "INQ-1"},
            )

        impl.assert_called_once_with(
            inquiry="INQ-1",
            assigned_to="staff@example.com",
            assignment_lane="Admissions",
            client_request_id="REQ-1",
        )
