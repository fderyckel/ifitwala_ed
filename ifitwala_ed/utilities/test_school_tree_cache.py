# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeCache:
    def __init__(self):
        self.data: dict[str, object] = {}

    def get_value(self, key: str):
        return self.data.get(key)

    def get_keys(self, pattern: str):
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [key for key in list(self.data.keys()) if key.startswith(prefix)]

    def set_value(self, key: str, value, expires_in_sec: int | None = None):
        self.data[key] = value

    def delete_value(self, key: str):
        self.data.pop(key, None)


class TestSchoolTreeCacheInvalidation(TestCase):
    def test_invalidate_school_tree_cache_clears_tree_prefixes(self):
        nestedset = types.ModuleType("frappe.utils.nestedset")
        nestedset.get_ancestors_of = lambda doctype, node: []
        nestedset.get_descendants_of = lambda doctype, node: []

        cache = _FakeCache()

        with stubbed_frappe(extra_modules={"frappe.utils.nestedset": nestedset}) as frappe:
            frappe.cache = lambda: cache
            frappe.validate_and_sanitize_search_inputs = lambda fn: fn
            module = import_fresh("ifitwala_ed.utilities.school_tree")

            cache.set_value("ifitwala_ed:school_tree:root_school", "SCH-ROOT")
            cache.set_value("ifitwala_ed:school_tree:ay_scope:SCH-1", ["SCH-1"])
            cache.set_value("tree:School:anc:SCH-1", ["SCH-1", "SCH-PARENT"])
            cache.set_value("tree:School:desc:SCH-1", ["SCH-1", "SCH-CHILD"])
            cache.set_value("tree:Organization:anc:ORG-1", ["ORG-1"])
            cache.set_value("unrelated:key", "keep")

            module.invalidate_school_tree_cache()

        self.assertNotIn("ifitwala_ed:school_tree:root_school", cache.data)
        self.assertNotIn("ifitwala_ed:school_tree:ay_scope:SCH-1", cache.data)
        self.assertNotIn("tree:School:anc:SCH-1", cache.data)
        self.assertNotIn("tree:School:desc:SCH-1", cache.data)
        self.assertIn("tree:Organization:anc:ORG-1", cache.data)
        self.assertIn("unrelated:key", cache.data)
