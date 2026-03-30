# Copyright (c) 2026, Contributors
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
    frappe_stub.whitelist = _decorator
    frappe_stub.db = SimpleNamespace(
        get_value=lambda *args, **kwargs: None,
    )
    frappe_stub.defaults = SimpleNamespace(get_user_default=lambda *args, **kwargs: None)
    frappe_stub.session = SimpleNamespace(user="test@example.com")
    frappe_stub.get_roles = lambda *args, **kwargs: []
    frappe_stub.get_doc = lambda *args, **kwargs: SimpleNamespace()

    frappe_model = types.ModuleType("frappe.model")
    frappe_document = types.ModuleType("frappe.model.document")

    class _Document:
        pass

    frappe_document.Document = _Document

    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.cstr = lambda value="": str(value)
    frappe_utils.get_link_to_form = lambda *args, **kwargs: ""
    frappe_utils.getdate = lambda value=None: value

    frappe_nestedset = types.ModuleType("frappe.utils.nestedset")
    frappe_nestedset.get_ancestors_of = lambda *args, **kwargs: []
    frappe_nestedset.get_descendants_of = lambda *args, **kwargs: []

    school_tree_stub = types.ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree_stub.get_ancestor_schools = lambda *args, **kwargs: []
    school_tree_stub.get_descendant_schools = lambda *args, **kwargs: []

    sys.modules.setdefault("frappe", frappe_stub)
    sys.modules.setdefault("frappe.model", frappe_model)
    sys.modules.setdefault("frappe.model.document", frappe_document)
    sys.modules.setdefault("frappe.utils", frappe_utils)
    sys.modules.setdefault("frappe.utils.nestedset", frappe_nestedset)
    sys.modules.setdefault("ifitwala_ed.utilities.school_tree", school_tree_stub)

from ifitwala_ed.school_settings.doctype.academic_year import academic_year


class TestAcademicYearPermissions(TestCase):
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.frappe.get_roles",
        return_value=["Curriculum Coordinator"],
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.frappe.defaults.get_user_default",
        return_value="SCH-BRANCH",
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.get_descendant_schools",
        return_value=["SCH-BRANCH", "SCH-LEAF"],
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.get_ancestor_schools",
        return_value=["SCH-BRANCH", "SCH-ROOT"],
    )
    def test_permission_query_conditions_include_ancestor_school_visibility_for_branch_users(
        self,
        _mock_ancestors,
        _mock_descendants,
        _mock_default,
        _mock_roles,
    ):
        condition = academic_year.get_permission_query_conditions("staff@example.com")

        self.assertEqual(
            condition,
            "`tabAcademic Year`.`school` IN ('SCH-BRANCH', 'SCH-LEAF', 'SCH-ROOT')",
        )

    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.frappe.get_roles",
        return_value=["Curriculum Coordinator"],
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.frappe.defaults.get_user_default",
        return_value="SCH-BRANCH",
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.get_descendant_schools",
        return_value=["SCH-BRANCH", "SCH-LEAF"],
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.get_ancestor_schools",
        return_value=["SCH-BRANCH", "SCH-ROOT"],
    )
    def test_has_permission_allows_ancestor_school_year_for_branch_user(
        self,
        _mock_ancestors,
        _mock_descendants,
        _mock_default,
        _mock_roles,
    ):
        doc = SimpleNamespace(school="SCH-ROOT")

        self.assertTrue(academic_year.has_permission(doc, user="staff@example.com"))

    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.frappe.get_roles",
        return_value=["Curriculum Coordinator"],
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.frappe.defaults.get_user_default",
        return_value="SCH-BRANCH",
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.get_descendant_schools",
        return_value=["SCH-BRANCH", "SCH-LEAF"],
    )
    @patch(
        "ifitwala_ed.school_settings.doctype.academic_year.academic_year.get_ancestor_schools",
        return_value=["SCH-BRANCH", "SCH-ROOT"],
    )
    def test_has_permission_rejects_sibling_school_year_outside_branch(
        self,
        _mock_ancestors,
        _mock_descendants,
        _mock_default,
        _mock_roles,
    ):
        doc = SimpleNamespace(school="SCH-SIBLING")

        self.assertFalse(academic_year.has_permission(doc, user="staff@example.com"))
