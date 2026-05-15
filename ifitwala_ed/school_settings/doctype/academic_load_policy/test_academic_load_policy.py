# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_settings.doctype.academic_load_policy import academic_load_policy as policy_api


class TestAcademicLoadPolicy(FrappeTestCase):
    def test_ensure_default_policy_for_school_inserts_expected_defaults(self):
        inserted = {}

        class _FakeDoc:
            def __init__(self, payload):
                inserted.update(payload)
                self._payload = dict(payload)
                self.flags = type("Flags", (), {})()
                self.name = "POL-DEFAULT"

            def insert(self, ignore_permissions=False):
                inserted["ignore_permissions"] = ignore_permissions

            def get(self, key, default=None):
                return self._payload.get(key, default)

        original_get_doc = policy_api.frappe.get_doc

        def _fake_get_doc(*args, **kwargs):
            if len(args) == 1 and isinstance(args[0], dict) and args[0].get("doctype") == "Academic Load Policy":
                return _FakeDoc(args[0])
            return original_get_doc(*args, **kwargs)

        with (
            patch.object(policy_api.frappe.db, "get_value", return_value=None),
            patch.object(policy_api.frappe, "get_doc", side_effect=_fake_get_doc),
        ):
            name = policy_api.ensure_default_policy_for_school("SCH-1", ignore_permissions=True)

        self.assertEqual(name, "POL-DEFAULT")
        self.assertEqual(inserted["doctype"], "Academic Load Policy")
        self.assertEqual(inserted["school"], "SCH-1")
        self.assertEqual(inserted["meeting_blend_mode"], "Blended Past + Future")
        self.assertEqual(inserted["ignore_permissions"], True)

    def test_invalidate_academic_load_cache_increments_version(self):
        cache = MagicMock()
        cache.get_value.return_value = 4

        with patch.object(policy_api.frappe, "cache", return_value=cache):
            policy_api.invalidate_academic_load_cache()

        cache.set_value.assert_called_once_with("ifitwala_ed:academic_load:version", 5)

    def test_permission_query_conditions_blocks_users_without_policy_roles(self):
        with patch.object(policy_api.frappe, "get_roles", return_value=["Instructor"]):
            self.assertEqual(policy_api.get_permission_query_conditions("teacher@example.com"), "1=0")
