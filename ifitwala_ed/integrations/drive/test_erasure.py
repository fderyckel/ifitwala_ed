from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestDriveErasureIntegration(TestCase):
    def test_build_subject_file_erasure_decision_plan_uses_policy_without_legal_rules_in_code(self):
        with stubbed_frappe():
            module = import_fresh("ifitwala_ed.integrations.drive.erasure")

            decision_items = module.build_subject_file_erasure_decision_plan(
                [
                    {
                        "name": "DF-ERASE",
                        "purpose": "assessment_submission",
                        "retention_policy": "until_school_exit_plus_6m",
                        "legal_hold": 0,
                    },
                    {
                        "name": "DF-RETAIN",
                        "purpose": "safeguarding_evidence",
                        "retention_policy": "fixed_7y",
                        "legal_hold": 0,
                    },
                    {
                        "name": "DF-ANONYMIZE",
                        "purpose": "portfolio_export",
                        "retention_policy": "student_record",
                        "legal_hold": 0,
                    },
                    {
                        "name": "DF-HOLD",
                        "purpose": "assessment_submission",
                        "retention_policy": "until_school_exit_plus_6m",
                        "legal_hold": 1,
                    },
                ],
                school_policy={
                    "erase_retention_policies": ["until_school_exit_plus_6m"],
                    "retain_retention_policies": ["fixed_7y"],
                    "anonymize_retention_policies": ["student_record"],
                },
            )

        self.assertEqual(
            decision_items,
            [
                {
                    "drive_file_id": "DF-ERASE",
                    "decision": "erase",
                    "reason": "retention_policy:until_school_exit_plus_6m",
                },
                {
                    "drive_file_id": "DF-RETAIN",
                    "decision": "retain",
                    "reason": "retention_policy:fixed_7y",
                },
                {
                    "drive_file_id": "DF-ANONYMIZE",
                    "decision": "anonymize",
                    "reason": "retention_policy:student_record",
                },
                {
                    "drive_file_id": "DF-HOLD",
                    "decision": "retain",
                    "reason": "legal_hold",
                },
            ],
        )

    def test_create_subject_file_erasure_request_delegates_to_drive_request_api(self):
        calls = {}
        drive_erasure_api = types.ModuleType("ifitwala_drive.api.erasure")

        def _create_drive_erasure_request(**kwargs):
            calls["create"] = kwargs
            return {"erasure_request_id": "DER-0001", "status": "draft"}

        drive_erasure_api.create_drive_erasure_request = _create_drive_erasure_request

        with stubbed_frappe(
            {
                "ifitwala_drive": types.ModuleType("ifitwala_drive"),
                "ifitwala_drive.api": types.ModuleType("ifitwala_drive.api"),
                "ifitwala_drive.api.erasure": drive_erasure_api,
            }
        ):
            module = import_fresh("ifitwala_ed.integrations.drive.erasure")

            response = module.create_subject_file_erasure_request(
                data_subject_type="Student",
                data_subject_id="STU-0001",
                request_reason="Graduated and retention window complete",
            )

        self.assertEqual(response, {"erasure_request_id": "DER-0001", "status": "draft"})
        self.assertEqual(
            calls["create"],
            {
                "data_subject_type": "Student",
                "data_subject_id": "STU-0001",
                "scope": "files_only",
                "request_reason": "Graduated and retention window complete",
            },
        )

    def test_execute_subject_file_erasure_request_passes_metadata_and_decision_audit_to_drive(self):
        calls = {}
        drive_erasure_api = types.ModuleType("ifitwala_drive.api.erasure")

        def _execute_drive_erasure_request(**kwargs):
            calls["execute"] = kwargs
            return {"erasure_request_id": "DER-0001", "deleted_count": 1}

        drive_erasure_api.execute_drive_erasure_request = _execute_drive_erasure_request

        with stubbed_frappe(
            {
                "ifitwala_drive": types.ModuleType("ifitwala_drive"),
                "ifitwala_drive.api": types.ModuleType("ifitwala_drive.api"),
                "ifitwala_drive.api.erasure": drive_erasure_api,
            }
        ):
            module = import_fresh("ifitwala_ed.integrations.drive.erasure")

            response = module.execute_subject_file_erasure_request(
                erasure_request_id="DER-0001",
                metadata_filters={"organization": "ORG-0001", "school": "SCH-0001", "folder": "ignored"},
                decision_items=[
                    {"drive_file_id": "DF-0001", "decision": "delete", "reason": "retention_complete"},
                    {"slot": "student_log_evidence__row_1", "decision": "retain"},
                ],
            )

        self.assertEqual(response, {"erasure_request_id": "DER-0001", "deleted_count": 1})
        self.assertEqual(
            calls["execute"],
            {
                "erasure_request_id": "DER-0001",
                "metadata_filters": {"organization": "ORG-0001", "school": "SCH-0001"},
                "decision_items": [
                    {
                        "drive_file_id": "DF-0001",
                        "decision": "erase",
                        "reason": "retention_complete",
                    },
                    {
                        "slot": "student_log_evidence__row_1",
                        "decision": "retain",
                        "reason": "ed_decision_retain",
                    },
                ],
            },
        )
