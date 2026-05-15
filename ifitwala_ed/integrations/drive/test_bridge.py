from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _DetectableLegacySpec:
    workflow_id = "legacy.detected"
    contract_version = "1"
    is_private = None

    def validate_finalize_context(self, upload_session_doc):
        return {
            "owner_doctype": getattr(upload_session_doc, "owner_doctype", None),
            "owner_name": getattr(upload_session_doc, "owner_name", None),
            "slot": getattr(upload_session_doc, "intended_slot", None),
        }

    def resolve_attached_field_override(self, upload_session_doc):
        return None

    def resolve_context_override(self, upload_session_doc, authoritative_context):
        return None

    def resolve_binding_role(self, upload_session_doc, authoritative_context):
        return None

    def run_post_finalize(self, upload_session_doc, created_file):
        raise AssertionError("legacy workflow detection should not run post-finalize")


class TestDriveBridgeFinalizeContract(TestCase):
    def _legacy_upload_session(self):
        return types.SimpleNamespace(
            upload_contract_json="",
            owner_doctype="Task Submission",
            owner_name="TSUB-0001",
            attached_doctype="Task Submission",
            attached_name="TSUB-0001",
            intended_primary_subject_type="Student",
            intended_primary_subject_id="STU-0001",
            intended_data_class="assessment",
            intended_purpose="assessment_submission",
            intended_retention_policy="until_school_exit_plus_6m",
            intended_slot="submission",
        )

    def test_resolve_finalize_contract_requires_persisted_workflow_metadata(self):
        with stubbed_frappe():
            bridge = import_fresh("ifitwala_ed.integrations.drive.bridge")
            if hasattr(bridge, "iter_upload_specs"):
                bridge.iter_upload_specs = lambda: (_DetectableLegacySpec(),)

            contract = bridge.resolve_finalize_contract(self._legacy_upload_session())

        self.assertIsNone(contract["workflow_id"])
        self.assertIsNone(contract["authoritative_context"])

    def test_run_post_finalize_does_not_detect_legacy_session_workflow(self):
        with stubbed_frappe():
            bridge = import_fresh("ifitwala_ed.integrations.drive.bridge")
            if hasattr(bridge, "iter_upload_specs"):
                bridge.iter_upload_specs = lambda: (_DetectableLegacySpec(),)
                bridge.get_upload_spec = lambda workflow_id: _DetectableLegacySpec()

            result = bridge.run_post_finalize(self._legacy_upload_session(), object())

        self.assertEqual(result, {})
