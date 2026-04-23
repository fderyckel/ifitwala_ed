from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestWorkflowSpecsUnit(TestCase):
    def test_supporting_material_spec_uses_canonical_binding_role(self):
        with stubbed_frappe():
            module = import_fresh("ifitwala_ed.integrations.drive.workflow_specs")

            spec = module.get_upload_spec("supporting_material.file")

        self.assertEqual(spec.resolve_binding_role(None, {}), "supporting_material")
