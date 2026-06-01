from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.assessment.api.test_gradebook import _gradebook_stub_modules
from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestGradebookFacade(TestCase):
    def test_root_gradebook_facade_reexports_assessment_endpoint_contract(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()):
            endpoints = import_fresh("ifitwala_ed.assessment.api.gradebook.endpoints")
            module = import_fresh("ifitwala_ed.api.gradebook")

        self.assertEqual(module.__all__, endpoints.__all__)
        for method_name in module.__all__:
            self.assertIs(getattr(module, method_name), getattr(endpoints, method_name))
            self.assertFalse(bool(getattr(getattr(module, method_name), "allow_guest", False)))

    def test_root_gradebook_facade_delegates_reads_to_assessment_impl(self):
        calls: dict[str, object] = {}

        with stubbed_frappe(extra_modules=_gradebook_stub_modules()):
            endpoints = import_fresh("ifitwala_ed.assessment.api.gradebook.endpoints")
            module = import_fresh("ifitwala_ed.api.gradebook")

            def fake_get_grid(api, filters=None, **kwargs):
                calls["api"] = api
                calls["filters"] = filters
                calls["kwargs"] = kwargs
                return {"deliveries": []}

            endpoints.gradebook_reads.get_grid = fake_get_grid

            payload = module.get_grid(filters={"school": "SCHOOL-1"}, limit=5)

        self.assertEqual(payload, {"deliveries": []})
        self.assertIs(calls["api"], endpoints.gradebook_support)
        self.assertEqual(calls["filters"], {"school": "SCHOOL-1"})
        self.assertEqual(calls["kwargs"], {"limit": 5})

    def test_root_gradebook_facade_delegates_writes_to_assessment_impl(self):
        calls: dict[str, object] = {}

        with stubbed_frappe(extra_modules=_gradebook_stub_modules()):
            endpoints = import_fresh("ifitwala_ed.assessment.api.gradebook.endpoints")
            module = import_fresh("ifitwala_ed.api.gradebook")

            def fake_save_draft(api, payload=None, **kwargs):
                calls["api"] = api
                calls["payload"] = payload
                calls["kwargs"] = kwargs
                return {"result": {"name": "CONTRIB-1"}}

            endpoints.gradebook_writes.save_draft = fake_save_draft

            payload = module.save_draft({"task_outcome": "OUT-1"}, autosave=True)

        self.assertEqual(payload, {"result": {"name": "CONTRIB-1"}})
        self.assertIs(calls["api"], endpoints.gradebook_support)
        self.assertEqual(calls["payload"], {"task_outcome": "OUT-1"})
        self.assertEqual(calls["kwargs"], {"autosave": True})

    def test_root_gradebook_facade_keeps_contribution_alias_on_assessment_endpoint(self):
        calls: dict[str, object] = {}

        with stubbed_frappe(extra_modules=_gradebook_stub_modules()):
            endpoints = import_fresh("ifitwala_ed.assessment.api.gradebook.endpoints")
            module = import_fresh("ifitwala_ed.api.gradebook")

            def fake_save_draft(api, payload=None, **kwargs):
                calls["api"] = api
                calls["payload"] = payload
                calls["kwargs"] = kwargs
                return {"result": {"name": "CONTRIB-2"}}

            endpoints.gradebook_writes.save_draft = fake_save_draft

            payload = module.save_contribution_draft(payload={"task_outcome": "OUT-2"}, autosave=True)

        self.assertEqual(payload, {"result": {"name": "CONTRIB-2"}})
        self.assertIs(calls["api"], endpoints.gradebook_support)
        self.assertEqual(calls["payload"], {"task_outcome": "OUT-2"})
        self.assertEqual(calls["kwargs"], {"autosave": True})
