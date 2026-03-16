# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_settings/test_school_settings_utils.py

from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.school_settings import school_settings_utils


class TestSchoolSettingsUtils(TestCase):
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
