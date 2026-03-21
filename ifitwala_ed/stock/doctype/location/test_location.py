# Copyright (c) 2024, fdR and Contributors
# See license.txt

# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/stock/doctype/location/test_location.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.stock.doctype.location.location import Location, get_valid_parent_locations


class TestLocation(TestCase):
    @patch("ifitwala_ed.stock.doctype.location.location.frappe.db.sql")
    @patch(
        "ifitwala_ed.stock.doctype.location.location.get_location_scope",
        return_value=["LOC-PARENT", "LOC-CHILD"],
    )
    def test_capacity_validation_uses_location_subtree(
        self,
        _mock_scope,
        mock_sql,
    ):
        mock_sql.side_effect = [
            [{"name": "SG-1"}],
            [{"name": "SG-1", "active_count": 12}],
        ]

        doc = frappe._dict({"name": "LOC-PARENT", "maximum_capacity": 10})

        with self.assertRaises(frappe.ValidationError):
            Location.validate_capacity_against_groups(doc)

        query, params = mock_sql.call_args_list[0].args[:2]
        self.assertIn("sgs.location IN %(locations)s", query)
        self.assertEqual(params["locations"], ("LOC-PARENT", "LOC-CHILD"))

    @patch("ifitwala_ed.stock.doctype.location.location.frappe.get_all")
    @patch(
        "ifitwala_ed.stock.doctype.location.location.get_ancestor_schools",
        return_value=["Leaf School", "Parent School"],
    )
    def test_parent_location_query_uses_search_link_signature_and_scope_filters(
        self,
        _mock_ancestors,
        mock_get_all,
    ):
        mock_get_all.return_value = [
            frappe._dict({"name": "Bathroom Wing", "school": "Parent School"}),
            frappe._dict({"name": "Building Root", "school": None}),
            frappe._dict({"name": "Science Block", "school": "Sibling School"}),
        ]

        results = get_valid_parent_locations(
            "Location",
            "bath",
            "name",
            0,
            10,
            '{"organization":"Ifitwala Roots Campus","school":"Leaf School"}',
        )

        mock_get_all.assert_called_once_with(
            "Location",
            filters={"is_group": 1, "organization": "Ifitwala Roots Campus"},
            fields=["name", "school"],
            order_by="name asc",
        )
        self.assertEqual(results, [["Bathroom Wing"]])
