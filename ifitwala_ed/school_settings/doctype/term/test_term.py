# Copyright (c) 2024, fdR and Contributors
# See license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

try:
    import frappe  # noqa: F401
except ModuleNotFoundError:
    import sys
    import types

    def _decorator(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def wrapper(fn):
            return fn

        return wrapper

    frappe_stub = types.ModuleType("frappe")
    frappe_stub.ValidationError = Exception
    frappe_stub._ = lambda value: value
    frappe_stub._dict = dict
    frappe_stub.whitelist = _decorator
    frappe_stub.validate_and_sanitize_search_inputs = _decorator
    frappe_stub.db = SimpleNamespace(
        escape=lambda value: f"'{value}'",
        get_value=lambda *args, **kwargs: None,
        get_list=lambda *args, **kwargs: [],
    )
    frappe_stub.defaults = SimpleNamespace(get_user_default=lambda *args, **kwargs: None)
    frappe_stub.session = SimpleNamespace(user="test@example.com")
    frappe_stub.cache = lambda: SimpleNamespace(
        get_value=lambda *args, **kwargs: None,
        set_value=lambda *args, **kwargs: None,
    )
    frappe_stub.get_roles = lambda *args, **kwargs: []
    frappe_stub.get_doc = lambda *args, **kwargs: SimpleNamespace(lft=0, rgt=0)
    frappe_stub.get_all = lambda *args, **kwargs: []

    frappe_model = types.ModuleType("frappe.model")
    frappe_document = types.ModuleType("frappe.model.document")

    class _Document:
        pass

    frappe_document.Document = _Document

    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.get_link_to_form = lambda *args, **kwargs: ""
    frappe_utils.getdate = lambda value=None: value
    frappe_utils.nowdate = lambda: "2026-03-25"

    frappe_nestedset = types.ModuleType("frappe.utils.nestedset")
    frappe_nestedset.get_ancestors_of = lambda *args, **kwargs: []
    frappe_nestedset.get_descendants_of = lambda *args, **kwargs: []

    sys.modules.setdefault("frappe", frappe_stub)
    sys.modules.setdefault("frappe.model", frappe_model)
    sys.modules.setdefault("frappe.model.document", frappe_document)
    sys.modules.setdefault("frappe.utils", frappe_utils)
    sys.modules.setdefault("frappe.utils.nestedset", frappe_nestedset)

from ifitwala_ed.school_settings.doctype.term import term


class TestTermPermissions(TestCase):
    @patch("ifitwala_ed.school_settings.doctype.term.term.frappe.get_roles", return_value=["Academic Admin"])
    @patch(
        "ifitwala_ed.school_settings.doctype.term.term.frappe.defaults.get_user_default",
        return_value="SCH-BRANCH",
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.term.term.get_descendant_schools",
        return_value=["SCH-BRANCH", "SCH-CHILD"],
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.term.term.get_schools_per_academic_year_for_terms",
        return_value=[("SCH-ROOT", "AY-2026"), ("SCH-BRANCH", "AY-2025")],
    )
    @patch("ifitwala_ed.school_settings.doctype.term.term.frappe.db.escape", side_effect=lambda value: f"'{value}'")
    def test_permission_query_conditions_include_parent_term_fallback_for_non_leaf_scope(
        self,
        _mock_escape,
        _mock_pairs,
        _mock_descendants,
        _mock_default,
        _mock_roles,
    ):
        condition = term.get_permission_query_conditions("staff@example.com")

        self.assertIn("`tabTerm`.`school` IN ('SCH-BRANCH', 'SCH-CHILD')", condition)
        self.assertIn("`tabTerm`.`school` = 'SCH-ROOT' AND `tabTerm`.`academic_year` = 'AY-2026'", condition)
        self.assertNotIn("AY-2025", condition)

    @patch("ifitwala_ed.school_settings.doctype.term.term.frappe.get_roles", return_value=["Academic Admin"])
    @patch(
        "ifitwala_ed.school_settings.doctype.term.term.frappe.defaults.get_user_default",
        return_value="SCH-BRANCH",
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.term.term.get_descendant_schools",
        return_value=["SCH-BRANCH", "SCH-CHILD"],
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.term.term.get_schools_per_academic_year_for_terms",
        return_value=[("SCH-ROOT", "AY-2026")],
    )
    def test_has_permission_allows_parent_term_fallback_for_non_leaf_scope(
        self,
        _mock_pairs,
        _mock_descendants,
        _mock_default,
        _mock_roles,
    ):
        doc = SimpleNamespace(school="SCH-ROOT", academic_year="AY-2026")

        self.assertTrue(term.has_permission(doc, user="staff@example.com"))

    @patch("ifitwala_ed.school_settings.doctype.term.term.frappe.get_roles", return_value=["Academic Admin"])
    @patch(
        "ifitwala_ed.school_settings.doctype.term.term.frappe.defaults.get_user_default",
        return_value="SCH-BRANCH",
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.term.term.get_descendant_schools",
        return_value=["SCH-BRANCH", "SCH-CHILD"],
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.term.term.get_schools_per_academic_year_for_terms",
        return_value=[("SCH-ROOT", "AY-2026")],
    )
    def test_has_permission_rejects_sibling_term_outside_visible_scope(
        self,
        _mock_pairs,
        _mock_descendants,
        _mock_default,
        _mock_roles,
    ):
        doc = SimpleNamespace(school="SCH-SIBLING", academic_year="AY-2026")

        self.assertFalse(term.has_permission(doc, user="staff@example.com"))
