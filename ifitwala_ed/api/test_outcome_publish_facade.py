from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestOutcomePublishFacade(TestCase):
    def test_root_outcome_publish_facade_delegates_publish(self):
        calls: dict[str, object] = {}

        with stubbed_frappe():
            module = import_fresh("ifitwala_ed.api.outcome_publish")

            def fake_publish_outcomes(payload=None, **kwargs):
                calls["payload"] = payload
                calls["kwargs"] = kwargs
                return {"outcomes": []}

            module._impl.publish_outcomes = fake_publish_outcomes

            payload = module.publish_outcomes(payload={"outcome_ids": ["OUT-1"]}, notify=True)

        self.assertEqual(payload, {"outcomes": []})
        self.assertEqual(calls["payload"], {"outcome_ids": ["OUT-1"]})
        self.assertEqual(calls["kwargs"], {"notify": True})

    def test_root_outcome_publish_facade_delegates_unpublish(self):
        calls: dict[str, object] = {}

        with stubbed_frappe():
            module = import_fresh("ifitwala_ed.api.outcome_publish")

            def fake_unpublish_outcomes(payload=None, **kwargs):
                calls["payload"] = payload
                calls["kwargs"] = kwargs
                return {"outcomes": []}

            module._impl.unpublish_outcomes = fake_unpublish_outcomes

            payload = module.unpublish_outcomes(payload={"outcome_ids": ["OUT-1"]}, notify=True)

        self.assertEqual(payload, {"outcomes": []})
        self.assertEqual(calls["payload"], {"outcome_ids": ["OUT-1"]})
        self.assertEqual(calls["kwargs"], {"notify": True})
