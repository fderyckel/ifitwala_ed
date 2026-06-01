# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_settings/test_school_settings_utils.py

from unittest import TestCase
from unittest.mock import patch

try:
    import frappe  # noqa: F401
except ModuleNotFoundError:
    import sys
    import types
    from types import SimpleNamespace

    def _decorator(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def wrapper(fn):
            return fn

        return wrapper

    frappe_stub = types.ModuleType("frappe")
    frappe_stub.ValidationError = Exception
    frappe_stub.whitelist = _decorator
    frappe_stub.validate_and_sanitize_search_inputs = _decorator
    frappe_stub.defaults = SimpleNamespace(get_user_default=lambda *args, **kwargs: None)
    frappe_stub.session = SimpleNamespace(user="test@example.com")
    frappe_stub.db = SimpleNamespace(get_value=lambda *args, **kwargs: None)
    frappe_stub.cache = lambda: SimpleNamespace(
        get_value=lambda *args, **kwargs: None,
        set_value=lambda *args, **kwargs: None,
        get_keys=lambda *args, **kwargs: [],
        delete_value=lambda *args, **kwargs: None,
    )
    frappe_stub.get_roles = lambda *args, **kwargs: []

    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.getdate = lambda value=None: value

    frappe_nestedset = types.ModuleType("frappe.utils.nestedset")
    frappe_nestedset.get_ancestors_of = lambda *args, **kwargs: []
    frappe_nestedset.get_descendants_of = lambda *args, **kwargs: []

    sys.modules.setdefault("frappe", frappe_stub)
    sys.modules.setdefault("frappe.utils", frappe_utils)
    sys.modules.setdefault("frappe.utils.nestedset", frappe_nestedset)

from ifitwala_ed.school_settings import school_settings_utils


class TestSchoolSettingsUtils(TestCase):
    @patch("ifitwala_ed.school_settings.school_settings_utils.get_ancestor_schools")
    @patch("ifitwala_ed.school_settings.school_settings_utils.get_user_base_school", return_value="SCH-BRANCH")
    @patch(
        "ifitwala_ed.school_settings.school_settings_utils.get_user_visible_schools",
        return_value=["SCH-BRANCH", "SCH-CHILD"],
    )
    def test_get_user_branch_school_scope_combines_descendants_and_ancestors(
        self,
        _mock_visible,
        _mock_base_school,
        mock_ancestors,
    ):
        mock_ancestors.return_value = ["SCH-BRANCH", "SCH-ROOT"]

        schools = school_settings_utils.get_user_branch_school_scope("admissions@example.com")

        self.assertEqual(schools, ["SCH-BRANCH", "SCH-CHILD", "SCH-ROOT"])

    @patch(
        "ifitwala_ed.school_settings.school_settings_utils.frappe.defaults.get_user_default", return_value="SCH-ROOT"
    )
    @patch("ifitwala_ed.school_settings.school_settings_utils.get_descendant_schools")
    def test_get_allowed_schools_expands_selected_parent_with_descendants_in_visible_scope(
        self,
        mock_descendants,
        _mock_default,
    ):
        mock_descendants.side_effect = lambda school: {
            "SCH-ROOT": ["SCH-ROOT", "SCH-PARENT", "SCH-CHILD"],
            "SCH-PARENT": ["SCH-PARENT", "SCH-CHILD", "SCH-OUTSIDE"],
        }[school]

        allowed = school_settings_utils.get_allowed_schools(
            user="staff@example.com",
            selected_school="SCH-PARENT",
        )

        self.assertEqual(allowed, ["SCH-PARENT", "SCH-CHILD"])

    @patch(
        "ifitwala_ed.school_settings.school_settings_utils.frappe.defaults.get_user_default", return_value="SCH-ROOT"
    )
    @patch("ifitwala_ed.school_settings.school_settings_utils.get_descendant_schools")
    def test_get_allowed_schools_rejects_out_of_scope_selection(
        self,
        mock_descendants,
        _mock_default,
    ):
        mock_descendants.side_effect = lambda school: {
            "SCH-ROOT": ["SCH-ROOT", "SCH-PARENT", "SCH-CHILD"],
            "SCH-SIBLING": ["SCH-SIBLING"],
        }[school]

        allowed = school_settings_utils.get_allowed_schools(
            user="staff@example.com",
            selected_school="SCH-SIBLING",
        )

        self.assertEqual(allowed, [])
