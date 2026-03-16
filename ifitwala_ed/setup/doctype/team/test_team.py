# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.doctype.team import team as team_controller


class TestTeam(FrappeTestCase):
    def test_get_children_root_includes_visible_nodes_with_hidden_parent(self):
        all_visible = [
            frappe._dict(
                value="TEAM-CHILD",
                title="Child Team",
                expandable=0,
                parent_team="TEAM-OUTSIDE",
            ),
        ]

        with patch("ifitwala_ed.setup.doctype.team.team.frappe.get_all", return_value=all_visible):
            rows = team_controller.get_children("Team", parent="", is_root=True)

        self.assertEqual([row.get("value") for row in rows], ["TEAM-CHILD"])
        self.assertEqual(rows[0].get("expandable"), 0)

    def test_get_children_applies_supported_tree_filters(self):
        with patch("ifitwala_ed.setup.doctype.team.team.frappe.get_all", return_value=[]) as get_all:
            team_controller.get_children(
                "Team",
                parent="",
                is_root=True,
                filters={"organization": "ORG-001"},
                school="SCH-001",
            )

        get_all.assert_called_once()
        self.assertEqual(
            get_all.call_args.kwargs["filters"],
            {"organization": "ORG-001", "school": "SCH-001"},
        )

    def test_add_node_maps_virtual_root_to_empty_parent(self):
        doc = Mock()
        doc.name = "TEAM-001"

        with (
            patch(
                "frappe.desk.treeview.make_tree_args",
                return_value=frappe._dict(team_name="Leadership", parent="All Teams"),
            ),
            patch("ifitwala_ed.setup.doctype.team.team.frappe.get_doc", return_value=doc) as get_doc,
        ):
            result = team_controller.add_node()

        get_doc.assert_called_once_with(
            {
                "doctype": "Team",
                "team_name": "Leadership",
                "team_code": None,
                "is_group": 0,
                "organization": None,
                "school": None,
                "parent_team": None,
            }
        )
        doc.insert.assert_called_once_with()
        self.assertEqual(result, {"name": "TEAM-001"})
