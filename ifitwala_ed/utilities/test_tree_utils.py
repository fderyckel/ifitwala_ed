# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/utilities/test_tree_utils.py

from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from ifitwala_ed.utilities import tree_utils


class TestTreeUtils(TestCase):
    @patch("ifitwala_ed.utilities.tree_utils.frappe.get_all", return_value=["SCH-ROOT", "SCH-CHILD"])
    @patch("ifitwala_ed.utilities.tree_utils.frappe.get_doc", return_value=frappe._dict({"lft": 1, "rgt": 4}))
    @patch("ifitwala_ed.utilities.tree_utils.frappe.cache")
    def test_get_descendants_inclusive_uses_nestedset_bounds(
        self,
        cache_mock,
        _mock_doc,
        mock_get_all,
    ):
        cache = Mock()
        cache.get_value.return_value = None
        cache_mock.return_value = cache

        rows = tree_utils.get_descendants_inclusive("School", "SCH-ROOT")

        self.assertEqual(rows, ["SCH-ROOT", "SCH-CHILD"])
        mock_get_all.assert_called_once_with(
            "School",
            filters={"lft": (">=", 1), "rgt": ("<=", 4)},
            pluck="name",
        )

    @patch("ifitwala_ed.utilities.tree_utils.frappe.get_all", return_value=["ORG-ROOT"])
    @patch("ifitwala_ed.utilities.tree_utils.frappe.get_doc", return_value=frappe._dict({"lft": 2, "rgt": 3}))
    @patch("ifitwala_ed.utilities.tree_utils.frappe.cache")
    def test_get_ancestors_inclusive_uses_nestedset_bounds(
        self,
        cache_mock,
        _mock_doc,
        mock_get_all,
    ):
        cache = Mock()
        cache.get_value.return_value = None
        cache_mock.return_value = cache

        rows = tree_utils.get_ancestors_inclusive("Organization", "ORG-LEAF")

        self.assertEqual(rows, ["ORG-ROOT"])
        mock_get_all.assert_called_once_with(
            "Organization",
            filters={"lft": ("<=", 2), "rgt": (">=", 3)},
            pluck="name",
        )
